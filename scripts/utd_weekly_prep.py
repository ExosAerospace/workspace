#!/usr/bin/env python3
"""utd_weekly_prep.py: DRAFT-ONLY generator for UTD Team Atlas weekly tasks + lead-card batch
(utd-weekly-prep-exo3, launchd com.exos.utd-weekly-prep, owner Lizi Quinn).

Why: Weeks 6-8 tasks/lead cards were made by hand (utd_week6/7/8_tasks.py,
utd_capstone_lead_cards.py); Week 8 was due 10/19 and created 10/21.

Flow (exception-only, nothing created in MC until Lizi answers Yes):
  build   Sun >= 18:00 CT: propose next week's tasks + lead batch from the ranked queue
          (capstone-program.json work_queue) and file ONE Decision for Lizi:
          "Go week N tasks + lead batch?" (dedupeKey utd-weekly-prep-wkN).
  apply   on a HUMAN Yes (answeredByEmail lquinn@/jquinn@) create the tasks the same way the
          week scripts do (capstone_capture.supa POST tasks, tags utd-capstone + week-N) and the
          lead cards via utd_capstone_lead_cards.build()/insert(). Idempotent: skipped if the
          week is already applied, or if any task tagged week-N already exists; per-title and
          per-lead-tag skip on top.
  remind  if still unanswered at Tue 09:00 CT: ONE Discord post to channel 1539382179120021616.
  tick    launchd entry (every 15 min): build/apply/remind, each time-gated + state-gated.
  selftest  fixtures only: no Supabase writes, no Decision, no Discord (network is blocked).
  eval    output eval on the state file (one Decision per week, applied only after a human Yes,
          never applied twice, rules held in every proposal).

Rules (memory/channels/utd-exo3capstone/memory.md): Laura 1 lead/wk, Roel/Karan/Adrian/Sunidhi
3/wk (open cards count against the quota), Brenda creative only; gov/defense leads -> John
writes/signs/sends, else Lizi voice; skip orgs with open/any existing cards or parked by Lizi;
final presentation in person Thu Nov 20 10 AM (all work due before it); John leaves Nov 29.

Usage: python3 scripts/utd_weekly_prep.py build [--week N] [--dry-run] [--out FILE]
       python3 scripts/utd_weekly_prep.py apply [--dry-run] | remind [--dry-run] | tick | selftest | eval
"""
import json, os, re, sys, subprocess, tempfile, urllib.request
from datetime import datetime, date, timedelta, timezone

WS = "/Users/exomac/.openclaw/workspace"
sys.path.insert(0, os.path.join(WS, "scripts"))
DATA = os.path.join(WS, "mission-control", "data")
PROGRAM = os.path.join(DATA, "capstone-program.json")
DEC_FILE = os.path.join(DATA, "decisions.json")
TOKEN = os.path.join(DATA, ".decisions-token")
STATE = os.path.join(DATA, "utd-weekly-prep-state.json")
LOG = os.path.join(WS, "logs", "utd-weekly-prep.log")
SB = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1"
MC = "http://127.0.0.1:8080"
OPENCLAW = "/Users/exomac/.local/share/mise/shims/openclaw"
DISCORD = "channel:1539382179120021616"
LIZI, JON = "lquinn@exosaero.com", "jquinn@exosaero.com"
APPROVERS = {LIZI, JON}
AGENT = "utd-weekly-prep"
SOURCE = "utd_weekly_prep.py"

WEEK8_MEETING = date(2026, 10, 22)      # Week N meeting = this + 7*(N-8) (Thu)
FINAL = date(2026, 11, 20)              # final presentation, in person, 10 AM
LAST_DUE = FINAL - timedelta(days=1)    # all work finished before the final presentation
JOHN_LEAVES = date(2026, 11, 29)

EM = {"Roel Saenz": "RCS220001@utdallas.edu", "Laura Granados Lopez": "LEG240001@utdallas.edu",
      "Karan Vijaya Sankar": "KXV220043@utdallas.edu", "Adrian Haro": "AXH230026@utdallas.edu",
      "Brenda Segovia Saldana": "BXS230052@utdallas.edu", "Sunidhi Mathew": "SXM220350@utdallas.edu"}
FIRST = {v.split()[0]: v for v in EM}
QUOTA = {"Roel Saenz": 3, "Laura Granados Lopez": 1, "Karan Vijaya Sankar": 3, "Adrian Haro": 3,
         "Sunidhi Mathew": 3, "Brenda Segovia Saldana": 0}   # Lizi 10/15 + John 10/19
# Lizi parked / never-student leads (10/12 park; Jon/Scorpius; partner)
PARKED_RX = re.compile(r"Lumibird|CACI|Intuitive Machines|Space Port Australia|Scorpius|JHU|Johns Hopkins APL", re.I)
GOV_RX = re.compile(r"\b(NASA|AFRL|SpaceWERX|NRL|DEVCOM|DIU|Air Force|Space Force|Navy|Army|Naval|NIH|NCATS|NOAA|"
                    r"NSF|DoD|DOE|MDA|Sandia|Los Alamos|Livermore|Oak Ridge|Lincoln Lab|Aerospace Corp|FFRDC|"
                    r"UARC|National Lab|Kirtland|Department of)\b", re.I)
