#!/bin/zsh
# solar-report.sh
# Daily solar report — runs at 7:00 AM CT via OpenClaw cron
# Pulls live data from Home Assistant Enphase + EG4 integration

source /Users/exomac/.openclaw/workspace/ha-config.env

LOG_DIR="/Users/exomac/.openclaw/workspace/logs"
mkdir -p "$LOG_DIR"

# Fetch all solar/battery values
get_state() {
    curl -s -H "Authorization: Bearer $HA_TOKEN" \
        "$HA_URL/api/states/$1" 2>/dev/null | \
        python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('state','unknown'))"
}

# Enphase solar
CURRENT_PV=$(get_state "sensor.envoy_122027057902_current_power_production")
TODAY_KWH=$(get_state "sensor.envoy_122027057902_energy_production_today")
WEEK_KWH=$(get_state "sensor.envoy_122027057902_energy_production_last_seven_days")
LIFETIME_MWH=$(get_state "sensor.envoy_122027057902_lifetime_energy_production")

# EG4 battery/inverter
BATT_SOC=$(get_state "sensor.eg4_battery_soc")
BATT_SOH=$(get_state "sensor.eg4_battery_soh")
BATT_CYCLES=$(get_state "sensor.eg4_battery_cycle_count")
GRID_IMPORT=$(get_state "sensor.eg4_energy_daily_grid_import")
GRID_EXPORT=$(get_state "sensor.eg4_energy_daily_grid_export")
LOAD_TODAY=$(get_state "sensor.eg4_energy_daily_load")
INVERTER_MODE=$(get_state "sensor.eg4_inverter_mode")
FAULT_CODE=$(get_state "sensor.eg4_fault_code")
WARNING_CODE=$(get_state "sensor.eg4_warning_code")

# Check for underperforming microinverters
LOW_PANELS=$(curl -s -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/states" 2>/dev/null | \
python3 -c "
import json, sys
states = json.load(sys.stdin)
low = []
for s in states:
    if s['entity_id'].startswith('sensor.inverter_'):
        try:
            val = float(s['state'])
            if val < 50:
                low.append(f\"{s['entity_id']}: {val}W\")
        except:
            pass
print('\n'.join(low) if low else 'All panels nominal')
")

DATE=$(date "+%A, %B %-d")

echo "=== Solar Report $DATE ===" >> "$LOG_DIR/solar-$(date +%Y-%m-%d).log"
echo "PV: $CURRENT_PV kW | Today: $TODAY_KWH kWh | 7-day: $WEEK_KWH kWh" >> "$LOG_DIR/solar-$(date +%Y-%m-%d).log"

# Build Telegram message
MSG="☀️ *Daily Solar Report — $DATE*

*Enphase Solar*
├ Current output: ${CURRENT_PV} kW
├ Today so far: ${TODAY_KWH} kWh
├ Last 7 days: ${WEEK_KWH} kWh
└ Lifetime: ${LIFETIME_MWH} MWh

*EG4 Battery/Inverter*
├ Battery SOC: ${BATT_SOC}%
├ Battery health: ${BATT_SOH}%
├ Cycle count: ${BATT_CYCLES}
├ Mode: ${INVERTER_MODE}
├ Grid import today: ${GRID_IMPORT} kWh
├ Grid export today: ${GRID_EXPORT} kWh
├ Load today: ${LOAD_TODAY} kWh
├ Fault code: ${FAULT_CODE}
└ Warning code: ${WARNING_CODE}

*Panel Status*
${LOW_PANELS}"

# Send via msmtp to ProtonMail (which forwards to Telegram via OpenClaw)
# Use OpenClaw cron delivery instead — this script outputs the report
# so the cron agent can deliver it
echo "$MSG"
exit 0
