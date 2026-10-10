# Exos Series A — Data Room Manifest (Single Source of Truth)

**Owner:** John Quinn, Cofounder & CEO
**Established:** 2026-08-08 (P0 lockdown, post-MDB review)
**Rule:** Exactly ONE canonical file per artifact lives in the shared room. Everything else is archived (never deleted), outside the room. No reviewer should ever see two versions of the same document.

---

## CANONICAL — keep these live in the room (and ONLY these)

| Artifact | Canonical file | Version / Date | Anchor value | Owner |
|---|---|---|---|---|
| Financial model | `EXOS_Financial_Model_Full_Revenue_FIXED_v12_FY2025actuals_rev-2026-10-10.xlsx` | v12 rev 2026-10-10 (Funding Ask labels only: $10M Series A; Scorpius acquisition / BLK3 / propulsion trade study) · 10-yr + **FY2025 Actuals tab** | Holds valuation of record **$169.7M** ($8.66/sh, DLOM 36.51%); internal blended EV $194.9M shown only inside model, bridged to the concluded 409A | Jon / Kyle |
| 409A valuation | `EXOS_409A_Eqvista_2026-03-31_CURRENT.pdf` | Eqvista · dated 06/10/2026, as-of 03/31/2026 | **$8.66/sh**, $169.7M equity, DLOM 36.51% | Jon |
| Investor deck | `Exos_SeriesA_StrategicDeck_2026-09-06_CURRENT_rev-2026-10-10.pptx` | rev 2026-10-10 (newest) | Figures-of-record clean: $169.7M / a $10M Series A (Scorpius acquisition + BLK3 + propulsion trade study) / no ROFR / no Nebula / BLK4 not funded / TXSE-primary / no Euronext / no TBD. ⚠ still must pass P1 reconciliation before room reopens | Jon |
| Policy tailwind brief | `Exos_Policy_Tailwind_NSTP_2026-08-21.pdf` (+ editable `.docx` twin) | Aug 21 2026 · **on Exos PRIMARY letterhead** | National Space Transportation Policy ("Golden Age") → Exos alignment; **no valuation stated** (room-safe) | Jon / Exo |
| Cap table | `Exos_Capitalization_Table.xlsx` | confirm current dated version | — | Kyle |

**Single valuation of record:** **$169.7M equity value** (Eqvista 03/31/2026 409A). This is the only headline number that appears in the room. The DCF / market-approach / comps figures live *inside the model only*, tied together by a reconciliation tab (built in P1) — never shown side-by-side unbridged.

**Jon decisions — LOCKED 2026-08-13 (D1–D4); see FIGURES_OF_RECORD.md:**
- **Raise size of record** — **a $10 million Series A** *(Jon 2026-10-10; supersedes the 8/13 "$10M first close, tranched to $25M" and the prior $40–50M figure)*
- **Use of funds** — complete the Scorpius acquisition; finish and fly BLK3; next-gen propulsion trade study. **BLK4 is not funded by the raise** (future gated orbital path only)
- **Listing path** — private growth Series A now; public-markets path in progress; TXSE listing as the backup route (Jon 2026-10-10)

These are set. The room follows FIGURES_OF_RECORD.md; anything contradicting it is superseded.

---

## ARCHIVE — pull these OUT of the shared room (superseded, retained in `_ARCHIVE_Superseded/`)

**Models (all superseded by v12):**
- `EXOS_Financial_Model_Full_Revenue_FIXED_v9_409Afinal.xlsx` — v9, Jun 19 2026; superseded 2026-09-17 by v12 (FY2025 actuals refresh; same $169.7M valuation of record)
- `EXOS_Financial_Model_Full_Revenue_FIXED_v5_jq.xlsx` — 5-yr, DCF $74.8M (the file that made us look worth 1/3 as much)
- `..._v5_jq_BACKUP.xlsx`, `..._v7.xlsx`, `..._v8.xlsx`
- `EXOS_Financial_Model_Rev_May29_2026.docx`, `..._v8_May29_2026.docx`, `..._v8_May29_2026_TXSE.docx`

**409A (superseded — the drift is fine, but only the current one belongs in the room):**
- `EXOS_409A_Aranca_April2024.pdf` — $5.03
- `EXOS_409A_Eqvista_May2025.pdf` — $7.06

**Decks (superseded):**
- `Exos_PitchDeck_March_2026.pptx`
- `Exos_SeriesA_PitchDeck_May2026.pptx`
- `Exos_SeriesA_PitchDeck_June2026_PhysicalAI.pptx`
- `Exos_SeriesA_PitchDeck_June2026_PhysicalAI_TXSE.pptx`
- `Exos_SeriesA_PitchDeck_FULL_2026-08-16_CORRECTED.pptx` — superseded 2026-09-17 by the 9/6 Strategic deck
- `Exos_SeriesA_StrategicTeaser_2026-08-21.pptx` — teaser variant; superseded 2026-09-17

**Not room files (keep out — investor-specific / different purpose):** `Exos_Haas_Custom_Deck_2026-07.pptx`, Montana partnership decks, and `Exos_SSLC_Board_TechLicense_Request_2026-08-21.pptx`, and `Exos_Scorpius_AssetPurchase_TermSheet_forCounsel_2026-08-28.docx` (legal wording for counsel, not investor-facing; moved out of the room 2026-10-10) (SSLC board tech-license request — different audience/purpose; moved to `_RELATED_NotRoomFiles/`).

