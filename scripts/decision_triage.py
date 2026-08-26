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
import durable_send_shim  # noqa: F401  (durable delivery: spool-then-send)

WS = os.path.expanduser("~/.openclaw/workspace")
DEC = os.path.join(WS, "mission-control", "data", "decisions.json")
OPENCLAW = "/Users/exomac/.local/share/mise/installs/node/24.14.0/bin/openclaw"
JON = "1501632195163590739"
APPLY = "--apply" in sys.argv
BATCH_ID = "D-ROUTINE-BATCH"

# Standing delegation rule (Jon 2026-08-21): routine outreach is NOT Jon's to approve. Split it:
#   payload sales  -> UTD EXO3 Payload Capstone (Exos gate: Lizi)
#   BLK3 sales     -> Lizi Quinn
# Applied to EVERY newly-batched item automatically so it never re-nags Jon.
ROUTE_PAYLOAD = ("UTD EXO3 Payload Capstone", "EdwinVanDerVlist@utdallas.edu")
ROUTE_BLK3 = ("Lizi Quinn", "Lquinn@exosaero.com")
DEFAULT_ROUTING = {"payload": list(ROUTE_PAYLOAD), "blk3": list(ROUTE_BLK3)}
BLK3_SALES = re.compile(r"wet.?lease|flight[-\s]?2?\s*(fund|recap|sponsor|paths)|"
                        r"(fund|sponsor|recap).{0,20}(blk3|flight)|sell\s+(the\s+)?flight|"
                        r"vehicle\s+sale|flight\s+opportunit|charter|dedicated\s+flight", re.I)


def route_for(d, rule):
    """Classify a batched item and return (owner_label, owner_email, human_tag)."""
    blob = (d.get("title", "") + " " + d.get("question", "") + " " + d.get("proposedAction", ""))
    if BLK3_SALES.search(blob):
        who = rule.get("blk3", list(ROUTE_BLK3)); return who[0], who[1], "BLK3 sales → Lizi"
    who = rule.get("payload", list(ROUTE_PAYLOAD)); return who[0], who[1], "Payload sales → UTD (Exos gate: Lizi)"


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
# NEVER batch/delegate these — they are consequential (investor/capital, gov programs, Scorpius
# strategic, propulsion tech) OR they need Jon's authority, and MUST NOT land in the UTD student
# sandbox (scoped to Payload Sales; investor/409A/gov material is explicitly walled off there).
# Scanned against the FULL decision text, not just the title. (Fix 2026-08-22: a Senator SEARF
# request, the OSC loan, NASA M-STAR, Lockheed/Euronext Series A sends, and Scorpius Type-5 all
# leaked into the batch because CONSEQ_HARD only looked at title+relatedItem.)
CONSEQ_KEEP = re.compile(
    r"series\s*a\b|\b409a\b|data\s*room|\binvestor\b|capital\s+raise|strategic\s+(investment|fit|discussion)|"
    r"euronext|\bIPO\b|\bPIPE\b|diligence|"
    r"\bSen\.\s|\bsenat|congress|SEARF|\bOSC\b|TACFI|STRATFI|\bSBIR\b|\bSTTR\b|M-?STAR|fly-?in|"
    r"\bRDE\b|\bRDRE\b|type-?5|export|\bitar\b|\bhold\b|"
    r"get jon|jon approves|request\s+jon|approval\s+to\s+send|go\s+or\s+hold|jon'?s\s+(go|debrief|readout|inline|approval)|"
    r"go/?no-?go|discount\s+authoriz|decision\s+brief|authorize\s+send|capability\s+package|"
    r"confirm\s+(with\s+jon|whether)|which\s+.*proposal|submission\s+confirmation|portal\s+closes|"
    r"selects\s+the\s+routing|decide\s+the\s+.*route", re.I)
# Speculative "does a warm/known contact or intro path EXIST?" fishing (Jon 2026-07-31: don't ask
# maybe's). Always parked — overrides the gov-agency keep, since the gov mention is inside a
# hypothetical-relationship ask, not a real gov send.
SPECULATIVE = re.compile(
    r"confirm whether|whether (?:a |we have |there is |an? )?.{0,40}?(?:warm|known|existing|potential)\b"
    r".{0,40}?(?:contact|intro|introduction|relationship|connection|path|lead)|"
    r"\bdo we (?:have|know)\b|is there a (?:warm|known)|can .{0,30}? intro\b|ask jon (?:to confirm|whether)", re.I)

