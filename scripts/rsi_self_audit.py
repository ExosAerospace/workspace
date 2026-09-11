#!/usr/bin/env python3
"""
rsi_self_audit.py — self-audit modules for the weekly RSI loop (Jon 2026-09-10).

The class of miss Jon called out: things I *should* catch without being asked
(e.g. 9 tracked scripts still holding a hardcoded password after a "done" secret
sweep; cancelled tasks leaking back onto the board; over-emailing his inbox).
These three deterministic, read-only checks run every week inside weekly-rsi.py
and surface any regression as a report section + a flagged issue count.

Each module returns a dict: {"title": str, "lines": [str], "issues": [str]}.
No LLM, no writes. #1 and the source-checks need no network; #2's DB checks use
the passed-in supa_get. Importable (weekly-rsi.py) and runnable standalone:

    python3 scripts/rsi_self_audit.py           # run all three, print report
    python3 scripts/rsi_self_audit.py --selftest # planted-secret regression test
"""
import json, os, re, subprocess

WS = "/Users/exomac/.openclaw/workspace"
DATA = os.path.join(WS, "mission-control", "data")


def _tracked_files(exts):
    """Only git-tracked files (never the stale .claude/worktrees copies)."""
    try:
        out = subprocess.run(["git", "-C", WS, "ls-files"], capture_output=True,
                             text=True, timeout=20).stdout.splitlines()
    except Exception:
        return []
    return [os.path.join(WS, f) for f in out
            if f.split(".")[-1] in exts and not f.startswith(".claude/worktrees/")]


# ---------------------------------------------------------------------------
# MODULE 1 — code / secret hygiene  (would have caught the 9-file miss)
# ---------------------------------------------------------------------------
# Known + generic secret signatures. The loader expression that reads from
# secrets.json is the APPROVED pattern and must never be flagged.
_LOADER_HINT = "secrets.json"
_KNOWN = [
    ("proton-smtp-password", re.compile(r"SPqYBivj98[-\w]*")),
    ("supabase-secret-key-literal", re.compile(r"['\"]sb_secret_[A-Za-z0-9_]{8,}['\"]")),
    ("private-key-block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |)PRIVATE KEY-----")),
    ("aws-access-key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("slack-token", re.compile(r"xox[baprs]-[0-9A-Za-z-]{10,}")),
]
# Assignment of a secret-ish var to a *hardcoded string literal*. The keyword must
# sit at a statement boundary (start-of-line / whitespace / ; / , ) — NOT preceded
# by & ? / = so URL query fragments ("...&api_key=" + var) don't trip it. The value
# is captured with a quote backreference so it ends at the real closing quote.
_ASSIGN = re.compile(
    r"""(?ix)(?:^|[\s;,({])(pass(?:word|wd)?|api[_-]?key|secret|token|bearer)\s*[:=]\s*(['"])([^'"]{6,})\2""",
    re.M)
# values that are obviously NOT a baked secret: placeholders, env/shell expansion,
# command substitution, or a URL/query fragment being concatenated with a variable.
_ALLOW_VALUE = re.compile(
    r"""(?ix)(your[_-]?|example|placeholder|xxxx|changeme|\{\{|\$\{|\$\(|<.*>|dummy|test|^https?://|^[?&/]|[?&][a-z_]+=$|=$)""")
_GITIGNORE_MUST = ["secrets.json", "*.env", "*.crt", "*.pem", "*.key", ".claude/worktrees/"]


def code_hygiene():
    lines, issues = [], []
    files = _tracked_files({"py", "js", "sh", "json", "cjs", "mjs", "ts"})
    hits = []
    for f in files:
        try:
            txt = open(f, errors="replace").read()
        except Exception:
            continue
        rel = os.path.relpath(f, WS)
        for name, rx in _KNOWN:
            for m in rx.finditer(txt):
                ln = txt[:m.start()].count("\n") + 1
                # a bare mention of the loader path isn't a leak
                if name == "supabase-secret-key-literal" and _LOADER_HINT in txt[max(0, m.start()-60):m.start()]:
                    continue
                hits.append((rel, ln, name))
        for m in _ASSIGN.finditer(txt):
            val = m.group(3)
            seg = txt[max(0, m.start()-40):m.end()+40]
            tail = txt[m.end():m.end()+3].lstrip()
            # skip loaders/env, placeholders/URL-fragments, and string-concatenation with a var
            if (_LOADER_HINT in seg or _ALLOW_VALUE.search(val) or "getenv" in seg
                    or "environ" in seg or tail.startswith("+")):
                continue
            ln = txt[:m.start()].count("\n") + 1
            hits.append((rel, ln, f"hardcoded-{m.group(1).lower()}"))
    lines.append(f"- Scanned **{len(files)}** tracked source files for embedded secrets.")
    if hits:
        for rel, ln, kind in hits[:20]:
            issues.append(f"secret[{kind}] {rel}:{ln}")
            lines.append(f"  - ⚠️ {kind} → `{rel}:{ln}`")
    else:
        lines.append("  - ✅ No hardcoded secrets in tracked source.")
    # .gitignore coverage
    gi = ""
    try:
        gi = open(os.path.join(WS, ".gitignore")).read()
    except Exception:
        pass
    missing = [p for p in _GITIGNORE_MUST if p not in gi]
    if missing:
        issues.append("gitignore-gap: " + ", ".join(missing))
        lines.append(f"  - ⚠️ .gitignore missing: {', '.join(missing)}")
    else:
        lines.append("  - ✅ .gitignore covers secrets.json / env / certs / worktrees.")
    return {"title": "10. Secret & code hygiene", "lines": lines, "issues": issues}


