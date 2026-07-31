#!/usr/bin/env python3
"""
mission-score.py — the CEO Decision Architecture scorer (SHADOW mode).

Computes a composite Mission Score (0-100) for every open Mission Control task from the
signals we already collect, so the board can rank work by what actually moves Exos forward
instead of a hand-typed priority integer. This is the D (Decision Architecture) of DRIVE
feeding the DECIDE layer of the Intelligence Stack.

SHADOW / non-destructive: it writes ONLY to mission-control/data/mission-scores.json (a
side store the board joins in). It never writes to the Supabase tasks table and never
changes the board's default sort. Flip to live only after review.

Dimensions (weights):
  strategic (30)  MTP/mission-pillar fit (Capital-Bridge/flight > SeriesA/Scorpius > gov capture > BD > ops)
  value     (25)  parsed $ contract/opportunity size, log-scaled
  urgency   (25)  days-to-deadline curve (submittal close-dates included)
  signal    (15)  live cron signals (watched-sender, system/infra, security)
  aging     (10)  overdue tasks accrue score so they can't rot
  + label floor    small credit for a human-set high priority (intent isn't ignored)
  × blocker factor  a task gated by an OPEN decision / export-control hold drops on the
                    active board and is flagged for the "Blocked — needs decision" lane.

Run: python3 scripts/mission-score.py   (scheduled via launchd com.exos.mission-score)
"""

# --- supabase retry/backoff shim (auto-added) ---
import os as _sbu_os, sys as _sbu_sys; _sbu_sys.path.insert(0, _sbu_os.path.dirname(_sbu_os.path.abspath(__file__)))
import supabase_util as _sbu; _sbu.install()
# --- end shim ---
import json, os, re, math, time, urllib.request
from datetime import datetime, timezone, date

WS = "/Users/exomac/.openclaw/workspace"
DATA = os.path.join(WS, "mission-control", "data")
SECRETS = os.path.expanduser("~/.openclaw/secrets.json")
OUT = os.path.join(DATA, "mission-scores.json")
DEC_FILE = os.path.join(DATA, "decisions.json")
PINBOX = os.path.join(WS, "logs", "priority-inbox-hits.jsonl")
SUPA = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1/"

WEIGHTS = {"strategic": 30, "value": 25, "urgency": 25, "signal": 15, "aging": 10}

# Strategic decision layer (Jon 2026-07-21): each task is scored on how well it ladders to its
# OWNER's North Star — CEO/Jon → Series A, everyone else → Revenue, Neil → Part 450.
_NS_PATH = os.path.join(WS, "mission-control", "data", "north-stars.json")
NS = json.load(open(_NS_PATH)) if os.path.exists(_NS_PATH) else {"owner_map": {}, "default": "revenue", "north_stars": {}}


def owner_north_star(email, owner):
    e = (email or "").lower()
    m = NS.get("owner_map", {})
    if e in m:
        return m[e]
    o = (owner or "").lower()
    if "milburn" in o:
        return "part_450"
    if e == "jquinn@exosaero.com" or o in ("jon", "john quinn", "jquinn"):
        return "series_a"
    return NS.get("default", "revenue")


def classify_north_star(text):
    """Which North Star does this task actually ladder to (by content)? Returns
    (ns_key, strategic_pts 0-30, label). 'unaligned' = ladders to none (kill/defer candidate)."""
    low = (text or "").lower()
    best_ns, best_hits = "unaligned", 0
    for ns, cfg in NS.get("north_stars", {}).items():
        hits = sum(1 for k in cfg.get("keywords", []) if k in low)
        if hits > best_hits:
            best_ns, best_hits = ns, hits
    pts = 30 if best_hits >= 2 else (18 if best_hits == 1 else 5)
    label = NS.get("north_stars", {}).get(best_ns, {}).get("label", "Unaligned (no North Star)")
    return best_ns, pts, label

DOLLAR = re.compile(r'\$\s?([\d,]+(?:\.\d+)?)\s?([kKmMbB]|million|billion|thousand)?')


