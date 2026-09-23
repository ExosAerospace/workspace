# Receiving Capture Runbook

You read packing-list / parts photos taken on the Receiving page and draft the received line items
(part number + quantity), matched to the BLK3 BOM, for a human to confirm. Work the queue to empty.

## Loop
1. Run: `python3 scripts/receiving_capture.py next`
   - `EMPTY` → done, stop.
   - Else returns JSON: `id`, `po` (the QuickBooks PO #), `image_path`, `image_exists`.
2. If `image_exists`, **Read the image at `image_path`.** It is a packing slip and/or a photo of the
   parts. Identify each line item: the part number / manufacturer P/N and the quantity received.
3. Start a fresh draft for this PO: `python3 scripts/receiving_capture.py clear-draft --po <po>`
4. For EACH line you can read, match it to the BOM with
   `python3 scripts/inventory_capture.py bom-search "<part # or keywords>"`, pick the best line, then:
   ```
   python3 scripts/receiving_capture.py add-draft --po <po> --vendor-pn "<Vendor P/N>" \
     --mfg-pn "<Mfg P/N>" --item "<item#>" --section "<section>" --desc "<description>" --qty <n>
   ```
   Use the quantity from the packing slip. If a line is on the slip but you can't match it to the
   BOM, still add it with the raw description and qty (desc + qty), leaving P/N blank — the human
   will fix it.
5. When all readable lines are drafted: `python3 scripts/receiving_capture.py finish --id <id> --po <po>`
6. Back to step 1 until EMPTY.

## Rules
- This is a DRAFT for human confirmation — never check anything into inventory yourself. Do not run
  `receiving_apply.py` or `inventory_capture.py record/receive`. Only `clear-draft`, `add-draft`, `finish`.
- Read quantities carefully; when unsure, draft your best read and let the receiver correct it.
- Don't invent part numbers — if you can't match, leave P/N blank and keep the slip's description.
- Unit cost and bin location are left blank; the receiver fills those on the page.
