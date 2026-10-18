#!/usr/bin/env python3
"""drop_tombstone_exo3.py — GOVERN guard: a human "drop" is permanent across EVERY generator.

WHY (John 2026-10-18, "make sure whatever was causing the six spin ups of the Tim Crain task is
fixed globally"): PAY-7143 (IM / Tim Crain outreach) was raised SIX times (D-325, D-360, D-7241176,
D-7281448, D-7281516, D-7282096) and spawned task #3600 even though John said on 7/24
"Delete this — we are already working with them". Three leaks, all generic:
  1. The drop lived only in a decision NOTE (answer button was "Edit"), so nothing wrote it back
     to the source — the opportunity stayed live and the Opportunity Engine kept re-drafting it.
  2. Dedupe was per ROUTE key (opp-send-PAY-7143 vs opp-dec-PAY-7143); a route change minted a
     fresh key and slipped past the global dedupe.
  3. decision-note-router turned Exo's closing annotation ("Dropped: …") into a NEW subtask.

THE GUARD: an *entity* (opportunity/prospect id like PAY-7143, OPP-247, BD-007, FUND-038) is
TOMBSTONED when either
  (a) any decision whose dedupeKey names the entity was resolved with drop intent — in the
      answer, or in the note when the answer was not an affirmative (Send/Approve/Yes); or
  (b) it is listed in mission-control/data/drop-tombstones.json (explicit: task-cancel drops,
      email-command drops — `drop_tombstone_exo3.py add PAY-7143 --reason ...`).
Consumers: mission-control/server.js /api/decisions/ingest (mirrors this logic — refuses any new
decision on a tombstoned entity, whatever its route), opportunity_processor.py (treats as dead),
payload_pipeline_to_opps.py (won't re-stage), decision-note-router.py (drop/close notes never
spawn work). Lift a tombstone only by `remove` (logged).

Eval: `python3 scripts/drop_tombstone_exo3.py --selftest` replays the PAY-7143 history.
"""
import json, os, re, sys, argparse
from datetime import datetime, timezone

WS = "/Users/exomac/.openclaw/workspace"
DECISIONS = os.path.join(WS, "mission-control", "data", "decisions.json")
TOMBSTONES = os.path.join(WS, "mission-control", "data", "drop-tombstones.json")
AGENT = "drop-tombstone-exo3"
OWNER = "John Quinn"

# Entity ids: 2-6 uppercase letters + number (PAY-7143, OPP-247, BD-007, FUND-038, APAC-12).
# Decision ids (D-123) are single-letter, so they never match; WORD-20xx is a date stamp
# inside a key (reply-2026-10-…), not an entity.
ENTITY_RE = re.compile(r"\b([A-Z]{2,6}-(?!20\d\d\b)\d{2,7})\b")
# Keep in sync with DROP_RE / AFFIRM_RE in mission-control/server.js (decisions ingest).
DROP_RE = re.compile(r"\b(drop(ped)?(?!\s+(to|down|back)\b)|delete|kill(ed)?|dead|scrap|do not (pursue|engage|send|contact)|"
                     r"don'?t (pursue|send|contact)|not pursu\w*|no longer (pursu\w*|relevant|needed)|"
                     r"already working with|cancel(led)?|remove this|stop (this|pursuing))\b", re.I)
CONDITIONAL_RE = re.compile(r"\b(if|unless)\b", re.I)
AFFIRM_RE = re.compile(r"^\s*(send|approve[d]?|yes|go|ok|accept)\b", re.I)


def entities(text):
    return set(ENTITY_RE.findall(str(text or "").upper().replace("_", "-")))


def drop_intent(answer, note=""):
    """True when a resolved decision says 'drop this'. Note-only drops count unless the button
    pressed was an affirmative (an 'Approve' with a stray 'cancel' in the note is not a drop)."""
    a, n = str(answer or ""), str(note or "")
    if DROP_RE.search(a):
        return True
    h = human_text(n)
    # "delete it IF we missed the deadline" is conditional, not a drop (OPP-003 was then AWARDED).
    return bool(DROP_RE.search(h)) and not AFFIRM_RE.search(a) and not CONDITIONAL_RE.search(h)


def human_text(note):
    """A decision note minus Exo/system bracket annotations ('[refreshed …]', '[Exo 10/8: …]')."""
    return re.sub(r"\[[^\]]*\]", " ", str(note or "")).strip()


def _load(path, default):
    try:
        return json.load(open(path))
    except Exception:
        return default


# Only an OPPORTUNITY-scoped key tombstones the entity ("opp-send-PAY-7143", "opp-dec-FUND-002",
# "PAY-7143"). An action-scoped key ("OPP-003-aedc-velocity-cage-fix-resubmit") dropped one step,
# not the pursuit — OPP-003 went on to be AWARDED.
ENTITY_KEY_RE = re.compile(r"^(?:[a-z]+-){0,2}([A-Z]{2,6}-\d{2,7})$", re.I)


