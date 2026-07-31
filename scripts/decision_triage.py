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
# Speculative "does a warm/known contact or intro path EXIST?" fishing (Jon 2026-07-31: don't ask
# maybe's). Always parked — overrides the gov-agency keep, since the gov mention is inside a
# hypothetical-relationship ask, not a real gov send.
SPECULATIVE = re.compile(
    r"confirm whether|whether (?:a |we have |there is |an? )?.{0,40}?(?:warm|known|existing|potential)\b"
    r".{0,40}?(?:contact|intro|introduction|relationship|connection|path|lead)|"
    r"\bdo we (?:have|know)\b|is there a (?:warm|known)|can .{0,30}? intro\b|ask jon (?:to confirm|whether)", re.I)


def recipient_text(d):
    q = (d.get("question") or "") + " " + (d.get("proposedAction") or "")[:200]
    m = re.search(r"@[\w.-]+\.\w+", q)          # any email address in the ask
    to = re.search(r"send this email to ([^?\n]+)", d.get("question") or "", re.I)
    return (m.group(0) if m else "") + " " + (to.group(1) if to else "")


def is_routine(d):
    title = d.get("title") or ""
    q = title + " " + (d.get("question") or "") + " " + (d.get("proposedAction") or "")
    # Speculative warm-intro "maybe" asks are ALWAYS parked (even if they name a gov agency).
    if SPECULATIVE.search(q):
        return True
    # never batch anything with a gov/.mil recipient/agency or a hard investor/contract/legal signal
    if CONSEQ_RECIPIENT.search(title + " " + recipient_text(d)) or CONSEQ_HARD.search(title + " " + (d.get("relatedItem") or "")):
        return False
    return d.get("source") in OUTREACH_ENGINES or bool(ROUTINE_TITLE.search(title))


def load():
    with open(DEC) as f:
        raw = json.load(f)
    return raw, (raw if isinstance(raw, list) else raw.get("decisions", []))


def save(raw, arr):
    # arr is the authoritative (possibly reassigned) list — write IT, not the stale raw list.
    out = arr if isinstance(raw, list) else {**raw, "decisions": arr}
    tmp = DEC + ".tmp"
    with open(tmp, "w") as f:
        json.dump(out, f, indent=2)
    os.replace(tmp, DEC)


def is_open(d):
    return (d.get("status") or "open") == "open"


def text_of(d):
    return " ".join(str(d.get(k, "") or "") for k in ("title", "question", "context", "proposedAction", "relatedItem"))


def main():
    raw, arr = load()
    # Idempotent: restore previously-batched items to open so we re-classify from scratch every run
    # (lets the classifier self-correct and stay safe to run on a schedule). Never touches ANSWERED.
    for d in arr:
        if d.get("batched") and d.get("status") == "superseded":
            d["status"] = "open"; d.pop("batched", None)
            d["note"] = re.sub(r"\s*\[auto-batched routine[^\]]*\]", "", d.get("note") or "")
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
    # Preserve Jon's prior disposition: once he has answered the digest, DON'T reset it to open
    # every run (that was making him re-answer the same card daily). Only re-open when genuinely
    # NEW routine items appear beyond the count he already dispositioned.
    prev = next((d for d in arr if d.get("id") == BATCH_ID), None)
    arr = [d for d in arr if d.get("id") != BATCH_ID]
    lines = [f"• {d.get('id')} — {(d.get('title') or '').replace('Send: ','')[:70]}" for d in routine[:40]]
    extra = f"\n…+{len(routine)-40} more" if len(routine) > 40 else ""
    now = datetime.datetime.now().isoformat(timespec="seconds")
    digest = {
        "id": BATCH_ID, "created": (prev.get("created") if prev else now), "updated": now,
        "source": "Decision Triage",
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
        "batched_count": len(routine),
    }
    prev_ans = (prev or {}).get("answer")
    prev_count = (prev or {}).get("batched_count", 0) or 0
    surfaced_open = True
    # Ping only when the batch is genuinely new or has grown — not every 30-min run it sits open.
    if prev is None:
        should_ping = True                                   # first time
    elif prev_ans:
        should_ping = len(routine) > prev_count              # answered, but new items arrived
    else:
        should_ping = len(routine) > prev_count              # still open + unanswered, only if it grew
    if prev and prev_ans:
        # Carry forward his assignment (e.g. delegated to Lizi) either way.
        digest["assignedTo"] = prev.get("assignedTo", digest["assignedTo"])
        if len(routine) <= prev_count:
            # Nothing materially new — honor his answer, keep it OUT of his open inbox.
            digest.update(status=prev.get("status", "answered"), answer=prev_ans,
                          answeredAt=prev.get("answeredAt"), answeredBy=prev.get("answeredBy"),
                          note=prev.get("note", ""))
            surfaced_open = False
        else:
            # Genuinely new routine items beyond what he dispositioned — surface the delta.
            digest["note"] = f"{len(routine)-prev_count} new since you last dispositioned this batch."
    arr.append(digest)
    save(raw, arr)
    remaining = sum(1 for d in arr if is_open(d))
    print(f"\n✓ batched {len(routine)} routine items into {BATCH_ID}. Open decisions now: {remaining} "
          f"({len(kept)} consequential + 1 batch digest).")
    if APPLY and should_ping:
        # Only ping when the batch actually needs Jon (first time, or new items since he answered).
        # Once he's dispositioned it and nothing new arrived, stay silent — no daily re-nag.
        try:
            subprocess.run([OPENCLAW, "message", "send", "--channel", "discord", "--target", JON, "-m",
                            f"🧹 **Decisions triaged** — batched {len(routine)} routine outreach/archive items out of your inbox. "
                            f"You now have **{remaining}** open ({len(kept)} consequential + 1 batch). Open '{BATCH_ID}' to review or delegate the batch to Lizi."],
                           timeout=60, capture_output=True)
        except Exception:
            pass


if __name__ == "__main__":
    main()
