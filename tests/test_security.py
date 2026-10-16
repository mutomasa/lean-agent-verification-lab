import pytest

from src.demos.security import SecurityDemo, default_policy, find_violations, validate_policy
from src.verification.results import Status


def test_default_policy_has_no_violations():
    assert find_violations(default_policy()) == []


def test_find_violations_in_lean_order():
    policy = {**default_policy(), ("viewer", "delete"): True, ("editor", "delete"): True}
    assert find_violations(policy) == [("editor", "delete"), ("viewer", "delete")]


def test_validate_policy():
    policy = default_policy()
    del policy[("admin", "read")]
    assert validate_policy(policy)
    assert validate_policy({**default_policy(), ("root", "read"): True})
    assert validate_policy({**default_policy(), ("admin", "read"): 1})


@pytest.mark.lean
class TestSecurityDemo:
    def test_default_passes(self, verifier):
        assert SecurityDemo(verifier).verify_rbac(default_policy()).status == Status.PASS

    def test_edited_policy_is_reflected_in_lean(self, verifier):
        policy = {**default_policy(), ("viewer", "write"): True}
        r = SecurityDemo(verifier).verify_rbac(policy)
        assert r.status == Status.VIOLATION
        assert r.details["violations"] == [("viewer", "write")]
        assert "| .viewer, .write => true" in r.lean_source

    def test_revoking_admin_read_is_still_secure(self, verifier):
        policy = {**default_policy(), ("admin", "read"): False}
        r = SecurityDemo(verifier).verify_rbac(policy)
        assert r.status == Status.PASS
        assert "| .admin, .read => false" in r.lean_source