# Meta-redundant + info-capture pruning (Jon 2026-08-26, "reduce the human review cue"). A decision
# whose ACTION is merely to route/deliver/brief/email something TO Jon for approval is not a decision
# — it's Exo asking permission to do the delivery Jon already directed. And a meeting-debrief/readout
# ask is info-capture, not a CHOICE. Both get batched OUT of the CEO gate (reversible: superseded).
# GUARDED by TRUE_CONSEQ below: real gov/investor/contract/ITAR/Scorpius asks are NEVER pruned here,
# and SEND items (external approvals Jon explicitly keeps) never match these patterns.
META_REDUNDANT = re.compile(
    r"(?:email|e-?mail|route|deliver|send|surface|forward|escalate|present|bring|package)\b"
    r".{0,70}?\b(?:jon|john)\b"
    r".{0,90}?(?:for (?:his |your )?(?:approval|go|review|sign-?off|go/?no-?go|decision)|"
    r"requesting (?:his |your )?(?:go|approval|go/?no-?go|sign-?off)|to (?:approve|review|decide|sign))|"
    r"deliver (?:a |an )?.{0,40}?(?:brief|memo|summary|readout|package) to (?:jon|john)|"
    r"get (?:jon|john)'?s? (?:go|approval|sign-?off|go/?no-?go)\b", re.I)
DEBRIEF_INFO = re.compile(
    r"(?:get|capture|obtain)\s+jon'?s?\s+.{0,30}?(?:debrief|readout|inline debrief|structured debrief)\b|"
    r"\bsix-question debrief\b|debrief\s+of\s+the\s+.{0,30}?meeting", re.I)
# "TRUE" consequence — the real stuff that must stay with Jon (no meta phrasing that overlaps the
# above). Deliberately narrower than CONSEQ_KEEP so meta-wrappers don't self-protect.
TRUE_CONSEQ = re.compile(
    r"\.gov\b|\.mil\b|\bafrl\b|\bdarpa\b|\bonr\b|space\s?force|air\s?force|\bnro\b|\bmda\b|spacewerx|"
    r"\bnasa\b|\bsbir\b|\bsttr\b|tacfi|stratfi|\bosc\b|searf|senat|congress|"
    r"series\s*a|\binvestor\b|capital\s+raise|term\s?sheet|\b409a\b|data\s*room|euronext|"
    r"\bmnda\b|\bnda\b|counsel|contract|\bloi\b|\bitar\b|export.?control|\bddtc\b|"
    r"\brdre\b|\brde\b|type-?5|scorpius|rofr|\bcui\b|wire\s?transfer", re.I)


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
    # Meta-redundant "route/deliver/brief to Jon for approval" wrappers and meeting-debrief info-
    # capture asks are not CEO choices — park them (reversible) UNLESS they carry a true consequence
    # signal or are an external SEND (which Jon explicitly keeps approving).
    is_send = bool(ROUTINE_TITLE.search(title) is None and re.search(r"send this email to|^\s*send:", q, re.I))
    if (META_REDUNDANT.search(q) or DEBRIEF_INFO.search(q)) and not TRUE_CONSEQ.search(q) and not is_send:
        return True
    # never batch anything consequential/confidential or needing Jon's authority — scan FULL text,
    # not just the title (investor/gov/Scorpius/authority items must stay with Jon, never delegate).
    if CONSEQ_KEEP.search(q):
        return False
    # never batch anything with a gov/.mil recipient/agency or a hard investor/contract/legal signal
    if CONSEQ_RECIPIENT.search(title + " " + recipient_text(d)) or CONSEQ_HARD.search(q + " " + (d.get("relatedItem") or "")):
        return False
    return d.get("source") in OUTREACH_ENGINES or bool(ROUTINE_TITLE.search(title))


def load():
    with open(DEC) as f:
        raw = json.load(f)
    return raw, (raw if isinstance(raw, list) else raw.get("decisions", []))


