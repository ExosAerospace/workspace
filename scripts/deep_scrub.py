#!/usr/bin/env python3
"""
Deep CUI/ITAR scrub for the Exos workspace/data room.
Extracts text from every doc and flags export-controlled markings + controlled
technical content BEFORE off-site sync to non-CUI boxes (Mac backup / DGX Spark).

Output: compliance/deep-scrub-report.md  (content-free: filenames + matched
markers + short context only — the report itself is NOT CUI).
"""
import os, re, subprocess, zipfile, sys, html, json
from pathlib import Path

ROOT = Path("/Users/exomac/.openclaw/workspace")
EXCLUDE_DIRS = {".git", "node_modules", ".openclaw-cli-images", "compliance"}
# compliance/ excluded so we don't flag the remediation logs themselves.

# ---- marker definitions -------------------------------------------------
# TIER 1: explicit control markings — near-certain controlled data.
TIER1 = {
    "CUI banner":        r"\bCUI\b(?![a-z])",
    "Controlled Unclassified": r"controlled unclassified information",
    "ITAR":              r"\bITAR\b|international traffic in arms",
    "Export Controlled": r"export[- ]controlled|export control(?:led)? (?:data|information|warning)",
    "EAR / ECCN":        r"\bEAR99\b|\bECCN\b|export administration regulation",
    "USML / CFR cite":   r"\bUSML\b|22 ?C\.?F\.?R\.?|15 ?C\.?F\.?R\.? ?(?:730|740|774)",
    "Distribution Stmt": r"distribution statement [b-f]\b|distribution [b-f]\b(?: |:)",
    "FOUO":              r"\bFOUO\b|for official use only",
    "NOFORN":            r"\bNOFORN\b",
    "Gov Furnished":     r"government[- ]furnished|\bGFE\b|\bGFI\b",
    "Secret/Classified": r"\b(?:SECRET|CONFIDENTIAL)//|classified national security",
}

# TIER 2: controlled TECHNICAL content categories — manual review.
# (business/BD use of these words is common; require technical co-occurrence.)
TIER2 = {
    "RDRE/detonation perf": r"rotating detonation|\bRDRE\b|detonation (?:wave|chamber|engine)",
    "Propulsion perf data": r"chamber pressure|mixture ratio|mass flow rate|specific impulse|\bIsp\b|injector (?:design|element)|nozzle (?:expansion|geometry|contour)|throat (?:diameter|area)",
    "Structural loads data": r"loads data|coupled loads|load cases?\b|flight loads|design load|limit load|ultimate load|vibration (?:spectr|environment|test level)|shock (?:spectr|response)|random vibration|PSD|g[- ]?levels?",
    "Trajectory/GNC":     r"trajectory (?:data|optimization)|guidance (?:law|algorithm)|navigation (?:filter|state)|flight (?:profile|envelope) data|apogee.*velocity|state vector",
    "DARPA DSO tech":     r"DARPA|\bDSO\b|HR001125S0013",
    "SBIR PhaseII tech":  r"FA9300|phase ii (?:technical|final report|deliverable)|SBIR.*technical (?:volume|data)",
    "NASA GFE tech":      r"NASA.*(?:GFE|government furnished|usage agreement)|teasley",
    "Cryo/Type-V tech":   r"type[- ]?(?:v|5) (?:tank|cryo)|cryogenic (?:tank|storage|transfer).*(?:design|pressure|test data)|composite overwrap|\bCOPV\b",
}

ALL = {**{k: ("T1", v) for k, v in TIER1.items()},
       **{k: ("T2", v) for k, v in TIER2.items()}}
COMPILED = {k: (t, re.compile(v, re.IGNORECASE)) for k, (t, v) in ALL.items()}

