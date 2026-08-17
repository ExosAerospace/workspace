#!/usr/bin/env python3
"""
Promote an approved Series A deck into the canonical data room — with a HARD integrity gate.

Pipeline (only runs with --approve):
  1. Stage the candidate as the single canonical pitch deck in _CANONICAL/ (dated name),
     moving any prior *PitchDeck*.pptx to _ARCHIVE_Superseded/ (never deleted).
  2. Run the Data Room Integrity Guard (scripts/data_room_integrity.py).
  3. HARD BLOCK: if the room goes RED, roll the staging back and refuse to publish.
  4. On pass, update DATA_ROOM_MANIFEST.md's pitch-deck row and sync the MC-served copy
     so the link Jon sends investors always resolves to the approved file.

Usage:
  python3 scripts/promote_deck_to_dataroom.py --deck <path> [--approve]
Without --approve it does a dry run (gate preview only, no file changes).
"""
import os, re, sys, glob, json, shutil, hashlib, argparse, subprocess, datetime

ROOT = "/Users/exomac/.openclaw/workspace"
CANON = os.path.join(ROOT, "data-room/Exos_SeriesA/_CANONICAL")
ARCH  = os.path.join(ROOT, "data-room/Exos_SeriesA/_ARCHIVE_Superseded")
MANIFEST = os.path.join(ROOT, "data-room/Exos_SeriesA/DATA_ROOM_MANIFEST.md")
READINESS = os.path.join(ROOT, "mission-control/data/data-room-readiness.json")
UPLOADS = os.path.join(ROOT, "mission-control/uploads")
GUARD = os.path.join(ROOT, "scripts/data_room_integrity.py")

def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()

def run_guard():
    subprocess.run([sys.executable, GUARD], cwd=ROOT, capture_output=True)
    with open(READINESS) as f:
        j = json.load(f)
    return j.get("status"), j.get("score"), j.get("blocks", j.get("flags", []))

def current_pitch_decks():
    return sorted(glob.glob(os.path.join(CANON, "*PitchDeck*.pptx")))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--deck", required=True)
    ap.add_argument("--approve", action="store_true")
    a = ap.parse_args()

    deck = os.path.abspath(a.deck)
    if not os.path.exists(deck):
        sys.exit(f"ERROR: candidate not found: {deck}")

    today = datetime.date(2026, 8, 17).isoformat()  # stamped by caller context; avoids Date.now surprises
    target_name = f"Exos_SeriesA_PitchDeck_{today}_APPROVED.pptx"
    target = os.path.join(CANON, target_name)

    priors = current_pitch_decks()
    same_as_current = any(md5(deck) == md5(p) for p in priors)

    print(f"candidate : {deck}")
    print(f"md5       : {md5(deck)}")
    print(f"in-room   : {[os.path.basename(p) for p in priors]}")
    print(f"identical to a current canonical deck: {same_as_current}")

    # ---- DRY RUN: gate preview only ----
    if not a.approve:
        st, sc, bl = run_guard()
        print(f"\nDRY RUN — room integrity right now: {st} (score {sc})")
        if bl: print("  open flags:", json.dumps(bl, indent=2)[:1200])
        print("\nNo files changed. Re-run with --approve to publish.")
        return

    # ---- STAGE ----
    os.makedirs(ARCH, exist_ok=True)
    moved = []
    for p in priors:
        if md5(p) == md5(deck):
            # same content already canonical — retire the old name in favor of the dated APPROVED name
            dest = os.path.join(ARCH, os.path.basename(p))
        else:
            dest = os.path.join(ARCH, os.path.basename(p))
        if os.path.abspath(p) != target:
            shutil.move(p, dest); moved.append((p, dest))
    shutil.copy2(deck, target)
    print(f"\nstaged canonical: {target_name}")

    # ---- HARD GATE ----
    st, sc, bl = run_guard()
    print(f"integrity gate: {st} (score {sc})")
    if st == "RED":
        # rollback
        os.remove(target)
        for src, dest in moved:
            shutil.move(dest, src)
        run_guard()
        print("\n*** BLOCKED — deck FAILED the integrity gate. Room rolled back, nothing published. ***")
        print("blocks:", json.dumps(bl, indent=2)[:1600])
        sys.exit(2)

    # ---- SYNC MC-SERVED COPY (so the investor link always hits the approved file) ----
    served = os.path.join(UPLOADS, target_name)
    shutil.copy2(target, served)

    # ---- UPDATE MANIFEST pitch-deck row ----
    try:
        m = open(MANIFEST).read()
        m2 = re.sub(r"(\| Pitch deck \| )`[^`]+`", rf"\1`{target_name}`", m, count=1)
        if m2 != m:
            open(MANIFEST, "w").write(m2)
            print("manifest pitch-deck row updated ->", target_name)
    except Exception as e:
        print("manifest update skipped:", e)

    print(f"\nPUBLISHED. Canonical Series A deck = {target_name}  (room {st}, score {sc})")
    print(f"MC-served copy: mission-control/uploads/{target_name}")

if __name__ == "__main__":
    main()
