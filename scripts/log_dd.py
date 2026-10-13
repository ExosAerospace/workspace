#!/usr/bin/env python3
"""Log a due-diligence record to Mission Control dossiers so the whole team can see
DD has ALREADY been done on a company (and nobody repeats it). Upserts by firm. Deterministic.

Usage:
  python3 scripts/log_dd.py --firm "Grant Engine" --domain grantengine.com \
      --person "Sam Tetlow" --email sam@grantengine.com \
      --verdict pass --requester "Phil Eaton" \
      --summary "Legit non-dilutive funding consultancy; biotech-heavy; paid vendor; uncertain ROI." \
      --next "Optional 30-min call only if augmenting SBIR/DoD grant volume"

verdict: pass | caution | fail    (fail should ALSO be added to scripts/failed_dd.py)
"""
import os, sys, json, argparse, datetime, re

WS = os.path.expanduser("~/.openclaw/workspace")
F = os.path.join(WS, "mission-control", "data", "dossiers.json")
COLOR = {"pass": "#2E7D32", "caution": "#B8860B", "fail": "#B00020"}


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--firm", required=True)
    ap.add_argument("--domain", default="")
    ap.add_argument("--person", default="")
    ap.add_argument("--email", default="")
    ap.add_argument("--verdict", default="pass", choices=["pass", "caution", "fail"])
    ap.add_argument("--requester", default="")
    ap.add_argument("--summary", default="")
    ap.add_argument("--next", dest="next_step", default="")
    a = ap.parse_args()

    today = datetime.date.today().isoformat()
    store = json.load(open(F)) if os.path.exists(F) else {"dossiers": []}
    if isinstance(store, list):
        store = {"dossiers": store}
    arr = store.setdefault("dossiers", [])
    sid = "dd-" + slug(a.firm)
    flag = (f"DD {a.verdict.upper()} {today}"
            + (f" (req: {a.requester})" if a.requester else "")
            + (f": {a.summary}" if a.summary else ""))
    # Contacts are stored as DISPLAY STRINGS ("Name (email)"), matching build-dossiers.py, so every
    # reader stays simple (one format). Never store contact objects here.
    def contact_label(name, email):
        lbl = (name or "").strip()
        if email:
            lbl = f"{lbl} ({email})" if lbl else email
        return lbl or None
    contact = contact_label(a.person, a.email)
    dd = {"verdict": a.verdict, "date": today, "requester": a.requester,
          "domain": a.domain, "summary": a.summary}

    d = next((x for x in arr if x.get("id") == sid or (x.get("name", "").lower() == a.firm.lower())), None)
    if d is None:
        arr.append({
            "id": sid, "name": a.firm, "headline": (a.summary[:140] or f"DD {a.verdict}"),
            "stage": f"DD {a.verdict.title()}", "stage_color": COLOR[a.verdict],
            "deals": [], "status": f"DD complete ({a.verdict}) {today}",
            "next_step": a.next_step, "flags": [flag],
            "contacts": [contact] if contact else [], "agreements": [],
            "last_touch": today, "dd": dd,
        })
        action = "created"
    else:
        d["stage"] = f"DD {a.verdict.title()}"; d["stage_color"] = COLOR[a.verdict]
        d["status"] = f"DD complete ({a.verdict}) {today}"; d["last_touch"] = today
        if a.next_step:
            d["next_step"] = a.next_step
        d.setdefault("flags", []).insert(0, flag)
        if contact and not any(
                contact == c or (a.email and a.email in str(c)) for c in d.get("contacts", [])):
            d.setdefault("contacts", []).append(contact)
        d["dd"] = dd
        action = "updated"

    json.dump(store, open(F, "w"), indent=2)
    print(f"DD dossier {action}: {a.firm} [{a.verdict}] -> {F}")

    # A FAIL is a block: register it in the failed-DD registry, which rebuilds the blocked-senders
    # list immediately (Phil 10/13: every failed-DD entity, automatically, every time).
    if a.verdict == "fail" and (a.domain or a.email):
        sys.path.insert(0, os.path.join(WS, "scripts"))
        import failed_dd
        failed_dd.add(a.firm, [a.domain] if a.domain else [], [a.email] if a.email else [],
                      [a.person] if a.person else [], reason=a.summary, source="log_dd")
        print(f"failed-DD registry + blocked-senders list updated: {a.firm}")


if __name__ == "__main__":
    main()
