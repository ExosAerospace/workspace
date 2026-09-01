#!/usr/bin/env python3
"""
build_mnda_registry.py — single source of truth for "which company has an MNDA on record."
Auto-derives from (a) completed/partial DocuSign e-sign envelopes (envelopes.json),
(b) executed inbound-contract MNDA files, and merges an authoritative MANUAL_SEED for MNDAs
signed OUTSIDE MC (e.g. MDB in real DocuSign) or held as files/memory.

Writes mission-control/data/mnda-registry.json keyed by a normalized company name:
  { "<norm>": {company, status, date, source, on_record} }
status: executed | exos_signed | partial | pending | signature_ready
on_record (drives the purple border) = status == 'executed'

CRM/ERP/dossier surfaces read this via /api/mnda or the /api/crm row enrichment.
Run:  python3 scripts/build_mnda_registry.py   (idempotent; re-run whenever an MNDA changes)
"""
import json, os, re, glob

WS = os.path.expanduser("~/.openclaw/workspace")
ENV = os.path.join(WS, "mission-control", "data", "envelopes.json")
OUT = os.path.join(WS, "mission-control", "data", "mnda-registry.json")
INBOUND = os.path.join(WS, "inbound-contracts")

def norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())

# Authoritative entries (signed outside MC, on file, or memory-recorded). These win over derived.
MANUAL_SEED = {
    "MDB Capital Holdings":        {"status": "executed", "date": None,        "source": "real DocuSign (signed outside MC — confirm date)"},
    "Innovation Dojo Japan":       {"status": "executed", "date": "2026-04-23","source": "inbound-contracts (export-hardened mutual NDA)"},
    "University of North Dakota":  {"status": "executed", "date": None,        "source": "UND MNDA (Dr. Gupta) — confirm date"},
    "Gloyer-Taylor Laboratories":  {"status": "signature_ready", "date": None, "source": "uploads/MNDA_Exos_GloyerTaylorLabs (awaiting signature)"},
}

def counterparty_from_title(t):
    t = re.sub(r"\(rev\s*\d+\)", "", t, flags=re.I).strip()
    for sep in [" / ", " and ", " & ", " with "]:
        if sep in t:
            t = t.split(sep)[-1]
    # strip leading NDA/MNDA/Mutual noise and Exos self-reference
    t = re.sub(r"^(mutual\s+)?(m?nda|master nda|non-disclosure agreement)\s*[-—:]?\s*", "", t, flags=re.I)
    t = re.sub(r"exos aerospace( systems.*)?", "", t, flags=re.I).strip(" -—/&")
    t = re.sub(r"\bmaster nda\b|\bm?nda\b", "", t, flags=re.I).strip(" -—/&")
    return t.strip()

def derive_from_envelopes():
    out = {}
    try:
        envs = json.load(open(ENV))
    except Exception:
        return out
    for e in envs:
        title = e.get("title", "")
        if not re.search(r"\bm?nda\b|non-disclos", title, re.I):
            continue
        cp = counterparty_from_title(title)
        if not cp:
            continue
        sg = e.get("signers", [])
        signed = [s for s in sg if s.get("signed")]
        dates = sorted([s.get("signedAt") for s in signed if s.get("signedAt")])
        date = (dates[-1] or "")[:10] if dates else (e.get("completedAt") or e.get("createdAt") or "")[:10]
        if not sg:
            status = "pending"
        elif len(signed) == 0:
            status = "pending"
        elif len(signed) < len(sg):
            status = "partial"
        elif len(sg) == 1:
            status = "exos_signed"     # only Exos signed; counterparty countersignature pending
        else:
            status = "executed"
        out[norm(cp)] = {"company": cp, "status": status, "date": date or None,
                         "source": f"docusign:{e.get('id')}"}
    return out

def derive_from_inbound():
    out = {}
    if not os.path.isdir(INBOUND):
        return out
    for f in glob.glob(os.path.join(INBOUND, "**", "*.pdf"), recursive=True) + \
             glob.glob(os.path.join(INBOUND, "**", "*.docx"), recursive=True):
        name = os.path.basename(f)
        if not re.search(r"nda|non-disclos", name, re.I):
            continue
        executed = bool(re.search(r"execut|signed", name, re.I))
        # infer counterparty from parent folder (e.g. IDJ_Japan) or filename
        folder = os.path.basename(os.path.dirname(f))
        cp = folder.replace("_", " ").strip()
        dm = re.search(r"(20\d{2})[-_]?(\d{2})[-_]?(\d{2})", name)
        date = f"{dm.group(1)}-{dm.group(2)}-{dm.group(3)}" if dm else None
        key = norm(cp)
        if key and (key not in out or executed):
            out[key] = {"company": cp, "status": "executed" if executed else "pending",
                        "date": date, "source": f"inbound-contracts/{folder}"}
    return out

def main():
    reg = {}
    reg.update(derive_from_inbound())
    reg.update(derive_from_envelopes())   # envelope-derived beats folder-derived
    for company, info in MANUAL_SEED.items():
        reg[norm(company)] = {"company": company, **info}   # manual seed is authoritative
    # collapse known aliases (same entity, different derived name)
    ALIAS = {"idjjapan": "innovationdojojapan"}
    for a, c in ALIAS.items():
        if a in reg and c in reg:
            del reg[a]
    for k, v in reg.items():
        v["on_record"] = (v.get("status") == "executed")
    json.dump(reg, open(OUT, "w"), indent=2)
    on = [v["company"] for v in reg.values() if v["on_record"]]
    print(f"wrote {OUT}: {len(reg)} entries | on_record (purple): {len(on)} -> {', '.join(sorted(on))}")
    for v in sorted(reg.values(), key=lambda x: x["company"]):
        print(f"  {v['status']:15} | {v.get('date') or '(no date)':10} | {v['company']}")

if __name__ == "__main__":
    main()
