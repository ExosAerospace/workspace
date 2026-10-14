#!/usr/bin/env python3
"""rolling_opps_exo3.py — Rolling open opportunities: rank by max potential contract value, keep ONE high-priority
focus task on the top one, and verify one submittal closes each week (Jon 2026-10-14: "organize rolling open
opportunities by max potential contract value and move the highest value one to the top of the list verifying a
high priority up to 120 score within 5 days task is assigned from that list and one submittal closed each week").

  run      (daily 07:15 CT)  rank -> mission-control/data/rolling-opportunities.json (the page's list, highest $ first);
                             ensure exactly one OPEN focus task exists for the top un-submitted opportunity:
                             priority 120 + pin:100 (top of the board), due <= 5 days, named owner
                             (payload/partner -> Lizi Quinn, gov/DoD -> John Quinn). A focus task is never
                             re-pointed mid-week; when it is Done/Cancelled or its opp leaves the list, the next
                             highest gets a new one.
  --weekly (Fri 16:00 CT)    was >= 1 rolling submittal closed in the last 7 days? (focus task Done, or a rolling
                             opp that moved to SUBMITTED). Exception-only: posts one line to #exomac-system if not.
  --selftest                 failure-replay eval (no network, no writes).

"Rolling" = open opportunity whose due text says rolling / open BAA / no hard close / on-ramp / open-ended.
Max potential value = largest $ figure in the value text (K/M/B units; "$500 basic" is NOT $500B), or the opp's
explicit max_value_override. Owner: John Quinn. Registry: com.exos.rolling-opps-exo3.
"""
import json, os, re, sys, datetime, urllib.request

WS = "/Users/exomac/.openclaw/workspace"
OPPS = os.path.join(WS, "mission-control/data/opportunities.json")
OUT = os.path.join(WS, "mission-control/data/rolling-opportunities.json")
STATE = os.path.join(WS, "logs/rolling-opps-state.json")
SB = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1"
SOURCE = "rolling-opps-exo3"
FOCUS_PRIORITY, FOCUS_DAYS = 120, 5
LIZI = ("Lizi Quinn", "lquinn@exosaero.com")
JON = ("John Quinn", "jquinn@exosaero.com")

ROLL = re.compile(r"rolling|open baa|no hard close|on-?ramp|continuous(ly)? open|open until|accepted (on a rolling|continuously)|open[- ]ended|year-?round", re.I)
DEAD = re.compile(r"closed|submitted|dropped|dead|scam|awarded|pass|declin|won|parked|not awarded", re.I)
DOL = re.compile(r"\$\s*(\d[\d,]*(?:\.\d+)?)\s*(k|m|b|thousand|million|billion)?(?![a-z])", re.I)
UNIT = {"k": 1e3, "thousand": 1e3, "m": 1e6, "million": 1e6, "b": 1e9, "billion": 1e9}
GOV = re.compile(r"gov|dod|baa|idiq|on-?ramp|solicitation|sbir|sttr|afrl|nasa|darpa|diu|space force|ssc", re.I)


def max_value(o):
    if o.get("max_value_override"):
        try:
            return float(o["max_value_override"])
        except Exception:
            pass
    best = 0.0
    for m in DOL.finditer(str(o.get("value") or "")):
        best = max(best, float(m.group(1).replace(",", "")) * UNIT.get((m.group(2) or "").lower(), 1))
    return best


def is_rolling_open(o):
    return bool(ROLL.search(str(o.get("due") or ""))) and not DEAD.search(str(o.get("status") or "")) and not o.get("closed")


def rank(opps):
    rows = [{"id": o.get("id"), "title": o.get("title"), "status": o.get("status"), "type": o.get("type"),
             "due": o.get("due"), "value": o.get("value"), "max_value": max_value(o)} for o in opps if is_rolling_open(o)]
    rows.sort(key=lambda r: (-r["max_value"], str(r["id"])))
    return rows


def owner_for(row):
    return JON if GOV.search(f"{row.get('type')} {row.get('title')}") and not re.search(r"payload sale", str(row.get("type")), re.I) else LIZI


