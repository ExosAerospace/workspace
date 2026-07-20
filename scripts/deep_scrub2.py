#!/usr/bin/env python3
"""
Deep CUI/ITAR scrub v2 — high precision.
Distinguishes documents that ARE controlled data from documents that merely
DISCUSS compliance (CMMC/CUI posture, RFI responses, ITAR as a selling point).

Two independent signals:
  BANNER  = a genuine export-control marking/warning ON the document
            (CUI// banner, ITAR warning statement, Distribution Statement B-F,
             "technical data ... export ... restricted").
  TECHDATA = actual controlled TECHNICAL data (numeric propulsion/loads/
             trajectory values, or government-furnished technical files).

A file is a QUARANTINE CANDIDATE only if it has a BANNER, or TECHDATA with
hard numeric/engineering signal. Pure compliance-discussion is excluded.
"""
import os, re, subprocess, zipfile, html, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import itar_ear_screen as ee   # shared source of truth for CAD/artifact list + LLM classifier

ROOT = Path("/Users/exomac/.openclaw/workspace")
EXCLUDE_DIRS = {".git", "node_modules", ".openclaw-cli-images", "compliance"}
# Depth: controlled ARTIFACTS by file type (CAD / native-engineering / analysis / EDA / GNC model).
# The file itself is controlled — no content extraction needed.
ARTIFACT_EXTS = {e.lower() for e in ee.CAD_EXTS}
USE_LLM = "--llm" in sys.argv   # opt-in: LLM-review the borderline docs (topic hit, no numeric co-signal)

# ---- BANNER / WARNING statements: the document marks ITSELF as controlled ----
BANNER = {
    "CUI banner line":   r"(?m)^\s*CUI(?://|\s*$)|CUI//(?:SP-|CTI|EXPT)",
    "ITAR warning stmt": r"warning[:\-—\s].{0,60}(?:itar|export)|this document contains technical data|technical data .{0,40}export .{0,20}(?:restricted|controlled)|export of which is restricted|subject to (?:the )?(?:itar|export administration|export control)|controlled by the itar|itar[- ]controlled technical data|disclosure .{0,30}restricted by .{0,20}(?:itar|ear)",
    "Distribution Stmt": r"distribution statement [b-f][\.\s:]|distribution [b-f][\.\s]\s*(?:u\.?s\.?|government|dod|further)",
    "EAR control stmt":  r"controlled by .{0,20}ear|ear99 .{0,20}(?:controlled|classification)|eccn[:\s]+\d[a-z]\d",
    "DoD class banner":  r"(?m)^\s*TOP\s+SECRET\b|\b(?:TOP\s+SECRET|SECRET|CONFIDENTIAL|FOUO)\s*//|//\s*NOFORN|\bclassified by\s*[:\-]|\bderived from\s*[:\-]|\bdeclassify on\s*[:\-]",
}

# ---- TECHDATA: real engineering data in controlled categories ----
# Require a numeric/engineering co-signal to avoid topic-only mentions.
NUM = r"[-+]?\d[\d,\.]*\s*(?:psi[ag]?|kpa|mpa|bar|n\b|kn|lbf|kgf|sec|s\b|m/s|km/s|ft/s|hz|grms?|g'?s?\b|°|deg|k\b|kelvin|kg|lb|mm|cm|in\b|°c|°f)"
TECHDATA = {
    "RDRE engine data":   (r"rotating detonation|\bRDRE\b|detonation (?:wave|chamber)",
                           r"chamber pressure|specific impulse|\bIsp\b|mass flow|mixture ratio|fill height|wave speed|injector|" + NUM),
    "Propulsion data":    (r"thrust chamber|nozzle|injector|turbopump|combustion (?:chamber|instability)|regen(?:erative)? cool",
                           r"chamber pressure|specific impulse|\bIsp\b|expansion ratio|throat|mass flow|" + NUM),
    "Loads/vibe data":    (r"coupled loads|load case|flight loads|random vibration|shock response spectr|vibration (?:test level|environment)|qualification level|acceptance level",
                           r"\bgrms\b|\bg's\b|\bg level|psd|" + NUM),
    "Trajectory/GNC data":(r"trajectory (?:data|optimization|file)|guidance law|state vector|flight profile data|burn(?:out)? (?:velocity|altitude)",
                           NUM),
    "Gov-furnished tech": (r"government[- ]furnished (?:equipment|information|data)|\bGFE\b technical|data usage agreement|usage agreement.{0,30}(?:nasa|government)",
                           r"nasa|rdre|teasley|engine|propuls|cryo|tank"),
}

