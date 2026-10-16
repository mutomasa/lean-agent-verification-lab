"""Lean チェックの固定ケース（正常・違反・証明失敗）。"""

import dataclasses

import pytest

from src.verification.checks.coding import transfer_check
from src.verification.checks.optimization import ConstraintViolation, staffing_check
from src.verification.checks.security import rbac_check
from src.verification.results import Status
from tests.fixtures import (
    DEFAULT_POLICY,
    FEASIBLE,
    FEASIBLE_COST,
    LEAKY_POLICY,
    LEAKY_VIOLATIONS,
)

pytestmark = pytest.mark.lean


class TestTransfer:
    def test_pass(self, verifier):
        assert verifier.verify(transfer_check(100, 80, allowed=True)).status == Status.PASS

    def test_violation(self, verifier):
        assert verifier.verify(transfer_check(100, 120, allowed=False)).status == Status.VIOLATION

    def test_negative_amount_is_violation(self, verifier):
        assert verifier.verify(transfer_check(100, -5, allowed=False)).status == Status.VIOLATION

    def test_wrong_claim_is_proof_failed_not_violation(self, verifier):
        assert verifier.verify(transfer_check(100, 120, allowed=True)).status == Status.PROOF_FAILED

    def test_negative_balance_is_proof_failed(self, verifier):
        assert verifier.verify(transfer_check(-1, 0, allowed=True)).status == Status.PROOF_FAILED


class TestRbac:
    def test_default_policy_passes(self, verifier):
        assert verifier.verify(rbac_check(DEFAULT_POLICY, [])).status == Status.PASS

    def test_leaky_policy_violation(self, verifier):
        assert verifier.verify(rbac_check(LEAKY_POLICY, LEAKY_VIOLATIONS)).status == Status.VIOLATION

    def test_incomplete_violation_list_is_proof_failed(self, verifier):
        check = rbac_check(LEAKY_POLICY, LEAKY_VIOLATIONS[:1])
        assert verifier.verify(check).status == Status.PROOF_FAILED

    def test_claiming_secure_for_leaky_policy_fails(self, verifier):
        assert verifier.verify(rbac_check(LEAKY_POLICY, [])).status == Status.PROOF_FAILED


class TestStaffing:
    def test_feasible_passes(self, verifier):
        assert verifier.verify(staffing_check(FEASIBLE, FEASIBLE_COST, [])).status == Status.PASS

    def test_wrong_cost_is_proof_failed(self, verifier):
        check = staffing_check(FEASIBLE, FEASIBLE_COST + 1, [])
        assert verifier.verify(check).status == Status.PROOF_FAILED

    def test_capacity_violation(self, verifier):
        data = dataclasses.replace(FEASIBLE, capacity=[30, 40, 40, 40, 40])
        check = staffing_check(data, FEASIBLE_COST, [ConstraintViolation("capacity", employee=0)])
        assert verifier.verify(check).status == Status.VIOLATION

    def test_skill_violation(self, verifier):
        skilled = [row[:] for row in FEASIBLE.skilled]
        skilled[0][0] = False
        data = dataclasses.replace(FEASIBLE, skilled=skilled)
        check = staffing_check(data, FEASIBLE_COST, [ConstraintViolation("skill", 0, 0)])
        assert verifier.verify(check).status == Status.VIOLATION

    def test_demand_violation(self, verifier):
        data = dataclasses.replace(FEASIBLE, demand=[61, 50, 70])
        check = staffing_check(data, FEASIBLE_COST, [ConstraintViolation("demand", project=0)])
        assert verifier.verify(check).status == Status.VIOLATION

    def test_shape_violation(self, verifier):
        data = dataclasses.replace(FEASIBLE, rate=[50, 45])
        check = staffing_check(data, FEASIBLE_COST, [ConstraintViolation("shape")])
        assert verifier.verify(check).status == Status.VIOLATION

    def test_wrong_violation_claim_is_proof_failed(self, verifier):
        check = staffing_check(FEASIBLE, FEASIBLE_COST, [ConstraintViolation("capacity", employee=0)])
        assert verifier.verify(check).status == Status.PROOF_FAILED
