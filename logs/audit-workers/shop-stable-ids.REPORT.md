# shop-stable-ids — worker report (2026-09-30)

Directive: Jon, #exomac-system 13:02 CDT — build the matching approach, add the ID column to Steve's sheet, let Victor know; "They should not have the rights to delete the column without my decision."

## What changed
1. **Permanent IDs.** New `mission-control/data/shop-id-registry.json`, seeded from the current shop-inventory.json. All 1,717 existing SHOP ids kept their numbers (so shop-edits.json SHOP-01685 is still valid). `next_id` is 1718.
   - `scripts/reindex_shop_inventory.py` now assigns ids in this order: Exos ID column, then fingerprint (category + location + contents, tie-broken by SKUs and then occurrence), then "moved" (same category + contents, unique on both sides), then a new id.
   - Lines missing from a reload are marked retired, never deleted or reused.
   - A match summary goes to shop-inventory.json `id_match`, the registry `last_summary`, and fleet_log (agent `shop-id-guard`).
2. **ID column in Steve's workbook.** `scripts/shop_sheet_add_ids.py` produced `mission-control/uploads/1790791766628_Current_Inventory_Locations_EXOS-ID_2026-09-30.xlsx`.
   - An "Exos ID" column is appended (not inserted) on each sheet: Warehouse col S, Parts Room T, Trailer R, Assets L, Sales & Trash H (Sales & Trash has 0 item lines). The header is styled like its neighbour and all 1,717 ids are filled in.
   - Each item sheet is protected: deleting or inserting columns is blocked. Formatting, inserting/deleting rows, sorting, filtering and hyperlinks are all allowed. Every cell and the spare columns are unlocked.
   - The password was generated into `~/.config/exos/shop-sheet-protect.pw` (0600). It was never printed anywhere.
   - The file is registered in `uploads/_meta.json` (id dec730eeb7b301ab) and attached to task #3290.
   - The registry now has `id_column_required=true`.
3. **Guard.** Once the column is required, an upload is REJECTED if it:
   - is missing the column, or
   - has more than 2% blank/duplicate/unknown ids, or
   - would retire more than 25% of active ids. This bulk-deletion check is my addition, in the spirit of Jon's "no deletion without my decision".

   On rejection the previous inventory and registry are kept, the reason goes to `logs/shop-id-guard.log` and fleet_log, and the file is recorded in `data/shop-id-guard.json` so auto-pick skips it. A Decision is then filed for Jon: high priority, dedupeKey `shop-id-guard:<file>`, assignedTo jquinn@exosaero.com, approver John Quinn. Exo never answers it. If Jon picks accept, the path is `--file <f> --override-guard`, and the decision context includes that command. server.js now passes the uploaded file and the uploader's name to the reindex.
4. **Photos on the Full Shop Inventory page.** This reuses lib/inventory-photos.js and the inventory.html photo manager.
   - Each line has a Photos column (thumbnails + 📷). You can add several photos or take one, and delete behind a "Yes, delete" confirm; deleted photos go to the recycle bin.
   - Admin/manager or the person who uploaded a photo can delete it.
   - The key is `shop#SHOP-xxxxx`. Unknown shop ids are refused.
   - The page also shows each line's SHOP id, includes it in the CSV export, and lets you search by it.
5. **exo3 registration.** `shop-id-guard-exo3` is in agent-registry.json with owner John Quinn, eval = shop_ids_selftest.py, and a change_log entry approved by John Quinn 2026-09-30.
6. **Heads-up task #3290** for Steve Norsworthy, due 2026-10-02, with the workbook attached, owner-approved by Jon. No email and no Discord. The password is not mentioned.

## Commits
- Step 1 content: `9e3cd5d`. My staged files were swept into a concurrent r2 launchd-residuals commit (shared-index race). I did not rewrite history. `6754d63` is an empty attribution commit. After that I switched to `git commit -- <paths>`.
- `b4cfcda` step 2 · `2786373` step 3 · `4acc506` step 4 · `b65ac71` step 5 (registry) · `18eb2e5` step 6
- Not pushed.

## Match stats
- Seed reload (old sheet, no column): matched 1717, 0 id changes, 0 field changes.
- New EXOS-ID sheet: kept 1717, new 0, retired 0, 0 id changes vs before.

## Verification
- Workbook reopened and checked: header and ids present, protection on, deleteColumns/insertColumns blocked, row delete allowed, 0 locked cells, and all 1,762 formulas identical to the source. Both images and both Parts Room tables survived.
- `scripts/shop_ids_selftest.py`: 22/22 offline checks pass (same-sheet reload, mid-sheet insert, moved row, column removed → rejected + decision payload in dry-run, >2% bad ids, bulk removal, retire-not-delete, override). With `--live` it is 33/33.
  - The live run confirms served ids == shop-inventory.json == registry active (1,717).
  - It also checks photo add/list/delete, 403 for a non-uploader and 400 without confirm.
  - It used two throwaway users, which were removed afterwards; users.json is byte-identical.
- `node scripts/inventory_photos_selftest.js`: 17/17 pass.
- MC was restarted once. `/login` returned 200 after 2 seconds.
- No real Decision was filed, because no upload has been rejected.
- No email went to Steve for task #3290. The assignment-notifier at 13:18:25 CDT logged "suppressed ... snorsworthy@exosaero.com -> task 3290" and "sent=0".

## Not done / caveats
- **Victor is cc'd, not assigned.** MC tasks have one assignee and no cc field, so he is named in the body and a `cc:vcastilleja@exosaero.com` tag. He gets no notification unless he looks at the task. If Jon wants Victor to get his own copy, that means a second task (the spec said ONE).
- **The sheet protection only stops casual changes.** It works in Excel. If Steve opens the file in Google Sheets or re-exports it, the protection may not carry over. The real enforcement is the MC upload guard.
- **Blank ids count toward the 2% limit.** If Steve adds more than about 34 new rows in one upload, the upload is rejected and goes to Jon as a Decision. That is per spec, but worth knowing.
- **One-time differences in the new file:**
  - 4 Parts Room description cells now show their URL text. This is an openpyxl read-only quirk on the old file, not a data change.
  - Cached formula values are dropped; Excel recalculates when the file is opened.
  - The file is larger (1.13 MB vs 0.65 MB) because every cell carries an "unlocked" style.
- **Outside my lane:** `inventory_capture.py reindex-locations` (the location map) still runs on every location upload, including one the shop guard rejects.
- **Live selftest leftover:** one tiny test photo file is parked in the recycle bin with its recycle-bin record. Its entries in inventory-photos.json were removed.
- **Uncommitted:** uploads/_meta.json (live runtime file, other sessions' edits too) and logs/assignment-notify-suppress.json were changed but not committed.
