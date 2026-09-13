# Exos Mac Studio Migration Runbook
**Goal:** Mac Studio (M3 Ultra, 96 GB, 2 TB; order W1877619261) becomes the **primary always-on host** for the whole Exos stack. Current Mac mini M4 Pro ("ExoMac") → **offsite warm-standby / DR node at Location 2**.
**Security/connectivity layer = Cloudflare** (Zero Trust / Cloudflare One Client + cloudflared) for MC access AND machine-to-machine — **NOT Tailscale** (Jon/Atomus 2026-09-13).
**Scope on current host:** 127 `com.exos.*` launchd jobs · 9.7 GB workspace (git) · ~50 GB Ollama models · 37 secrets · ProtonMail Bridge · cloudflared tunnel (mc.exosaero.space) · QuickBooks OAuth · browser profile.
**Storage:** Studio → new **4 TB** Time Machine. Offsite Mini → keeps the **WD 8 TB** (offsite TM + Kimi K3 archive).
**DELIVERY: CONFIRMED Sept 16, 2026** (shipped 9/11, order W1877619261, Standard Delivery).
**Sites:** Studio = **Jon's residence** (fiber + Starlink backup; serves the Exos Greenville location remotely). Mini = **Lizi's residence** (fiber) — Lizi knows she inherits it once the Studio is up for backup services.

**Pre-built & self-tested on the mini 2026-09-13 (ready to point Studio→Mini + load):**
- `scripts/backup_health_gate.py` — shared gate (sentinel + pause). Tested: healthy/stale/pause/resume all pass.
- `scripts/studio_dr_backup.sh` — daily backup + manifest + sentinel. Tested rc=0 (and benign 23/24 handling).
- `scripts/backup_watchdog.py` — hourly; alerts Jon + pauses risky crons on outage, dedupes, auto-resumes. Tested full cycle w/ stubbed alerts.
- `scripts/studio_model_pull.sh` — 96 GB model set (dense coder + 70B + embed).
- `scripts/secrets_transfer.py` — AES-256 package/unpack of secrets+Bridge cert+msmtp for local transfer.
- `config/dr-backup.json` — tunables (currently LOCAL self-test; flip `dest`→Mini + `dest_is_remote:true` + `git_push:true` at migration).
- `config/launchd-staged/{com.exos.dr-backup,com.exos.backup-watchdog}.plist` — copy to `~/Library/LaunchAgents/` + `launchctl load`.
- ⚠️ At migration, **wire the gate into the risky crons**: add `import backup_health_gate; backup_health_gate.guard_or_exit("<job>")` at the top of the state-mutating/external-send jobs (mc-email-command, decisions ingest, CRM/task writers, funds trackers). NOT wired on the mini today so current production is unaffected.

---
## Phase 0 — Pre-arrival (stage now)
- [ ] **Decide + hold: Studio admin username = `exomac`.** ⛔ Non-negotiable — all 127 launchd plists + configs hardcode `/Users/exomac/...`. Same username = drop-in; different = rewrite 127 files.
- [ ] Confirm Atomus will **enroll the Studio in MDM/CMMC scope** and provision the **Cloudflare One Client / Zero Trust** posture on it (same as ExoMac). Give Atomus the ship-date heads-up.
- [ ] Finalize the **Ollama model set for 96 GB**: a **dense coder** (qwen3.6-27B dense Q6/Q8 or Qwen2.5-Coder-32B — the MoE was weak on the Trick benchmark) + a **70B-class general** model. Install **current Ollama** (mini is on 0.24.0) and evaluate **MLX-LM** (~10–30% faster on Apple Silicon).
- [ ] Inventory the **37 secrets** + ProtonMail Bridge cert/password + QuickBooks OAuth tokens + browser logins. Transfer plan = local high-speed during setup (both machines co-located), **never Discord/email**.
- [ ] Snapshot current host state: `launchctl list | grep com.exos` (expect 127), `ollama list`, git status clean/committed, latest Time Machine + WD backup verified.

## Phase 1 — Studio base (co-located with Mini)
- [ ] macOS setup, **username `exomac`**, latest updates, FileVault ON.
- [ ] Static LAN IP / DHCP reservation; 10 GbE wired (Cat6a). UPS connected + PowerPanel/macOS graceful-shutdown configured.
- [ ] Homebrew, mise (node 24.x), python3, git, msmtp, rsync.

## Phase 2 — Cloudflare (security layer)
- [ ] Install **Cloudflare One Client (WARP)** + enroll in the Exos Zero Trust org (Atomus).
- [ ] Install **cloudflared**; stage the tunnel config that will serve MC (do NOT cut over yet).
- [ ] Verify machine-to-machine reachability (Studio ↔ Mini) goes over Cloudflare, per Atomus design. No Tailscale.

## Phase 3 — Data sync (local, high-speed 10 GbE / TB5)
- [ ] `rsync` the **workspace** (`~/.openclaw/workspace`, 9.7 GB, git repo).
- [ ] Copy `~/.openclaw/` config, **secrets.json (37 keys)**, `~/.protonmail-bridge.crt`, msmtp config, browser profile.
- [ ] **Ollama models (~50 GB):** copy `~/.ollama/models` OR re-pull fresh on the Studio (prefer fresh pull of the finalized 96 GB set).

## Phase 4 — Services
- [ ] Install OpenClaw gateway; point at the synced workspace/config.
- [ ] **ProtonMail Bridge** reinstall + **re-auth (2FA)** — inbound/outbound email depends on it; verify send + IMAP read.
- [ ] QuickBooks OAuth: re-auth if tokens don't carry over.
- [ ] Start Ollama (current version) on `:11434`; confirm the model set loads.
- [ ] MC server up on its port (launchd-owned); confirm `/api/decisions` responds locally.