def focus_row(row, today):
    name, email = owner_for(row)
    due = today + datetime.timedelta(days=FOCUS_DAYS)
    return {"title": f"SUBMIT (rolling focus): {row['title'][:90]} [{row['id']}] — max ${row['max_value']:,.0f}",
            "state": "To Do", "owner": name, "assigned_to": name, "assigned_email": email,
            "category": "Business Development", "priority": FOCUS_PRIORITY, "source": SOURCE,
            "due_date": f"{due:%Y-%m-%d}T22:00:00+00:00",
            "tags": ["rolling-focus", f"rolling-focus:{row['id']}", "pin:100"],
            "description": (f"Highest max-potential-value ROLLING open opportunity ({row['id']}): {row['title']}\n"
                            f"Value: {row.get('value')}\nDue: {row.get('due')}\nStatus: {row.get('status')}\n\n"
                            f"Done when: the submittal (quote / proposal / white paper / on-ramp package) is SENT and the "
                            f"opportunity status is set to SUBMITTED. Target: one rolling submittal closed every week "
                            f"(Jon 2026-10-14). Next highest-value rolling opp gets the focus task when this one is done.")}


def short_title(title):
    """Distinctive head of an opp title for matching existing tasks: 'OSP-4 On-Ramp - Suborbital ...' -> 'OSP-4 On-Ramp'."""
    head = re.split(r"\s+[-–—(:|]\s*|\s+\(", str(title or ""))[0].strip()
    return head[:40] if len(head) >= 6 else str(title or "")[:40]


def adopt_patch(task, row, today):
    """Adopt an EXISTING open task for the opp as the focus task (no duplicate task; group under existing)."""
    due = today + datetime.timedelta(days=FOCUS_DAYS)
    cur_due = str(task.get("due_date") or "")[:10]
    tags = [t for t in (task.get("tags") or []) if not str(t).startswith("pin:")] + ["rolling-focus", f"rolling-focus:{row['id']}", "pin:100"]
    p = {"tags": sorted(set(tags)), "priority": max(FOCUS_PRIORITY, task.get("priority") or 0), "source": task.get("source") or SOURCE}
    if not cur_due or cur_due > due.isoformat():
        p["due_date"] = f"{due:%Y-%m-%d}T22:00:00+00:00"
    if not task.get("assigned_email"):
        p["owner"], p["assigned_email"] = owner_for(row)
        p["assigned_to"] = p["owner"]
    return p


def choose_action(ranked, open_focus):
    """Pure decision logic. open_focus = list of open focus tasks [{id, opp}]. Returns ('keep', task) or
    ('create', row) or ('none', None). Never re-points a live focus task whose opp is still on the list."""
    live_ids = {r["id"] for r in ranked}
    for t in open_focus:
        if t["opp"] in live_ids:
            return "keep", t
    return ("create", ranked[0]) if ranked else ("none", None)


def week_closed(focus_done_7d, opp_status_now, opp_status_prev):
    """>= 1 submittal closed in 7 days: a focus task Done, or a rolling opp that moved to SUBMITTED."""
    moved = [i for i, s in opp_status_now.items() if re.search(r"submitted", str(s), re.I)
             and not re.search(r"submitted", str(opp_status_prev.get(i, "")), re.I)]
    return bool(focus_done_7d) or bool(moved), moved


# ── IO ───────────────────────────────────────────────────────────────────────
def sb(method, path, body=None, prefer=None):
    key = json.load(open(os.path.expanduser("~/.openclaw/secrets.json")))["supabase_service_role_key"]
    h = {"apikey": key, "Authorization": "Bearer " + key, "Content-Type": "application/json"}
    if prefer:
        h["Prefer"] = prefer
    r = urllib.request.Request(f"{SB}/{path}", data=json.dumps(body).encode() if body is not None else None, headers=h, method=method)
    with urllib.request.urlopen(r, timeout=30) as resp:
        raw = resp.read().decode()
        return json.loads(raw) if raw.strip() else None


def load_opps():
    d = json.load(open(OPPS))
    return d["opportunities"] if isinstance(d, dict) and "opportunities" in d else (d if isinstance(d, list) else next(v for v in d.values() if isinstance(v, list)))