**Related package (separate room):** `../Navy_Commission/` — Commission on the Future of the Navy site-visit materials (deck + deck-aligned model + projections) on the **conservative Cash Flow case (2027–2032)**. Kept separate on purpose; do not co-mingle with the Series A canonical set. See `../Navy_Commission/DATA_ROOM_MANIFEST.md`.

---

## PRE-ACCESS CHECKLIST — run before granting ANY new reviewer

Do not share the room until every box is true:
- [ ] Only ONE model, ONE 409A, ONE deck, ONE cap table are visible in the room.
- [ ] Valuation number is identical across model, deck, and 409A ($169.7M).
- [ ] Raise size is identical everywhere (single number of record).
- [ ] Use-of-funds table is identical everywhere (Scorpius acquisition / BLK3 / propulsion trade study; no BLK4).
- [ ] No ROFR / "right of first refusal" / "2021 basis" wording; no "Nebula … contracts in hand"; no RTO in any room file.
- [ ] Base case shows contracted revenue only; TACFI/STRATFI/entX-expansion sit in a separate Upside column.
- [ ] No file marked "TBD" on listing path.
- [ ] Scorpius related-party: fairness opinion + disclosure memo present (once P3 done).

---

## Status
- **P0 (this doc):** DONE — canonical set staged in `_CANONICAL/`, superseded staged in `_ARCHIVE_Superseded/`, manifest published. Execute the same keep/archive split inside the Peony room.
- **2026-08-21 policy update:** added policy-tailwind slide to the canonical pitch deck (slide 18) + new `Exos_Policy_Tailwind_NSTP_2026-08-21.pdf`. **To sync to the Peony room:** upload the updated deck + the policy brief. Deck backup at `.backups/`.
- **2026-09-17 reconciliation (task #1859):** model of record promoted **v9 → v12** (FY2025 actuals + bridged reconciliation note; holds $169.7M); v9 moved to `_ARCHIVE_Superseded/`. Room now has ONE model again. **Deck deconflicted (same run):** `_CANONICAL/` now holds ONE investor deck — `Exos_SeriesA_StrategicDeck_2026-09-06_CURRENT.pptx` (newest; figures-of-record clean: $169.7M / $10M→$25M / BLK3-first / TXSE / no Euronext / no TBD). The Aug-16 Pitch FULL + Aug-21 Teaser moved to `_ARCHIVE_Superseded/`; the SSLC Board tech-license deck moved to `_RELATED_NotRoomFiles/` (different purpose). Done as reversible cleanup while the room is CLOSED (no external exposure); Jon can swap the pick if he prefers the Aug-16 Pitch. ⚠ The single deck still must pass P1 figures-of-record before the room reopens.
- **2026-10-10 CURRENT STRATEGY (Jon):** raise = a $10 million Series A; use of funds = Scorpius acquisition + finish/fly BLK3 + next-gen propulsion trade study; BLK4 out of the raise; no ROFR language; first OTV tank sale cited without naming the customer. New revisions created next to the originals: deck `_CANONICAL/Exos_SeriesA_StrategicDeck_2026-09-06_CURRENT_rev-2026-10-10.pptx`, model `_CANONICAL/EXOS_Financial_Model_Full_Revenue_FIXED_v12_FY2025actuals_rev-2026-10-10.xlsx`, market docs `05_Market_Information/5.1_…_rev-2026-10-10.docx` + `5.2_…_rev-2026-10-10.docx`. ⚠ The pre-10/10 originals are still in place (not yet archived) — move them to `_ARCHIVE_Superseded/` and swap the Peony copies before the room reopens.
- **P1–P4:** blocked on Jon decisions #1 (fairness opinion), #2 (listing path), #3 (raise size). See task 1859.

---

## DECISIONS LOCKED — 2026-08-13 (Jon, D1–D4)
- **Raise size of record:** ~~$10M first close, tranched to $25M~~ → **a $10 million Series A** (Jon 2026-10-10).
- **Use of funds:** ~~first close = Scorpius option + RDRE/TACFI match + BLK3; BLK4 in the $25M expansion~~ → **Scorpius acquisition + finish/fly BLK3 + next-gen propulsion trade study; no BLK4** (Jon 2026-10-10).
- **Listing path:** private growth Series A now; **TXSE-primary as the dated, conditioned destination** (~18–24 mo, conditioned on capital raised + revenue scale ~$20–50M); prior Euronext route discontinued; purge all "TBD."
- **Scorpius fairness opinion:** **Eqvista ENGAGED (in progress)** to opine on the acquisition terms. Eqvista's multi-year familiarity is an asset (not a conflict); independence = flat/non-contingent fee + no stake (confirm). Jon fully informs the appraiser; **disinterested directors approve with Jon abstaining from that vote** (not recusal from knowledge). Related-party disclosure memo drafted (`drafts/Scorpius_RelatedParty_Disclosure_Memo_DRAFT_2026-08-13.md`) — securities counsel review before use.
- **Single source of truth:** `FIGURES_OF_RECORD.md` (this folder) — every file must match it.
- **2026-10-10 archive + swap (D-7282041, Jon):** superseded originals of the deck (2026-09-06 CURRENT), model v12, 5.1, and 5.2 moved to `_ARCHIVE_Superseded/2026-10-10_strategy-rev/`, along with the `_BROKEN_pre-smartart-fix` folder. The `rev-2026-10-10` files are now the room copies. The Scorpius counsel term sheet moved to `_RELATED_NotRoomFiles/`. Peony room copies get swapped to match.
