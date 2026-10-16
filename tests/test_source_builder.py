import pytest

from src.verification.checks.security import rbac_check
from src.verification.results import Status
from src.verification.source_builder import SourceAssembler, lean_bool, lean_int, lean_nat


def test_lean_int_formats_negative():
    assert lean_int(-5) == "(-5)"
    assert lean_int(7) == "7"


@pytest.mark.parametrize("bad", ["1; #eval 1", 1.5, True, None])
def test_lean_int_rejects_non_int(bad):
    with pytest.raises(TypeError):
        lean_int(bad)


def test_lean_nat_rejects_negative():
    with pytest.raises(ValueError):
        lean_nat(-1)


def test_lean_bool_rejects_non_bool():
    with pytest.raises(TypeError):
        lean_bool("true")


def test_check_first_line_points_after_definitions():
    asm = SourceAssembler(imports=["Demo"])
    asm.define("def a := 1")
    asm.prove("t", "a = 1", "rfl")
    check = asm.build(Status.PASS)
    lines = check.source.splitlines()
    assert lines[check.check_first_line - 1].startswith("theorem t")
    assert "#print axioms t" in check.source


def test_rbac_rejects_unknown_role():
    policy = {(r, a): False for r in ("admin", "editor", "viewer")
              for a in ("read", "write", "delete")}
    with pytest.raises(ValueError):
        rbac_check(policy, [("root", "read")])