def focus_tasks():
    rows = sb("GET", "tasks?tags=cs.%7Brolling-focus%7D&select=id,title,state,tags,assigned_email,due_date,updated_at") or []
    for t in rows:
        t["opp"] = next((x.split(":", 1)[1] for x in (t.get("tags") or []) if str(x).startswith("rolling-focus:")), None)
    return rows


def fleet(action, detail):
    try:
        sys.path.insert(0, os.path.join(WS, "scripts"))
        from fleet_log import event
        event("rolling-opps-exo3", "decide", action, detail=detail, owner="John Quinn")
    except Exception:
        pass


def write_json(path, obj):
    tmp = path + ".tmp"
    json.dump(obj, open(tmp, "w"), indent=1)
    os.replace(tmp, path)


def run():
    today = datetime.date.today()
    opps = load_opps()
    ranked = rank(opps)
    tasks = focus_tasks()
    open_focus = [t for t in tasks if t.get("state") not in ("Done", "Cancelled")]
    act, obj = choose_action(ranked, open_focus)
    if act == "create":
        import urllib.parse
        q = urllib.parse.quote(f"(title.ilike.*{obj['id']}*,title.ilike.*{short_title(obj['title'])}*)", safe="(),.*")
        existing = sb("GET", f"tasks?select=id,title,state,tags,priority,due_date,assigned_email,source&state=not.in.(Done,Cancelled)&or={q}&order=id.asc") or []
        if existing:
            t = existing[0]
            sb("PATCH", f"tasks?id=eq.{t['id']}", adopt_patch(t, obj, today))
            focus = {"id": t["id"], "opp": obj["id"], "adopted": True}
            fleet("focus_task_adopted", {"task": t["id"], "opp": obj["id"], "max_value": obj["max_value"]})
        else:
            c = sb("POST", "tasks", focus_row(obj, today), prefer="return=representation")
            focus = {"id": c[0]["id"], "opp": obj["id"]}
            fleet("focus_task_created", {"task": focus["id"], "opp": obj["id"], "max_value": obj["max_value"]})
    else:
        focus = obj
    try:
        state = json.load(open(STATE))
    except Exception:
        state = {}
    state.setdefault("status_history", {})[today.isoformat()] = {r["id"]: r["status"] for r in ranked}
    state["status_history"] = dict(sorted(state["status_history"].items())[-21:])
    write_json(STATE, state)
    write_json(OUT, {"generated": datetime.datetime.now().isoformat(timespec="seconds"), "count": len(ranked),
                     "focus": focus, "items": ranked})
    print(f"rolling: {len(ranked)} open; top {ranked[0]['id'] if ranked else '-'}; focus task {act}: {focus}")


def weekly():
    today = datetime.date.today()
    tasks = focus_tasks()
    since = (today - datetime.timedelta(days=7)).isoformat()
    done = [t for t in tasks if t.get("state") == "Done" and str(t.get("updated_at") or "") >= since]
    try:
        hist = json.load(open(STATE)).get("status_history", {})
    except Exception:
        hist = {}
    prev_day = next((d for d in sorted(hist) if d >= since), None)
    now = {o.get("id"): o.get("status") for o in load_opps() if ROLL.search(str(o.get("due") or ""))}
    ok, moved = week_closed(done, now, hist.get(prev_day, {}) if prev_day else {})
    fleet("weekly_check", {"closed": ok, "focus_done": [t["id"] for t in done], "moved_to_submitted": moved})
    if not ok:
        open_t = [t for t in tasks if t.get("state") not in ("Done", "Cancelled")]
        sys.path.insert(0, os.path.join(WS, "scripts"))
        from deliver import deliver
        deliver(f"⚠️ No rolling-opportunity submittal closed this week (target: 1/week). Focus task: "
                + (f"#{open_t[0]['id']} {open_t[0]['title'][:80]} (owner {open_t[0].get('assigned_email')}, due {str(open_t[0].get('due_date'))[:10]})" if open_t else "none open"),
                source=SOURCE)
    print(f"weekly: closed={ok} done={[t['id'] for t in done]} moved={moved}")