def extract(path: Path) -> str:
    ext = path.suffix.lower()
    try:
        if ext in (".md", ".txt", ".csv", ".json", ".html"):
            return path.read_text(errors="ignore")
        if ext == ".pdf":
            return subprocess.run(["pdftotext","-q",str(path),"-"],capture_output=True,timeout=90).stdout.decode(errors="ignore")
        if ext == ".docx":
            return subprocess.run(["textutil","-convert","txt","-stdout",str(path)],capture_output=True,timeout=90).stdout.decode(errors="ignore")
        if ext in (".pptx",".xlsx"):
            out=[]
            with zipfile.ZipFile(path) as z:
                for n in z.namelist():
                    if n.endswith(".xml") and any(k in n for k in ("slide","sheet","sharedStrings","notes")):
                        try: out.append(re.sub(r"<[^>]+>"," ",z.read(n).decode(errors="ignore")))
                        except Exception: pass
            return html.unescape(" ".join(out))
    except Exception as e:
        return f"__ERR__ {e}"
    return ""

def ctx(text,m,pad=50):
    s=max(0,m.start()-pad); e=min(len(text),m.end()+pad)
    return re.sub(r"\s+"," ",text[s:e]).strip()

bres,tres,ares,lres,errors=[],[],[],[],[]
BAN={k:re.compile(v,re.I) for k,v in BANNER.items()}
TEC={k:(re.compile(a,re.I),re.compile(b,re.I)) for k,(a,b) in TECHDATA.items()}

for dp,dn,fn in os.walk(ROOT):
    dn[:]=[d for d in dn if d not in EXCLUDE_DIRS]
    for f in fn:
        p=Path(dp)/f
        rel=str(p.relative_to(ROOT))
        ext=p.suffix.lower().lstrip(".")
        # Depth layer: controlled ARTIFACT by file type (CAD/engineering/analysis/EDA/GNC model).
        # The file itself is controlled — flag it without extracting content.
        if ext in ARTIFACT_EXTS:
            ares.append({"file":rel,"ext":"."+ext}); continue
        if p.suffix.lower() not in (".docx",".pdf",".pptx",".xlsx",".md",".txt",".csv"): continue
        t=extract(p)
        if t.startswith("__ERR__"): errors.append((rel,t)); continue
        bhits={}
        for k,rx in BAN.items():
            m=rx.search(t)
            if m: bhits[k]=ctx(t,m)
        # Shared MARKINGS/pins from the intake screen apply here too ("everywhere", Jon 7/19):
        # USML/Munitions List, deemed export, commodity jurisdiction, DSP-#, 22 CFR 121, EAR99+classif, etc.
        for rx,label in ee._COMPILED:
            m=rx.search(t)
            if m: bhits.setdefault("marking: "+label, ctx(t,m))
        thits={}; borderline=[]
        for k,(ra,rb) in TEC.items():
            ma=ra.search(t)
            if ma and rb.search(t):
                thits[k]=ctx(t,ma)
            elif ma:
                borderline.append(k)   # controlled TOPIC present but no hard numeric co-signal
        if bhits: bres.append({"file":rel,"banner":bhits,"tech":list(thits)})
        elif thits: tres.append({"file":rel,"tech":thits})
        elif borderline and USE_LLM:
            # Layer the classifier: let the local LLM judge whether this borderline doc
            # actually exceeds the cleared Payload User's Guide.
            v=ee.classify_llm(t, timeout=30)
            if v: lres.append({"file":rel,"category":v["category"],"reason":v["reason"],"topics":borderline})

