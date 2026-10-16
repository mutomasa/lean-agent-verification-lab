/-!
# Demo 3: Verified Optimization — 人員配置の制約充足

OR-Tools CP-SAT で求めた具体的な割当 `hours[employee][project]` が
全制約を満たすことを検証する。最適性は証明しない（制約充足のみ）。

制約:
* 各社員の稼働時間合計 ≤ 稼働上限
* 各案件の配賦時間合計 ≥ 必要時間
* スキル不適合の組には時間を割り当てない
* 非負整数（`Nat` の型で保証）
-/

namespace Demo.Optimization

/-- 配置問題と具体的な解。行は社員、列は案件。 -/
structure Staffing where
  capacity : List Nat
  demand : List Nat
  rate : List Nat
  skilled : List (List Bool)
  hours : List (List Nat)

namespace Staffing

def numEmployees (s : Staffing) : Nat := s.capacity.length
def numProjects (s : Staffing) : Nat := s.demand.length

/-- 社員 `i` が案件 `j` に割り当てられた時間。 -/
def h (s : Staffing) (i j : Nat) : Nat := (s.hours.getD i []).getD j 0

/-- 社員 `i` が案件 `j` のスキルを持つか。 -/
def sk (s : Staffing) (i j : Nat) : Bool := (s.skilled.getD i []).getD j false

/-- 社員 `i` の稼働時間合計。 -/
def assigned (s : Staffing) (i : Nat) : Nat :=
  ((List.range s.numProjects).map (s.h i)).sum

/-- 案件 `j` に配賦された時間合計。 -/
def covered (s : Staffing) (j : Nat) : Nat :=
  ((List.range s.numEmployees).map (fun i => s.h i j)).sum

/-- 総コスト = Σ 社員単価 × 稼働時間。 -/
def totalCost (s : Staffing) : Nat :=
  ((List.range s.numEmployees).map (fun i => s.rate.getD i 0 * s.assigned i)).sum

/-! ## 制約（Prop） -/

/-- 入力の次元が揃っている。 -/
def WellFormed (s : Staffing) : Prop :=
  s.rate.length = s.numEmployees ∧
  s.hours.length = s.numEmployees ∧
  s.skilled.length = s.numEmployees ∧
  (∀ row ∈ s.hours, row.length = s.numProjects) ∧
  (∀ row ∈ s.skilled, row.length = s.numProjects)

def CapacityOK (s : Staffing) : Prop :=
  ∀ i, i < s.numEmployees → s.assigned i ≤ s.capacity.getD i 0

def DemandOK (s : Staffing) : Prop :=
  ∀ j, j < s.numProjects → s.demand.getD j 0 ≤ s.covered j

def SkillOK (s : Staffing) : Prop :=
  ∀ i, i < s.numEmployees → ∀ j, j < s.numProjects → 0 < s.h i j → s.sk i j = true

/-- 解が全制約を満たす。 -/
def Feasible (s : Staffing) : Prop :=
  WellFormed s ∧ CapacityOK s ∧ DemandOK s ∧ SkillOK s

instance (s : Staffing) : Decidable (WellFormed s) := by unfold WellFormed; infer_instance
instance (s : Staffing) : Decidable (CapacityOK s) := by unfold CapacityOK; infer_instance
instance (s : Staffing) : Decidable (DemandOK s) := by unfold DemandOK; infer_instance
instance (s : Staffing) : Decidable (SkillOK s) := by unfold SkillOK; infer_instance
instance (s : Staffing) : Decidable (Feasible s) := by unfold Feasible; infer_instance

/-! ## 補題 -/

theorem capacity_of_feasible {s : Staffing} (hf : Feasible s) {i : Nat}
    (hi : i < s.numEmployees) : s.assigned i ≤ s.capacity.getD i 0 :=
  hf.2.1 i hi

theorem demand_of_feasible {s : Staffing} (hf : Feasible s) {j : Nat}
    (hj : j < s.numProjects) : s.demand.getD j 0 ≤ s.covered j :=
  hf.2.2.1 j hj

theorem skill_of_feasible {s : Staffing} (hf : Feasible s) {i j : Nat}
    (hi : i < s.numEmployees) (hj : j < s.numProjects) (hpos : 0 < s.h i j) :
    s.sk i j = true :=
  hf.2.2.2 i hi j hj hpos

end Staffing
end Demo.Optimization
