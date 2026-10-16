"""Demo 1: Verified Coding — 送金検証サービス。"""

from __future__ import annotations

from src.verification.checks.coding import transfer_check
from src.verification.results import Status, VerificationResult
from src.verification.verifier import LeanVerifier

RULE_TEXT = "送金は 0 ≤ 送金額 ≤ 残高 のときだけ許可。許可された送金後の残高は非負かつ元の残高以下。"


def is_transfer_allowed(balance: int, amount: int) -> bool:
    """業務ルール（Python 側の判定）。Lean で独立に検証される。"""
    return 0 <= amount <= balance


def validate_transfer_input(balance: int, amount: int) -> list[str]:
    errors = [f"{name} は整数で指定してください" for name, v in
              (("balance", balance), ("amount", amount))
              if isinstance(v, bool) or not isinstance(v, int)]
    if not errors and balance < 0:
        errors.append("残高は 0 以上で指定してください")
    return errors


class CodingDemo:
    def __init__(self, verifier: LeanVerifier) -> None:
        self.verifier = verifier

    def verify_transfer(self, balance: int, amount: int) -> VerificationResult:
        errors = validate_transfer_input(balance, amount)
        if errors:
            return VerificationResult(Status.ERROR, "入力エラー: " + " / ".join(errors))
        allowed = is_transfer_allowed(balance, amount)
        details = {"balance": balance, "amount": amount, "allowed": allowed,
                   "new_balance": balance - amount if allowed else None}
        return self.verifier.verify(transfer_check(balance, amount, allowed), details)
