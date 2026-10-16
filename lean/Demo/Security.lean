/-!
# Demo 2: Security Policy Verifier — RBAC

ロール `Admin / Editor / Viewer` とアクション `Read / Write / Delete`。
ポリシーは 9 組の許可フラグで表し、禁止ルールを満たすかを検証する。

禁止ルール:
* Viewer は Write / Delete できない
* Editor は Delete できない
* Delete できるなら Admin である
-/

namespace Demo.Security

inductive Role where
  | admin | editor | viewer
  deriving DecidableEq, Repr

inductive Action where
  | read | write | delete
  deriving DecidableEq, Repr

/-- 権限マトリクス。 -/
structure Policy where
  allow : Role → Action → Bool

def allRoles : List Role := [.admin, .editor, .viewer]
def allActions : List Action := [.read, .write, .delete]

theorem mem_allRoles (r : Role) : r ∈ allRoles := by cases r <;> simp [allRoles]
theorem mem_allActions (a : Action) : a ∈ allActions := by cases a <;> simp [allActions]

/-! ## 仕様（Prop） -/

def ViewerReadOnly (p : Policy) : Prop :=
  p.allow .viewer .write = false ∧ p.allow .viewer .delete = false

def EditorNoDelete (p : Policy) : Prop :=
  p.allow .editor .delete = false

def DeleteImpliesAdmin (p : Policy) : Prop :=
  ∀ r : Role, p.allow r .delete = true → r = .admin

/-- セキュアなポリシー。 -/
def Secure (p : Policy) : Prop :=
  ViewerReadOnly p ∧ EditorNoDelete p ∧ DeleteImpliesAdmin p

/-! ## 違反の列挙（決定手続き） -/

/-- 禁止されている (role, action) の組。 -/
def forbidden : Role → Action → Bool
  | .viewer, .write => true
  | .viewer, .delete => true
  | .editor, .delete => true
  | _, _ => false

/-- 許可されているが禁止されている組の一覧（ロール→アクション順）。 -/
def violations (p : Policy) : List (Role × Action) :=
  allRoles.flatMap fun r =>
    (allActions.filter fun a => forbidden r a && p.allow r a).map fun a => (r, a)

/-- 決定手続き: 違反がないこと。 -/
def checkSecure (p : Policy) : Bool := violations p == []

theorem violations_eq_nil_iff (p : Policy) :
    violations p = [] ↔ ∀ r a, forbidden r a = true → p.allow r a = false := by
  constructor
  · intro h r a hf
    cases hp : p.allow r a
    · rfl
    · exfalso
      have hmem : (r, a) ∈ violations p := by
        simp only [violations, List.mem_flatMap, List.mem_map, List.mem_filter]
        exact ⟨r, mem_allRoles r, a, ⟨mem_allActions a, by simp [hf, hp]⟩, rfl⟩
      rw [h] at hmem
      simp at hmem
  · intro h
    apply List.eq_nil_iff_forall_not_mem.mpr
    intro ⟨r, a⟩ hmem
    simp only [violations, List.mem_flatMap, List.mem_map, List.mem_filter] at hmem
    obtain ⟨r', _, a', ⟨_, hfa⟩, heq⟩ := hmem
    cases heq
    have hf : forbidden r a = true := by simp_all
    have hp : p.allow r a = true := by simp_all
    simp [h r a hf] at hp

theorem secure_iff_forbidden (p : Policy) :
    Secure p ↔ ∀ r a, forbidden r a = true → p.allow r a = false := by
  constructor
  · intro ⟨⟨hvw, hvd⟩, hed, hdel⟩ r a hf
    unfold EditorNoDelete at hed
    cases r <;> cases a <;> simp_all [forbidden]
  · intro h
    refine ⟨⟨h .viewer .write rfl, h .viewer .delete rfl⟩, h .editor .delete rfl, ?_⟩
    intro r hr
    cases r
    · rfl
    · simp [h .editor .delete rfl] at hr
    · simp [h .viewer .delete rfl] at hr

/-- 健全性: 決定手続きが真ならポリシーはセキュア。 -/
theorem checkSecure_sound (p : Policy) (h : checkSecure p = true) : Secure p := by
  rw [secure_iff_forbidden, ← violations_eq_nil_iff]
  simpa [checkSecure] using h

/-- 完全性: セキュアなら決定手続きは真。 -/
theorem checkSecure_complete (p : Policy) (h : Secure p) : checkSecure p = true := by
  rw [secure_iff_forbidden, ← violations_eq_nil_iff] at h
  simp [checkSecure, h]

/-- 違反が 1 件でもあればポリシーはセキュアでない。 -/
theorem not_secure_of_violations (p : Policy) (h : violations p ≠ []) : ¬ Secure p := by
  intro hs
  have := checkSecure_complete p hs
  simp [checkSecure] at this
  exact h this

end Demo.Security
