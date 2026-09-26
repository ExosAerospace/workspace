#!/bin/zsh
# Weekly floor-rotation for high-volume channel sessions so transcripts never grow
# unbounded even if LLM summarization is unavailable. Uses --max-lines (deterministic,
# no model call). Event-driven compaction (config maxActiveTranscriptBytes) is primary;
# this is the belt-and-suspenders cadence Jon asked for.
OC=$(command -v openclaw || echo /Users/exomac/.local/share/mise/shims/openclaw)
KEEP=150
# add channel session keys here as needed
KEYS=(
  "agent:main:discord:channel:1501636614034821320"   # #rd-team
)
for k in "${KEYS[@]}"; do
  "$OC" sessions compact "$k" --agent main --max-lines "$KEEP" 2>&1 | tail -2
done
