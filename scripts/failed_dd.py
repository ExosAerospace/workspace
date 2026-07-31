#!/usr/bin/env python3
"""
FAILED-DD REGISTRY — shared blocklist of entities that failed due diligence
(cold-broker / advance-fee / scam solicitations). Anyone at Exos who gets a
communication from one of these is meant to recognize it instantly.

- lead-auto-capture.py calls check() before creating a CRM lead: a match is
  flagged as do-not-engage instead of becoming a live lead.
- DD-on-inbound can call check() to short-circuit (return the known verdict
  without re-running DD).

CLI:
  python3 scripts/failed_dd.py check <email-or-domain-or-name>
  python3 scripts/failed_dd.py add --firm "X" --domain x.com --email a@x.com --person "Name" --reason "..." [--category "..."]
  python3 scripts/failed_dd.py list
"""
import os, sys, json, argparse
from datetime import date

WS = os.path.expanduser("~/.openclaw/workspace")
REG = os.path.join(WS, "config", "failed-dd-registry.json")


def load():
    try:
        return json.load(open(REG))
    except Exception:
        return {"entities": []}


def save(reg):
    reg["updated"] = date.today().isoformat()
    json.dump(reg, open(REG, "w"), indent=2)


def check(email=None, domain=None, name=None):
    """Return the matching failed-DD entity dict, or None.
    Matches on exact email, exact domain, or firm/person name substring."""
    email = (email or "").strip().lower()
    domain = (domain or "").strip().lower()
    if not domain and "@" in email:
        domain = email.split("@")[-1]
    name = (name or "").strip().lower()
    for e in load().get("entities", []):
        emails = [x.lower() for x in e.get("emails", [])]
        domains = [x.lower() for x in e.get("domains", [])]
        # EXACT full-name / firm equality only — never substring (a "Josh" must not
        # match "Josh Keller", or every short first name false-flags).
        names = [x.lower().strip() for x in (e.get("people", []) + [e.get("firm", "")]) if x]
        if email and email in emails:
            return e
        if domain and domain in domains:
            return e
        if name and name in names:
            return e
    return None


def add(firm, domains=None, emails=None, people=None, reason="", category="cold-broker / advance-fee flag",
        verdict="do-not-engage", source="manual"):
    reg = load()
    ents = reg.setdefault("entities", [])
    firm_l = (firm or "").strip().lower()
    existing = next((e for e in ents if e.get("firm", "").strip().lower() == firm_l), None)
    entry = existing or {"firm": firm, "domains": [], "emails": [], "people": []}
    for k, vals in (("domains", domains), ("emails", emails), ("people", people)):
        for v in (vals or []):
            v = v.strip()
            if v and v.lower() not in [x.lower() for x in entry[k]]:
                entry[k].append(v)
    entry.update({"verdict": verdict, "category": category, "reason": reason or entry.get("reason", ""),
                  "date": date.today().isoformat(), "source": source})
    if not existing:
        ents.append(entry)
    save(reg)
    return entry


def _cli():
    a = sys.argv[1] if len(sys.argv) > 1 else ""
    if a == "check":
        tok = sys.argv[2] if len(sys.argv) > 2 else ""
        hit = check(email=tok if "@" in tok else None,
                    domain=tok if "." in tok and "@" not in tok else None,
                    name=tok if "." not in tok and "@" not in tok else None)
        print(json.dumps(hit, indent=2) if hit else "NO MATCH (not a known failed-DD entity)")
    elif a == "add":
        p = argparse.ArgumentParser()
        p.add_argument("--firm", required=True); p.add_argument("--domain", action="append", default=[])
        p.add_argument("--email", action="append", default=[]); p.add_argument("--person", action="append", default=[])
        p.add_argument("--reason", default=""); p.add_argument("--category", default="cold-broker / advance-fee flag")
        p.add_argument("--source", default="manual")
        ns = p.parse_args(sys.argv[2:])
        print(json.dumps(add(ns.firm, ns.domain, ns.email, ns.person, ns.reason, ns.category, source=ns.source), indent=2))
    elif a == "list":
        for e in load().get("entities", []):
            print(f"- {e['firm']}: {e.get('domains')} {e.get('emails')} [{e.get('verdict')}]")
    else:
        print(__doc__)


if __name__ == "__main__":
    _cli()
