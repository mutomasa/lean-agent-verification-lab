"""環境変数から読み込むアプリケーション設定。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _env_str(name: str, default: str) -> str:
    return os.environ.get(name, default)


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    return int(raw) if raw else default


def _resolve(path: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else PROJECT_ROOT / p


@dataclass(frozen=True)
class LLMSettings:
    base_url: str
    api_key: str
    model: str
    timeout_sec: int
    max_retries: int
    tool_mode: str = "json"
    guided_json: bool = True


@dataclass(frozen=True)
class LeanSettings:
    project_dir: Path
    work_dir: Path
    timeout_sec: int


@dataclass(frozen=True)
class Settings:
    llm: LLMSettings
    lean: LeanSettings


def load_settings() -> Settings:
    load_dotenv(PROJECT_ROOT / ".env")
    return Settings(llm=_load_llm(), lean=_load_lean())


def _load_llm() -> LLMSettings:
    return LLMSettings(
        base_url=_env_str("VLLM_BASE_URL", "http://127.0.0.1:8000/v1"),
        api_key=_env_str("VLLM_API_KEY", "local"),
        model=_env_str("VLLM_MODEL", "Qwen/Qwen3-1.7B"),
        timeout_sec=_env_int("VLLM_TIMEOUT_SEC", 30),
        max_retries=_env_int("AGENT_MAX_RETRIES", 2),
        tool_mode=_env_str("AGENT_TOOL_MODE", "json"),
        guided_json=_env_str("VLLM_GUIDED_JSON", "1") == "1",
    )


def _load_lean() -> LeanSettings:
    return LeanSettings(
        project_dir=_resolve(_env_str("LEAN_PROJECT_DIR", "lean")),
        work_dir=_resolve(_env_str("LEAN_WORK_DIR", ".lean_work")),
        timeout_sec=_env_int("LEAN_TIMEOUT_SEC", 60),
    )
