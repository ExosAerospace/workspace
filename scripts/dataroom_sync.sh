#!/bin/bash
# dataroom_sync.sh — sync the Exos workspace (data room) to a target host.
# Excludes .git history so removed/quarantined files (e.g. NASA RDRE GFE data)
# can NEVER travel via history, plus transient junk. Working-tree only.
#
# Usage: bash scripts/dataroom_sync.sh exos@<DGX_LAN_IP>:/home/exos/.openclaw/workspace/
set -euo pipefail
SRC=/Users/exomac/.openclaw/workspace/
DEST="${1:?usage: dataroom_sync.sh user@host:/dest/workspace/}"

CUI_EXCLUDE=/Users/exomac/.openclaw/workspace/scripts/cui-exclude-list.txt
DYN_EXCLUDE=/Users/exomac/.openclaw/workspace/scripts/cui-exclude-dynamic.txt

# Refresh the dynamic controlled-file list BEFORE syncing so anything the scrub now flags
# (marking/banner, CAD artifact, technical data, or LLM) is blocked this run — no manual step.
echo "=== pre-sync deep scrub (regenerating dynamic exclude list) ==="
python3 /Users/exomac/.openclaw/workspace/scripts/deep_scrub2.py || echo "(warn: deep_scrub2 failed; falling back to static + prior dynamic excludes)"
touch "$DYN_EXCLUDE"   # ensure it exists even if the scrub failed

rsync -avz --delete \
  --exclude='.git/' \
  --exclude='node_modules/' \
  --exclude='logs/' \
  --exclude='*.log' \
  --exclude='.DS_Store' \
  --exclude='cui-quarantine/' \
  --exclude-from="$CUI_EXCLUDE" \
  --exclude-from="$DYN_EXCLUDE" \
  -e ssh "$SRC" "$DEST"

echo
echo "=== post-sync CUI check on target — must print NONE ==="
TARGET_HOST="${DEST%%:*}"; TARGET_PATH="${DEST#*:}"
# Scan the WHOLE target tree for any controlled family that slipped through,
# plus the original NASA RDRE GFE files. Any hit = FAIL (non-zero exit).
ssh "$TARGET_HOST" "find '$TARGET_PATH' -type f \( \
   -iname 'DARPA_DSO*' -o -iname '*HR001125S0013*' -o -iname 'SPRINT-BAA-RDRE*' \
   -o -iname 'STRATFI-PY26-1-Exos-RDRE*' -o -iname 'NASA-SBIR-AERO4S26B-Technical-Proposal*' \
   -o -iname 'NASA-SBIR-AERO4S26B-Full-Proposal*' -o -iname 'AERO4S26B-Technical-Proposal-ProSAMS*' \
   -o -iname 'KARMEN-D2P2-Technical-Volume*' -o -iname 'KARMEN-Phase-III-Sole-Source-Justification*' \
   -o -iname 'GTL_RDRE_Info_Request*' -o -iname 'Exos_GTL_RDRE_Deal_Structure*' \
   -o -iname 'TACFI_RDRE_Technical_Summary*' -o -iname 'Exos_RDRE_Capability_Statement*' \
   -o -iname '*rdre-data-usage-agreement*' -o -iname '*teasley-nasa-rdre*' \) 2>/dev/null \
   | grep . && { echo '*** CUI CHECK FAILED — controlled files present on target ***'; exit 1; } || echo NONE"

echo
echo "=== post-sync CONTROLLED-ARTIFACT check (CAD/engineering files by type) — must print NONE ==="
# Any CAD / native-engineering / analysis / EDA / GNC-model file on target = FAIL.
# Extensions kept in sync with scripts/cui-exclude-list.txt + itar_ear_screen.py CAD_EXTS.
ssh "$TARGET_HOST" "find '$TARGET_PATH' -type f \( \
   -iname '*.sldprt' -o -iname '*.sldasm' -o -iname '*.slddrw' -o -iname '*.step' -o -iname '*.stp' \
   -o -iname '*.iges' -o -iname '*.igs' -o -iname '*.x_t' -o -iname '*.x_b' -o -iname '*.xmt_txt' \
   -o -iname '*.catpart' -o -iname '*.catproduct' -o -iname '*.cgr' -o -iname '*.ipt' -o -iname '*.iam' \
   -o -iname '*.idw' -o -iname '*.prt' -o -iname '*.asm' -o -iname '*.drw' -o -iname '*.dwg' -o -iname '*.dxf' \
   -o -iname '*.stl' -o -iname '*.3mf' -o -iname '*.sat' -o -iname '*.jt' -o -iname '*.3dm' \
   -o -iname '*.inp' -o -iname '*.odb' -o -iname '*.cae' -o -iname '*.nas' -o -iname '*.bdf' \
   -o -iname '*.cas' -o -iname '*.msh' -o -iname '*.cgns' -o -iname '*.nc' -o -iname '*.gcode' \
   -o -iname '*.cnc' -o -iname '*.tap' -o -iname '*.sim' -o -iname '*.fem' \
   -o -iname '*.brd' -o -iname '*.sch' -o -iname '*.kicad_pcb' -o -iname '*.gbr' \
   -o -iname '*.slx' -o -iname '*.mdl' \) 2>/dev/null \
   | grep . && { echo '*** ARTIFACT CHECK FAILED — controlled CAD/engineering files on target ***'; exit 1; } || echo NONE"

echo
echo "=== post-sync DYNAMIC controlled-file check (every scrub-flagged file) — must print NONE ==="
# Literal per-path existence check (robust to spaces/brackets in filenames). Any leak = FAIL.
DYN_LIST=/Users/exomac/.openclaw/workspace/compliance/controlled-files-dynamic.txt
if [ -s "$DYN_LIST" ]; then
  ssh "$TARGET_HOST" "cd '$TARGET_PATH' 2>/dev/null || exit 0; leak=0; while IFS= read -r p; do [ -n \"\$p\" ] && [ -e \"\$p\" ] && { echo \"LEAK: \$p\"; leak=1; }; done; [ \$leak -eq 0 ] && echo NONE || { echo '*** DYNAMIC CHECK FAILED — scrub-flagged files on target ***'; exit 1; }" < "$DYN_LIST"
else
  echo "NONE (no dynamic list / empty)"
fi
