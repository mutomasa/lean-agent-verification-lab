"""Lean の実行結果を Status に分類する。

証明失敗（PROOF_FAILED）を仕様違反（VIOLATION）と混同しないことが重要。
VIOLATION は「違反していること」を Lean が証明できた場合にのみ返す。
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from src.verification.guards import parse_axioms, unapproved_axioms
from src.verification.lean_runner import LeanRun
from src.verification.results import Status
from src.verification.source_builder import LeanCheck

_ERROR_LINE_RE = re.compile(r"^[^\n:]+\.lean:(\d+):\d+: error", re.MULTILINE)


@dataclass(frozen=True)
class Classification:
    status: Status
    summary: str


def classify(check: LeanCheck, run: LeanRun) -> Classification:
    if run.timed_out:
        return Classification(Status.TIMEOUT, "Lean の実行がタイムアウトしました")
    if run.exit_code is None:
        return Classification(Status.ERROR, f"Lean を起動できませんでした: {run.stderr}")
    error_lines = _error_lines(run.stdout + "\n" + run.stderr)
    if run.exit_code != 0 or error_lines:
        return _classify_failure(check, error_lines)
    return _classify_success(check, run)


def _error_lines(output: str) -> list[int]:
    return [int(n) for n in _ERROR_LINE_RE.findall(output)]


def _classify_failure(check: LeanCheck, error_lines: list[int]) -> Classification:
    if error_lines and all(n >= check.check_first_line for n in error_lines):
        return Classification(Status.PROOF_FAILED,
                              "Lean で主張を証明できませんでした（違反の証明ではありません）")
    return Classification(Status.ERROR, "Lean の実行エラー（定義部・構文・環境）")


def _classify_success(check: LeanCheck, run: LeanRun) -> Classification:
    axioms = parse_axioms(run.stdout)
    missing = [n for n in check.theorem_names if n not in axioms]
    if missing:
        return Classification(Status.ERROR, f"公理の確認結果がありません: {missing}")
    bad = unapproved_axioms(axioms)
    if bad:
        return Classification(Status.ERROR, f"未承認の公理に依存しています: {bad}")
    return Classification(check.claim, _success_summary(check.claim))


def _success_summary(claim: Status) -> str:
    if claim == Status.VIOLATION:
        return "Lean が仕様違反を証明しました"
    return "Lean が仕様を満たすことを証明しました"
