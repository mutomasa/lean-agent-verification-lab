"""Demo 1: 送金検証の Lean チェック生成。"""

from __future__ import annotations

from src.verification.results import Status
from src.verification.source_builder import LeanCheck, SourceAssembler, lean_int

DECIDE = "by decide +kernel"


def transfer_check(balance: int, amount: int, allowed: bool) -> LeanCheck:
    """Python 側の判定 `allowed` を Lean で独立に証明するチェックを作る。"""
    asm = SourceAssembler(imports=["Demo.Coding"], opens=["Demo.Coding"])
    b, a = lean_int(balance), lean_int(amount)
    asm.prove("check_valid_balance", f"ValidBalance {b}", DECIDE)
    if allowed:
        asm.prove("check_safe", f"SafeTransfer {b} {a}", f"safe_of_allowed ({DECIDE})")
        asm.prove("check_result", f"transfer {b} {a} = some ({b} - {a})",
                  f"transfer_of_allowed ({DECIDE})")
        return asm.build(Status.PASS)
    asm.prove("check_not_allowed", f"¬ TransferAllowed {b} {a}", DECIDE)
    asm.prove("check_rejected", f"transfer {b} {a} = none",
              f"transfer_of_not_allowed ({DECIDE})")
    return asm.build(Status.VIOLATION)
