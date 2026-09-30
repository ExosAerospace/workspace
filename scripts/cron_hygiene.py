#!/usr/bin/env python3
"""
cron_hygiene.py — deterministic exo3 guards over the OpenClaw cron store (r2-cron-hygiene, 2026-09-29).

Read-only. Never edits a cron, never prints a secret value (only secret NAMES / pattern kinds).
Wired into agent_eval.py (hourly) as the "cron-hygiene" checks; also runnable by hand.

Checks
  1. SECRETS IN PROMPTS (FAIL): any cron job (enabled or disabled) whose stored job JSON contains
     a known secret value or a literal-credential pattern.
       - known values: every string in ~/.openclaw/secrets.json (len >= 12), every file in
         ~/.config/exos/ (whole-file value + KEY=VALUE values), mission-control/data/.decisions-token.
         Compared by SHA-256 of candidate tokens cut from the prompt; the values themselves are
         hashed at load and discarded.
       - patterns: pass/password = literal, token/api_key/secret = literal, Bearer literal, JWT,
         Supabase sb_* key, sk-* key, literal X-Exo-Token header.
  2. MODEL ALLOWLIST (FAIL): an ENABLED agentTurn cron whose payload.model is not in
     ~/.openclaw/openclaw.json agents.defaults.models (the gateway preflight rejects it -> the
     cron never runs; SAM.gov renewal reminder, 9/11).
     Also WARN: an enabled anthropic/* or claude-cli/* cron that carries payload.toolsAllow
     (dies instantly: "CLI backend claude-cli cannot enforce runtime toolsAllow").
  3. TRANSIENT CRONS (WARN): a cron_run fleet event with registered:false that does not match the
     registry class "cron-class:transient-agent-reminder" (a one-shot that is gone from the store,
     i.e. self-deleted, or a live schedule kind "at" job with delete_after_run).

Usage:
  cron_hygiene.py            # scan the live store, print findings (names only), exit 1 on any FAIL
  cron_hygiene.py --selftest # fixtures only
"""
import glob, hashlib, json, os, re, sys, datetime

WS = "/Users/exomac/.openclaw/workspace"
SECRETS = os.path.expanduser("~/.openclaw/secrets.json")
EXOS_CFG_DIR = os.path.expanduser("~/.config/exos")
DECISIONS_TOKEN = os.path.join(WS, "mission-control", "data", ".decisions-token")
OPENCLAW_CFG = os.path.expanduser("~/.openclaw/openclaw.json")
EVENTS = os.path.join(WS, "logs", "fleet-events.jsonl")
TRANSIENT_CLASS = "cron-class:transient-agent-reminder"
sys.path.insert(0, os.path.join(WS, "scripts"))

# config values that are identifiers/hosts, not credentials (a domain list is not a secret)
NON_SECRET_KEY = re.compile(r"(host|url|uri|base|subdomain|_env$|cloud|realm_id|client_id|tenant_id|domain)", re.I)
SECRET_ENV_KEY = re.compile(r"(token|pass|secret|key|pw)", re.I)
_H = lambda s: hashlib.sha256(s.encode("utf-8", "ignore")).hexdigest()
_NOT_LITERAL = r"(?!<|\$\(|\$\{|\{|\[|read\b|see\b|from\b|the\b|your\b|none\b|null\b)"
PATTERNS = [
    ("password literal", re.compile(r"\bpass(?:word|wd)?\s*[:=]\s*" + _NOT_LITERAL + r"[^\s,)'\"]{6,}", re.I)),
    ("token/key literal", re.compile(r"\b(?:token|api[_-]?key|secret)\s*[:=]\s*[\"']?" + _NOT_LITERAL + r"[A-Za-z0-9._\-]{16,}", re.I)),
    ("bearer literal", re.compile(r"\bBearer\s+" + _NOT_LITERAL + r"[A-Za-z0-9._\-]{20,}")),
    ("JWT", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
    ("supabase key", re.compile(r"\bsb_(?:publishable|secret)_[A-Za-z0-9_-]{10,}")),
    ("sk- api key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}")),
    ("X-Exo-Token literal", re.compile(r"x-exo-token\s*:\s*" + _NOT_LITERAL + r"[A-Za-z0-9_-]{16,}", re.I)),
]


