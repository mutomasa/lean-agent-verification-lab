"""ガード → Lean 実行 → 分類 をまとめる検証サービス。"""

from __future__ import annotations

from typing import Any, Protocol

from src.verification.classifier import classify
from src.verification.guards import find_forbidden_tokens
from src.verification.lean_runner import LeanRun
from src.verification.results import Status, VerificationResult
from src.verification.source_builder import LeanCheck


class Runner(Protocol):
    def run(self, source: str) -> LeanRun: ...


class LeanVerifier:
    def __init__(self, runner: Runner) -> None:
        self.runner = runner

    def verify(self, check: LeanCheck, details: dict[str, Any] | None = None) -> VerificationResult:
        details = details or {}
        forbidden = find_forbidden_tokens(check.source)
        if forbidden:
            return self._rejected(check, forbidden, details)
        run = self.runner.run(check.source)
        c = classify(check, run)
        return VerificationResult(
            status=c.status, summary=c.summary, lean_stdout=run.stdout,
            lean_stderr=run.stderr, elapsed_ms=run.elapsed_ms,
            lean_source=check.source, exit_code=run.exit_code, details=details,
        )

    @staticmethod
    def _rejected(check: LeanCheck, forbidden: list[str], details: dict[str, Any]) -> VerificationResult:
        return VerificationResult(
            status=Status.ERROR,
            summary=f"禁止トークンを検出したため実行しません: {forbidden}",
            lean_source=check.source, details=details,
        )


def default_verifier() -> LeanVerifier:
    from config.settings import load_settings
    from src.verification.lean_runner import LeanRunner

    lean = load_settings().lean
    return LeanVerifier(LeanRunner(lean.project_dir, lean.work_dir, lean.timeout_sec))