DEFENSE_RX = re.compile(r"\b(Kratos|BAE|Lockheed|Northrop|Raytheon|RTX|L3Harris|General Dynamics|Leidos|Boeing|"
                        r"Anduril|Orbit Fab)\b", re.I)
UNIV_RX = re.compile(r"Universit|College|Institute of Technology|\bUC[A-Z]?\b|\bMIT\b|Purdue|Embry", re.I)
BANNED_TXT = ('Use "early 2027" (never a month), "designed for about 2.5 minutes of microgravity", '
              'no only/first/fastest, no "FAA-licensed", no refly, no "2-3 day turnaround".')
JOHN_NOTE = ("Government/defense contact, so John writes, signs and sends this one himself (not Lizi). Keep the "
             "draft in John's voice, signed John Quinn, Cofounder and CEO. " + BANNED_TXT)
LIZI_NOTE = "Lizi sends this one, so write it in her voice. " + BANNED_TXT

# --- injectable I/O (selftest swaps these for fixtures) ---------------------------------------
IO = {}


def log(m):
    try:
        with open(LOG, "a") as f:
            f.write(f"{datetime.now(timezone.utc).isoformat()} {m}\n")
    except Exception:
        pass


def _sb_get(path):
    key = json.load(open(os.path.expanduser("~/.openclaw/secrets.json")))["supabase_service_role_key"]
    req = urllib.request.Request(f"{SB}/{path}", headers={"apikey": key, "Authorization": "Bearer " + key})
    return json.load(urllib.request.urlopen(req, timeout=60))


def _decisions():
    d = json.load(open(DEC_FILE))
    out = d if isinstance(d, list) else d.get("decisions", [])
    try:  # open ones also live behind the API
        tok = open(TOKEN).read().strip()
        api = json.load(urllib.request.urlopen(urllib.request.Request(f"{MC}/api/decisions",
                                               headers={"X-Exo-Token": tok}), timeout=20))
        out = out + (api if isinstance(api, list) else api.get("decisions", []))
    except Exception:
        pass
    return out


def _file_decision(body):
    tok = open(TOKEN).read().strip()
    r = urllib.request.urlopen(urllib.request.Request(f"{MC}/api/decisions/ingest", data=json.dumps(body).encode(),
                               headers={"Content-Type": "application/json", "x-exo-token": tok}, method="POST"),
                               timeout=30)
    return json.load(r)


def _discord(msg):
    r = subprocess.run([OPENCLAW, "message", "send", "--channel", "discord", "--target", DISCORD, "-m", msg],
                       capture_output=True, text=True, timeout=60)
    return r.returncode == 0


def _create_task(row):  # same code path as utd_week6/7/8_tasks.py
    import capstone_capture as cc
    r = cc.supa("POST", "tasks", row)
    return r[0]["id"] if r else None


def _create_lead(lead):  # same code path as utd_capstone_lead_cards.py
    import utd_capstone_lead_cards as lc
    t = lc.pipeline_text()
    name, desc = lc.build(t, lead["prefix"], lead["draft_label"], lead["note"])
    if "(No draft yet" in desc:
        raise RuntimeError("no AI draft (card builder refuses draft-less cards)")
    owner = lead["student"]
    row = {"title": f"[Lead] {name} — verify + get to READY"[:200], "description": desc, "owner": owner,
           "assigned_to": owner, "assigned_email": EM[owner], "state": "To Do", "category": "Payload Sales",
           "due_date": lead["due"], "priority": 80, "source": "exo-capstone-lead",
           "tags": ["utd-capstone", "utd-lead", "lead:" + lead["prefix"], f"week-{lead['week']}"]}
    return lc.insert(row)


def _now():
    from zoneinfo import ZoneInfo
    return datetime.now(ZoneInfo("America/Chicago"))


def _pipeline_text():
    return open(os.path.join(WS, "tasks/blk3-payload-sales-pipeline.md"), encoding="utf-8").read()


def _drafts_text():
    try:
        return open(os.path.join(WS, "drafts/payload-outreach-drafts.md"), encoding="utf-8").read()
    except FileNotFoundError:
        return ""


IO.update(sb_get=_sb_get, decisions=_decisions, file_decision=_file_decision, discord=_discord,
          create_task=_create_task, create_lead=_create_lead, now=_now, program=lambda: json.load(open(PROGRAM)),
          pipeline=_pipeline_text, drafts=_drafts_text)


# --- state ------------------------------------------------------------------------------------
def load_state():
    try:
        return json.load(open(STATE))
    except Exception:
        return {"weeks": {}}


def save_state(s):
    tmp = STATE + ".tmp"
    json.dump(s, open(tmp, "w"), indent=1, default=str)
    os.replace(tmp, STATE)


# --- calendar ---------------------------------------------------------------------------------
def meeting_of(week):
    return WEEK8_MEETING + timedelta(days=7 * (week - 8))


def week_for_build(now_ct):
    """The week whose meeting is the next Thursday after now (Sun 10/25 -> Week 9, meeting 10/29)."""
    d = now_ct.date()
    days = (3 - d.weekday()) % 7 or 7
    thu = d + timedelta(days=days)
    return 8 + (thu - WEEK8_MEETING).days // 7


