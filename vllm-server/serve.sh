#!/usr/bin/env bash
# vLLM + Qwen3-1.7B を RTX A1000 8GB で起動する。
# VLLM_USE_FLASHINFER_SAMPLER=0: CUDA Toolkit (nvcc) が無い環境で FlashInfer の JIT を避ける。
set -euo pipefail
cd "$(dirname "$0")"
export VLLM_USE_FLASHINFER_SAMPLER="${VLLM_USE_FLASHINFER_SAMPLER:-0}"
exec uv run vllm serve "${VLLM_MODEL:-Qwen/Qwen3-1.7B}" \
  --host 127.0.0.1 --port "${VLLM_PORT:-8000}" --dtype auto \
  --max-model-len "${VLLM_MAX_MODEL_LEN:-4096}" \
  --gpu-memory-utilization "${VLLM_GPU_MEMORY_UTILIZATION:-0.80}" \
  --enable-auto-tool-choice --tool-call-parser hermes "$@"