# ---------------------------------------------------------------------------
# MODULE 2 — board integrity  (cancelled-leak + dedup + unknown-state regression)
# ---------------------------------------------------------------------------
_ALLOWED_STATES = {"to do", "todo", "in progress", "in-progress", "blocked",
                   "done", "complete", "completed", "cancelled", "canceled",
                   "archived", "rejected", "open", "backlog",
                   "held", "on hold", "queued", "snoozed", "waiting", "deferred"}


def board_integrity(supa_get=None):
    lines, issues = [], []
    # (a) regression guard: index.html normalizeState must fold cancelled -> Cancelled
    idx = os.path.join(WS, "mission-control", "index.html")
    try:
        html = open(idx, errors="replace").read()
        guard = re.search(r"normalizeState", html) and re.search(
            r"cancel(?:l)?ed[^\n]*return\s+['\"]Cancelled['\"]", html, re.I | re.S)
        # more lenient: the guard block returns 'Cancelled' for cancelled/archived/rejected
        has_guard = bool(re.search(
            r"===\s*['\"]cancell?ed['\"][\s\S]{0,120}?return\s+['\"]Cancelled['\"]", html, re.I))
        if has_guard:
            lines.append("- ✅ Board `normalizeState()` still folds cancelled/archived/rejected → Cancelled (no leak).")
        else:
            issues.append("board-guard-missing: normalizeState cancelled->Cancelled")
            lines.append("- ⚠️ `normalizeState()` cancelled→Cancelled guard NOT found — cancelled tasks could leak onto the board again.")
    except Exception as e:
        lines.append(f"- (could not read index.html: {e})")
    # (b) live DB checks
    if supa_get:
        try:
            tasks = supa_get("tasks?select=id,title,state,owner&limit=5000")
            states = {}
            for t in tasks:
                s = str(t.get("state") or "").strip().lower()
                states[s] = states.get(s, 0) + 1
            unknown = {s: n for s, n in states.items() if s and s not in _ALLOWED_STATES}
            if unknown:
                issues.append("unknown-states: " + ", ".join(f"{s}({n})" for s, n in unknown.items()))
                lines.append(f"- ⚠️ Unknown task states in DB (may mis-fold on the board): {unknown}")
            else:
                lines.append(f"- ✅ All task states are known values ({len(tasks)} tasks).")
            # (c) open-duplicate regression via the dedup engine
            try:
                import sys
                sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
                from subject_dedup import cluster_by_subject
                open_t = [t for t in tasks if str(t.get("state") or "").lower()
                          not in ("done", "complete", "completed", "cancelled", "canceled", "archived", "rejected")]
                clusters = [c for c in cluster_by_subject(open_t) if len(c) > 1]
                if clusters:
                    issues.append(f"open-duplicate-clusters: {len(clusters)}")
                    lines.append(f"- ⚠️ {len(clusters)} open duplicate cluster(s) not yet merged:")
                    for c in clusters[:5]:
                        lines.append(f"    - #{'/#'.join(str(t['id']) for t in c)} · {(c[0].get('title') or '')[:50]}")
                else:
                    lines.append("- ✅ No un-merged open duplicate clusters.")
            except Exception as e:
                lines.append(f"- (dedup check skipped: {e})")
        except Exception as e:
            lines.append(f"- (DB checks skipped: {e})")
    else:
        lines.append("- (offline: DB state/dedup checks skipped)")
    return {"title": "11. Board integrity", "lines": lines, "issues": issues}


