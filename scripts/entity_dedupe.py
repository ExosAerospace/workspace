#!/usr/bin/env python3
"""
ENTITY-LEVEL TASK DEDUPE — stops "4 tasks for one action". Deterministic, zero LLM tokens.

CONSERVATIVE by design (a wrong merge loses real work):
  * matches a real PERSON name (from the CRM) only when it appears in the task TITLE,
  * ignores titles that name 0 or 2+ different people (reports/lists),
  * excludes company/role names (Capital, Ventures, Relations, "the team", etc.),
  * and only merges when the two titles are genuinely SIMILAR (token overlap >= 0.5 after
    stripping the person name and [..]/version noise).
Same-person tasks with clearly different titles are left alone. Keep richest, cancel the rest.

Run:  python3 scripts/entity_dedupe.py            # dry-run
      python3 scripts/entity_dedupe.py --apply
"""
import os, sys, json, re, datetime, subprocess, urllib.request
import durable_send_shim  # noqa: F401  (durable delivery: spool-then-send)
from collections import defaultdict

SB = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1/"
K = json.load(open(os.path.expanduser("~/.openclaw/secrets.json")))["supabase_service_role_key"]
WS = os.path.expanduser("~/.openclaw/workspace")
OPENCLAW = "/Users/exomac/.local/share/mise/shims/openclaw"
JON = "1501632195163590739"
LOG = os.path.join(WS, "logs", "entity-dedupe.jsonl")
APPLY = "--apply" in sys.argv
SIM_THRESHOLD = 0.5

# tokens that mean a "name" is really a company/role, not a person
CORP = re.compile(r'\b(capital|ventures?|partners?|holdings?|fund|group|inc|llc|corp|co|company|'
                  r'relations|team|point|labs?|systems?|technolog|aerospace|space|industries|'
                  r'associates|solutions|global|international|the|office|program|board|committee|'
                  r'university|institute|agency|command|national|defense|air force|navy|army)\b', re.I)
STOP = set("the a an to for of and with re fw fwd ready send from you approve review revised final "
           "draft v1 v2 v3 v4 pilot email letter update outreach due today paxton".split())


def q(path, method="GET", body=None):
    r = urllib.request.Request(SB + path, data=(json.dumps(body).encode() if body is not None else None),
        method=method, headers={"apikey": K, "Authorization": "Bearer " + K,
        "Content-Type": "application/json", "Prefer": "return=representation"})
    with urllib.request.urlopen(r, timeout=60) as resp:
        raw = resp.read().decode()
        return json.loads(raw) if raw.strip() else []


def page(path, fields):
    out, off = [], 0
    while True:
        pg = q(f"{path}?select={fields}&order=id&limit=1000&offset={off}")
        out += pg
        if len(pg) < 1000:
            return out
        off += 1000


def toks(title, name):
    t = (title or "").lower()
    t = re.sub(r'\[[^\]]*\]', ' ', t)          # strip [..] tags
    t = t.replace(name.lower(), ' ')            # remove the person's name
    t = re.sub(r'[^a-z0-9 ]', ' ', t)
    return {w for w in t.split() if w not in STOP and len(w) > 2}


def sim(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def richness(t):
    return (sum(1 for k in ("description", "due_date", "category") if (t.get(k) or "")),
            str(t.get("created_at") or ""), t.get("priority") or 0)


def main():
    people = set()
    for c in page("contacts", "name"):
        nm = (c.get("name") or "").strip()
        tk = nm.split()
        if 2 <= len(tk) <= 3 and all(re.fullmatch(r"[A-Za-z.'-]{2,}", x) for x in tk) and not CORP.search(nm):
            people.add(nm)
    tasks = [t for t in page("tasks", "id,title,description,tags,state,owner,priority,due_date,created_at")
             if (t.get("state") or "") not in ("Done", "Cancelled")]
    print(f"open tasks: {len(tasks)} | real person names: {len(people)}")

    # each task -> the people named IN ITS TITLE; keep only single-person titles
    by_person = defaultdict(list)
    for t in tasks:
        title = (t.get("title") or "")
        named = [nm for nm in people if nm.lower() in title.lower()]
        if len(named) == 1:
            by_person[named[0]].append(t)

    merged, clusters_seen = 0, 0
    for nm, ts in by_person.items():
        if len(ts) < 2:
            continue
        used = set()
        for i, a in enumerate(ts):
            if a["id"] in used:
                continue
            cluster = [a]
            ta = toks(a.get("title"), nm)
            for b in ts[i + 1:]:
                if b["id"] in used:
                    continue
                if sim(ta, toks(b.get("title"), nm)) >= SIM_THRESHOLD:
                    cluster.append(b); used.add(b["id"])
            if len(cluster) < 2:
                continue
            clusters_seen += 1
            cluster.sort(key=richness, reverse=True)
            keep = cluster[0]
            for dup in cluster[1:]:
                print(f"  {'[merge]' if APPLY else '[would merge]'} #{dup['id']} -> keep #{keep['id']} ({nm}): "
                      f"{(dup.get('title') or '')[:50]}")
                if APPLY:
                    now = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
                    q(f"tasks?id=eq.{dup['id']}", "PATCH", {"state": "Cancelled", "completed_at": now,
                      "description": f"Entity-duplicate of #{keep['id']} (same person: {nm}, near-identical title). Auto-consolidated {now[:10]}."})
                    with open(LOG, "a") as f:
                        f.write(json.dumps({"ts": now, "cancelled": dup["id"], "kept": keep["id"], "person": nm}) + "\n")
                merged += 1

    print(f"\n{'MERGED' if APPLY else 'WOULD MERGE'}: {merged} duplicate task(s) across {clusters_seen} cluster(s).")
    if APPLY and merged:
        try:
            subprocess.run([OPENCLAW, "message", "send", "--channel", "discord", "--target", JON,
                            "-m", f"🔗 Entity dedupe: merged {merged} same-person near-duplicate task(s)."],
                           timeout=60, capture_output=True)
        except Exception:
            pass


if __name__ == "__main__":
    main()
