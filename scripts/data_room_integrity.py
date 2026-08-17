#!/usr/bin/env python3
"""
Data Room Integrity Guard — the "MDB firewall".

MDB Capital declined Exos (2026-08-04) over inconsistencies a diligent reader caught:
un-reconciled valuation/raise numbers, unsupported claims, gov-pipeline-as-base, and
missing governance (no fairness opinion, fuzzy listing path). This scans the ACTIVE
investor-facing set against FIGURES_OF_RECORD.md + a banned-claims list and emits a
Readiness Score + JSON the Mission Control dashboard renders. Nothing about the archive.

v1 scans text-extractable formats (.md .pptx .docx). Figure-checking inside .xlsx/.pdf
is phase 2 (flagged as 'not text-scanned' so coverage is never silently overstated).

Run: python3 scripts/data_room_integrity.py
"""
import os, re, json, zipfile, datetime, glob

ROOT = "/Users/exomac/.openclaw/workspace"
FIGURES = os.path.join(ROOT, "data-room/Exos_SeriesA/FIGURES_OF_RECORD.md")
OUT_JSON = os.path.join(ROOT, "mission-control/data/data-room-readiness.json")

# ── What the investor actually sees. Archive is walled off by design. ──
SCAN_GLOBS = [
    "data-room/**/*.md",
    "data-room/**/*.pptx",
    "data-room/**/*.docx",
    "drafts/Exos_Strategic_Capital_Deck_2026-08-13.pptx",
]
EXCLUDE_DIRS = ("_ARCHIVE_Superseded", "Leonid_TACFI_Match")  # Leonid REJECTED 8/2 — not a live counterparty

# ── Rules. severity: BLOCK = cannot ship red; WARN = fix but not fatal. ──
# Each: (label, regex, severity, allow-rx [context that CLEARS it], require-rx [ctx that must ALSO be present to fire])
def rx(p): return re.compile(p, re.I)
# The rulebook itself necessarily quotes the banned phrases — never claim-scan it.
SKIP_CLAIMS = {os.path.relpath(FIGURES, ROOT)}
RAISE_CTX = rx(r"rais|tranche|round|series\s*a")
BANNED = [
    ("'audited' financials (private co — never claim audited)", rx(r"audited\s+financ|financials?\s+are\s+audited|audited\s+statements?\b"), "BLOCK", rx(r"will\s+be\s+(prepared|available)|once\s+audited|unaudited"), None),
    ("bare 'audited'", rx(r"\baudited\b"), "WARN", rx(r"un-?audited|audit\s+trail|audit\s+log|will\s+be"), None),
    ("2-day / 48-hr turnaround as demonstrated (only PROPOSED under KARMEN)", rx(r"(2[-\s]?day|two[-\s]?day|48[-\s]?hour).{0,30}(turn[-\s]?around|turn)"), "BLOCK", rx(r"propos|karmen|target|design|goal|not\s+demonstrat"), None),
    ("'flying commercially' / 'currently flying' (BLK3 not yet flown)", rx(r"flying\s+commercial|currently\s+flying|now\s+flying|already\s+flying"), "BLOCK", None, None),
    ("absolute 'world's first' / 'only operational|reusable'", rx(r"world'?s\s+first|only\s+operational|only\s+reusable|first\s+commercial\s+reusable"), "WARN", rx(r"one\s+of\s+(only\s+)?three|none\s+we'?re\s+aware"), None),
    ("raise range $40–50M (superseded by $10M first close → $25M)", rx(r"\$?\s*40\s*[-–]\s*50\s*M"), "BLOCK", None, None),
    ("$40M/$50M in a RAISE context (raise of record is $10M→$25M)", rx(r"\$?\s*[45]0\s*M(?:illion)?\b"), "BLOCK", rx(r"note|pilot\s+fund|consortium|test\s+vehicle|\bIP\b|authority|competitor|per\s+flight"), RAISE_CTX),
    ("valuation drift (only $169.7M shows; $252M/$137.8M live behind recon tab)", rx(r"\$?\s*252\s*M|\$?\s*137\.8\s*M"), "WARN", rx(r"reconcil|dcf|behind\s+the\s+tab"), None),
    ("dead/removed entities in a live doc (Jaguar / Aaron Schwartzbart / Leonid)", rx(r"\bjaguar\b|aaron\s+schwartzbart|\bleonid\b"), "WARN", None, None),
]
# Governance gates (C1–C4) — presence signals somewhere in the active set.
GOV_GATES = {
    "C3_fairness_opinion (Eqvista engaged)": rx(r"eqvista|fairness\s+opinion"),
    "C4_listing_narrative (private now / TXSE dated+conditioned)": rx(r"txse|private\s+growth|listing\s+path|dated,?\s+conditioned"),
    "C1_reconciliation_tab (DCF/market behind recon)": rx(r"reconciliation\s+tab|reconcil"),
    "C2_base_upside (contracted base; TACFI/entX labeled upside)": rx(r"labeled\s+upside|contracted\s+(backbone|revenue)|base\s+case"),
}

