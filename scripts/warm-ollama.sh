#!/bin/zsh
# warm-ollama.sh
# Runs at boot via com.exos.warm-ollama LaunchAgent.
# Waits for the Ollama server to come up after a reboot, then loads the primary
# cron model into RAM and pins it resident (keep_alive: -1) so the morning/noon
# Ollama cron jobs never pay the cold-load penalty (which was timing them out
# right after a reboot).

LOG="/Users/exomac/.openclaw/logs/warm-ollama.log"
MODEL="gemma4:e4b"   # pin the LIGHT model (~10GB). Pinning 35B (27GB) OOMs this 48GB box.
HOST="http://localhost:11434"
mkdir -p "$(dirname "$LOG")"

echo "=== warm-ollama: $(date) ===" >> "$LOG"

# 1. Wait for Ollama to be reachable (up to ~5 min: 60 tries x 5s)
i=0
until curl -sf "$HOST/api/tags" >/dev/null 2>&1; do
    i=$((i+1))
    if [ "$i" -ge 60 ]; then
        echo "[!] Ollama not reachable after 5 min — giving up." >> "$LOG"
        exit 1
    fi
    sleep 5
done
echo "[✓] Ollama reachable after $((i*5))s" >> "$LOG"

# 2. Load the model and pin it resident (keep_alive -1 = stay until unloaded/reboot)
RESP=$(curl -s "$HOST/api/generate" \
    -d "{\"model\":\"$MODEL\",\"prompt\":\"ok\",\"stream\":false,\"keep_alive\":-1}" 2>&1)
if echo "$RESP" | grep -q '"response"'; then
    echo "[✓] $MODEL loaded and pinned resident (keep_alive=-1)" >> "$LOG"
else
    echo "[!] Warm request did not succeed: $(echo "$RESP" | head -c 200)" >> "$LOG"
    exit 1
fi

echo "=== done: $(date) ===" >> "$LOG"
exit 0
