#!/usr/bin/env python3
"""deadline-watch.py — actively re-verify external deadlines and prevent a stale-
sourced date from masquerading as "overdue."

The error this fixes: a task due-date set from an unreliable source (e.g. a stale
LinkedIn post) later reads as "OVERDUE" though the real deadline was different or
still open. This watcher re-checks each watched task's AUTHORITATIVE source URL and:
  - re-stamps `verified:` when the source still supports the stored date,
  - ALERTS (does not silently change) when the source shows a different date — a human
    confirms before the date moves, because trusting an unverified auto-source is the
    exact mistake we are preventing,
  - tags a task `date-unverified` when no firm deadline can be confirmed on the source,
    so an unconfirmed date is treated as "confirm" not "missed" — and nudges Jon when
    such a task is within NEAR_DAYS of (or past) its due date.

Opt-in per task: tag it `deadline-watch` and add a block to its description:
    [DEADLINE-WATCH]
    source_url: https://...
    event_date: YYYY-MM-DD (...)
    submission_deadline: YYYY-MM-DD  |  ROLLING / UNVERIFIED — ...
    verified: YYYY-MM-DD
    [/DEADLINE-WATCH]

Daily via launchd com.exos.deadline-watch. Fail-safe: any error leaves dates untouched.
"""
import os, sys, re, json, subprocess, urllib.request, urllib.parse
import durable_send_shim  # noqa: F401  (durable delivery: spool-then-send)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import supabase_util; supabase_util.install()
except Exception:
    pass
from datetime import datetime, date

WS = "/Users/exomac/.openclaw/workspace"
SECRETS = os.path.expanduser("~/.openclaw/secrets.json")
SB = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1/tasks"
LOG = os.path.join(WS, "logs", "deadline-watch.log")
OLLAMA_URL = "http://localhost:11434/api/generate"
LLM_MODEL = "qwen3.6:35b-a3b"
OPENCLAW = "/Users/exomac/.local/share/mise/installs/node/24.14.0/bin/openclaw"
JON_DISCORD = "1501632195163590739"
NEAR_DAYS = 21

BLOCK_RE = re.compile(r"\[DEADLINE-WATCH\](.*?)\[/DEADLINE-WATCH\]", re.S)
DATE_RE = re.compile(r"20\d\d-\d\d-\d\d")


def _key():
    return json.load(open(SECRETS)).get("supabase_service_role_key")


def sb_get(params):
    k = _key(); h = {"apikey": k, "Authorization": "Bearer " + k}
    url = SB + "?" + urllib.parse.urlencode(params, safe="(),*.")
    return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=40))


def sb_patch(tid, body):
    k = _key()
    h = {"apikey": k, "Authorization": "Bearer " + k,
         "Content-Type": "application/json", "Prefer": "return=representation"}
    req = urllib.request.Request(SB + f"?id=eq.{tid}", data=json.dumps(body).encode(),
                                 headers=h, method="PATCH")
    return json.load(urllib.request.urlopen(req, timeout=40))


def log(msg):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a") as f:
        f.write(f"[{datetime.now():%Y-%m-%d %H:%M}] {msg}\n")


def alert(text):
    env = dict(os.environ)
    env["PATH"] = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:" + os.path.dirname(OPENCLAW)
    try:
        subprocess.run([OPENCLAW, "message", "send", "--channel", "discord",
                        "--target", JON_DISCORD, "-m", text],
                       capture_output=True, text=True, timeout=60, env=env)
    except Exception:
        pass


def parse_block(desc):
    m = BLOCK_RE.search(desc or "")
    if not m:
        return None
    fields = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            fields[k.strip().lower()] = v.strip()
    return fields