def due(d):
    d = min(d, LAST_DUE)
    return f"{d.isoformat()}T16:59:00+00:00"   # 11:59 CT, as the week scripts use


def fmt(d):
    return f"{d:%a} {d.month}/{d.day}"


# --- lead selection ---------------------------------------------------------------------------
def org_key(name):
    root = re.split(r" — | \(| /|:", re.sub(r"^\[Lead[^\]]*\]\s*", "", name or ""))[0].strip()
    words = re.findall(r"[A-Za-z0-9&]+", root)
    if not words:
        return ""
    if words[0].isupper() and len(words[0]) >= 3:   # acronym orgs: AFRL, DIU, BAE, NASA ...
        return words[0].lower()
    return " ".join(w.lower() for w in words[:2])


def student_week_tasks(week):
    """Student tasks already tagged week-N (Exo's own reminder card for the week does not count)."""
    rows = IO["sb_get"](f"tasks?select=id,title,owner,tags&tags=cs.%7Bweek-{week}%7D")
    return [t for t in rows if t.get("owner") in EM]


def lead_cards():
    return IO["sb_get"]("tasks?select=id,title,owner,state,tags,description&tags=cs.%7Butd-lead%7D&limit=1000")


def segment_of(name):
    if GOV_RX.search(name) or DEFENSE_RX.search(name):
        return "gov"
    if UNIV_RX.search(name):
        return "university"
    return "commercial"


def find_draft_label(name, pipe, drafts):
    root = re.split(r" — | \(", name)[0].strip()
    key = re.escape(root[:25])
    m = re.search(r"\*\*DRAFT ([A-Z]{1,3}) —[^\n]*" + key, pipe)
    if m:
        return m.group(1)
    m = re.search(r"^## (" + key + r"[^\n]*)", drafts, re.M)
    if m:
        return "file:" + root
    return None


def pick_leads(queue, cards, week, pipe="", drafts=""):
    """Return (assigned leads, skipped [(name, why)], open cards per student, shortfall per student)."""
    open_by = {s: 0 for s in QUOTA}
    used_keys, used_tags = set(), set()
    for c in cards:
        for t in c.get("tags") or []:
            if str(t).startswith("lead:"):
                used_tags.add(t[5:])
        used_keys.add(org_key(c.get("title") or ""))
        m = re.search(r"^LEAD:\s*(.+)", c.get("description") or "", re.M)
        if m:
            used_keys.add(org_key(m.group(1)))
        if c.get("state") not in ("Done", "Cancelled") and c.get("owner") in open_by:
            open_by[c["owner"]] += 1
    room = {s: max(0, q - open_by[s]) for s, q in QUOTA.items()}
    meeting = meeting_of(week)
    if meeting + timedelta(days=7) > FINAL:   # final week: finish, no new leads
        room = {s: 0 for s in room}
    leads, skipped = [], []
    for q in sorted(queue, key=lambda x: x.get("rank", 99)):
        name = q.get("name") or ""
        k = org_key(name)
        prefix = re.sub(r"\s*[⭐✅].*$", "", name)[:40].strip()
        if q.get("owner") or q.get("card"):
            skipped.append((name, f"already on a card (#{q.get('card')})")); continue
        if PARKED_RX.search(name):
            skipped.append((name, "parked by Lizi / not a student lead")); continue
        if k in used_keys or prefix in used_tags:
            skipped.append((name, "org already has a lead card (open or done)")); continue
        seg = segment_of(name)
        prefs = {"gov": ["Karan Vijaya Sankar", "Sunidhi Mathew", "Roel Saenz"],
                 "university": ["Laura Granados Lopez", "Adrian Haro", "Sunidhi Mathew", "Roel Saenz"],
                 "commercial": ["Adrian Haro", "Sunidhi Mathew", "Roel Saenz"]}[seg]
        who = next((s for s in prefs if room.get(s, 0) > 0), None)
        if not who:
            skipped.append((name, "no student quota left this week")); continue
        label = find_draft_label(name, pipe, drafts)
        room[who] -= 1
        used_keys.add(k)
        leads.append({"name": name, "prefix": prefix, "student": who, "segment": seg, "week": week,
                      "sender": "John" if seg == "gov" else "Lizi", "draft_label": label,
                      "note": JOHN_NOTE if seg == "gov" else LIZI_NOTE,
                      "due": due(meeting + timedelta(days=7)), "score": q.get("score"), "rank": q.get("rank")})
    short = {s: r for s, r in room.items() if r > 0 and QUOTA[s] > 0}
    return leads, skipped, open_by, short


