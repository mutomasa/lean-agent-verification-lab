import pytest

from src.demos.coding import CodingDemo, is_transfer_allowed, validate_transfer_input
from src.verification.results import Status


@pytest.mark.parametrize("balance,amount,expected", [
    (100, 80, True), (100, 100, True), (100, 0, True),
    (100, 120, False), (100, -1, False), (0, 1, False),
])
def test_is_transfer_allowed(balance, amount, expected):
    assert is_transfer_allowed(balance, amount) is expected


def test_validate_rejects_negative_balance_and_non_int():
    assert validate_transfer_input(-1, 0)
    assert validate_transfer_input(10, "5")
    assert validate_transfer_input(10, 5) == []


@pytest.mark.lean
class TestCodingDemo:
    def test_pass(self, verifier):
        r = CodingDemo(verifier).verify_transfer(100, 80)
        assert r.status == Status.PASS and r.details["new_balance"] == 20

    def test_violation(self, verifier):
        r = CodingDemo(verifier).verify_transfer(100, 120)
        assert r.status == Status.VIOLATION and r.details["allowed"] is False

    def test_input_error_does_not_run_lean(self, verifier):
        r = CodingDemo(verifier).verify_transfer(-5, 1)
        assert r.status == Status.ERROR and r.lean_source == ""

    def test_input_change_changes_lean_target(self, verifier):
        demo = CodingDemo(verifier)
        a, b = demo.verify_transfer(100, 80), demo.verify_transfer(250, 80)
        assert "SafeTransfer 100 80" in a.lean_source
        assert "SafeTransfer 250 80" in b.lean_source
