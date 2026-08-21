# Exos Series A — Data Room Manifest (Single Source of Truth)

**Owner:** John Quinn, Cofounder & CEO
**Established:** 2026-08-08 (P0 lockdown, post-MDB review)
**Rule:** Exactly ONE canonical file per artifact lives in the shared room. Everything else is archived (never deleted), outside the room. No reviewer should ever see two versions of the same document.

---

## CANONICAL — keep these live in the room (and ONLY these)

| Artifact | Canonical file | Version / Date | Anchor value | Owner |
|---|---|---|---|---|
| Financial model | `EXOS_Financial_Model_Full_Revenue_FIXED_v9_409Afinal.xlsx` | v9 · Jun 19 2026 · 10-yr | DCF $252.0M / concluded equity **$169.7M** | Jon / Kyle |
| 409A valuation | `EXOS_409A_Eqvista_2026-03-31_CURRENT.pdf` | Eqvista · dated 06/10/2026, as-of 03/31/2026 | **$8.66/sh**, $169.7M equity, DLOM 36.51% | Jon |
| Pitch deck | `Exos_SeriesA_PitchDeck_FULL_2026-08-16_CORRECTED.pptx` | Aug 16 2026 · **policy-tailwind slide added Aug 21 2026** (slide 18, after "Why Now") | ⚠ must pass P1 reconciliation before room reopens; hold to $169.7M valuation of record | Jon |
| Policy tailwind brief | `Exos_Policy_Tailwind_NSTP_2026-08-21.pdf` (+ editable `.docx` twin) | Aug 21 2026 · **on Exos PRIMARY letterhead** | National Space Transportation Policy ("Golden Age") → Exos alignment; **no valuation stated** (room-safe) | Jon / Exo |
| Cap table | `Exos_Capitalization_Table.xlsx` | confirm current dated version | — | Kyle |

**Single valuation of record:** **$169.7M equity value** (Eqvista 03/31/2026 409A). This is the only headline number that appears in the room. The DCF / market-approach / comps figures live *inside the model only*, tied together by a reconciliation tab (built in P1) — never shown side-by-side unbridged.

**Jon decisions — LOCKED 2026-08-13 (D1–D4); see FIGURES_OF_RECORD.md:**
- **Raise size of record** — $10M first close, tranched to $25M *(supersedes the prior $40–50M 5-year figure)*
- **Use of funds** — BLK3 in the first close; BLK4 in the $25M expansion
- **Listing path** — private growth Series A now; TXSE-primary as the dated, conditioned destination

These are set. The room follows FIGURES_OF_RECORD.md; anything contradicting it is superseded.

---

## ARCHIVE — pull these OUT of the shared room (superseded, retained in `_ARCHIVE_Superseded/`)

**Models (all superseded by v9):**
- `EXOS_Financial_Model_Full_Revenue_FIXED_v5_jq.xlsx` — 5-yr, DCF $74.8M (the file that made us look worth 1/3 as much)
- `..._v5_jq_BACKUP.xlsx`, `..._v7.xlsx`, `..._v8.xlsx`
- `EXOS_Financial_Model_Rev_May29_2026.docx`, `..._v8_May29_2026.docx`, `..._v8_May29_2026_TXSE.docx`

**409A (superseded — the drift is fine, but only the current one belongs in the room):**
- `EXOS_409A_Aranca_April2024.pdf` — $5.03
- `EXOS_409A_Eqvista_May2025.pdf` — $7.06

**Decks (superseded by July 2026):**
- `Exos_PitchDeck_March_2026.pptx`
- `Exos_SeriesA_PitchDeck_May2026.pptx`
- `Exos_SeriesA_PitchDeck_June2026_PhysicalAI.pptx`
- `Exos_SeriesA_PitchDeck_June2026_PhysicalAI_TXSE.pptx`

**Not room files (keep out — investor-specific / different purpose):** `Exos_Haas_Custom_Deck_2026-07.pptx`, Montana partnership decks.

**Related package (separate room):** `../Navy_Commission/` — Commission on the Future of the Navy site-visit materials (deck + deck-aligned model + projections) on the **conservative Cash Flow case (2027–2032)**. Kept separate on purpose; do not co-mingle with the Series A canonical set. See `../Navy_Commission/DATA_ROOM_MANIFEST.md`.

---

## PRE-ACCESS CHECKLIST — run before granting ANY new reviewer

Do not share the room until every box is true:
- [ ] Only ONE model, ONE 409A, ONE deck, ONE cap table are visible in the room.
- [ ] Valuation number is identical across model, deck, and 409A ($169.7M).
- [ ] Raise size is identical everywhere (single number of record).
- [ ] Use-of-funds table is identical everywhere (BLK3 vs BLK4 resolved).
- [ ] Base case shows contracted revenue only; TACFI/STRATFI/entX-expansion sit in a separate Upside column.
- [ ] No file marked "TBD" on listing path.
- [ ] Scorpius related-party: fairness opinion + disclosure memo present (once P3 done).

---

## Status
- **P0 (this doc):** DONE — canonical set staged in `_CANONICAL/`, superseded staged in `_ARCHIVE_Superseded/`, manifest published. Execute the same keep/archive split inside the Peony room.
- **2026-08-21 policy update:** added policy-tailwind slide to the canonical pitch deck (slide 18) + new `Exos_Policy_Tailwind_NSTP_2026-08-21.pdf`. **To sync to the Peony room:** upload the updated deck + the policy brief. Deck backup at `.backups/`. NOTE: `_CANONICAL/` currently holds TWO decks (Pitch FULL Aug-16 + Strategic Aug-13) — the one-canonical-deck rule wants one; confirm whether to archive the Strategic deck or mirror the policy slide into it.
- **P1–P4:** blocked on Jon decisions #1 (fairness opinion), #2 (listing path), #3 (raise size). See task 1859.

---

## DECISIONS LOCKED — 2026-08-13 (Jon, D1–D4)
- **Raise size of record:** $10M first close, tranched to $25M. *(supersedes the "$10M / $25M / $40–50M" open item)*
- **Use of funds:** first close = Scorpius ROFR + RDRE/TACFI match + **BLK3** build; **BLK4** in the $25M expansion.
- **Listing path:** private growth Series A now; **TXSE-primary as the dated, conditioned destination** (~18–24 mo, conditioned on ~$25M raised + revenue scale ~$20–50M); prior Euronext route discontinued; purge all "TBD."
- **Scorpius fairness opinion:** **Eqvista ENGAGED (in progress)** to opine on the acquisition terms. Eqvista's multi-year familiarity is an asset (not a conflict); independence = flat/non-contingent fee + no stake (confirm). Jon fully informs the appraiser; **disinterested directors approve with Jon abstaining from that vote** (not recusal from knowledge). Related-party disclosure memo drafted (`drafts/Scorpius_RelatedParty_Disclosure_Memo_DRAFT_2026-08-13.md`) — securities counsel review before use.
- **Single source of truth:** `FIGURES_OF_RECORD.md` (this folder) — every file must match it.
