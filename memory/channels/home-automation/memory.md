# EC Channel Memory — #home-automation
_Purpose: Home Assistant + solar (Enphase) + battery/inverter infra at Jon's residence_
_Last updated: 2026-09-13_
_Canonical detail lives in `home-automation-board.md` + `enphase-envoy-network-fix.md` (repo root) — this file is the channel's working memory._

## System overview
- **Home Assistant:** `http://192.168.1.198:8123` — v2026.3.4, 79 entities.
  - Moved from .166 → .198 on 2026-07-03 (AmpliFi retired, new router = new DHCP pool). Needs a **static DHCP reservation** so it stops moving.
  - **Timezone is wrong:** reports America/New_York; should be **America/Chicago** (Settings → System → General).
- **Network / core problem:** Provider **360 Broadband** manages the mesh; it's handing out **three subnets** (double-NAT): `192.168.1.x` (EXOS router — HA), `192.168.22.x` ("John's Router" — Envoy landed here), legacy `192.168.143.x`. No local route between them → HA can't reach the Envoy locally.
  - **Fix ask for provider:** put the entire mesh on ONE subnet / one DHCP server; secondary nodes in **bridge/AP mode** (not router/NAT); + DHCP reservations for HA and Envoy.

## Open threads
### P-005 | Enphase solar offline in HA — Envoy local API 500 (biggest open item)
- Envoy / IQ Gateway: SN **122027057902** · SKU **X-IQ-AM1-240-3** · MAC **00:35:ff:22:80:1c** (use for reservation) · Wi-Fi only, 2.4GHz ch6.
- HA entry `enphase_envoy` (entry_id `01KKJCHWGRDFGJ7353KXJAV1SG`) stuck in `setup_retry`: local API returns **500**. Token already refreshed — it's the network path + an Envoy needing a reboot. Enphase phone app works (cloud, not the local API HA uses).
- **Fix:** reboot the Envoy (Enlighten installer → Gateway → Reboot, or local UI `http://<envoy-ip>` → Reboot, or power-cycle 30s, ~5 min to repopulate), then reload the HA entry → ~31–37 microinverters + Envoy return.
- Enlighten installer account: `megawattcontrols@gmail.com` (creds on file).

### P-001 | Basen battery (JK BMS via RS485) — serial line physically DEAD
- `sensor.basen_green_jkbms_health = no_serial_data`; ZERO bytes for ~69 days. Not a baud/protocol issue.
- **Next (physical):** verify USB-RS485 adapter plugged/enumerated; A/B not swapped or loose; BMS RS485 port enabled/powered. Only after bytes flow, revisit baud/address. Writes authorized (`switch.basen_green_authorize_modify_settings = on`).

### P-002 | EG4 inverter (Modbus)
- Breakout boards arrived, pending install. No EG4 entities in HA yet.
- **Next:** install breakout board → wire Pin 1 (A+) and Pin 4 (B-) to RS485C port.

### Ready now
- Static DHCP reservations for HA + Envoy (kills the recurring IP-move breakage).
- Fix HA timezone → America/Chicago.
- Remove 4 dead AmpliFi entities from HA.

## Completed
- **2026-07-03** — Restored HA connectivity after it moved to .198 (config pointed at stale .166); API verified `{"message":"API running."}`.
