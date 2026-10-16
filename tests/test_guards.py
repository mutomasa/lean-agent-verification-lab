import pytest

from src.verification.guards import find_forbidden_tokens, parse_axioms, unapproved_axioms


@pytest.mark.parametrize("src", [
    "theorem x : 1 = 2 := sorry",
    "theorem x : 1 = 2 := by admit",
    "axiom bad : False",
    "theorem x : 2 = 2 := by native_decide",
    "set_option debug.skipKernelTC true",
    "#eval IO.println 1",
])
def test_detects_forbidden(src):
    assert find_forbidden_tokens(src)


def test_allows_clean_source_and_print_axioms():
    src = "theorem x : 1 + 1 = 2 := by decide +kernel\n#print axioms x\n"
    assert find_forbidden_tokens(src) == []


def test_identifiers_containing_token_are_not_flagged():
    assert find_forbidden_tokens("def sorryCount := 1\ndef my_axiomatic := 2") == []


def test_parse_axioms():
    out = ("'a' depends on axioms: [propext, Classical.choice]\n"
           "'b' does not depend on any axioms\n"
           "'c' depends on axioms: [sorryAx]\n")
    ax = parse_axioms(out)
    assert ax == {"a": {"propext", "Classical.choice"}, "b": set(), "c": {"sorryAx"}}
    assert unapproved_axioms(ax) == {"c": {"sorryAx"}}