def save(raw, arr):
    # arr is the authoritative (possibly reassigned) list — write IT, not the stale raw list.
    out = arr if isinstance(raw, list) else {**raw, "decisions": arr}
    tmp = DEC + f".tmp.{os.getpid()}"  # per-process temp: avoid concurrent-writer race on shared .tmp
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
    now = datetime.datetime.now().isoformat(timespec="seconds")

    # Carry Jon's standing disposition forward. Once he has dispositioned this batch (standing=True
    # or an answer on record) it becomes a PERSISTENT RULE: every newly-batched item is routed
    # automatically and the digest never resurfaces to him. That is the whole point — he answered
    # once ("payload sales -> UTD, BLK3 sales -> Lizi"); we apply it every run, not re-ask daily.
    prev = next((d for d in arr if d.get("id") == BATCH_ID), None)
    prev_ans = (prev or {}).get("answer")
    prev_count = (prev or {}).get("batched_count", 0) or 0
    standing = bool(prev and (prev.get("standing") or prev_ans))
    routing = (prev or {}).get("routing_rule") or DEFAULT_ROUTING

    np = nb = 0
    for d in routine:
        d["batched"] = True
        d["note"] = (d.get("note") or "") + f" [auto-batched routine {today}]"
        if standing:
            owner, email, tag = route_for(d, routing)
            d["status"] = "delegated"; d["assignedTo"] = email
            d["owner"] = owner; d["delegatedTo"] = owner; d["delegation"] = tag
            nb += 1 if tag.startswith("BLK3") else 0
            np += 0 if tag.startswith("BLK3") else 1
        else:
            d["status"] = "superseded"

    arr = [d for d in arr if d.get("id") != BATCH_ID]
    grew = len(routine) > prev_count
    lines = [f"• {d.get('id')} — {(d.get('title') or '').replace('Send: ','')[:70]}" for d in routine[:40]]
    extra = f"\n…+{len(routine)-40} more" if len(routine) > 40 else ""

    if standing:
        # Answered + off Jon's board. Do NOT bump `updated` unless the batch actually grew, so the
        # card stops re-sorting to the top of his board every 30-min run (that made it feel daily).
        digest = {
            "id": BATCH_ID, "created": (prev.get("created") if prev else now),
            "updated": (now if grew else prev.get("updated", now)),
            "source": "Decision Triage",
            "title": "📬 Routine outreach auto-delegated (payload → UTD, BLK3 → Lizi) — standing rule",
            "question": f"{len(routine)} routine outreach items are auto-routed per your standing rule "
                        f"(payload sales → UTD capstone; BLK3 sales → Lizi). No action needed.",
            "context": "Routed automatically every run — NOT in your CEO queue. Items:\n" + "\n".join(lines) + extra,
            "proposedAction": "Standing rule in effect. To change routing, answer this card again.",
            "type": "choice", "options": ["Keep rule", "Route all to Lizi", "Route all to UTD", "Send back to me"],
            "priority": "low", "status": "answered",
            "answer": prev_ans or "Delegate: payload sales → UTD; BLK3 sales → Lizi",
            "answeredAt": (prev or {}).get("answeredAt") or today,
            "answeredBy": (prev or {}).get("answeredBy") or "Jon",
            "assignedTo": ROUTE_BLK3[1],           # Lizi (capstone Exos gate) — OFF Jon's board
            "dedupeKey": "routine-batch", "batched_count": len(routine),
            "standing": True, "routing_rule": routing,
            "note": f"Standing rule applied {today}: {np} payload → UTD, {nb} BLK3 → Lizi. "
                    f"Auto-applied every run; not resurfaced to Jon.",
        }
        should_ping = False
    else:
        # First time / not yet dispositioned — surface once and ping so Jon can set the rule.
        digest = {
            "id": BATCH_ID, "created": (prev.get("created") if prev else now), "updated": now,
            "source": "Decision Triage",
            "title": f"📬 {len(routine)} routine outreach/archive items set aside (review or release)",
            "question": f"{len(routine)} low-consequence outreach items were batched out of your main inbox.",
            "context": "Kept OUT of your CEO queue so only consequential decisions remain. Items:\n" + "\n".join(lines) + extra,
            "proposedAction": "Set a standing rule: 'Delegate split' routes payload sales → UTD and BLK3 sales → Lizi.",
            "type": "choice", "options": ["Delegate split (payload→UTD, BLK3→Lizi)", "Delegate to Lizi", "Leave batched"],
            "priority": "med", "status": "open", "answer": None,
            "assignedTo": "jquinn@exosaero.com", "dedupeKey": "routine-batch",
            "batched_count": len(routine),
        }
        should_ping = (prev is None) or grew

    arr.append(digest)
    save(raw, arr)

    # Wire payload-sales delegations into the UTD capstone TASK queue (Jon 2026-08-21 "wire it").
    # Routing the decision alone is inert for the students (early_adopter = tasks board only,
    # scoped to category "Payload Sales"); payload_task_spawn.py turns each into a Supabase task
    # in that category. Idempotent + notifier-silent. Runs only when the standing rule is active.
    if standing:
        try:
            subprocess.Popen([sys.executable, os.path.join(WS, "scripts", "payload_task_spawn.py")],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    remaining = sum(1 for d in arr if is_open(d))
    tag = ("auto-delegated (payload→UTD, BLK3→Lizi)" if standing else "batched")
    print(f"\n✓ {tag}: {len(routine)} routine items. Open decisions now: {remaining} "
          f"({len(kept)} consequential{'' if standing else ' + 1 batch digest'}).")
    if APPLY and should_ping:
        try:
            subprocess.run([OPENCLAW, "message", "send", "--channel", "discord", "--target", JON, "-m",
                            f"🧹 **Decisions triaged** — {len(routine)} routine outreach items batched out of your inbox. "
                            f"You have **{remaining}** open ({len(kept)} consequential + 1 batch). Set the standing rule on '{BATCH_ID}'."],
                           timeout=60, capture_output=True)
        except Exception:
            pass


if __name__ == "__main__":
    main()