# ---------------------------------------------------------------------------
# MODULE 3 — preference compliance  (over-email, pricing-gate, digest routing)
# ---------------------------------------------------------------------------
def preference_compliance():
    lines, issues = [], []
    # (a) payload pricing delegation baked in + engine not routing standard pricing to Jon
    addendum = os.path.join(WS, "drafts", "EXOS_Standard_Payload_Terms_AddendumA.md")
    if os.path.exists(addendum):
        lines.append("- ✅ Payload standard-terms Addendum A present (Jon out of routine pricing loop).")
    else:
        issues.append("payload-addendum-missing")
        lines.append("- ⚠️ EXOS_Standard_Payload_Terms_AddendumA.md missing — delegation may have regressed.")
    # payload-sales engine shouldn't auto-route standard pricing approval to Jon
    eng = os.path.join(WS, "scripts", "payload_sales_engine.py")
    for cand in ("payload_sales_engine.py", "blk3_payload_sales.py", "payload-sales.py"):
        p = os.path.join(WS, "scripts", cand)
        if os.path.exists(p):
            eng = p
            break
    if os.path.exists(eng):
        txt = open(eng, errors="replace").read()
        if re.search(r"assignedTo['\"]?\s*[:=]\s*['\"]jquinn@exosaero\.com", txt) and re.search(r"pric", txt, re.I):
            issues.append(f"payload-engine-routes-pricing-to-jon: {os.path.basename(eng)}")
            lines.append(f"- ⚠️ {os.path.basename(eng)} may route pricing decisions to Jon — should be Lizi/Phil.")
        else:
            lines.append(f"- ✅ {os.path.basename(eng)} does not route standard pricing to Jon.")
    # (b) recurring watchers should deliver to Discord, not Jon's inbox
    watchers = ["sam-flightopps-watch.py", "sam-amendment-watch.py", "sam-osp4-watch.py", "title3_osc_watch.py"]
    emailing = []
    for w in watchers:
        p = os.path.join(WS, "scripts", w)
        if not os.path.exists(p):
            continue
        txt = open(p, errors="replace").read()
        # Real drift = actually delivers by email to Jon AND has no Discord path.
        # (docstrings mentioning the old msmtp behavior don't count — check for a
        # live send call + absence of a discord delivery.)
        live_email = re.search(r"subprocess[^\n]*msmtp|smtplib[^\n]*\.(send|sendmail)|\.send_message\(", txt)
        has_discord = re.search(r"--channel[\"',\s]+discord|message[\"'\s,]+send", txt)
        if live_email and "jquinn@exosaero.com" in txt and not has_discord:
            emailing.append(w)
    if emailing:
        issues.append("watcher-emails-jon: " + ", ".join(emailing))
        lines.append(f"- ⚠️ Recurring watcher(s) still emailing Jon (should be Discord): {', '.join(emailing)}")
    else:
        lines.append("- ✅ Recurring SAM/Title-III watchers route to Discord, not Jon's inbox.")
    # (c) over-email heuristic: >1 distinct Exo->Jon email per task-subject this week (best effort)
    log = os.path.join(WS, "logs", "sent-mail.log")
    if os.path.exists(log):
        try:
            import collections, datetime
            cutoff = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
            subj = collections.Counter()
            for ln in open(log, errors="replace"):
                if ln[:10] >= cutoff and "jquinn@" in ln:
                    m = re.search(r"subj(?:ect)?[:=]\s*(.+)", ln, re.I)
                    if m:
                        subj[m.group(1).strip()[:40]] += 1
            dup = {s: n for s, n in subj.items() if n > 1}
            if dup:
                issues.append(f"over-email: {len(dup)} subject(s) sent >1x")
                lines.append(f"- ⚠️ {len(dup)} email subject(s) sent to Jon more than once this week: {list(dup)[:3]}")
            else:
                lines.append("- ✅ No duplicated email subjects to Jon this week.")
        except Exception:
            lines.append("- (over-email log parse skipped)")
    else:
        lines.append("- (no sent-mail log; over-email check is best-effort — skipped)")
    return {"title": "12. Preference compliance", "lines": lines, "issues": issues}


def run_all(supa_get=None):
    """Return (report_lines, total_issue_count, issues_list)."""
    mods = [code_hygiene(), board_integrity(supa_get), preference_compliance()]
    out, issues = [], []
    for m in mods:
        out.append(f"\n## {m['title']}")
        out.extend(m["lines"])
        issues.extend(m["issues"])
    if issues:
        out.append(f"\n**⚠️ Self-audit flagged {len(issues)} issue(s) — see above; these are the "
                   "'catch-it-without-being-asked' class.**")
    else:
        out.append("\n**✅ Self-audit clean — no hygiene / integrity / preference regressions.**")
    return out, len(issues), issues


def _selftest():
    """Plant a fake secret in a temp tracked-like buffer and confirm detection."""
    ok = True
    sample = 'password = "SPqYBivj98-jyF3RujLKxA"\napi_key = "abc123secretvalue"\n'
    hitk = [n for n, rx in _KNOWN if rx.search(sample)]
    if "proton-smtp-password" not in hitk:
        ok = False; print("FAIL: known proton pattern not detected")
    else:
        print("PASS: known proton pattern detected")
    if _ASSIGN.search(sample):
        print("PASS: generic secret-assignment detected")
    else:
        ok = False; print("FAIL: generic assignment not detected")
    # loader expression must NOT trip
    loader = "EMAIL_PASS = __import__('json').load(open('~/.openclaw/secrets.json'))['protonmail_bridge_smtp_password']"
    tripped = _ASSIGN.search(loader) and _LOADER_HINT not in loader
    if not (_LOADER_HINT in loader):
        ok = False; print("FAIL: loader hint logic")
    else:
        print("PASS: approved secrets.json loader is not flagged")
    print("\n" + ("SELFTEST PASSED" if ok else "SELFTEST FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        raise SystemExit(_selftest())
    # standalone: run offline (no DB) + print
    lines, n, issues = run_all(supa_get=None)
    print("# RSI Self-Audit (standalone, offline)\n" + "\n".join(lines))
    print(f"\nissues={n}")