def supa_get(path):
    k = json.load(open(SECRETS))["supabase_service_role_key"]
    for i in range(4):
        try:
            return json.loads(urllib.request.urlopen(urllib.request.Request(
                SUPA + path, headers={"apikey": k, "Authorization": "Bearer " + k}), timeout=30).read())
        except Exception:
            if i == 3:
                raise
            time.sleep(2)


def supa_get_all(select_path):
    """Paginated fetch — PostgREST caps every response at 1000 rows regardless of limit=, so page
    with offset until a short page. Without this the scorer only sees the first 1000 tasks and
    everything beyond (higher ids) goes unscored. select_path must NOT include limit/offset."""
    out, off = [], 0
    while True:
        page = supa_get(f"{select_path}&order=id&limit=1000&offset={off}")
        out += page
        if len(page) < 1000:
            return out
        off += 1000


def parse_dollars(text):
    best = 0
    for m in DOLLAR.finditer(text or ""):
        try:
            n = float(m.group(1).replace(",", ""))
        except Exception:
            continue
        unit = (m.group(2) or "").lower()
        mult = {"k": 1e3, "thousand": 1e3, "m": 1e6, "million": 1e6,
                "b": 1e9, "billion": 1e9}.get(unit, 1)
        best = max(best, n * mult)
    return best


def pillar_of(text):
    for name, pts, rx in PILLARS:
        if rx.search(text or ""):
            return name, pts
    return DEFAULT_PILLAR[0], DEFAULT_PILLAR[1]


def value_score(dollars):
    if dollars <= 0:
        return 0
    # $50k→~6, $1M→~15, $10M→~22, $25M→~25 (capped)
    return round(min(25, max(0, (math.log10(dollars) - 3) * 7)), 1)


def days_until(due):
    if not due:
        return None
    try:
        d = datetime.strptime(str(due)[:10], "%Y-%m-%d").date()
        return (d - date.today()).days
    except Exception:
        return None


def urgency_score(days, text):
    if days is None:
        # no date, but language implies a deadline → small credit
        return 6 if re.search(r'deadline|due |submittal|\bcob\b|close date|by (?:mon|tue|wed|thu|fri)', text or "", re.I) else 0
    if days <= 0:
        return 25
    for lim, sc in [(2, 25), (7, 20), (14, 14), (30, 8), (60, 4)]:
        if days <= lim:
            return sc
    return 2


def signal_score(t, pinbox_terms):
    s = 0
    blob = " ".join(str(t.get(f, "") or "") for f in ("title", "description", "source", "tags")).lower()
    if "task-sys-cron" in blob or "cron-watchdog" in blob or t.get("source") == "cron-watchdog":
        s = max(s, 12)   # system/infra failure — high floor
    if re.search(r'\.mil\b|nasa\.gov|cerberus|\bmda\b|space force|\busaf\b', blob):
        s = max(s, 8)
    if "nightly-security" in blob or "security" == t.get("category"):
        s = max(s, 6)
    # watched-sender inbox hit whose subject shares 2+ distinctive tokens with the task title
    ttl = set(re.findall(r"[a-z0-9]{4,}", (t.get("title") or "").lower()))
    for subj in pinbox_terms:
        if len(ttl & subj) >= 2:
            s = max(s, 8)
            break
    return s


def aging_score(days, state):
    if str(state).lower() in ("done", "complete", "completed"):
        return 0
    if days is not None and days < 0:
        return round(min(10, 3 + abs(days) * 0.3), 1)
    return 0


PIN_RX = re.compile(r'pin:(\d{1,3})', re.I)


def manual_pin(tags):
    """Extract a manual Mission-Score override from a `pin:<N>` tag (0-100), if present.
    A pin is a deliberate human override set from the board's Edit tab — it HARD-SETS the
    displayed score, beating the computed value and the blocker downgrade. Tags come back
    from PostgREST as a list, but tolerate a raw string too. Returns int 0-100 or None."""
    if not tags:
        return None
    if isinstance(tags, (list, tuple)):
        blob = " ".join(str(x) for x in tags)
    else:
        blob = str(tags)
    m = PIN_RX.search(blob)
    if not m:
        return None
    try:
        return max(0, min(100, int(m.group(1))))
    except Exception:
        return None