def _norm(t):
    return re.sub(r"[^a-z0-9 ]+", " ", str(t or "").lower()).split()


def same_subject(a, b):
    """Opp ids are NOT unique in the tracker (two BD-025s: Kolon and SwRI), so a tombstone that
    carries a title only matches a candidate about the same subject."""
    ta, tb = _norm(a), _norm(b)
    if not ta or not tb:
        return True
    if " ".join(ta)[:30] == " ".join(tb)[:30]:
        return True
    A, B = set(ta), set(tb)
    return len(A & B) / max(1, min(len(A), len(B))) >= 0.6


def explicit():
    data = _load(TOMBSTONES, {"tombstones": []})
    out = {}
    for t in data.get("tombstones", []):
        if t.get("entity") and not t.get("lifted"):
            out.setdefault(t["entity"].upper(), []).append(t)
    return out


def derived(decisions=None):
    decs = decisions if decisions is not None else _load(DECISIONS, [])
    if isinstance(decs, dict):
        decs = decs.get("decisions", [])
    out = {}
    for d in decs:
        st = str(d.get("status") or "open")
        if st in ("open", "pending", "delegated", "reassigning"):
            continue
        m = ENTITY_KEY_RE.match(str(d.get("dedupeKey") or "").strip())
        if not m or not drop_intent(d.get("answer"), d.get("note")):
            continue
        e = m.group(1).upper()
        rel = str(d.get("relatedItem") or "")
        out.setdefault(e, []).append({
            "entity": e, "title": "" if rel.strip().upper() == e else rel[:120],
            "reason": f"{d.get('id')}: {str(d.get('answer'))[:60]} / {human_text(d.get('note'))[:80]}",
            "source": d.get("id"), "at": d.get("answeredAt")})
    return out


def tombstoned(decisions=None):
    t = derived(decisions)
    for e, recs in explicit().items():
        t.setdefault(e, []).extend(recs)
    return t


def check(*texts, title=None, decisions=None, _cache={}):
    """Tombstone record for the first tombstoned entity named in texts (about the same subject
    as `title`, when given), else None."""
    if decisions is None:
        if "t" not in _cache:
            _cache["t"] = tombstoned()
        ts = _cache["t"]
    else:
        ts = tombstoned(decisions)
    for txt in texts:
        for e in sorted(entities(txt)):
            for rec in ts.get(e, []):
                if title is None or same_subject(rec.get("title"), title):
                    return rec
    return None


def _log(action, detail):
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import fleet_log
        fleet_log.event(AGENT, "govern", action, detail=detail, owner=OWNER)
    except Exception:
        pass


def add(entity, reason, by):
    data = _load(TOMBSTONES, {"tombstones": []})
    entity = entity.upper()
    for t in data["tombstones"]:
        if t["entity"].upper() == entity and not t.get("lifted"):
            return t
    rec = {"entity": entity, "reason": reason, "by": by, "at": datetime.now(timezone.utc).isoformat()}
    data["tombstones"].append(rec)
    json.dump(data, open(TOMBSTONES, "w"), indent=1)
    _log("tombstone_add", rec)
    return rec


def remove(entity, by):
    data = _load(TOMBSTONES, {"tombstones": []})
    n = 0
    for t in data["tombstones"]:
        if t["entity"].upper() == entity.upper() and not t.get("lifted"):
            t["lifted"] = {"by": by, "at": datetime.now(timezone.utc).isoformat()}
            n += 1
    json.dump(data, open(TOMBSTONES, "w"), indent=1)
    _log("tombstone_lift", {"entity": entity, "by": by, "n": n})
    return n