# --- weekly task templates (pattern of utd_week8_tasks.py) ------------------------------------
def tasks_for(week, leads, open_cards_by_owner, gate):
    M = meeting_of(week)
    nxt = M + timedelta(days=7)
    final_week = nxt > FINAL
    tag = f"Week {week}"
    mine = lambda s: [l for l in leads if l["student"] == s]
    def lead_line(s):
        new = mine(s)
        parts = []
        if new:
            parts.append("New lead cards: " + ", ".join(re.split(r" — | \(", l["name"])[0] for l in new) + ".")
        if open_cards_by_owner.get(s):
            parts.append(f"Finish your {open_cards_by_owner[s]} open lead card(s) first.")
        return " ".join(parts) or "No new lead cards this week."
    T = [
        ("Roel Saenz", M + timedelta(days=1),
         f"[{tag} · Lead] Minutes from Thu {M.month}/{M.day} by {fmt(M + timedelta(days=1))}; agenda for "
         f"{fmt(nxt if not final_week else FINAL)} by {fmt(M + timedelta(days=5))}",
         f"1. Send the {M.month}/{M.day} minutes to Lizi by {fmt(M + timedelta(days=1))} (decisions, action items, "
         f"owners, dates).\n2. Send the next agenda by {fmt(M + timedelta(days=5))}.\n3. Post both as notes on this card."),
        ("Roel Saenz", nxt,
         f"[{tag} · Lead] Team lead cards + READY scoreboard on #3164",
         f"{lead_line('Roel Saenz')} Post the team scoreboard on #3164 (lead cards Done per person). If something is "
         f"stuck, post one sentence on why and a new date on the card. This week's gate: {gate}"),
        ("Roel Saenz", min(nxt, LAST_DUE),
         (f"[{tag} · Lead] Final presentation (Thu Nov 20, 10 AM, in person): full run-through + final deck to Lizi"
          if final_week else
          f"[{tag} · Lead] Final presentation (Thu Nov 20, 10 AM, in person): deck draft progress + who presents what"),
         ("Final deck to Lizi by Wed 11/18 and one full run-through. All work must be finished before the final "
          "presentation; John is not available after Nov 29." if final_week else
          f"Post the current deck draft (or outline) on this card with who owns each section and what the handoff to "
          f"Exos includes (lead list, templates, AI audit, social content). Final presentation is Thu Nov 20, 10 AM, "
          f"in person; all work has to be finished before it.")),
        ("Laura Granados Lopez", nxt,
         f"[{tag} · University segment] ONE lead card this week",
         lead_line("Laura Granados Lopez") + " One lead card per week (Lizi 10/15). If it is not finished by the due "
         "date, post one sentence on why and a new date."),
        ("Adrian Haro", nxt,
         f"[{tag} · Commercial segment] Lead cards + segment/competitive research",
         lead_line("Adrian Haro") + " Lizi sends commercial leads, so write in her voice. " + BANNED_TXT +
         " Research: sources 2023+, linked."),
        ("Karan Vijaya Sankar", nxt,
         f"[{tag} · Gov/civil segment] Lead cards (John sends)",
         lead_line("Karan Vijaya Sankar") + " Government and defense leads are John-send: keep them in John's "
         "voice, signed John Quinn, Cofounder and CEO. Confirm current names and leaders (2026 reorgs)."),
        ("Karan Vijaya Sankar", nxt - timedelta(days=1),
         f"[{tag} · AI audit] Add this week's AI errors + one-paragraph trend by {fmt(nxt - timedelta(days=1))}",
         "Log every Exo error the team found this week (wrong contact, missing draft, banned claim, stale title) "
         "with a source, then write a one-paragraph week-over-week trend."),
        ("Sunidhi Mathew", nxt,
         f"[{tag} · Lead] Lead cards",
         lead_line("Sunidhi Mathew") + " Check who sends each one (John for government and defense, Lizi for "
         "everyone else). " + BANNED_TXT),
        ("Sunidhi Mathew", nxt,
         f"[{tag} · Data Trust] Check every lead card moved to Done this week",
         "For each teammate card moved to Done this week: contact current? every claim sourced? signed by the right "
         "person (John for government and defense, Lizi for everyone else)? 'early 2027' with no month, no "
         "only/first/fastest? PASS -> leave it in Done. FAIL -> post what's wrong and move it back to In Progress."),
        ("Brenda Segovia Saldana", M + timedelta(days=5),
         f"[{tag} · Creative] Next week's posts ready for Lizi by {fmt(M + timedelta(days=5))}",
         "Creative only (no lead cards). Next week's posts from the content calendar, each with its approved link "
         "(microsite, exosaero.com/blog, or the payload calculator at exosaero.com/pricing; never the payload "
         "questionnaire, PUG or investor blog). No specs, prices or dates; Exos-approved photos only."),
    ]
    out = []
    for owner, d, title, desc in T:
        out.append({"title": title, "owner": owner, "assigned_to": owner, "assigned_email": EM[owner],
                    "state": "To Do", "priority": 95, "category": "Payload Sales", "due_date": due(d),
                    "description": desc, "tags": ["utd-capstone", f"week-{week}"], "source": SOURCE})
    return out


# --- build ------------------------------------------------------------------------------------
def propose(week):
    M = meeting_of(week)
    if M > FINAL:
        return None, f"Week {week} meeting {M} is after the final presentation ({FINAL}); nothing to propose"
    prog = IO["program"]()
    gate = next((g["gate"] for g in prog.get("weekly_gates", []) if g.get("week") == week), "")
    existing = student_week_tasks(week)
    if existing:
        return None, f"Week {week} already has {len(existing)} task(s) tagged week-{week}; not proposing again"
    cards = lead_cards()
    leads, skipped, open_by, short = pick_leads(prog.get("work_queue", []), cards, week,
                                                IO["pipeline"](), IO["drafts"]())
    open_cards = {s: n for s, n in open_by.items() if n}
    tasks = tasks_for(week, leads, open_cards, gate)
    return {"week": week, "meeting": M.isoformat(), "tasks": tasks, "leads": leads, "skipped": skipped,
            "open_cards": open_cards, "shortfall": short, "gate": gate}, ""


