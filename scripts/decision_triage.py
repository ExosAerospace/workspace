#!/usr/bin/env python3
"""
DECISION TRIAGE — keep Jon's Decisions inbox to what actually needs the CEO.

Problem: BD/payload engines create a "Send: approve this outreach email?" decision for EVERY drafted
email — dozens a day, all defaulting to Jon. He can't read 80/day, so the gate defeats itself.

Fix: routine, low-consequence items (commercial-outreach send-approvals + low-value archives) are
COLLAPSED into a single daily batch digest and removed from the main inbox. Genuinely consequential
items (gov/.mil/.gov, investor/capital/ROFR, contracts/LOI, ITAR/export, wires) stay as individual
decisions. Reversible: batched items are marked 'superseded' (searchable), not deleted, and listed
in the digest so Jon can open/release any of them.

Run:  python3 scripts/decision_triage.py            # dry-run (show what it would batch)
      python3 scripts/decision_triage.py --apply
"""
import os, re, sys, json, datetime, subprocess

WS = os.path.expanduser("~/.openclaw/workspace")
DEC = os.path.join(WS, "mission-control", "data", "decisions.json")
OPENCLAW = "/Users/exomac/.local/share/mise/installs/node/24.14.0/bin/openclaw"
JON = "1501632195163590739"
APPLY = "--apply" in sys.argv
BATCH_ID = "D-ROUTINE-BATCH"

# These are the auto-outreach engines whose per-email "Send:" approvals flood the inbox.
OUTREACH_ENGINES = {"Opportunity Engine", "De-Risk Orbital Engine", "BLK3 Payload Sales Engine"}
# Consequence is about the RECIPIENT and the decision TYPE — not keywords in an outreach pitch.
# A gov/.mil/.gov recipient must route through Jon (policy). Actual investor/contract/legal
# DECISIONS stay too. Everything else from the outreach engines is routine → batch.
CONSEQ_RECIPIENT = re.compile(r"\.gov\b|\.gov[/>\s]|\.mil\b|\bsenat|\bcongress|\.house\.gov|whitehouse|@.*\.gov|"
                              r"\bafrl\b|\bdarpa\b|\bonr\b|space\s?force|air\s?force|\bnro\b|\bmda\b|"
                              r"spacewerx|\bnasa\s+(?:hq|msfc|jsc|ksc|glenn|langley|ames|directorate|sbir)", re.I)
CONSEQ_HARD = re.compile(r"\bFUND-\d|\brofr\b|term\s?sheet|cap\s?table|acquisition|wire\s?transfer|"
                         r"sign(?:ed|ing)?\s+(?:the\s+)?contract|execute|\bMNDA\b|\bNDA\b|counsel|"
                         r"investor\s+(?:commit|term|round)|capital\s+raise|"
                         r"\bitar\b|export.?control|\bddtc\b|\bear99\b|foreign\s+nation|\bcui\b", re.I)
ROUTINE_TITLE = re.compile(r"^\s*(send:|archive\b|get jon|capture jon|.*\b(debrief|readout)\b)", re.I)


def recipient_text(d):
    q = (d.get("question") or "") + " " + (d.get("proposedAction") or "")[:200]
    m = re.search(r"@[\w.-]+\.\w+", q)          # any email address in the ask
    to = re.search(r"send this email to ([^?\n]+)", d.get("question") or "", re.I)
    return (m.group(0) if m else "") + " " + (to.group(1) if to else "")


def is_routine(d):
    title = d.get("title") or ""
    # never batch anything with a gov/.mil recipient/agency or a hard investor/contract/legal signal
    if CONSEQ_RECIPIENT.search(title + " " + recipient_text(d)) or CONSEQ_HARD.search(title + " " + (d.get("relatedItem") or "")):
        return False
    return d.get("source") in OUTREACH_ENGINES or bool(ROUTINE_TITLE.search(title))


def load():
    with open(DEC) as f:
        raw = json.load(f)
    return raw, (raw if isinstance(raw, list) else raw.get("decisions", []))


def save(raw, arr):
    tmp = DEC + ".tmp"
    with open(tmp, "w") as f:
        json.dump(raw if isinstance(raw, list) else {**raw, "decisions": arr}, f, indent=2)
    os.replace(tmp, DEC)


def is_open(d):
    return (d.get("status") or "open") == "open"


def text_of(d):
    return " ".join(str(d.get(k, "") or "") for k in ("title", "question", "context", "proposedAction", "relatedItem"))


def main():
    raw, arr = load()
    openones = [d for d in arr if is_open(d) and d.get("id") != BATCH_ID]
    routine, kept = [], []
    for d in openones:
        (routine if is_routine(d) else kept).append(d)

    print(f"open decisions: {len(openones)}  ->  keep with Jon: {len(kept)}  |  batch (routine): {len(routine)}")
    for d in routine[:10]:
        print(f"   batch: [{d.get('priority')}] {(d.get('title') or '')[:66]}")
    if not APPLY:
        print("\n(dry-run — add --apply to batch the routine items)")
        return

    today = datetime.date.today().isoformat()
    for d in routine:
        d["status"] = "superseded"
        d["note"] = (d.get("note") or "") + f" [auto-batched routine {today}]"
        d["batched"] = True

    # (Re)build the single batch digest listing what was set aside.
    arr = [d for d in arr if d.get("id") != BATCH_ID]
    lines = [f"• {d.get('id')} — {(d.get('title') or '').replace('Send: ','')[:70]}" for d in routine[:40]]
    extra = f"\n…+{len(routine)-40} more" if len(routine) > 40 else ""
    now = datetime.datetime.now().isoformat(timespec="seconds")
    digest = {
        "id": BATCH_ID, "created": now, "updated": now, "source": "Decision Triage",
        "title": f"📬 {len(routine)} routine outreach/archive items set aside (review or release)",
        "question": f"{len(routine)} low-consequence items (commercial outreach + low-value archives) were "
                    f"batched out of your main inbox. Open any to handle, or bulk-release.",
        "context": "Kept OUT of your CEO queue so only consequential decisions (gov/investor/contract/ITAR) "
                   "remain. Items:\n" + "\n".join(lines) + extra,
        "proposedAction": "These are Lizi/BD-domain outreach approvals. Options: 'Delegate to Lizi' routes the batch "
                          "to her; 'Release all' sends the staged drafts; 'Leave batched' keeps them parked.",
        "type": "choice", "options": ["Delegate to Lizi", "Release all", "Leave batched"],
        "priority": "med", "status": "open", "answer": None,
        "assignedTo": "jquinn@exosaero.com", "dedupeKey": "routine-batch",
    }
    arr.append(digest)
    save(raw, arr)
    remaining = sum(1 for d in arr if is_open(d))
    print(f"\n✓ batched {len(routine)} routine items into {BATCH_ID}. Open decisions now: {remaining} "
          f"({len(kept)} consequential + 1 batch digest).")
    if APPLY:
        try:
            subprocess.run([OPENCLAW, "message", "send", "--channel", "discord", "--target", JON, "-m",
                            f"🧹 **Decisions triaged** — batched {len(routine)} routine outreach/archive items out of your inbox. "
                            f"You now have **{remaining}** open ({len(kept)} consequential + 1 batch). Open '{BATCH_ID}' to review or delegate the batch to Lizi."],
                           timeout=60, capture_output=True)
        except Exception:
            pass


if __name__ == "__main__":
    main()