def load_secret_hashes(secrets_path=SECRETS, cfg_dir=EXOS_CFG_DIR, extra_files=(DECISIONS_TOKEN,)):
    """{sha256: secret NAME}. Values are hashed immediately and not kept."""
    out = {}
    def add(name, v):
        v = str(v or "").strip()
        if len(v) >= 12: out[_H(v)] = name
    try:
        for k, v in json.load(open(secrets_path)).items():
            if isinstance(v, (str, int)) and not NON_SECRET_KEY.search(k): add("secrets.json:" + k, v)
    except Exception:
        pass
    for f in sorted(glob.glob(os.path.join(cfg_dir, "*"))) + list(extra_files):
        try:
            txt = open(f).read()
        except Exception:
            continue
        base = os.path.basename(f)
        env = [ln for ln in txt.splitlines() if "=" in ln and not ln.lstrip().startswith("#")]
        if not env:
            add(base, txt)  # single-value secret file (bridge-studio.pw, *.token)
        for ln in env:
            k, v = ln.split("=", 1)
            if SECRET_ENV_KEY.search(k): add(base + ":" + k.strip(), v.strip().strip("'\""))
    return out


def _candidates(text):
    for piece in re.split(r"[\s'\"`()<>\[\]{},;|\\]+", text or ""):
        piece = piece.strip(".")
        if len(piece) < 12: continue
        yield piece
        for sub in re.split(r"[:=@/]", piece):
            sub = sub.strip(".")
            if len(sub) >= 12 and sub != piece: yield sub


def scan_text(text, hashes):
    """Sorted list of finding labels (secret names / pattern kinds). Never returns values."""
    found = set()
    for c in _candidates(text):
        n = hashes.get(_H(c))
        if n: found.add("known secret " + n)
    for kind, rx in PATTERNS:
        if rx.search(text or ""): found.add(kind)
    return sorted(found)


def load_jobs_full(db=None):
    import cron_telemetry, sqlite3
    con = cron_telemetry.connect(db or cron_telemetry.DB)
    try:
        con.row_factory = sqlite3.Row
        rows = con.execute("select job_id, name, enabled, schedule_kind, delete_after_run, payload_kind, "
                           "payload_model, payload_tools_allow_json, job_json from cron_jobs").fetchall()
        return {r["job_id"]: dict(r) for r in rows}
    finally:
        con.close()


def model_allowlist(path=OPENCLAW_CFG):
    try:
        return set((json.load(open(path)).get("agents", {}).get("defaults", {}).get("models") or {}).keys())
    except Exception:
        return None


def _job_model(job):
    m = job.get("payload_model")
    if m: return m
    try: return (json.loads(job.get("job_json") or "{}").get("payload") or {}).get("model")
    except Exception: return None


def _has_tools_allow(job):
    t = job.get("payload_tools_allow_json")
    if t not in (None, "", "null"): return True
    try: return "toolsAllow" in (json.loads(job.get("job_json") or "{}").get("payload") or {})
    except Exception: return False


def model_findings(job, allow):
    """(status, why) for one job. Only enabled agentTurn jobs with an explicit model are checked."""
    if not job.get("enabled") or job.get("payload_kind") != "agentTurn": return None
    m = _job_model(job)
    if allow is not None and m and m not in allow:
        return ("FAIL", "model %s not in agents.defaults.models allowlist (gateway rejects it; cron never runs)" % m)
    if m and (m.startswith("anthropic/") or m.startswith("claude-cli/")) and _has_tools_allow(job):
        return ("WARN", "anthropic/claude-cli cron carries payload.toolsAllow (claude-cli cannot enforce it; run dies) - run --clear-tools")
    return None