def render(p):
    L = [f"UTD Team Atlas — Week {p['week']} PROPOSED tasks + lead batch (DRAFT, nothing created)",
         f"Meeting Thu {p['meeting']} -> next Thu; final presentation Thu Nov 20 10 AM in person "
         f"(all due dates capped at {LAST_DUE}); John leaves Nov 29.", f"Week gate: {p['gate']}", "",
         f"WEEKLY TASKS ({len(p['tasks'])})"]
    for i, t in enumerate(p["tasks"], 1):
        L.append(f"{i:>2}. {t['owner']:<24} due {t['due_date'][:10]}  {t['title']}")
        L.append(f"      {t['description']}")
    L += ["", f"LEAD-CARD BATCH ({len(p['leads'])})"]
    for i, l in enumerate(p["leads"], 1):
        L.append(f"{i:>2}. {l['student']:<24} {l['name']}  [{l['segment']}, {l['sender']} sends, score "
                 f"{l['score']}, draft={'yes ' + l['draft_label'] if l['draft_label'] else 'NO - Exo writes one before cards are made'}]")
    if not p["leads"]:
        L.append("    (none available)")
    if p["open_cards"]:
        L += ["", "Open lead cards (count against quota): " + ", ".join(f"{k.split()[0]} {v}" for k, v in p["open_cards"].items())]
    if p["shortfall"]:
        L += ["", "SHORTFALL (queue ran out; new lead sourcing needed): " +
              ", ".join(f"{k.split()[0]} {v}" for k, v in p["shortfall"].items())]
    L += ["", "Skipped from the ranked queue:"] + [f"  - {n[:70]}: {w}" for n, w in p["skipped"]]
    return "\n".join(L)


def build(week=None, dry=False, out=None):
    now = IO["now"]()
    week = week or week_for_build(now)
    st = load_state()
    w = st["weeks"].get(str(week), {})
    if w.get("decision_id") and not dry:
        print(f"Week {week}: Decision {w['decision_id']} already filed; nothing to do"); return w
    p, why = propose(week)
    if not p:
        print(why); log(f"build wk{week}: {why}"); return None
    text = render(p)
    if dry:
        print("=== DRY RUN (no Decision filed, nothing created) ===\n" + text)
        if out:
            open(out, "w").write(text + "\n")
        return p
    body = {"title": f"Go week {week} tasks + lead batch?",
            "question": (f"Create the {len(p['tasks'])} Week {week} student tasks and {len(p['leads'])} new lead "
                         f"card(s) listed in Context on the students' boards?"),
            "type": "yesno", "options": [f"Yes — create Week {week} tasks + lead cards", "No — hold"],
            "priority": "high", "source": "Exo (UTD weekly prep)", "context": text[:20000],
            "relatedItem": f"UTD Team Atlas Week {week}",
            "proposedAction": ("On Yes, Exo creates exactly these tasks and lead cards in MC within ~15 minutes "
                               "(once; never twice). On No, nothing is created; add a note with edits and Exo re-files."),
            "assignedTo": LIZI, "approver": LIZI, "agentClass": AGENT, "dedupeKey": f"utd-weekly-prep-wk{week}"}
    r = IO["file_decision"](body)
    st["weeks"][str(week)] = {"decision_id": r.get("id"), "dedupeKey": body["dedupeKey"],
                              "built": datetime.now(timezone.utc).isoformat(), "proposal": p,
                              "applied": False, "reminded": False}
    save_state(st)
    log(f"build wk{week}: decision={r.get('id')} tasks={len(p['tasks'])} leads={len(p['leads'])}")
    try:
        from fleet_log import event
        if not IO.get("selftest"):
            event(AGENT, "decide", "propose", detail={"decision": r.get("id"), "week": week}, owner="Lizi Quinn")
    except Exception:
        pass
    print(f"Week {week}: Decision {r.get('id')} filed for Lizi ({len(p['tasks'])} tasks, {len(p['leads'])} leads)")
    return st["weeks"][str(week)]


# --- apply / remind ---------------------------------------------------------------------------
def find_decision(w):
    for d in IO["decisions"]():
        if d.get("id") == w.get("decision_id") or (w.get("dedupeKey") and d.get("dedupeKey") == w["dedupeKey"]
                                                      and d.get("answer")):
            if d.get("answer") or d.get("id") == w.get("decision_id"):
                return d
    return None


def answered(d):
    return bool(d and d.get("answer"))


def human_yes(d):
    return (answered(d) and str(d.get("answeredByEmail") or "").strip().lower() in APPROVERS
            and str(d.get("answer")).strip().lower().startswith("yes"))


