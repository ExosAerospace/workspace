#!/usr/bin/env python3
"""Close tasks whose text SAYS they were merged/closed as duplicate but whose STATE was never changed.

Root cause (Jon 2026-10-16, FAA RFI #2361): a cleanup wrote "merged into #2452 / closed as duplicate"
into the description but never flipped state, so the task stayed "In Progress" on everyone's lists.
This sweeper makes the text authoritative: an OPEN task whose description claims it was merged into /
is a duplicate of / was superseded by ANOTHER existing task gets set Done with a note pointing at the
survivor. Claims that point at itself or at a missing task are reported, not acted on.
Dry-run by default; --apply to write. Snapshot written before any change. Companion to dupe_collapse.py.
"""
import json, urllib.request, re, os, sys
from datetime import datetime, timezone

SB = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1"
KEY = json.load(open(os.path.expanduser("~/.openclaw/secrets.json")))["supabase_service_role_key"]
WS = "/Users/exomac/.openclaw/workspace"
DONE = {"Done", "Completed", "Closed", "Archived", "Cancelled"}
APPLY = "--apply" in sys.argv
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}"}

# Claims about THIS task. Each must name the survivor (#N); "closed as duplicate" alone needs a #N nearby.
CLAIMS = [
    r"\[\s*(?:consolidated|merged|folded|rolled)\s+into\s+#(\d+)\s*\]",
    r"\b(?:this (?:task|card) (?:was |is |has been )?)?(?:merged|consolidated|folded|rolled up)(?:\s+(?:on\s+)?\d{4}-\d{2}-\d{2})?(?:\s*\(sweep\))?\s+into\s+(?:the\s+)?(?:master|hub|parent)?\s*(?:task\s+)?#(\d+)",
    r"\b(?:closed|marked)\s+as\s+(?:a\s+)?dup(?:licate)?\b[^.#\n]{0,40}#(\d+)",
    r"\bdup(?:licate)?\s+of\s+(?:task\s+)?#(\d+)",
    r"\bsuperseded\s+by\s+(?:task\s+)?#(\d+)",
]
CLAIM_RE = [re.compile(p, re.I) for p in CLAIMS]
# Description OPENS with a closure word but names no survivor: can't auto-close, list for review.
LOOSE_RE = re.compile(r"^\W*(?:superseded|closed as (?:a )?dup|consolidated(?:\s+\S+)?\s+into|merged into)", re.I)

def qall():
    out, off = [], 0
    while True:
        req = urllib.request.Request(
            f"{SB}/tasks?select=id,title,state,owner,description&order=id&offset={off}&limit=1000", headers=H)
        r = json.load(urllib.request.urlopen(req, timeout=60)); out += r
        if len(r) < 1000: return out
        off += 1000

def patch(tid, f):
    req = urllib.request.Request(f"{SB}/tasks?id=eq.{tid}", data=json.dumps(f).encode(),
        headers={**H, "Content-Type": "application/json", "Prefer": "return=minimal"}, method="PATCH")
    urllib.request.urlopen(req, timeout=30).read()

def survivor(t):
    d = t.get("description") or ""
    # only the head of the description: a hub listing "#2351 merged into #2452" deep in its history
    # is talking about OTHER tasks; cleanup notes are written at the top.
    head = d[:600]
    for rx in CLAIM_RE:
        m = rx.search(head)
        if m:
            return int(m.group(1)), m.group(0)
    return None, None

alltasks = qall()
byid = {t["id"]: t for t in alltasks}
act, report = [], []
for t in alltasks:
    if (t.get("state") or "") in DONE:
        continue
    sid, txt = survivor(t)
    if sid is None:
        if LOOSE_RE.search(t.get("description") or ""):
            report.append((t, None, (t.get("description") or "")[:60], "closure text, no #survivor"))
        continue
    s = byid.get(sid)
    if sid == t["id"] or s is None:
        report.append((t, sid, txt, "self-reference" if sid == t["id"] else "survivor missing"))
    else:
        act.append((t, s, txt))

print(f"open tasks claiming merge/duplicate but still open: {len(act)}")
for t, s, txt in act:
    print(f"  close #{t['id']} [{t['state']}] {t['title'][:50]!r} -> #{s['id']} [{s['state']}]  ({txt.strip()[:60]!r})")
for t, sid, txt, why in report:
    print(f"  SKIP #{t['id']} ({why}, #{sid}): {txt.strip()[:60]!r}")

if APPLY and act:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from attachment_migrate import migrate_attachments
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    os.makedirs(f"{WS}/logs/merge-claim-sweeper", exist_ok=True)
    json.dump([{"id": t["id"], "prev_state": t["state"], "survivor": s["id"]} for t, s, _ in act],
              open(f"{WS}/logs/merge-claim-sweeper/{ts}.json", "w"), indent=1)
    for t, s, _ in act:
        note = (f"[AUTO-CLOSED {ts[:8]}: description says merged/duplicate → #{s['id']}; "
                f"state was left '{t['state']}' (merge-claim sweeper)]\n\n") + (t.get("description") or "")
        patch(t["id"], {"state": "Done", "description": note})
        moved = migrate_attachments(t["id"], s["id"])  # docs follow the survivor, as in dupe_collapse
        if moved:
            print(f"    migrated {moved} attachment(s) #{t['id']} -> #{s['id']}")
    print(f"applied {len(act)}; snapshot logs/merge-claim-sweeper/{ts}.json")
