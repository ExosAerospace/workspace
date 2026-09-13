#!/bin/bash
# studio_model_pull.sh — stand up the Ollama model set on the new Mac Studio (M3 Ultra, 96GB).
# Run this ON THE STUDIO after Ollama is installed. 96GB unified memory comfortably runs
# 70B-class DENSE models (~40-48GB @ Q4). The Trick C++/Python benchmark showed the MoE
# (qwen3.6:35b-a3b) underperformed on coding, so the coder here is DENSE.
#
# Storage: models land on the 2TB internal SSD (fast). Kimi K3 (1.5TB) is NOT loaded here —
# it stays an offsite archive on the WD 8TB with the Mini (can't fit in 96GB).
set -uo pipefail

echo "=== 1) Ollama version check (mini was on 0.24.0 — upgrade to current) ==="
if command -v ollama >/dev/null 2>&1; then ollama --version; else
  echo "Ollama not installed. Install:  brew install ollama   (or download from ollama.com), then re-run."
  exit 1
fi

echo "=== 2) Core model set for 96GB ==="
# --- Dense coder (primary AI-assist for Trick / C++ / Python; replaces the weak MoE) ---
ollama pull qwen2.5-coder:32b            # ~20GB Q4 — dense, strong on code
# --- 70B-class general model (reasoning/synthesis fallback when cloud is unavailable) ---
ollama pull llama3.3:70b                  # ~40GB Q4 — dense 70B; fits 96GB
# --- Embeddings (RAG / semantic search; already used across MC) ---
ollama pull nomic-embed-text
# --- Small fast local (quick classification / cheap calls) ---
ollama pull gemma4:e4b

echo "=== 3) Bring over the tuned Exos BD model from the mini ==="
echo "exos-glimmer (Muse-Glimmer-30B) is a local fine-tune — copy ~/.ollama/models from the mini"
echo "OR re-create from its Modelfile. Verify with: ollama list | grep glimmer"

echo "=== 4) OPTIONAL extras (pull only if you want them resident) ==="
echo "  ollama pull qwen2.5:72b        # alt 70B-class general"
echo "  # qwen3.6:35b-a3b (MoE) — SKIP as the coder; keep only if you want it for general chat"

echo "=== 5) Consider MLX-LM for ~10-30% faster inference on Apple Silicon ==="
echo "  pip install mlx-lm   # then benchmark vs Ollama on a sample Trick task before committing"

echo "=== done — verify: ollama list ==="
ollama list
