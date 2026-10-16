import shutil

import pytest

from config.settings import load_settings
from src.verification.lean_runner import LeanRunner
from src.verification.verifier import LeanVerifier


@pytest.fixture(scope="session")
def lean_runner(tmp_path_factory):
    if shutil.which("lake") is None:
        pytest.skip("lake が見つかりません")
    lean = load_settings().lean
    runner = LeanRunner(lean.project_dir, tmp_path_factory.mktemp("lean_work"), timeout_sec=120)
    build = runner.build()
    assert build.exit_code == 0, build.stdout + build.stderr
    return runner


@pytest.fixture(scope="session")
def verifier(lean_runner):
    return LeanVerifier(lean_runner)