def extract_text(path):
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext in (".md", ".txt"):
            return open(path, encoding="utf-8", errors="ignore").read(), True
        if ext == ".pptx":
            t = []
            with zipfile.ZipFile(path) as z:
                for n in sorted(x for x in z.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", x)):
                    t.append(re.sub(r"<[^>]+>", " ", z.read(n).decode("utf-8", "ignore")))
            return " ".join(t), True
        if ext == ".docx":
            with zipfile.ZipFile(path) as z:
                xml = z.read("word/document.xml").decode("utf-8", "ignore")
            return re.sub(r"<[^>]+>", " ", xml), True
        return "", False  # xlsx/pdf: not text-scanned in v1
    except Exception as e:
        return f"[extract-error: {e}]", False

def main():
    figs_mtime = os.path.getmtime(FIGURES)
    files = []
    seen = set()
    for g in SCAN_GLOBS:
        for p in glob.glob(os.path.join(ROOT, g), recursive=True):
            if any(d in p for d in EXCLUDE_DIRS): continue
            rp = os.path.relpath(p, ROOT)
            if rp in seen: continue
            seen.add(rp); files.append(p)

    findings, scanned, unscanned = [], [], []
    gov_hits = {k: [] for k in GOV_GATES}
    corpus = ""

    for p in sorted(files):
        rp = os.path.relpath(p, ROOT)
        text, ok = extract_text(p)
        if not ok:
            unscanned.append(rp); continue
        scanned.append(rp)
        corpus += " " + text
        # staleness
        if os.path.getmtime(p) < figs_mtime - 1:
            age = int((figs_mtime - os.path.getmtime(p)) / 86400)
            findings.append({"file": rp, "severity": "WARN", "rule": f"stale — older than FIGURES_OF_RECORD by ~{age}d (may predate a locked figure)"})
        # banned claims — skip the governance meta-layer (rulebook + manifests necessarily
        # quote superseded figures); they're still scanned for staleness + gates above/below.
        if rp not in SKIP_CLAIMS and "MANIFEST" not in os.path.basename(rp).upper():
            for label, pat, sev, allow, require in BANNED:
                for m in pat.finditer(text):
                    s, e = max(0, m.start()-55), min(len(text), m.end()+55)
                    ctx = re.sub(r"\s+", " ", text[s:e]).strip()
                    if allow and allow.search(ctx):      # context clears it
                        continue
                    if require and not require.search(ctx):  # needs corroborating context to fire
                        continue
                    findings.append({"file": rp, "severity": sev, "rule": label, "match": m.group(0).strip(), "context": ctx})
        for gk, gpat in GOV_GATES.items():
            if gpat.search(text): gov_hits[gk].append(rp)

    missing_gates = [k for k, v in gov_hits.items() if not v]
    blocks = [f for f in findings if f["severity"] == "BLOCK"]
    warns = [f for f in findings if f["severity"] == "WARN"]
    score = max(0, 100 - 15*len(blocks) - 3*len(warns) - 8*len(missing_gates))
    status = "GREEN" if (not blocks and not missing_gates) else ("RED" if blocks else "AMBER")

    report = {
        "generated": datetime.datetime.now().isoformat(timespec="seconds"),
        "status": status, "score": score,
        "counts": {"block": len(blocks), "warn": len(warns), "missing_gates": len(missing_gates),
                   "scanned": len(scanned), "not_text_scanned": len(unscanned)},
        "blocks": blocks, "warns": warns,
        "governance": {"present": {k: v for k, v in gov_hits.items() if v}, "missing": missing_gates},
        "scanned_files": scanned, "not_text_scanned": unscanned,
    }
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    json.dump(report, open(OUT_JSON, "w"), indent=2)

    # human summary
    print(f"\n  DATA ROOM READINESS: {status}  (score {score}/100)")
    print(f"  scanned {len(scanned)} docs · {len(blocks)} BLOCK · {len(warns)} WARN · {len(missing_gates)} missing governance gate(s)")
    if unscanned:
        print(f"  NOT text-scanned (xlsx/pdf — phase 2): {len(unscanned)}  [{', '.join(os.path.basename(u) for u in unscanned[:4])}...]")
    if blocks:
        print("\n  ── BLOCK (cannot ship) ──")
        for f in blocks: print(f"   ✗ {f['file']}: {f['rule']}\n       '{f.get('match','')}'  …{f.get('context','')[:80]}")
    if missing_gates:
        print("\n  ── MISSING GOVERNANCE GATES ──")
        for g in missing_gates: print(f"   ✗ {g}")
    if warns:
        print(f"\n  ── WARN ({len(warns)}) ──")
        for f in warns[:12]: print(f"   • {f['file']}: {f['rule']}" + (f"  '{f.get('match','')}'" if f.get('match') else ""))
        if len(warns) > 12: print(f"   … +{len(warns)-12} more (full list in {os.path.relpath(OUT_JSON, ROOT)})")
    print(f"\n  report → {os.path.relpath(OUT_JSON, ROOT)}\n")

if __name__ == "__main__":
    main()