# ---- text extraction ----------------------------------------------------
def extract(path: Path) -> str:
    ext = path.suffix.lower()
    try:
        if ext in (".md", ".txt", ".csv", ".json", ".html"):
            return path.read_text(errors="ignore")
        if ext == ".pdf":
            r = subprocess.run(["pdftotext", "-q", str(path), "-"],
                               capture_output=True, timeout=90)
            return r.stdout.decode(errors="ignore")
        if ext == ".docx":
            r = subprocess.run(["textutil", "-convert", "txt", "-stdout", str(path)],
                               capture_output=True, timeout=90)
            return r.stdout.decode(errors="ignore")
        if ext in (".pptx", ".xlsx"):
            out = []
            with zipfile.ZipFile(path) as z:
                for n in z.namelist():
                    if n.endswith(".xml") and ("slide" in n or "sheet" in n
                                               or "sharedStrings" in n or "notes" in n):
                        try:
                            x = z.read(n).decode(errors="ignore")
                            out.append(re.sub(r"<[^>]+>", " ", x))
                        except Exception:
                            pass
            return html.unescape(" ".join(out))
    except Exception as e:
        return f"__EXTRACT_ERROR__ {e}"
    return ""

# ---- scan ---------------------------------------------------------------
def walk():
    for dp, dn, fn in os.walk(ROOT):
        dn[:] = [d for d in dn if d not in EXCLUDE_DIRS]
        for f in fn:
            p = Path(dp) / f
            if p.suffix.lower() in (".docx", ".pdf", ".pptx", ".xlsx",
                                    ".md", ".txt", ".csv"):
                yield p

results = []
errors = []
for p in walk():
    text = extract(p)
    if text.startswith("__EXTRACT_ERROR__"):
        errors.append((str(p.relative_to(ROOT)), text))
        continue
    hits = {}
    for name, (tier, rx) in COMPILED.items():
        m = rx.search(text)
        if m:
            s = max(0, m.start() - 40); e = min(len(text), m.end() + 40)
            ctx = re.sub(r"\s+", " ", text[s:e]).strip()
            hits[name] = (tier, ctx)
    if hits:
        t1 = [k for k, v in hits.items() if v[0] == "T1"]
        results.append({
            "file": str(p.relative_to(ROOT)),
            "tier": "T1" if t1 else "T2",
            "markers": hits,
        })

# T1 files first, then T2
results.sort(key=lambda r: (r["tier"] != "T1", r["file"]))

t1 = [r for r in results if r["tier"] == "T1"]
t2 = [r for r in results if r["tier"] == "T2"]

lines = ["# Deep CUI/ITAR Scrub Report",
         "",
         f"Scanned workspace (excl {', '.join(sorted(EXCLUDE_DIRS))}). "
         "Content-free: filenames + matched marker + short context only.",
         "",
         f"- **TIER 1 (explicit control markings — quarantine candidates):** {len(t1)} files",
         f"- **TIER 2 (controlled technical content — review):** {len(t2)} files",
         f"- **Extraction errors:** {len(errors)} files",
         "",
         "## TIER 1 — explicit control markings", ""]
for r in t1:
    lines.append(f"### `{r['file']}`")
    for k, (tier, ctx) in r["markers"].items():
        lines.append(f"- **[{tier}] {k}** — …{ctx}…")
    lines.append("")
lines += ["## TIER 2 — controlled technical content (review)", ""]
for r in t2:
    mk = ", ".join(f"{k}" for k in r["markers"])
    lines.append(f"- `{r['file']}` — {mk}")
lines += ["", "## Extraction errors (manual check)", ""]
for f, e in errors:
    lines.append(f"- `{f}` — {e[:80]}")

(ROOT / "compliance" / "deep-scrub-report.md").write_text("\n".join(lines))
json.dump({"t1": t1, "t2": t2, "errors": errors},
          open(ROOT / "compliance" / "deep-scrub-report.json", "w"), indent=1)
print(f"T1={len(t1)} T2={len(t2)} errors={len(errors)}")
print(f"Report: compliance/deep-scrub-report.md")
