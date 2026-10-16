import pytest

from src.verification.checks.coding import transfer_check
from src.verification.lean_runner import LeanRunner
from src.verification.results import Status
from src.verification.source_builder import SourceAssembler
from src.verification.verifier import LeanVerifier

pytestmark = pytest.mark.lean


def test_definition_error_is_error(verifier):
    asm = SourceAssembler(imports=["Demo.Coding"])
    asm.define("def broken : Nat := \"not a nat\"")
    asm.prove("t", "1 = 1", "rfl")
    assert verifier.verify(asm.build(Status.PASS)).status == Status.ERROR


def test_unknown_import_is_error(verifier):
    asm = SourceAssembler(imports=["Demo.DoesNotExist"])
    asm.prove("t", "1 = 1", "rfl")
    assert verifier.verify(asm.build(Status.PASS)).status == Status.ERROR


def test_forbidden_token_is_rejected_before_running(verifier):
    asm = SourceAssembler(imports=["Demo.Coding"])
    asm.prove("t", "1 = 2", "sorry")
    result = verifier.verify(asm.build(Status.PASS))
    assert result.status == Status.ERROR
    assert result.exit_code is None


def test_timeout(lean_runner):
    runner = LeanRunner(lean_runner.project_dir, lean_runner.work_dir, timeout_sec=0)
    result = LeanVerifier(runner).verify(transfer_check(100, 80, allowed=True))
    assert result.status == Status.TIMEOUT


def test_missing_lake_is_error(lean_runner):
    runner = LeanRunner(lean_runner.project_dir, lean_runner.work_dir, lake_cmd="no-such-lake")
    assert LeanVerifier(runner).verify(transfer_check(1, 1, True)).status == Status.ERROR


def test_work_files_are_cleaned_up(verifier, lean_runner):
    verifier.verify(transfer_check(100, 80, allowed=True))
    assert list(lean_runner.work_dir.glob("*.lean")) == []