def transient_class_match(detail, live_jobs):
    """True if an unregistered cron run belongs to the registered transient one-shot class."""
    jid = (detail or {}).get("cron_id")
    j = live_jobs.get(jid)
    if j is None: return True  # gone from the store after running = self-deleting one-shot
    return j.get("schedule_kind") == "at" and bool(j.get("delete_after_run"))


def unregistered_run_events(since_ts, events_path=EVENTS):
    out = []
    try:
        lines = open(events_path, errors="ignore").read().splitlines()[-20000:]
    except Exception:
        return out
    for ln in lines:
        if '"cron_run"' not in ln or '"registered": false' not in ln: continue
        try:
            r = json.loads(ln)
            if datetime.datetime.fromisoformat(r["ts"]).timestamp() < since_ts: continue
        except Exception:
            continue
        out.append(r)
    return out


def check(now_s, window_h=26, jobs=None, hashes=None, allow="load", events=None):
    """[(label, status, why)] for agent_eval. Non-OK only. Never raises."""
    res = []
    try:
        jobs = load_jobs_full() if jobs is None else jobs
        hashes = load_secret_hashes() if hashes is None else hashes
        allow = model_allowlist() if allow == "load" else allow
        import cron_telemetry
        for jid, j in sorted(jobs.items(), key=lambda kv: kv[1].get("name") or ""):
            label = "cron:" + cron_telemetry.slug(j.get("name"))
            f = scan_text(j.get("job_json") or "", hashes)
            if f: res.append((label, "FAIL", "credential in cron prompt/job JSON: " + ", ".join(f) +
                              " (move to secrets store; value not shown)"))
            mf = model_findings(j, allow)
            if mf: res.append((label, mf[0], mf[1]))
        evs = unregistered_run_events(now_s - window_h * 3600) if events is None else events
        stray = {}
        for r in evs:
            d = r.get("detail") or {}
            if not transient_class_match(d, jobs):
                stray[r.get("agent") or d.get("cron_id")] = d.get("cron_id")
        for label, jid in sorted(stray.items()):
            res.append((label, "WARN", "unregistered cron ran (%s) and is not a self-deleting one-shot "
                        "(%s) - register it" % ((jid or "?")[:8], TRANSIENT_CLASS)))
    except Exception as e:
        res.append(("cron-hygiene", "WARN", "cron hygiene check skipped: %s" % e))
    return res


