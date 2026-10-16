"""証明の抜け道を検出するガード。"""

from __future__ import annotations

import re

FORBIDDEN_TOKENS = (
    "sorry",
    "admit",
    "axiom",
    "native_decide",
    "unsafe",
    "implemented_by",
    "extern",
    "#eval",
    "run_cmd",
    "run_tac",
    "macro",
    "syntax",
    "elab",
    "set_option",
    "debug.skipKernelTC",
)

ALLOWED_AXIOMS = frozenset({"propext", "Classical.choice", "Quot.sound"})

_AXIOMS_RE = re.compile(r"'([^']+)' depends on axioms: \[([^\]]*)\]")
_NO_AXIOMS_RE = re.compile(r"'([^']+)' does not depend on any axioms")


def find_forbidden_tokens(source: str) -> list[str]:
    """ソース中の禁止トークンを返す（`#print axioms` 行は除外）。"""
    body = "\n".join(
        line for line in source.splitlines() if not line.startswith("#print axioms ")
    )
    return [t for t in FORBIDDEN_TOKENS if _contains_token(body, t)]


def _contains_token(text: str, token: str) -> bool:
    pattern = rf"(?<![\w.]){re.escape(token)}(?![\w])"
    return re.search(pattern, text) is not None


def parse_axioms(output: str) -> dict[str, set[str]]:
    """`#print axioms` の出力を {定理名: 公理集合} に変換する。"""
    result: dict[str, set[str]] = {}
    for name, axioms in _AXIOMS_RE.findall(output):
        result[name] = {a.strip() for a in axioms.split(",") if a.strip()}
    for name in _NO_AXIOMS_RE.findall(output):
        result[name] = set()
    return result


def unapproved_axioms(axioms_by_theorem: dict[str, set[str]]) -> dict[str, set[str]]:
    bad = {n: ax - ALLOWED_AXIOMS for n, ax in axioms_by_theorem.items()}
    return {n: ax for n, ax in bad.items() if ax}
