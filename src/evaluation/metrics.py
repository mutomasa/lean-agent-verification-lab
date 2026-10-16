"""評価指標の計算。"""

from __future__ import annotations

import statistics
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class Timing:
    mean_ms: float
    p50_ms: float
    max_ms: float


def timing(values_ms: list[int]) -> Timing | None:
    if not values_ms:
        return None
    return Timing(statistics.mean(values_ms), statistics.median(values_ms), max(values_ms))


def rate(hits: int, total: int) -> float:
    return hits / total if total else 0.0


def gpu_memory_used_mib() -> int | None:
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10, check=True, shell=False)
    except (OSError, subprocess.SubprocessError):
        return None
    return int(out.stdout.strip().splitlines()[0])
