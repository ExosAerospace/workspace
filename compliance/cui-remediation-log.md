# CUI/ITAR Remediation Log — exomac

Record of controlled-data removal from exomac. Content-free (filenames + hashes only) — this log is NOT itself CUI; it is proof-of-remediation.

## 2026-06-16 — NASA RDRE government-furnished technical data
Authorized by Jon ("delete from exomac"). Removed from exomac entirely.

| file | sha256 | original path | action |
|------|--------|---------------|--------|
| nasa-rdre-data-usage-agreement.doc | 7aa7c50ee65ebb362b1b554c59e6d11bad4f8e5ce3642236e6e666212805c3ca | references/nasa-rdre-data-usage-agreement.doc | removed from working tree (git rm) + quarantine copy deleted |
| teasley-nasa-rdre-dev-2025.pdf | dbd2139460af13c4a915405b1f2bdd3b9cad9280e8b6de99121371013efbf716 | references/teasley-nasa-rdre-dev-2025.pdf | removed from working tree (git rm) + quarantine copy deleted |

Status:
- [x] Removed from workspace working tree
- [x] Quarantine copies deleted from exomac
- [x] Purged from local git history (blobs 7a3602b… / fc39289… physically gone; filter-branch + gc; .git backup deleted) — 2026-06-16
- [ ] Atomus custody in GCC High (authoritative copy) — REMAINING (Atomus action; exomac no longer holds any copy)

Recovery source if ever needed: original NASA / Teasley source, or Atomus GCC High.

## 2026-10-02 - Sandia TAOS Manual v11.1 (OUO / Export Controlled) restricted (John Quinn)
- sha256 4a05de04...bf6c7. Moved out of project-lazarus/inputs to the restricted OUO folder in the exomac home dir (dir 0500, file 0400, Spotlight off, README access notice). Byte-identical duplicate in media/inbound deleted.
- Excluded from DR mirror; AI-tool deny rules in Claude Code project + user settings (verified: blocked a command naming the path). Access: Exos employees (US persons), local only.
- Exos trajectory/6DOF/Monte Carlo math work RELEASED by Jon (not CUI; backed up; ITAR-sensitive, no foreign sharing w/o export review).

## 2026-10-02 — NASA RDRE GFE re-found on the Mac Studio (byte-identical copies), deleted
Authorized by Jon, decision D-7281874 (answered 2026-10-01 06:10 CDT): "delete them from the Mac Studio and its local backups".
Found by r2-controlled-docs (9/30) after the Mac Studio cutover: the 6/16 removal above did not cover OpenClaw's inbound
media store. Deleted by the exo3 r3-followthrough worker. Only files whose sha256 matches the two hashes above were touched.

| path | sha256 | document | bytes | mtime | action |
|------|--------|----------|-------|-------|--------|
| `~/.openclaw/media/inbound/NASAs_RDRE_Dev_AAS_Teasley_Final---8f63bdee-edd3-4c3c-af37-98ba3b693cdc.pdf` | dbd2139460af13c4a915405b1f2bdd3b9cad9280e8b6de99121371013efbf716 | AAS paper (teasley-nasa-rdre-dev-2025) | 1002534 | 2026-03-25T09:35:01 | rm (permanent, not Trash) 2026-10-02T07:37:49-05:00 |
| `~/.openclaw/media/inbound/Data_Usage_Agreement_US_General_and_Govt_Purpose_ITAR_and_EA---3028362f-9d2c-4405-bbc8-d1871fd4a2ad` | 7aa7c50ee65ebb362b1b554c59e6d11bad4f8e5ce3642236e6e666212805c3ca | Teasley DUA (nasa-rdre-data-usage-agreement) | 57856 | 2026-03-25T23:13:13 | rm (permanent, not Trash) 2026-10-02T07:37:49-05:00 |
| `~/.openclaw/media/inbound/NASAs_RDRE_Dev_AAS_Teasley_Final---354d3413-626c-4e87-9027-059e50e6bcf8.pdf` | dbd2139460af13c4a915405b1f2bdd3b9cad9280e8b6de99121371013efbf716 | AAS paper (teasley-nasa-rdre-dev-2025) | 1002534 | 2026-03-25T22:56:31 | rm (permanent, not Trash) 2026-10-02T07:37:49-05:00 |

Sweep (sha256 of every file with a matching byte size, whole home dir incl. ~/.openclaw, ~/exos-asset-backups,
~/dr-selftest-mirror, workspace drafts/ + mission-control/uploads/, Desktop/Documents/Downloads, iCloud Drive, /tmp):
before 3 hits (all in ~/.openclaw/media/inbound), after 0 hits. ~/exos-asset-backups and ~/dr-selftest-mirror held no copy.

Status:
- [x] Live copies on the Mac Studio deleted (3)
- [ ] Time Machine: ~/.openclaw is NOT excluded, so the external "My Book" Time Machine backups and the hourly local APFS
      snapshots (which expire on their own within ~24h) almost certainly still hold these files. They cannot be deleted
      one file at a time, and this worker has no Full Disk Access, so they were not touched. This is Jon's call: EXO3 Decision D-7281891.
- [ ] Atomus custody in GCC High (authoritative copy), unchanged from 6/16
- [x] Trajectory / 6DOF / Monte Carlo dispersion files (lazarus_taos, project-lazarus, blk3_polar, MC frameworks) NOT deleted.
      Jon released them as not CUI (entry above). Only the two GFE hashes were in scope.