bres.sort(key=lambda r:r["file"]); tres.sort(key=lambda r:r["file"]); ares.sort(key=lambda r:r["file"]); lres.sort(key=lambda r:r["file"])
out=["# Deep CUI/ITAR Scrub — v2 (high precision)","",
 f"- **BANNER (document marked/declared controlled):** {len(bres)} files — quarantine candidates",
 f"- **TECHDATA only (controlled tech + numeric data, no banner):** {len(tres)} files — review",
 f"- **CONTROLLED ARTIFACTS (CAD/engineering files by type):** {len(ares)} files — exclude from off-box sync",
 f"- **LLM-flagged (exceeds cleared guide; topic hit, no numeric co-signal):** {len(lres)} files" + ("" if USE_LLM else " — _(run with --llm to populate)_"),
 f"- **Extraction errors:** {len(errors)}","",
 "## BANNER — declared/marked controlled (highest priority)",""]
for r in bres:
    out.append(f"### `{r['file']}`")
    if r["tech"]: out.append(f"  _(also tech: {', '.join(r['tech'])})_")
    for k,c in r["banner"].items(): out.append(f"- **{k}** — …{c}…")
    out.append("")
out+=["## CONTROLLED ARTIFACTS — CAD / engineering files (controlled by type)",""]
for r in ares:
    out.append(f"- `{r['file']}`  _(**{r['ext']}** — controlled artifact)_")
out+=["","## TECHDATA — controlled technical data w/ numbers (review)",""]
for r in tres:
    out.append(f"### `{r['file']}`")
    for k,c in r["tech"].items(): out.append(f"- **{k}** — …{c}…")
    out.append("")
if lres:
    out+=["## LLM-FLAGGED — exceeds cleared Payload Guide (borderline, no numeric co-signal)",""]
    for r in lres:
        out.append(f"### `{r['file']}`")
        out.append(f"- **{r['category']}** — {r['reason']}  _(topics: {', '.join(r['topics'])})_")
        out.append("")
out+=["## Extraction errors",""]+[f"- `{f}` — {e[:60]}" for f,e in errors]
(ROOT/"compliance"/"deep-scrub-report.md").write_text("\n".join(out))
json.dump({"banner":bres,"tech":tres,"artifacts":ares,"llm":lres,"errors":errors},open(ROOT/"compliance"/"deep-scrub-report.json","w"),indent=1)

# --- Dynamic sync-exclusion list: every flagged-controlled file (marking/banner, CAD
# artifact, technical data w/ numbers, or LLM) blocked from off-box sync the moment the
# scrub sees it. Consumed by scripts/dataroom_sync.sh via --exclude-from. ---
# Auto-exclude = MARKINGS/banner + CAD ARTIFACTS + LLM-flagged (what Jon approved: "marking or CAD artifact").
# TECHDATA-only (numeric co-signal) stays REVIEW-only in the report — it is noisy (e.g. any doc mentioning
# 'RDRE' + a number), so it is NOT auto-excluded from sync unless a human promotes it.
controlled=sorted({r["file"] for r in bres}|{r["file"] for r in ares}|{r["file"] for r in lres})
def _rsync_pat(rel): return "/"+re.sub(r'([\[\]\*\?])', r'\\\1', rel)   # anchor + escape rsync wildcards
dyn=["# AUTO-GENERATED by deep_scrub2.py — DO NOT edit by hand (regenerated each scrub run).",
     "# rsync exclude patterns for files flagged controlled. Consumed by scripts/dataroom_sync.sh.",
     f"# {len(controlled)} files."]+[_rsync_pat(p) for p in controlled]
(ROOT/"scripts"/"cui-exclude-dynamic.txt").write_text("\n".join(dyn)+"\n")
(ROOT/"compliance"/"controlled-files-dynamic.txt").write_text("\n".join(controlled)+"\n")
print(f"BANNER={len(bres)} TECHDATA={len(tres)} ARTIFACTS={len(ares)} LLM={len(lres)} DYNAMIC-EXCLUDE={len(controlled)} errors={len(errors)}")
