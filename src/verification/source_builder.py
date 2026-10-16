"""承認済みテンプレートと型付きデータから Lean ソースを組み立てる共通部品。

LLM の文字列をそのまま Lean コードに埋め込まないこと。ここに渡す値は
`lean_int` / `lean_nat` / `lean_bool` などで型変換したものに限る。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.verification.results import Status


@dataclass(frozen=True)
class LeanCheck:
    """生成した Lean ソースと、証明できた場合に意味する判定。

    `check_first_line` 以降が証明ブロック。ここでのエラーは PROOF_FAILED、
    それより前（定義部）のエラーは ERROR に分類する。
    """

    source: str
    claim: Status
    theorem_names: tuple[str, ...]
    check_first_line: int


def lean_int(value: int) -> str:
    v = _require_int(value)
    return f"({v})" if v < 0 else str(v)


def lean_nat(value: int) -> str:
    v = _require_int(value)
    if v < 0:
        raise ValueError(f"Nat には負の値を指定できません: {v}")
    return str(v)


def lean_bool(value: bool) -> str:
    if not isinstance(value, bool):
        raise TypeError(f"bool が必要です: {value!r}")
    return "true" if value else "false"


def lean_nat_list(values: list[int]) -> str:
    return "[" + ", ".join(lean_nat(v) for v in values) + "]"


def lean_bool_list(values: list[bool]) -> str:
    return "[" + ", ".join(lean_bool(v) for v in values) + "]"


def _require_int(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"int が必要です: {value!r}")
    return value


@dataclass
class SourceAssembler:
    """定義部と証明部を分けて Lean ソースを組み立てる。"""

    imports: list[str]
    opens: list[str] = field(default_factory=list)
    definitions: list[str] = field(default_factory=list)
    theorems: list[tuple[str, str]] = field(default_factory=list)

    def define(self, code: str) -> None:
        self.definitions.append(code)

    def prove(self, name: str, statement: str, proof: str) -> None:
        self.theorems.append((name, f"theorem {name} : {statement} :=\n  {proof}"))

    def build(self, claim: Status) -> LeanCheck:
        header = self._header()
        check_first_line = header.count("\n") + 1
        body = "\n\n".join(code for _, code in self.theorems)
        footer = "\n".join(f"#print axioms {name}" for name, _ in self.theorems)
        return LeanCheck(
            source=f"{header}{body}\n\n{footer}\n",
            claim=claim,
            theorem_names=tuple(name for name, _ in self.theorems),
            check_first_line=check_first_line,
        )

    def _header(self) -> str:
        lines = [f"import {m}" for m in self.imports]
        if self.opens:
            lines.append("open " + " ".join(self.opens))
        parts = ["\n".join(lines), *self.definitions, "-- BEGIN CHECKS"]
        return "\n\n".join(parts) + "\n"
