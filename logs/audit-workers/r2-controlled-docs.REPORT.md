# r2-controlled-docs — REPORT (exo3 round 2, audit theme 7)

Worker restarted 2026-09-30 13:05 CDT. The killed 9/29 run had committed nothing in this scope, so all of this was done fresh.

## Decisions filed to Jon (all open; none answered or closed by me)
| id | priority | what |
|---|---|---|
| **D-7281870** | med | Keep or roll back the CM register, the nightly unapproved-change check, and the newly committed library docs |
| **D-7281871** | high | Keep or roll back the RTO data-room lock |
| **D-7281872** | med | CM numbering scheme `EXOS-<AREA>-<NNN>-<REV>` (renumber at next revision / new only / keep) |
| **D-7281873** | med | Named owner per Process Library area (69 of 82 rows list "Exo", a role or a vendor) + owners for 9 unregistered docs |
| **D-7281874** | high | Export-controlled / GFE / trajectory files on the Mac Studio: Atomus moves them to GCC High, then local copies are deleted (Jon's call) |

## What changed (commits, none pushed)
- **a546271**: `scripts/doc_cm.py` + `mission-control/data/cm-register.json`. The register has 116 rows: 110 Process Library files (from process-register.json) + the data-room manifest + its 5 served files. Each row holds doc no., proposed CM id, rev, owner, status, sha256, git-tracked, marking flags, and the approved sha256 with who, which decision and when.
  - Drift check: content that differs from the approved sha256, a missing file, a new doc added to the data-room manifest, or a stray file in the data-room folder is a FAIL, and it files ONE deduped Decision card (`cm-drift:<digest>`). The card is HIGH if the data room is involved.
  - Baselines move only on a HUMAN-answered approving decision (`approve --decision`, or `check --accept-answered`). Agent-proposed answers (the e13a807 gate) never move a baseline.
  - Marking guard: files with CUI banner / ITAR / export-controlled / distribution-statement / USML markings are hash-only and are never offered for git commit.
- **1616783**: committed 35 previously untracked controlled library docs + `dataroom-manifest.json`. The data-room binaries (409A, financial model, etc.) are deliberately NOT committed; they are hash-locked instead. The repo has no git remote.
- **fa9b669**: committed 26 pre-brand prior revisions (`*.prebrand-*`) as revision history. All passed the marking scan.
- **bec14c8**: data-room lock. The manifest and served files are set to 0400 and the folder to 0500; the check now warns if the lock is loosened. MC still reads them (`/api/dataroom` is live).
- **4eb774d**: `scripts/cui-exclude-list.txt` gains trajectory/6DOF/dispersion/GFE patterns, so these files stay off the Studio→Mini DR mirror. Also adds `logs/audit-workers/r2-controlled-docs.controlled-paths.txt` (299 candidate paths; paths only).
- **6139648**: agent-registry entry for `com.exos.doc-cm-drift` (full spec, change_log pending D-7281870), a change_log note on dataroom-integrity (D-7281871), the agent-evals liveness entry, and a versioned plist.
- Live, outside git: `~/Library/LaunchAgents/com.exos.doc-cm-drift.plist` is loaded (daily 03:20, run_logged). I kickstarted it once: exit 0.

## Verified
- `doc_cm.py --selftest` passes 16/16. It replays both audit gaps (an unapproved edit, and an unapproved data-room addition) and proves an agent-proposed answer can't re-baseline.
- Live check: 116 docs, 0 FAIL, 9 WARN (unregistered HR/safety files, covered by D-7281873), 5 marked. fleet_log `cm_drift_check` events are written; agent_eval reports doc-cm-drift OK.
- rsync dry-run over `~/.openclaw/`: 57 trajectory/GFE files would have gone to the DR mirror before the new exclusions, 0 after.
- All 5 decisions show `open` in decisions.json. Re-posting D-7281870 through its dedupeKey updated the card in place (no duplicate).

## Controlled-data finding (D-7281874). Nothing moved, copied or shared.
- NASA RDRE GFE: the Teasley DUA (sha256 7aa7c50e…) and the AAS paper (dbd21394…). `compliance/cui-remediation-log.md` records both as "removed from exomac" on 6/16, but byte-identical copies are still in `~/.openclaw/media/inbound` (3 files).
- BLK3 6DOF / trajectory inputs: `lazarus_taos/`, `project-lazarus/`, `blk3_polar/`, and media inbound/outbound.
- Part 450 Monte Carlo dispersion frameworks: `drafts/`, `mission-control/uploads/`, `~/.openclaw/tmp/`.
- Copies also exist in `~/exos-asset-backups` (44) and the local `~/dr-selftest-mirror`. rsync `--delete` does not remove newly excluded files already in a mirror.

## Left undone, and why
- **Serve-time sha check in `/api/dataroom-doc`** was not built. `mission-control/server.js` (and `lib/inventory-photos.js`) have another session's uncommitted, in-progress shop-inventory photo edits (modified 13:11), so I didn't touch either file or restart MC. The file lock + nightly check cover the gap for now.
- Renumbering, owner changes and status-enum cleanup wait on D-7281872 and D-7281873. The 9 unregistered library docs also wait on D-7281873.
- Deleting or relocating controlled files waits on D-7281874 (irreversible).
- The pre-existing uncommitted deletion `process-library/01-quality-as9100/Exos-US-Procedures_list.docx` (another session) was left alone.
- `state/doc-cm-state.json` is runtime state and is intentionally not committed.
- Side effect: running `agent_eval.py --help` executed a normal eval pass (it has no help flag). Result: 168 OK / 13 WARN / 2 FAIL, the same FAILs as the hourly job (series-a-worklist paused, missioncontrol exit 15), and its alerts are deduped.
- I skipped the CLAUDE.md session-startup routine (CronList / RemoteTrigger / status message). The worker hard rules forbid Discord sends, and this is a scoped worker session.

## Rollback
- Nightly job: `launchctl bootout gui/$(id -u)/com.exos.doc-cm-drift && rm ~/Library/LaunchAgents/com.exos.doc-cm-drift.plist`
- Data-room lock: `chmod 600 mission-control/data/dataroom-manifest.json mission-control/dataroom/*; chmod 700 mission-control/dataroom`
- DR exclusions: delete the 2026-09-30 block at the end of `scripts/cui-exclude-list.txt`
- Code/registry: `git revert 6139648 bec14c8 a546271` (the committed documents can stay in git)