def main():
    # Score EVERY task (Jon 2026-07-29: "all tasks have some kind of score"). Legacy-lane items
    # (source=mc-board-legacy) are hidden from the main board but several are real strategic work,
    # so they get scored too — the score is a shadow side-store, harmless where the task isn't shown.
    tasks = supa_get_all("tasks?select=id,title,description,state,priority,due_date,owner,"
                         "assigned_email,source,tags,category,updated_at")
    # open decisions → blocker map (match relatedItem or an id reference to the task)
    dec = json.load(open(DEC_FILE)) if os.path.exists(DEC_FILE) else []
    dec = dec if isinstance(dec, list) else dec.get("decisions", [])
    open_dec = [d for d in dec if str(d.get("status", "")).lower() == "open"]

    def blocked_by(tid):
        sid = str(tid)
        for d in open_dec:
            rel = str(d.get("relatedItem") or "")
            if rel == sid:
                return d.get("id")
            if re.search(r'\btask[ #-]*' + sid + r'\b', (d.get("context") or "") + " " + (d.get("title") or ""), re.I):
                return d.get("id")
            if str(d.get("source", "")).startswith("Export-control") and rel == sid:
                return d.get("id")
        return None

    pinbox_terms = []
    if os.path.exists(PINBOX):
        try:
            for line in open(PINBOX):
                try:
                    subj = json.loads(line).get("subject", "")
                    pinbox_terms.append(set(re.findall(r"[a-z0-9]{4,}", subj.lower())))
                except Exception:
                    continue
        except Exception:
            pass

    scores = {}
    for t in tasks:
        if str(t.get("state", "")).lower() in ("done", "complete", "completed"):
            continue
        text = (t.get("title") or "") + " " + (t.get("description") or "")
        ns, strategic, pillar = classify_north_star(text)
        role_ns = owner_north_star(t.get("assigned_email"), t.get("owner"))
        val = value_score(parse_dollars(text))
        days = days_until(t.get("due_date"))
        urg = urgency_score(days, text)
        sig = signal_score(t, pinbox_terms)
        age = aging_score(days, t.get("state"))
        label_floor = min(12, (t.get("priority") or 0) * 0.15)
        raw = strategic + val + urg + sig + age + label_floor
        blk = blocked_by(t["id"])
        factor = 0.45 if blk else 1.0
        computed = round(min(100, raw) * factor)
        # Manual override: a `pin:<N>` tag hard-sets the score, beating the computed value
        # (and the blocker downgrade). Explicit human intent wins. The computed score is kept
        # in the breakdown so we can show "pinned to 95 (would compute 58)".
        pin = manual_pin(t.get("tags"))
        final = pin if pin is not None else computed
        scores[str(t["id"])] = {
            "score": final, "pillar": pillar, "blocked": bool(blk),
            "pinned": pin is not None, "pin_value": pin, "computed_score": computed,
            "north_star": ns, "role_ns": role_ns, "owner": t.get("assigned_email") or t.get("owner"),
            "title": (t.get("title") or "")[:70],
            "blocked_by": blk, "days_to_due": days,
            "breakdown": {"strategic": strategic, "value": val, "urgency": urg,
                          "signal": sig, "aging": age, "label_floor": round(label_floor, 1),
                          "blocker_factor": factor},
        }
    ranked = sorted(scores.items(), key=lambda kv: -kv[1]["score"])
    now = datetime.now(timezone.utc)
    out = {
        "generated": now.isoformat(),
        "generated_display": now.astimezone().strftime("%Y-%m-%d %H:%M") + " local",
        "mode": "shadow",
        "weights": WEIGHTS,
        "count": len(scores),
        "top": [{"task_id": tid, **v} for tid, v in ranked[:20]],
        "scores": scores,
    }
    tmp = OUT + ".tmp"
    json.dump(out, open(tmp, "w"), indent=2)
    os.replace(tmp, OUT)
    blocked = sum(1 for v in scores.values() if v["blocked"])
    print(f"scored {len(scores)} open tasks | blocked(gated): {blocked} | top score: "
          f"{ranked[0][1]['score'] if ranked else 0} | -> {OUT}")


if __name__ == "__main__":
    main()