def selftest():
    import tempfile
    n = 0
    def ok(c, name):
        nonlocal n
        assert c, name
        n += 1
    fake = "Zq9" + "xY7-" + "wVb3Kp0Lm2Nn"  # built at runtime; never a real secret
    with tempfile.TemporaryDirectory() as td:
        sp = os.path.join(td, "s.json"); json.dump({"smtp_pw": fake, "short": "production"}, open(sp, "w"))
        cd = os.path.join(td, "cfg"); os.mkdir(cd)
        open(os.path.join(cd, "ha.token"), "w").write("tok" + "A" * 30 + "\n")
        open(os.path.join(cd, "vw.env"), "w").write("ADMIN_TOKEN='" + "B" * 20 + "'\nSIGNUPS_DOMAINS_WHITELIST=" + "c" * 14 + ".com\n")
        h = load_secret_hashes(sp, cd, ())
    ok(sorted(h.values()) == ["ha.token", "secrets.json:smtp_pw", "vw.env:ADMIN_TOKEN"], "hash load: long secret values only; env non-secret keys + host/domain config skipped")
    ok(fake not in json.dumps(h), "hash map holds no plaintext")
    ok(scan_text("pw is %s ok" % fake, h) == ["known secret secrets.json:smtp_pw"], "known value by hash")
    ok("known secret ha.token" in scan_text("-H Authorization:tok" + "A" * 30, h), "known value inside header token")
    ok("known secret vw.env:ADMIN_TOKEN" in scan_text("x " + "B" * 20, h), "env value")
    ok(scan_text("user: a@b.c, pass: Qw3rty-Ab9_zz, STARTTLS", {}) == ["password literal"], "password pattern (unknown value, e.g. old Mini pw)")
    ok("JWT" in scan_text("Token: eyJ" + "a" * 20 + ".eyJ" + "b" * 20 + "." + "c" * 20, {}), "JWT pattern")
    ok("X-Exo-Token literal" in scan_text("-H 'X-Exo-Token: " + "f" * 32 + "'", {}), "decisions token header")
    ok("supabase key" in scan_text("apikey sb_" + "publishable_" + "x" * 20, {}), "supabase key")
    clean = ("Token: read it at run time from /Users/exomac/.config/exos/home-assistant.token. "
             "curl -H \"Authorization: Bearer $(cat ~/.config/exos/home-assistant.token)\" "
             "-H \"x-exo-token: $(cat mission-control/data/.decisions-token)\" password read at run time; "
             "python3 scripts/send_email.py --to jquinnexo@pm.me --subject x")
    ok(scan_text(clean, h) == [], "run-time reads are not findings")
    allow = {"anthropic/claude-haiku-4-5", "ollama/qwen3.6:35b-a3b"}
    base = {"enabled": 1, "payload_kind": "agentTurn", "payload_tools_allow_json": None, "job_json": "{}"}
    ok(model_findings(dict(base, payload_model="anthropic/claude-haiku-4-5-20251001"), allow)[0] == "FAIL", "dated haiku id rejected (SAM 9/11 replay)")
    ok(model_findings(dict(base, payload_model="anthropic/claude-haiku-4-5"), allow) is None, "allowlisted model ok")
    ok(model_findings(dict(base, payload_model="anthropic/claude-haiku-4-5-20251001", enabled=0), allow) is None, "disabled skipped")
    ok(model_findings(dict(base, payload_model=None), allow) is None, "no override = default model ok")
    ok(model_findings(dict(base, payload_model="anthropic/claude-haiku-4-5", payload_tools_allow_json='["exec"]'), allow)[0] == "WARN", "anthropic + toolsAllow trap")
    ok(model_findings(dict(base, payload_model="ollama/qwen3.6:35b-a3b", payload_tools_allow_json='["exec"]'), allow) is None, "ollama + toolsAllow fine")
    live = {"rec": {"schedule_kind": "cron", "delete_after_run": 0}, "one": {"schedule_kind": "at", "delete_after_run": 1},
            "keep": {"schedule_kind": "at", "delete_after_run": 0}}
    ok(transient_class_match({"cron_id": "gone"}, live), "self-deleted one-shot matches class")
    ok(transient_class_match({"cron_id": "one"}, live), "live at+delete_after_run matches class")
    ok(not transient_class_match({"cron_id": "rec"}, live), "recurring unregistered does not match")
    ok(not transient_class_match({"cron_id": "keep"}, live), "kept one-shot does not match")
    evs = [{"agent": "cron:x", "detail": {"cron_id": "rec", "registered": False}},
           {"agent": "cron:y", "detail": {"cron_id": "gone", "registered": False}}]
    jobs = {"rec": dict(base, name="Rec", schedule_kind="cron", delete_after_run=0, payload_model=None,
                        job_json=json.dumps({"payload": {"message": "pass: Qw3rty-Ab9_zz"}}))}
    r = check(0, jobs=jobs, hashes={}, allow=allow, events=evs)
    ok(("cron:rec", "FAIL") in [(a, b) for a, b, _ in r] and "Qw3rty" not in json.dumps(r), "check(): FAIL without leaking value")
    ok([a for a, b, _ in r if b == "WARN"] == ["cron:x"], "check(): WARN only for the non-class unregistered run")
    print("cron_hygiene selftest: %d/%d pass" % (n, n))
    return 0


def main():
    if "--selftest" in sys.argv: return selftest()
    import time
    res = check(time.time())
    for label, st, why in res: print("%s: %s - %s" % (st, label, why))
    print("cron_hygiene: %d FAIL / %d WARN" % (sum(s == "FAIL" for _, s, _ in res), sum(s == "WARN" for _, s, _ in res)))
    return 1 if any(s == "FAIL" for _, s, _ in res) else 0


if __name__ == "__main__":
    sys.exit(main())
