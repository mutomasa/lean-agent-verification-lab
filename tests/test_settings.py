from config.settings import PROJECT_ROOT, load_settings


def test_defaults(monkeypatch):
    for key in ["VLLM_BASE_URL", "VLLM_MODEL", "LEAN_TIMEOUT_SEC", "LEAN_PROJECT_DIR"]:
        monkeypatch.delenv(key, raising=False)
    s = load_settings()
    assert s.llm.model == "Qwen/Qwen3-1.7B"
    assert s.lean.project_dir == PROJECT_ROOT / "lean"


def test_env_override(monkeypatch):
    monkeypatch.setenv("VLLM_MODEL", "custom")
    monkeypatch.setenv("LEAN_TIMEOUT_SEC", "5")
    s = load_settings()
    assert s.llm.model == "custom"
    assert s.lean.timeout_sec == 5