def fetch_text(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    t = urllib.request.urlopen(req, timeout=25).read().decode("utf-8", "ignore")
    t = re.sub(r"<script.*?</script>", " ", t, flags=re.S)
    t = re.sub(r"<style.*?</style>", " ", t, flags=re.S)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", t.replace("&nbsp;", " "))


def extract_deadline(text):
    """Local-LLM extraction of the firm submission deadline + event date. Returns
    ISO strings or None. None means 'not stated' — we never invent a date."""
    def norm(x):
        if not x or str(x).lower() in ("null", "none", ""):
            return None
        m = DATE_RE.search(str(x))
        return m.group(0) if m else None
    prompt = ("From the event/solicitation page text, extract dates. Respond ONLY as JSON: "
              '{"submission_deadline":"YYYY-MM-DD or null","event_date":"YYYY-MM-DD or null"}. '
              "submission_deadline is the firm last day to apply/submit/register; use null if "
              "none is stated (rolling/open counts as null). event_date is when the event occurs. "
              "Do NOT guess — null if not explicitly on the page.\n\nPAGE:\n" + text[:6000])
    try:
        payload = json.dumps({"model": LLM_MODEL, "prompt": prompt, "stream": False,
                              "format": "json", "think": False,
                              "options": {"temperature": 0}}).encode()
        req = urllib.request.Request(OLLAMA_URL, data=payload,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as f:
            v = json.loads((json.load(f).get("response") or "{}").strip())
        return norm(v.get("submission_deadline")), norm(v.get("event_date"))
    except Exception:
        for kw in ("deadline", "submit by", "applications close", "register by", "no later than"):
            m = re.search(kw + r"[^.]{0,40}?" + DATE_RE.pattern, text, re.I)
            if m:
                d = DATE_RE.search(m.group(0))
                if d:
                    return d.group(0), None
        return None, None


def days_until(iso):
    try:
        return (datetime.strptime(iso[:10], "%Y-%m-%d").date() - date.today()).days
    except Exception:
        return None


def main():
    today = date.today().isoformat()
    try:
        tasks = sb_get({"select": "id,title,state,due_date,tags,description",
                        "description": "ilike.*DEADLINE-WATCH*", "limit": "500"})
    except Exception as e:
        log(f"supabase fetch failed: {e}")
        return
    tasks = [t for t in tasks if t.get("state") not in ("Done", "Cancelled")]
    log(f"watching {len(tasks)} task(s)")
    changes = []
    for t in tasks:
        tid = t["id"]; desc = t.get("description") or ""
        blk = parse_block(desc)
        if not blk or not blk.get("source_url"):
            continue
        url = blk["source_url"]
        m = DATE_RE.search(blk.get("submission_deadline", "") or "")
        stored_sub = m.group(0) if m else None
        try:
            text = fetch_text(url)
        except Exception as e:
            log(f"[{tid}] source unreachable ({url}): {e}")
            continue
        found_sub, found_evt = extract_deadline(text)
        newdesc = re.sub(r"(verified:).*", rf"\1 {today}", desc, count=1)
        tags = list(t.get("tags") or [])
        msgs = []

        if found_sub and found_sub != stored_sub:
            # A firm date appeared/changed on the authoritative source — ALERT, do not
            # silently move the task date; a human confirms (that is the whole lesson).
            newdesc = re.sub(r"(submission_deadline:).*",
                             rf"\1 {blk.get('submission_deadline','')}  <<SOURCE NOW SHOWS {found_sub} as of {today} — CONFIRM & UPDATE>>",
                             newdesc, count=1)
            msgs.append(f"source now shows a firm submission deadline **{found_sub}** "
                        f"(task had: {stored_sub or 'rolling/unset'}) — confirm and set the due date")

        if not found_sub:
            if "date-unverified" not in tags:
                tags.append("date-unverified")
            du = days_until((t.get("due_date") or "")[:10]) if t.get("due_date") else None
            if du is not None and du <= NEAR_DAYS:
                when = f"due in {du}d" if du >= 0 else f"{abs(du)}d past its (unverified) due date"
                msgs.append(f"no firm deadline on source (rolling/open); task is {when} — "
                            f"treat as CONFIRM-WITH-ORGANIZER, not a miss")
        else:
            tags = [x for x in tags if x != "date-unverified"]

        try:
            sb_patch(tid, {"description": newdesc, "tags": tags})
        except Exception as e:
            log(f"[{tid}] patch failed: {e}")
        if msgs:
            changes.append(f"• [{tid}] {(t.get('title') or '')[:55]}: " + "; ".join(msgs))
        log(f"[{tid}] checked {url}: source_sub={found_sub or 'none/rolling'} evt={found_evt or '-'}")

    if changes:
        report = ("📅 Deadline-watch — items needing your confirmation:\n" + "\n".join(changes) +
                  "\n\n(Dates are NOT auto-moved; reply to confirm and I'll update them.)")
        if "--dry" in sys.argv:
            log("DRY — would alert:\n" + report)
            print(report)
        else:
            alert(report)
    log(f"done — {len(changes)} flag(s)")


if __name__ == "__main__":
    main()
