# Supplier-Diligence-exo3 — process governance record

**Type:** exo3 process (AI-managed program). **Owner:** Exo + human clearer (John Quinn / quality-security owner).
**Purpose:** continuous due diligence on every Exos supplier; proves DIB readiness SCRM-1..5 and feeds ERP/GAAP supplier analytics. ERP/QuickBooks is the system of record — this never duplicates the vendor master.

## Data sources (ERP is SoR)
- **QuickBooks Online API** — vendor master + AP/spend. Divvy/BILL Spend & Expense is **already synced into QuickBooks**, so QB alone covers card spend; no separate BILL API needed. Creds in secrets.json: `qb_client_id`, `qb_client_secret`, `qb_refresh_token`, `qb_realm_id` (client: `scripts/qb_client.py`, auto-rotates the refresh token).

## Screen (deterministic dispatch; the model is NOT in the approve path)
Per supplier: **OFAC SDN** + **SAM.gov exclusions** + **FOCI/country** (reused from the CRM DD engine / `export_screen`), **adverse-media** (Tavily results *model-adjudicated* — flag-only, never auto-clears; falls back to no-flag if unavailable), **spend concentration** (single-source, SCRM-4), **FCI/CUI exposure** (CMMC flow-down, SCRM-5). → tier **GREEN / AMBER / RED**.

## Clearance (AI + human)
- **GREEN** (clean, domestic, no concentration): **auto-cleared by Exo**, logged (dossier pass). No human needed.
- **AMBER / RED** (any possible issue): **HELD** → a dual-clearance **Decision card** routes to the human (`assignedTo`); nothing risky clears without a human signature. Hard fails (OFAC/SAM/adversary) also raise priority + a dossier fail. Re-runs carry the human's prior answer forward (no re-nag).

## SCRM readiness mapping (Government/DIB Readiness Register)
- SCRM-1 approved-supplier list · SCRM-2 quality/performance scorecards · SCRM-3 risk tier · SCRM-4 concentration · SCRM-5 CMMC/CUI flow-down — all populated from `supplier-dd-registry.json`.

## Operating model
- **Schedule:** nightly launchd `com.exos.supplier-dd-exo3` (windowed, resumable, cost-capped via the CRM engine's Tavily/Ollama budget — local model = ~$0). Real-time single-supplier: `--supplier "Name"`.
- **Outputs:** `mission-control/data/supplier-dd-registry.json` (supplier master + DD status + metrics), Decisions inbox (held items), dossiers (`/dossier.html`), failed-DD registry (hard fails).
- **Files:** `scripts/supplier_dd_exo3.py`, `scripts/qb_client.py`, `config/launchd/com.exos.supplier-dd-exo3.plist`.

## To go live
1. Add the four `qb_*` creds to secrets.json (Intuit Developer app + OAuth Playground → Refresh Token + Realm ID).
2. `python3 scripts/supplier_dd_exo3.py --now` (first full pass against live QuickBooks).
3. Install the launchd unit (below) for the standing nightly process.
4. (Next) wire `supplier-dd-registry.json` into the gov-readiness register + a `/api/supplier-dd` MC view.