## Phase 5 — launchd (127 jobs)
- [ ] Copy all `~/Library/LaunchAgents/com.exos.*.plist` (paths match iff username = `exomac`).
- [ ] `launchctl load` all; `launchctl list | grep com.exos` → **expect 127**.
- [ ] Spot-check the critical ones fire: heartbeat, capital_bridge_funds, legacy-triage, weekly-meeting-prep, mc-email-command, forwarded-mail-watch.

## Phase 6 — Cloudflare tunnel cutover (brief MC downtime)
- [ ] Repoint the **mc.exosaero.space** tunnel origin from Mini → Studio (cloudflared config / Cloudflare dashboard).
- [ ] Verify `mc.exosaero.space` resolves to the Studio through Cloudflare Access; `.public-url` = `https://mc.exosaero.space` (never LAN IP).
- [ ] Confirm Zero Trust policies still gate access as before.

## Phase 7 — Verify (before decommissioning Mini as primary)
- [ ] MC loads via Cloudflare; Decisions/CRM/tasks render; `/api/decisions` OK.
- [ ] Crons producing output (watch logs for a full cycle); **fix the two known-broken loops while here**: Overnight Resolver → Decision API bridge (dead 27 days) and the meta-evaluator loop (D-7281648).
- [ ] Bridge sends a test email + reads inbox. Ollama serves a test prompt. Fleet health/watchdog green.
- [ ] Run **48 h in parallel** (Mini still able to resume) before flipping Mini to DR-only.

## Phase 8 — Mini → Lizi's residence (Location 2: offsite DR + Lizi's workstation + batch worker)
- [ ] Relocate Mini to **Lizi's residence** (reliable fiber); attach **WD 8 TB** (offsite TM + Kimi K3 archive) + UPS + internet + display/kb for Lizi.
- [ ] Cloudflare tunnel/Access on the Mini for DR reachability **and Lizi's identity** (per Atomus).
- [ ] **Compliance (machine at an employee residence holding DR + portal logins):** Atomus MDM/CMMC enrollment + FileVault ON + Cloudflare Access gated to Lizi.
- [ ] **Lizi's application/login workstation:** OpenClaw session on the Mini she drives at her desk (MC Exobot widget for chat + browser tool with HER browser profile / HER portal creds+2FA). This is how she gets Exo support filling web applications (the NIH-style capability), local + low-latency for her.
- [ ] Roles on the Mini: (1) Lizi interactive, (2) batch worker, (3) hot DR. **Batch yields to Lizi's active session** (interactive priority). It does NOT run the autonomous send-crons (singleton stays on the Studio → no split-brain).
- [ ] Sync workspace + model set Studio↔Mini **over Cloudflare**.
- [ ] Studio → new **4 TB Time Machine** + UPS.
- [ ] Redundancy check: **models 2 copies / 2 sites**; **Mac data 3 copies** (Studio live + Studio 4TB TM + Mini/WD 8TB at Lizi's).

## Phase 8b — Utilization-sharing loop go-live (both boxes)
- [ ] Load `com.exos.util-metrics` on the Studio too (collector already live on the Mini since 9/13).
- [ ] **GPU telemetry sudoers** (each box) — enables real GPU% sampling when proxies cross the warm line. Add a drop-in `/etc/sudoers.d/exos-powermetrics`:
      `exomac ALL=(root) NOPASSWD: /usr/bin/powermetrics --samplers gpu_power -n 1 -i 200`
      (run `sudo visudo -f /etc/sudoers.d/exos-powermetrics`). Atomus should bless this.
- [ ] Build the **dispatcher** (route jobs by latency + live load; interactive-priority on the Mini). Config in `config/capacity-forecast.json`.
- [ ] Pre-order authority = **Option 1: draft a Decision for Jon's approval** (built default; no auto-purchase).

## Phase 9 — Daily backup + failover safety (both machines = `exomac`)
**Design:** both the Studio and the offsite Mini run as username `exomac` (identical `/Users/exomac` paths) — this is what makes failover clean: any plist/script/config runs on either box unchanged. Guardrail: **only ONE box is "active" at a time** (active crons + cloudflared tunnel + ProtonMail Bridge). Studio = active/primary; Mini = **standby** (active jobs disabled) until promoted, so no duplicate sends/Decisions (split-brain).

- [ ] **Daily auto-backup Studio → offsite Mini** (launchd, ~02:00 CT, over Cloudflare): rsync workspace + `~/.openclaw` config + secrets + MC data; `git push`; write a `.backup-healthy` sentinel with timestamp + checksum manifest on success.
- [ ] **Backup-health watchdog** (launchd, ~03:00 CT + hourly): if the last Studio→Mini backup is older than the threshold (e.g. >26 h) OR the manifest checksum fails →
  - **Notify Jon** (Discord DM + email).
  - **Pause Studio-only / state-mutating tasks** via a shared **backup-health gate**: risky crons (external sends, Decisions, CRM/task mutations, funds trackers) check `.backup-healthy` at startup and **no-op if stale** — so state can't drift further while unprotected. Read-only jobs keep running. Auto-resume when backup health returns.
- [ ] **Failover to Mini = human-confirmed promote (NOT auto).** Because both are `exomac` with synced state, promoting the Mini is: enable its active crons + repoint the cloudflared tunnel to it. Kept manual-with-confirmation on purpose — auto-promote risks both boxes going active = duplicate email/Decisions.
- [ ] Redundancy: models 2 copies/2 sites; **Mac data 3 copies** (Studio live + Studio 4TB TM + offsite Mini/WD 8TB).

## Rollback
If the Studio fails verification, **Mini stays primary** — do not relocate/decommission it until the Studio has run clean for 48 h.
