"""検証結果の型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Status(str, Enum):
    PASS = "PASS"
    VIOLATION = "VIOLATION"
    PROOF_FAILED = "PROOF_FAILED"
    ERROR = "ERROR"
    TIMEOUT = "TIMEOUT"
    INFEASIBLE = "INFEASIBLE"


@dataclass
class VerificationResult:
    status: Status
    summary: str
    lean_stdout: str = ""
    lean_stderr: str = ""
    elapsed_ms: int = 0
    lean_source: str = ""
    exit_code: int | None = None
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def lean_confirmed(self) -> bool:
        """Lean が主張（PASS または VIOLATION）を証明できたか。"""
        return self.status in (Status.PASS, Status.VIOLATION)
