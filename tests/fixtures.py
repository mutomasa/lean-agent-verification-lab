"""固定ケース（正常・違反）。"""

from src.verification.checks.optimization import StaffingData

ROLES = ("admin", "editor", "viewer")
ACTIONS = ("read", "write", "delete")

DEFAULT_POLICY = {
    ("admin", "read"): True, ("admin", "write"): True, ("admin", "delete"): True,
    ("editor", "read"): True, ("editor", "write"): True, ("editor", "delete"): False,
    ("viewer", "read"): True, ("viewer", "write"): False, ("viewer", "delete"): False,
}

LEAKY_POLICY = {**DEFAULT_POLICY, ("viewer", "write"): True, ("editor", "delete"): True}
LEAKY_VIOLATIONS = [("editor", "delete"), ("viewer", "write")]

FEASIBLE = StaffingData(
    capacity=[40, 40, 40, 40, 40],
    demand=[60, 50, 70],
    rate=[50, 45, 60, 40, 55],
    skilled=[[True, True, False], [True, False, True], [False, True, True],
             [True, True, True], [True, False, True]],
    hours=[[20, 20, 0], [30, 0, 10], [0, 30, 10], [10, 0, 30], [0, 0, 20]],
)
FEASIBLE_COST = 50 * 40 + 45 * 40 + 60 * 40 + 40 * 40 + 55 * 20
