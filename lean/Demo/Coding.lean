/-!
# Demo 1: Verified Coding — 送金仕様

残高 `balance` と送金額 `amount` を整数でモデル化する。
送金は `0 ≤ amount ≤ balance` のときだけ許可され、
許可された送金の後の残高は非負かつ元の残高以下であることを証明する。

注意: ここで保証するのは Lean 上のモデルについての性質であり、
Python 等で書かれた実際の送金プログラムの正しさではない。
-/

namespace Demo.Coding

/-- 送金前提: 残高は非負。 -/
def ValidBalance (balance : Int) : Prop := 0 ≤ balance

/-- 送金許可の条件。 -/
def TransferAllowed (balance amount : Int) : Prop :=
  0 ≤ amount ∧ amount ≤ balance

instance (balance amount : Int) : Decidable (TransferAllowed balance amount) :=
  inferInstanceAs (Decidable (_ ∧ _))

instance (balance : Int) : Decidable (ValidBalance balance) :=
  inferInstanceAs (Decidable (_ ≤ _))

/-- 送金処理。許可されない場合は `none`。 -/
def transfer (balance amount : Int) : Option Int :=
  if TransferAllowed balance amount then some (balance - amount) else none

/-- 許可されていれば送金は成功し、残高は `balance - amount` になる。 -/
theorem transfer_of_allowed {balance amount : Int}
    (h : TransferAllowed balance amount) :
    transfer balance amount = some (balance - amount) := by
  simp [transfer, h]

/-- 許可されていなければ送金は拒否される。 -/
theorem transfer_of_not_allowed {balance amount : Int}
    (h : ¬ TransferAllowed balance amount) :
    transfer balance amount = none := by
  simp [transfer, h]

/-- 送金後の残高は非負。 -/
theorem new_balance_nonneg {balance amount : Int}
    (h : TransferAllowed balance amount) : 0 ≤ balance - amount := by
  unfold TransferAllowed at h; omega

/-- 送金後の残高は元の残高以下。 -/
theorem new_balance_le {balance amount : Int}
    (h : TransferAllowed balance amount) : balance - amount ≤ balance := by
  unfold TransferAllowed at h; omega

/-- `transfer` が返す残高は常に非負かつ元の残高以下（実装レベルの安全性）。 -/
theorem transfer_safe {balance amount r : Int}
    (h : transfer balance amount = some r) : 0 ≤ r ∧ r ≤ balance := by
  unfold transfer at h
  split at h
  · rename_i ha
    cases h
    exact ⟨new_balance_nonneg ha, new_balance_le ha⟩
  · cases h

/-- 安全な送金: 許可され、送金後残高が非負かつ元残高以下。 -/
def SafeTransfer (balance amount : Int) : Prop :=
  TransferAllowed balance amount ∧ 0 ≤ balance - amount ∧ balance - amount ≤ balance

theorem safe_of_allowed {balance amount : Int}
    (h : TransferAllowed balance amount) : SafeTransfer balance amount :=
  ⟨h, new_balance_nonneg h, new_balance_le h⟩

end Demo.Coding
