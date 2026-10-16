from src.verification.classifier import classify
from src.verification.lean_runner import LeanRun
from src.verification.results import Status
from src.verification.source_builder import LeanCheck

CHECK = LeanCheck(source="", claim=Status.VIOLATION, theorem_names=("t",), check_first_line=10)


def run(stdout="", code=0, timed_out=False):
    return LeanRun(stdout=stdout, stderr="", exit_code=code, elapsed_ms=1, timed_out=timed_out)


def test_timeout():
    assert classify(CHECK, run(code=None, timed_out=True)).status == Status.TIMEOUT


def test_launch_failure_is_error():
    assert classify(CHECK, run(code=None)).status == Status.ERROR


def test_error_in_check_region_is_proof_failed():
    out = "/w/x.lean:12:3: error: decide failed"
    assert classify(CHECK, run(out, 1)).status == Status.PROOF_FAILED


def test_error_in_definitions_is_error():
    out = "/w/x.lean:3:1: error: unknown identifier\n/w/x.lean:12:3: error: x"
    assert classify(CHECK, run(out, 1)).status == Status.ERROR


def test_nonzero_exit_without_location_is_error():
    assert classify(CHECK, run("unknown module prefix", 1)).status == Status.ERROR


def test_success_returns_claim():
    out = "'t' depends on axioms: [propext]"
    assert classify(CHECK, run(out)).status == Status.VIOLATION


def test_missing_axiom_report_is_error():
    assert classify(CHECK, run("")).status == Status.ERROR


def test_unapproved_axiom_is_error():
    out = "'t' depends on axioms: [sorryAx]"
    assert classify(CHECK, run(out)).status == Status.ERROR