def apply(dry=False):
    st = load_state()
    done = []
    for wk, w in sorted(st["weeks"].items()):
        if w.get("applied") or w.get("declined") or not w.get("decision_id"):
            continue
        d = find_decision(w)
        if not answered(d):
            continue
        if not human_yes(d):
            if str(d.get("answer")).lower().startswith("no") or str(d.get("answeredByEmail") or "").lower() in APPROVERS:
                w["declined"] = d.get("answer"); log(f"apply wk{wk}: answered {d.get('answer')!r}; nothing created")
            else:
                log(f"apply wk{wk}: answered by non-approver {d.get('answeredByEmail')!r}; ignored")
            continue
        existing = student_week_tasks(wk)
        have = {t["title"] for t in existing}
        if existing and not w.get("partial"):
            w["applied"] = True; w["applied_note"] = f"week-{wk} tasks already existed ({len(existing)}); not re-created"
            log(f"apply wk{wk}: {w['applied_note']}"); continue
        p, made, fails = w["proposal"], [], []
        if dry:
            print(f"DRY apply wk{wk}: would create {len(p['tasks'])} tasks + {len(p['leads'])} leads"); continue
        w["partial"] = True; save_state(st)   # crash mid-run -> resume by title, never duplicate
        for t in p["tasks"]:
            if t["title"] in have:
                continue
            made.append(IO["create_task"](t))
        keys = {g[5:] for c in lead_cards() for g in (c.get("tags") or []) if str(g).startswith("lead:")}
        for l in p["leads"]:
            if l["prefix"] in keys:
                continue
            try:
                made.append(IO["create_lead"](l))
            except Exception as e:
                fails.append(f"{l['name'][:50]}: {e}")
        w.update(applied=True, partial=False, applied_at=datetime.now(timezone.utc).isoformat(),
                 created=made, lead_failures=fails, answered_by=d.get("answeredByEmail"),
                 answered_at=d.get("answeredAt") or d.get("answered_at"))
        save_state(st)
        log(f"apply wk{wk}: created {made} failures={fails}")
        done.append((wk, made, fails))
        if fails:
            IO["discord"](f"UTD Week {wk}: created {len(made)} item(s); {len(fails)} lead card(s) not made: "
                          + "; ".join(fails))
    save_state(st)
    for wk, made, fails in done:
        print(f"Week {wk}: created {len(made)} item(s)" + (f", {len(fails)} lead failures" if fails else ""))
    return done


def remind(dry=False):
    now = IO["now"]()
    st = load_state()
    sent = []
    for wk, w in st["weeks"].items():
        if w.get("applied") or w.get("declined") or w.get("reminded") or not w.get("decision_id"):
            continue
        built = datetime.fromisoformat(w["built"]).astimezone(now.tzinfo)
        tue = (built + timedelta(days=(1 - built.weekday()) % 7 or 7)).replace(hour=9, minute=0, second=0, microsecond=0)
        if now < tue or answered(find_decision(w)):
            continue
        msg = (f"Lizi: Week {wk} UTD tasks + lead batch are waiting on your Go (Decision {w['decision_id']}, "
               f"\"Go week {wk} tasks + lead batch?\"). Nothing is on the students' boards until you answer.")
        if dry:
            print("DRY remind:", msg); continue
        IO["discord"](msg)
        w["reminded"] = now.isoformat()
        sent.append(wk)
    save_state(st)
    return sent


def tick():
    now = IO["now"]()
    if now.weekday() == 6 and now.hour >= 18:   # Sunday 18:00 CT build window
        build()
    apply()
    remind()


# --- output eval ------------------------------------------------------------------------------
def output_eval(st=None, quiet=False):
    st = st or load_state()
    problems = []
    dkeys = {}
    for wk, w in st.get("weeks", {}).items():
        if w.get("dedupeKey") in dkeys:
            problems.append(f"wk{wk}: duplicate Decision dedupeKey {w['dedupeKey']}")
        dkeys[w.get("dedupeKey")] = wk
        p = w.get("proposal") or {}
        per = {}
        for l in p.get("leads", []):
            per[l["student"]] = per.get(l["student"], 0) + 1
            if l["segment"] == "gov" and l["sender"] != "John":
                problems.append(f"wk{wk}: gov lead {l['name'][:40]} not John-send")
            if PARKED_RX.search(l["name"]):
                problems.append(f"wk{wk}: parked org proposed {l['name'][:40]}")
        for s, n in per.items():
            if n > QUOTA.get(s, 0):
                problems.append(f"wk{wk}: {s} gets {n} leads > quota {QUOTA.get(s, 0)}")
        for t in p.get("tasks", []):
            if t["due_date"][:10] > LAST_DUE.isoformat():
                problems.append(f"wk{wk}: task due after final presentation: {t['title'][:40]}")
        if w.get("applied") and w.get("created"):
            if str(w.get("answered_by") or "").lower() not in APPROVERS:
                problems.append(f"wk{wk}: created without a human Yes ({w.get('answered_by')})")
            if len(w["created"]) > len(p.get("tasks", [])) + len(p.get("leads", [])):
                problems.append(f"wk{wk}: created more items than proposed")
    verdict = "FAIL" if problems else "PASS"
    if not quiet:
        print(f"utd-weekly-prep output eval: {verdict} ({len(st.get('weeks', {}))} week(s) checked)"
              + "".join("\n  - " + x for x in problems))
    return not problems


