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
