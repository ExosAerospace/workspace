# EC Channel Memory — #home-automation
_Purpose: Home Assistant + solar (Enphase) + battery/inverter infra at Jon's residence_
_Last updated: 2026-09-13 20:01 CDT_
_Canonical detail lives in `home-automation-board.md` + `enphase-envoy-network-fix.md` (repo root) — this file is the channel's working memory._

## System overview
- **Home Assistant:** currently answers at `http://192.168.143.198:8123` — v2026.3.4, 79 entities. (Board previously said 192.168.1.198; verified 2026-09-13 it's live on the 143 subnet, not .1.) Needs a **static DHCP reservation** so it stops moving.
  - **HA long-lived token in `ha-config.env` is DEAD** (401 as of 2026-09-13, re-verified same day) — regenerate a new token in HA (Profile → Long-Lived Access Tokens) and update `ha-config.env` before any HA API work.
  - **2026-09-13 20:00 finding:** Jon handed a FRESH long-lived token (minted 17:06 CDT, 10yr exp, iss `a96da852...`) via clipboard. It **also 401s against `.198`** — as does the old token. `.198` frontend still serves HTTP 200 (HA headers), host pings 3.5ms. Conclusion: **the fresh token was minted on a DIFFERENT HA instance (the "Green box"), not `.198`.** The Green box is NOT on the 143 subnet (full /24 sweep of :8123 returned only `.198`). Mac (on 143) has **no route to `192.168.1.x` or `192.168.22.x`** (double-NAT confirmed) — so if the Green box sits on either, it's unreachable from ExoMac until the network is flattened. NEED FROM JON: the exact URL/IP he sees HA at in his browser (where he generated the token). Fresh token held, NOT yet written to `ha-config.env` (would be wrong to pair it with the `.198` URL).
  - **GUARDRAIL (Jon 2026-09-13): NEVER ask anyone to post a live token/secret in Discord.** Secure handoff only — Jon writes it into `ha-config.env` directly, or Exo mints its own via HA login on the local net. No tokens/secrets in any Discord channel, ever.
  - **Timezone is wrong:** reports America/New_York; should be **America/Chicago** (Settings → System → General).
- **Network / core problem:** Provider **360 Broadband** manages the mesh; it's handing out **three subnets** (double-NAT): `192.168.1.x` (EXOS router — HA), `192.168.22.x` ("John's Router" — Envoy landed here), legacy `192.168.143.x`. No local route between them → HA can't reach the Envoy locally.
  - **Fix ask for provider:** put the entire mesh on ONE subnet / one DHCP server; secondary nodes in **bridge/AP mode** (not router/NAT); + DHCP reservations for HA and Envoy.

## Open threads
### P-005 | Enphase solar offline — Envoy fully OFFLINE since Aug 29 (biggest open item)
- Envoy / IQ Gateway: SN **122027057902** · SKU **X-IQ-AM1-240-3** · MAC **00:35:ff:22:80:1c** (use for reservation) · Wi-Fi only, 2.4GHz ch6 · SW **v8.3.5289**.
- **2026-09-13 20:01 CDT CAPTURE (from Enlighten portal open on ExoMac, System 2011721 "MCS 7107 Deerwood", Gateway detail /envoys/101139545):** Gateway **Web Communication = DOWN, "not connected to Enlighten," LAST REPORT Sat Aug 29 2026 03:03 AM CDT** (~15 days dark). Power Line Comm data unavailable. Devices page: Gateway + microinverter **482144039526 = Not Reporting**; other ~9 micros + Production Meter show Normal (cached/stale). **Supersedes the earlier "phone app works / it's just the HA local API 500" read — the Envoy is offline to Enphase CLOUD too, not just HA.**
- **Root cause reframed:** not a token/HA-network issue — the Envoy dropped off Wi-Fi on Aug 29 and hasn't reported to cloud OR HA since. NOTHING on ExoMac fixes this until the Envoy is physically back online.
- **Fix (at the residence, in order):** (1) power-cycle the Envoy 30s, wait ~5 min for it to rejoin 2.4GHz ch6 Wi-Fi; (2) confirm it flips to "connected" in Enlighten (last-report time updates); (3) then set the static DHCP reservation (MAC 00:35:ff:22:80:1c); (4) reload the HA `enphase_envoy` entry → micros + Envoy return. Cloud "Check Signal Strength / Scan / Reboot" buttons are DISABLED while it's offline, so remote reboot via Enlighten is not possible right now.
- HA entry `enphase_envoy` (entry_id `01KKJCHWGRDFGJ7353KXJAV1SG`) stuck in `setup_retry` / local API 500 — a downstream symptom of the Envoy being offline.
- Enlighten installer account: `megawattcontrols@gmail.com` (creds on file). Portal maintained by Megawatt Control Solutions.

### P-001 | Basen battery (JK BMS via RS485) — serial line physically DEAD
- `sensor.basen_green_jkbms_health = no_serial_data`; ZERO bytes for ~69 days. Not a baud/protocol issue.
- **Next (physical):** verify USB-RS485 adapter plugged/enumerated; A/B not swapped or loose; BMS RS485 port enabled/powered. Only after bytes flow, revisit baud/address. Writes authorized (`switch.basen_green_authorize_modify_settings = on`).

### P-002 | EG4 inverter (Modbus)
- Breakout boards arrived, pending install. No EG4 entities in HA yet.
- **Next:** install breakout board → wire Pin 1 (A+) and Pin 4 (B-) to RS485C port. ⚠️ Pinout conflict: earlier note said pins 7/8 — verify against the EG4 RS485 label before landing wires.
- EG4 model still unknown — need it to build the HA Modbus register map.

### Bench probe tool (2026-09-13, Jon tasking: test EG4 + batteries)
- `home-automation/rs485_probe.py` — self-bootstrapping (venv auto-installs pyserial+pymodbus). Modes: `ports` (list adapters), `sniff [PORT]` (raw byte listen — for the dead BMS line; all-zero across bauds = physical layer), `scan [PORT]` (Modbus RTU scan baud×addr 1-8×regs — finds live baud+slave for HA config). Fixed the macOS venv-symlink re-exec bug (env sentinel). Bench method: pull RS485 adapter from HA → plug into a Mac/Linux box → prove device talks before touching HA. Validated in `ports` mode 2026-09-13.

### Ready now
- Static DHCP reservations for HA + Envoy (kills the recurring IP-move breakage).
- Fix HA timezone → America/Chicago.
- Remove 4 dead AmpliFi entities from HA.

## Completed
- **2026-07-03** — Restored HA connectivity after it moved to .198 (config pointed at stale .166); API verified `{"message":"API running."}`.