# --- selftest (fixtures only) -----------------------------------------------------------------
def selftest():
    global STATE, LOG
    from zoneinfo import ZoneInfo
    CT = ZoneInfo("America/Chicago")
    ok = True
    def chk(c, label):
        nonlocal ok
        print(("PASS " if c else "FAIL ") + label); ok = ok and bool(c)
    tmp = tempfile.mkdtemp(prefix="utd-weekly-prep-")
    saved = (STATE, LOG, dict(IO), urllib.request.urlopen, subprocess.run)
    STATE, LOG = os.path.join(tmp, "state.json"), os.path.join(tmp, "log")
    def no_net(*a, **k):
        raise AssertionError("network/subprocess used in selftest")
    urllib.request.urlopen = no_net; subprocess.run = no_net
    clock = {"now": datetime(2026, 10, 25, 18, 5, tzinfo=CT)}
    db = {"tasks": [
        {"id": 1, "title": "[Lead] Castelion — verify + get to READY", "owner": "Roel Saenz", "state": "In Progress",
         "tags": ["utd-lead", "lead:Castelion — UPDATED"], "description": "LEAD: Castelion"},
        {"id": 2, "title": "[Lead] Kratos Defense — verify", "owner": "Karan Vijaya Sankar", "state": "To Do",
         "tags": ["utd-lead", "lead:Kratos Defense & Security Solutions"], "description": "LEAD: Kratos Defense"},
        {"id": 3, "title": "[Lead] UMontana — verify", "owner": "Laura Granados Lopez", "state": "Done",
         "tags": ["utd-lead", "lead:UMontana"], "description": "LEAD: UMontana"}]}
    decs, filed, posts = [], [], []
    def sb_get(path):
        m = re.search(r"week-(\d+)", path)
        if m:
            return [t for t in db["tasks"] if f"week-{m.group(1)}" in (t.get("tags") or [])]
        return [t for t in db["tasks"] if "utd-lead" in (t.get("tags") or [])]
    def file_decision(body):
        for d in decs:
            if d["dedupeKey"] == body["dedupeKey"]:
                return {"id": d["id"], "deduped": True}
        d = {"id": f"D-T{len(decs) + 1}", "dedupeKey": body["dedupeKey"], "answer": None}
        decs.append(d); filed.append(body); return {"id": d["id"]}
    def create_task(row):
        tid = 100 + len(db["tasks"]); db["tasks"].append({**row, "id": tid}); return tid
    def create_lead(l):
        if not l["draft_label"]:
            raise RuntimeError("no AI draft")
        tid = 100 + len(db["tasks"])
        db["tasks"].append({"id": tid, "title": "[Lead] " + l["name"], "owner": l["student"], "state": "To Do",
                            "tags": ["utd-lead", "lead:" + l["prefix"], f"week-{l['week']}"]}); return tid
    queue = [
        {"name": "DIU HyCAT Program — Col. X ⭐⭐⭐", "rank": 1, "score": 88},
        {"name": "Kratos Defense & Security Solutions — Josh", "rank": 2, "score": 88, "owner": "Karan Vijaya Sankar", "card": 2},
        {"name": "Lumibird Photonics USA — Quantel", "rank": 3, "score": 65},
        {"name": "Castelion — new angle", "rank": 4, "score": 70},
        {"name": "Acme Orbital Labs", "rank": 5, "score": 60},
        {"name": "Beta Microgravity Inc", "rank": 6, "score": 59},
        {"name": "Gamma Space Bio", "rank": 7, "score": 58},
        {"name": "Delta Payload Co", "rank": 8, "score": 57},
        {"name": "Zeta University of Somewhere", "rank": 9, "score": 56},
        {"name": "Eta State University Lab", "rank": 10, "score": 55},
        {"name": "Sandia Space Lab", "rank": 11, "score": 54},
    ]
    pipe = "**DRAFT ZZ — Col. X, DIU HyCAT Program**\n**DRAFT ZY — Jane, Acme Orbital Labs**\n"
    IO.update(sb_get=sb_get, decisions=lambda: decs, file_decision=file_decision, discord=lambda m: posts.append(m) or True,
              create_task=create_task, create_lead=create_lead, now=lambda: clock["now"], selftest=True,
              program=lambda: {"work_queue": queue, "weekly_gates": [{"week": 9, "gate": "Scale"}]},
              pipeline=lambda: pipe, drafts=lambda: "")
    try:
        chk(week_for_build(clock["now"]) == 9 and meeting_of(9) == date(2026, 10, 29), "Sun 10/25 18:00 -> Week 9 (meeting Thu 10/29)")
        chk(meeting_of(8) == date(2026, 10, 22), "Week 8 meeting = Thu 10/22 (matches utd_week8_tasks.py)")
        p, _ = propose(9)
        per = {}
        for l in p["leads"]:
            per[l["student"]] = per.get(l["student"], 0) + 1
        chk(per.get("Laura Granados Lopez", 0) <= 1, "Laura <= 1 lead")
        chk("Brenda Segovia Saldana" not in per, "Brenda gets no lead cards")
        chk(all(n <= QUOTA[s] for s, n in per.items()), "everyone within quota (open cards counted)")
        chk(per.get("Roel Saenz", 0) <= 2, "Roel's open card counts against his 3")
        names = " ".join(l["name"] for l in p["leads"])
        chk("Lumibird" not in names, "Lizi-parked org skipped")
        chk("Castelion" not in names, "org with an open card skipped")
        chk("Kratos" not in names, "queue item already on a card skipped")
        diu = next(l for l in p["leads"] if l["name"].startswith("DIU"))
        chk(diu["sender"] == "John" and diu["student"] == "Karan Vijaya Sankar" and "John" in diu["note"], "gov lead -> Karan, John sends")
        acme = next(l for l in p["leads"] if l["name"].startswith("Acme"))
        chk(acme["sender"] == "Lizi" and "her voice" in acme["note"] and acme["draft_label"] == "ZY", "commercial lead -> Lizi voice + draft found")
        chk(all(t["due_date"][:10] <= "2026-11-19" for t in p["tasks"]), "all due dates before final presentation")
        chk(len([t for t in p["tasks"] if t["owner"] == "Brenda Segovia Saldana"]) == 1 and
            all("week-9" in t["tags"] and t["source"] == SOURCE for t in p["tasks"]), "Brenda creative task; week-9 tags")
        chk(propose(13)[0] is None, "no proposal after the final presentation (Week 13, meeting 11/26)")
        p12, _ = propose(12)
        chk(p12 and not p12["leads"] and all(t["due_date"][:10] <= "2026-11-19" for t in p12["tasks"]), "final week: no new leads, dues capped 11/19")
        build(); build()
        chk(len(filed) == 1 and filed[0]["title"] == "Go week 9 tasks + lead batch?" and filed[0]["assignedTo"] == LIZI,
            "build files ONE Decision for Lizi; re-run files none")
        n0 = len(db["tasks"])
        apply()
        chk(len(db["tasks"]) == n0, "unanswered -> nothing created")
        clock["now"] = datetime(2026, 10, 27, 8, 59, tzinfo=CT); remind()
        chk(not posts, "no reminder before Tue 09:00")
        clock["now"] = datetime(2026, 10, 27, 9, 1, tzinfo=CT); remind(); remind()
        chk(len(posts) == 1 and "Week 9" in posts[0], "exactly one reminder after Tue 09:00")
        decs[0].update(answer="Yes — create Week 9 tasks + lead cards", answeredByEmail="someone@utdallas.edu")
        apply()
        chk(len(db["tasks"]) == n0, "Yes from a non-approver -> nothing created")
        decs[0].update(answeredByEmail=LIZI)
        apply()
        st = load_state()["weeks"]["9"]
        nt = len([t for t in db["tasks"] if "week-9" in (t.get("tags") or [])])
        chk(st["applied"] and nt == len(st["created"]) and len(st["created"]) >= len(p["tasks"]), "Lizi Yes -> tasks + leads created")
        chk(any("no AI draft" in f for f in st["lead_failures"]), "draft-less lead refused (fail closed)")
        apply(); chk(len([t for t in db["tasks"] if "week-9" in (t.get("tags") or [])]) == nt, "re-run apply creates nothing (idempotent)")
        IO["now"] = lambda: datetime(2026, 11, 1, 18, 5, tzinfo=CT)
        db["tasks"].append({"id": 998, "title": "Exo reminder", "owner": "Exo", "tags": ["utd-capstone", "week-10"]})
        chk(propose(10)[0] is not None, "Exo's own week-N reminder card does not block the week")
        db["tasks"].append({"id": 999, "title": "manual", "owner": "Roel Saenz", "tags": ["utd-capstone", "week-10"]})
        build(); chk(len(filed) == 1, "week already made by hand -> no Decision")
        chk(output_eval(load_state()), "output eval PASS on fixture state")
        bad = {"weeks": {"1": {"dedupeKey": "a", "applied": True, "created": [1], "answered_by": "x@y.com",
                               "proposal": {"tasks": [], "leads": [{"name": "Lumibird", "student": "Laura Granados Lopez",
                                                                    "segment": "gov", "sender": "Lizi"}] * 2}}}}
        chk(not output_eval(bad, quiet=True), "output eval FAILs a bad state (no human Yes, parked, quota, gov voice)")
    finally:
        STATE, LOG = saved[0], saved[1]
        IO.clear(); IO.update(saved[2]); urllib.request.urlopen = saved[3]; subprocess.run = saved[4]
    print("selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    a = sys.argv[1:]
    dry = "--dry-run" in a
    cmd = a[0] if a and not a[0].startswith("-") else ("build" if dry else "")
    if cmd == "build":
        wk = int(a[a.index("--week") + 1]) if "--week" in a else None
        out = a[a.index("--out") + 1] if "--out" in a else None
        build(wk, dry, out)
    elif cmd == "apply":
        apply(dry)
    elif cmd == "remind":
        remind(dry)
    elif cmd == "tick":
        tick()
    elif cmd == "eval":
        sys.exit(0 if output_eval() else 1)
    elif cmd == "selftest":
        sys.exit(0 if selftest() else 1)
    else:
        print(__doc__)
