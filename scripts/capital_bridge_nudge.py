#!/usr/bin/env python3
"""Capital-Bridge Nudge — direct follow-up flag to David Mitchell for PO10 outreach.

When it has been >= commitment_trigger_days since the LAST commitment of any type
(cash received OR a signed subscription packet), email David a direct flag telling
him to send the next round of investor follow-ups. EVERY email points back at the
Mission Control finance card so he can click straight to the live 504 status.

Dedup: re-nudges at most once per `renudge_interval_days` for a given stale streak
(and immediately re-arms once a new commitment lands, then goes stale again) — so it
prompts persistently without spamming daily.

  python3 scripts/capital_bridge_nudge.py            # send if triggered (daily launchd)
  python3 scripts/capital_bridge_nudge.py --dry-run  # compute + print, never send
  python3 scripts/capital_bridge_nudge.py --force    # send regardless of dedup/threshold
"""
import os, sys, json, subprocess, datetime

WS = os.path.expanduser("~/.openclaw/workspace")
LEDGER = os.path.join(WS, "mission-control", "data", "capital_bridge_ledger.json")
ACCESS = os.path.join(WS, "mission-control", "data", "finance-access.json")
STATE  = os.path.join(WS, "logs", "capital-bridge-nudge-state.json")
LOG    = os.path.join(WS, "logs", "capital-bridge-nudge.log")
MC_LINK = "https://mc.exosaero.space/finance.html"      # always point David back here
DAVID = "dmitchell@exosaero.com"
FROM  = "Jon Quinn <jquinnexo@pm.me>"

def log(m):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(LOG, "a") as f: f.write(f"[{ts}] {m}\n")
    except Exception: pass

def load(p, d):
    try: return json.load(open(p))
    except Exception: return d

def money(x): return "$" + format(int(round(x)), ",")

def pdate(s):
    try: return datetime.date.fromisoformat(str(s)[:10])
    except Exception: return None

def compute():
    led = load(LEDGER, {})
    target = led.get("target", 0); base = led.get("baseline_amount", 0)
    entries = [e for e in led.get("entries", []) if isinstance(e, dict)]
    received = base + sum(e.get("amount") or 0 for e in entries)
    commits = []
    for e in entries:
        for k in ("date", "signed_date"):
            d = pdate(e.get(k));
            if d: commits.append((d, e.get("investor", "?")))
    for p in led.get("pending_packets", []):
        if isinstance(p, dict):
            for k in ("signed_date", "date"):
                d = pdate(p.get(k));
                if d: commits.append((d, p.get("investor", "?")))
    commits.sort()
    last = commits[-1] if commits else None
    today = datetime.date.today()
    days = (today - last[0]).days if last else None
    return {"target": target, "received": received, "pct": round(received/target*100) if target else 0,
            "last_commit_date": last[0].isoformat() if last else None,
            "last_commit_who": last[1] if last else None, "days_since": days,
            "pending": len(led.get("pending_packets", [])), "program": led.get("program", "PO10")}

def email_body(c, thr):
    return f"""Hello David,

>> OPEN MISSION CONTROL (live 504 status):  {MC_LINK}
   (log in with your exosaero.com email; the Finance card is in the top menu)

Flagging PO10 for a follow-up push. It has been {c['days_since']} days since our last commitment of any kind (threshold {thr} days), so it's time for the next round of investor outreach.

Where we stand:
  Raised:            {money(c['received'])} of {money(c['target'])} ({c['pct']}%)
  Last commitment:   {c['last_commit_date']}{(' — ' + c['last_commit_who']) if c['last_commit_who'] else ''}
  Signed packets pending funds: {c['pending']}

Action: send your next round of follow-ups and outreach to move PO10 toward the $1M target. As commitments and funds come in, the counter resets automatically.

Everything above stays current on the Mission Control link at the top of this email:
  {MC_LINK}

— Exo (for Exos Aerospace)
"""

import shutil as _shutil
# launchd runs with a minimal PATH that excludes Homebrew; resolve msmtp to an absolute path.
MSMTP = _shutil.which("msmtp") or next((p for p in ("/opt/homebrew/bin/msmtp", "/usr/local/bin/msmtp") if os.path.exists(p)), "msmtp")

def send(to, subject, body):
    msg = f"To: {to}\nFrom: {FROM}\nSubject: {subject}\n\n{body}"
    r = subprocess.run([MSMTP, to], input=msg, text=True, capture_output=True)
    return r.returncode == 0, (r.stderr[:200] if r.returncode else "")

def main():
    args = set(sys.argv[1:])
    dry = "--dry-run" in args; force = "--force" in args
    acc = load(ACCESS, {})
    thr = acc.get("commitment_trigger_days", 7)
    renudge = acc.get("renudge_interval_days", 3)
    c = compute()
    today = datetime.date.today()

    if c["days_since"] is None or c["target"] == 0:
        log("no ledger data — skip"); print("no ledger data"); return
    if c["received"] >= c["target"] and not force:
        log("target reached — no nudge"); print("target reached"); return

    triggered = c["days_since"] >= thr
    st = load(STATE, {})
    last_nudge = pdate(st.get("last_nudge_date"))
    # re-arm if a NEW commitment has landed since we last nudged
    new_streak = st.get("last_commit_seen") != c["last_commit_date"]
    due = (last_nudge is None) or new_streak or ((today - last_nudge).days >= renudge)

    banner = (f"{'TRIGGERED' if triggered else 'ok'} · {c['days_since']}d since last commitment "
              f"(thr {thr}) · {money(c['received'])}/{money(c['target'])} · due={due}")
    print(banner)
    if dry:
        print("--- email preview ---"); print(email_body(c, thr)); return

    if not triggered:
        log("not triggered: " + banner); return
    if not (due or force):
        log("triggered but deduped (nudged recently): " + banner); return

    subject = f"[Exos] PO10 follow-up flag — {c['days_since']} days since last commitment"
    ok, err = send(DAVID, subject, email_body(c, thr))
    if ok:
        json.dump({"last_nudge_date": today.isoformat(), "last_commit_seen": c["last_commit_date"],
                   "days_since_at_nudge": c["days_since"]}, open(STATE, "w"), indent=2)
        log("NUDGE SENT to David: " + banner)
        print("nudge sent to", DAVID)
    else:
        log("send FAILED: " + err); print("send failed:", err)

if __name__ == "__main__":
    main()