def selftest():
    """Replay the PAY-7143 history: every leak must now be closed; the IM test campaign must not."""
    hist = [
        {"id": "D-325", "status": "answered", "answer": "Send", "note": "", "dedupeKey": "opp-send-PAY-7143"},
        {"id": "D-360", "status": "answered", "answer": "Edit", "note": "Delete this- we are already working with them",
         "dedupeKey": "opp-send-PAY-7143"},
        {"id": "D-x", "status": "answered", "answer": "Approve", "note": "cancel the old draft, send the new one",
         "dedupeKey": "opp-send-PAY-9999"},
        {"id": "D-y", "status": "open", "answer": None, "note": "drop it", "dedupeKey": "opp-send-PAY-8888"},
        {"id": "D-z", "status": "answered", "answer": "Send", "note": "", "dedupeKey": "opp-send-BD-007"},
        {"id": "D-100", "status": "answered", "answer": "None", "note": "dropped- they wanted Scorpius cage code",
         "dedupeKey": "OPP-003-aedc-velocity-cage-fix-resubmit", "relatedItem": "OPP-003"},
        {"id": "D-7281492", "status": "answered", "answer": "Closed — Dropped: stale SwRI hook", "note": "",
         "dedupeKey": "opp-send-BD-025", "relatedItem": "SwRI - C.J. Nolen + Alan Stern Payload Outreach (NEW June 10)"},
    ]
    hist[1]["relatedItem"] = "Intuitive Machines — Tim Crain (CTO/Co-founder) ⭐⭐⭐ WARM — SCORPIUS CONNECTION"
    fails = []
    # Leak 1: a note-only drop (answer 'Edit') tombstones the entity.
    if not check("opp-send-PAY-7143", decisions=hist): fails.append("note-only drop not tombstoned")
    # Leak 2: a different route key for the same entity is still blocked (D-7282096 = opp-dec-PAY-7143).
    if not check("opp-dec-PAY-7143", decisions=hist): fails.append("route change evaded tombstone")
    if not check("Intro to Tim Crain (PAY-7143)", decisions=hist): fails.append("title-named entity not caught")
    # Affirmative button + stray 'cancel' in note is NOT a drop; open decisions never tombstone.
    if check("opp-send-PAY-9999", decisions=hist): fails.append("affirmative answer wrongly tombstoned")
    if check("opp-send-PAY-8888", decisions=hist): fails.append("open decision wrongly tombstoned")
    # The kept IM test campaign stays live.
    if check("opp-dec-BD-007", "OPP-247", decisions=hist): fails.append("BD-007/OPP-247 wrongly tombstoned")
    # Leak 3: the #3600 note was nothing but Exo bracket annotations -> no human directive left.
    n3600 = ("[pulled back from UTD 2026-08-22 — consequential/confidential, not a student task] "
             "[re-sorted→UTD 2026-08-22] [refreshed 2026-10-07: current draft OPP_PAY-7143_2026-10-07.docx] "
             "[Exo 10/8: Dropped: John 7/24 'already working with IM'; stale ROFR claim; awaiting Lizi confirm]")
    if human_text(n3600): fails.append("system annotations left residual 'directive' text")
    if not drop_intent("Closed — Dropped: John 7/24 'already working with IM'", n3600):
        fails.append("closed-dropped answer not recognised")
    if drop_intent("Edit", "[pulled back from UTD 2026-08-22 — dropped by system]"):
        fails.append("bracketed system annotation judged as human drop")
    if drop_intent("Edit", "delete it if we missed teh deadline."): fails.append("conditional drop read as a drop")
    # Action-scoped drop must not kill the pursuit (OPP-003 was later AWARDED).
    if check("OPP-003", decisions=hist): fails.append("action-scoped drop tombstoned the whole opp")
    # Duplicate ids: dropping SwRI BD-025 must not kill Kolon BD-025; same-subject retitle still blocked.
    if check("BD-025", title="Hongsuk Yoon / Kolon USA Inc. - Advanced Composites Partners", decisions=hist):
        fails.append("id collision: Kolon BD-025 killed by SwRI drop")
    if not check("opp-dec-PAY-7143", title="Intuitive Machines — Tim Crain (CTO/Co-founder) ⭐⭐⭐ WARM", decisions=hist):
        fails.append("same-subject PAY-7143 not blocked")
    if entities("D-7282096") or entities("reply-2026-10-02"): fails.append("decision id / date parsed as entity")
    if drop_intent("Drop to low-touch now", ""): fails.append("'drop to low-touch' (downgrade) read as a drop")
    print("selftest", "FAIL" if fails else "OK", fails or "")
    _log("selftest", {"ok": not fails, "fails": fails})
    return not fails


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")
    a = sub.add_parser("add"); a.add_argument("entity"); a.add_argument("--reason", required=True); a.add_argument("--by", default="Exo")
    r = sub.add_parser("remove"); r.add_argument("entity"); r.add_argument("--by", required=True)
    c = sub.add_parser("check"); c.add_argument("text", nargs="+")
    sub.add_parser("list")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        sys.exit(0 if selftest() else 1)
    if args.cmd == "add":
        print(json.dumps(add(args.entity, args.reason, args.by)))
    elif args.cmd == "remove":
        print(f"lifted {remove(args.entity, args.by)}")
    elif args.cmd == "check":
        hit = check(*args.text)
        print(json.dumps(hit) if hit else "clear")
        sys.exit(2 if hit else 0)
    else:
        for e, recs in sorted(tombstoned().items()):
            for t in recs:
                print(f"{e}\t{t.get('source') or t.get('by')}\t{str(t.get('title'))[:40]}\t{str(t.get('reason'))[:70]}")


if __name__ == "__main__":
    main()
