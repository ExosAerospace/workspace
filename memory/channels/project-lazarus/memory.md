# EC Channel Memory — #project-lazarus
_Purpose: BLK3 flight dynamics / aero engineering + Spaceport America launch-site licensing_
_Last updated: 2026-09-13_
_Note: two Discord channels share this name (text + voice-category). This file covers the text channel's engineering thread._

## Standing context
### BLK3 flight dynamics (aero)
- **Fin resize** to cut boost weathercocking / high-alt pitch-over (Neil flagged over-stability). 70% fin = root 350 / tip 140 / span 210 mm ≈ 49% area — shrinking about the fixed top-of-root corner drops fin force + moment arm together.
- **Toolchain:** Phil swaps fin CHORD/SSPAN arrays into the REV5 DATCOM deck → runs current + 70% fins → `datcom_to_taos_tbl.py` converts `for006` → TAOS `BLK3_MASS_AERO` TBL → Neil reruns nominal mission for static margin + Segment-1 drift. Converter round-trip validated vs REV5. Kit: `project-lazarus/fin_resize/` + `BLK3_Fin_Resize_Kit.zip`.
- Contributors: Neil Milburn, Phil.

### Spaceport America / launch-site licensing
- NM meeting with Spaceport America (NMSA) + entX on 2026-08-03 → pursuing a **Launch Agreement with NMSA** to contract for launch review with **White Sands Missile Range (WSMR)**. MC task **#1812** "Spaceport America — Licensing Agreement" (two sub-tasks loaded).

## Open threads
- Awaiting Phil's DATCOM `for006` outputs to generate the finished TAOS TBLs.
- Advance the NMSA licensing agreement (task #1812).