def selftest():
    n = 0
    def ok(c, m):
        nonlocal n
        assert c, "FAIL: " + m
        n += 1
    opps = [
        {"id": "P1", "title": "Payload A", "status": "NEW", "type": "Payload Sale", "due": "Rolling", "value": "$22,500–$45,000 plus $500 basic integration"},
        {"id": "G1", "title": "OSP-4 On-Ramp", "status": "DRAFT", "type": "DoD IDIQ On-Ramp", "due": "On-ramp submissions accepted on rolling basis", "value": "$986M ceiling"},
        {"id": "X1", "title": "Closed BAA", "status": "CLOSED", "type": "Gov", "due": "Rolling Open BAA", "value": "$2M"},
        {"id": "D1", "title": "Dated RFP", "status": "NEW", "type": "Gov", "due": "2026-11-01", "value": "$50M"},
        {"id": "S1", "title": "Already submitted", "status": "SUBMITTED", "type": "Payload Sale", "due": "Rolling", "value": "$1M"},
        {"id": "O1", "title": "Override", "status": "NEW", "type": "Partnership", "due": "open-ended", "value": "TBD", "max_value_override": 5e6},
    ]
    r = rank(opps)
    ok([x["id"] for x in r] == ["G1", "O1", "P1"], "only open rolling opps, highest max value first (closed/submitted/dated excluded)")
    ok(max_value(opps[0]) == 45000, "'$500 basic' is not read as $500 billion")
    ok(r[0]["max_value"] == 986e6, "$986M parsed")
    fr = focus_row(r[0], datetime.date(2026, 10, 14))
    ok(fr["priority"] == 120 and "pin:100" in fr["tags"] and fr["due_date"].startswith("2026-10-19"), "focus task: priority 120, pinned, due within 5 days")
    ok(fr["assigned_email"] == JON[1] and focus_row(r[2], datetime.date(2026, 10, 14))["assigned_email"] == LIZI[1], "owner: gov -> John, payload -> Lizi")
    ok(choose_action(r, []) == ("create", r[0]), "no open focus task -> create one on the top opp")
    ok(choose_action(r, [{"id": 7, "opp": "P1"}])[0] == "keep", "live focus task is not re-pointed mid-week")
    ok(choose_action(r, [{"id": 7, "opp": "S1"}]) == ("create", r[0]), "focus opp left the list (submitted) -> next highest gets a task")
    ok(week_closed([], {"P1": "SUBMITTED"}, {"P1": "NEW"}) == (True, ["P1"]), "opp moved to SUBMITTED counts as the weekly submittal")
    ok(week_closed([], {"P1": "NEW"}, {"P1": "NEW"})[0] is False, "nothing closed -> weekly exception")
    ok(short_title("OSP-4 On-Ramp - Suborbital Services (FA8626-25-R-B008)") == "OSP-4 On-Ramp", "short title for existing-task match")
    ap = adopt_patch({"id": 1178, "tags": ["awaiting-john", "pin:40"], "priority": 85, "due_date": "2026-12-01T00:00:00+00:00", "assigned_email": "jquinn@exosaero.com"}, r[0], datetime.date(2026, 10, 14))
    ok(ap["priority"] == 120 and "pin:100" in ap["tags"] and "pin:40" not in ap["tags"] and "awaiting-john" in ap["tags"] and ap["due_date"].startswith("2026-10-19") and "owner" not in ap, "adopt existing task: priority 120, pin replaced, due pulled in to <=5d, owner kept")
    print(f"rolling_opps_exo3 selftest: {n}/{n} pass")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    elif "--weekly" in sys.argv:
        weekly()
    elif "--auto" in sys.argv:   # launchd: daily 07:15 rank+focus; Fri 16:05 also the weekly submittal check
        run()
        now = datetime.datetime.now()
        if now.weekday() == 4 and now.hour >= 16:
            weekly()
    elif "--dry-run" in sys.argv:
        r = rank(load_opps())
        print(json.dumps({"count": len(r), "top": r[:5]}, indent=1)[:2000])
    else:
        run()
