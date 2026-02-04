/-
  Extracted Lean 4 code from field_u256.rs

  This is an EXAMPLE of what Hax extraction produces.
  Actual extraction may vary based on Hax version.
-/

namespace FieldU256

/-- A 256-bit unsigned integer represented as 4 × 64-bit limbs (little-endian) -/
structure U256 where
  limbs : Array UInt64 4
  deriving Repr, DecidableEq

namespace U256

/-- Zero constant -/
def zero : U256 := ⟨#[0, 0, 0, 0]⟩

/-- One constant -/
def one : U256 := ⟨#[1, 0, 0, 0]⟩

/-- Create from a single u64 -/
def fromU64 (value : UInt64) : U256 := ⟨#[value, 0, 0, 0]⟩

/-- Check if zero -/
def isZero (self : U256) : Bool :=
  self.limbs[0]! == 0 && self.limbs[1]! == 0 &&
  self.limbs[2]! == 0 && self.limbs[3]! == 0

end U256

-- ============================================================================
-- Addition with carry chain
-- ============================================================================

/-- Add two u64 values with carry in, returning (sum, carry_out) -/
def adc (a b carry : UInt64) : UInt64 × UInt64 :=
  let sum := a + b + carry
  let carryOut := if sum < a || (sum == a && (b != 0 || carry != 0)) then 1 else 0
  (sum, carryOut)

/-- Add two U256 values, returning (result, carry) -/
def addWithCarry (a b : U256) : U256 × UInt64 :=
  let (s0, c0) := adc a.limbs[0]! b.limbs[0]! 0
  let (s1, c1) := adc a.limbs[1]! b.limbs[1]! c0
  let (s2, c2) := adc a.limbs[2]! b.limbs[2]! c1
  let (s3, c3) := adc a.limbs[3]! b.limbs[3]! c2
  (⟨#[s0, s1, s2, s3]⟩, c3)

/-- Wrapping addition (ignores overflow) -/
def add (a b : U256) : U256 :=
  (addWithCarry a b).1

-- ============================================================================
-- Subtraction with borrow chain
-- ============================================================================

/-- Subtract b from a with borrow in, returning (difference, borrow_out) -/
def sbb (a b borrow : UInt64) : UInt64 × UInt64 :=
  let diff := a - b - borrow
  let borrowOut := if a < b || (a == b && borrow != 0) then 1 else 0
  (diff, borrowOut)

/-- Subtract b from a, returning (result, borrow) -/
def subWithBorrow (a b : U256) : U256 × UInt64 :=
  let (d0, b0) := sbb a.limbs[0]! b.limbs[0]! 0
  let (d1, b1) := sbb a.limbs[1]! b.limbs[1]! b0
  let (d2, b2) := sbb a.limbs[2]! b.limbs[2]! b1
  let (d3, b3) := sbb a.limbs[3]! b.limbs[3]! b2
  (⟨#[d0, d1, d2, d3]⟩, b3)

/-- Wrapping subtraction -/
def sub (a b : U256) : U256 :=
  (subWithBorrow a b).1

-- ============================================================================
-- Comparison
-- ============================================================================

/-- Compare two U256 values: returns .lt, .eq, or .gt -/
def cmp (a b : U256) : Ordering :=
  -- Compare from most significant limb
  if a.limbs[3]! < b.limbs[3]! then .lt
  else if a.limbs[3]! > b.limbs[3]! then .gt
  else if a.limbs[2]! < b.limbs[2]! then .lt
  else if a.limbs[2]! > b.limbs[2]! then .gt
  else if a.limbs[1]! < b.limbs[1]! then .lt
  else if a.limbs[1]! > b.limbs[1]! then .gt
  else if a.limbs[0]! < b.limbs[0]! then .lt
  else if a.limbs[0]! > b.limbs[0]! then .gt
  else .eq

/-- a >= b -/
def gte (a b : U256) : Bool := cmp a b != .lt

/-- a < b -/
def lt (a b : U256) : Bool := cmp a b == .lt

-- ============================================================================
-- Bitwise operations
-- ============================================================================

/-- Bitwise XOR -/
def xor (a b : U256) : U256 :=
  ⟨#[a.limbs[0]! ^^^ b.limbs[0]!,
     a.limbs[1]! ^^^ b.limbs[1]!,
     a.limbs[2]! ^^^ b.limbs[2]!,
     a.limbs[3]! ^^^ b.limbs[3]!]⟩

/-- Bitwise AND -/
def and (a b : U256) : U256 :=
  ⟨#[a.limbs[0]! &&& b.limbs[0]!,
     a.limbs[1]! &&& b.limbs[1]!,
     a.limbs[2]! &&& b.limbs[2]!,
     a.limbs[3]! &&& b.limbs[3]!]⟩

/-- Bitwise OR -/
def or (a b : U256) : U256 :=
  ⟨#[a.limbs[0]! ||| b.limbs[0]!,
     a.limbs[1]! ||| b.limbs[1]!,
     a.limbs[2]! ||| b.limbs[2]!,
     a.limbs[3]! ||| b.limbs[3]!]⟩

-- ============================================================================
-- Modular arithmetic
-- ============================================================================

/-- Example modulus: p = 2^255 - 19 (Curve25519 field) -/
def modulus : U256 := ⟨#[
  0xFFFFFFFFFFFFFFED,  -- 2^64 - 19
  0xFFFFFFFFFFFFFFFF,
  0xFFFFFFFFFFFFFFFF,
  0x7FFFFFFFFFFFFFFF   -- 2^63 - 1
]⟩

/-- Modular addition: (a + b) mod p -/
def modAdd (a b p : U256) : U256 :=
  let (sum, carry) := addWithCarry a b
  if carry != 0 || gte sum p then
    (subWithBorrow sum p).1
  else
    sum

/-- Modular subtraction: (a - b) mod p -/
def modSub (a b p : U256) : U256 :=
  let (diff, borrow) := subWithBorrow a b
  if borrow != 0 then
    (addWithCarry diff p).1
  else
    diff

-- ============================================================================
-- Constant-time operations
-- ============================================================================

/-- Constant-time conditional select: returns a if choice == 0, b if choice == 1 -/
def ctSelect (a b : U256) (choice : UInt64) : U256 :=
  -- Requires: choice ∈ {0, 1}
  let mask := 0 - choice  -- 0 or 0xFFFF...
  ⟨#[a.limbs[0]! ^^^ (mask &&& (a.limbs[0]! ^^^ b.limbs[0]!)),
     a.limbs[1]! ^^^ (mask &&& (a.limbs[1]! ^^^ b.limbs[1]!)),
     a.limbs[2]! ^^^ (mask &&& (a.limbs[2]! ^^^ b.limbs[2]!)),
     a.limbs[3]! ^^^ (mask &&& (a.limbs[3]! ^^^ b.limbs[3]!))]⟩

/-- Constant-time equality comparison -/
def ctEq (a b : U256) : Bool :=
  let acc := (a.limbs[0]! ^^^ b.limbs[0]!) |||
             (a.limbs[1]! ^^^ b.limbs[1]!) |||
             (a.limbs[2]! ^^^ b.limbs[2]!) |||
             (a.limbs[3]! ^^^ b.limbs[3]!)
  acc == 0

-- ============================================================================
-- Proofs (manually added after extraction)
-- ============================================================================

namespace Proofs

/-- Addition is commutative -/
theorem add_comm (a b : U256) : add a b = add b a := by
  sorry  -- Proof obligation: show limb-wise addition commutes

/-- Modular addition stays in bounds -/
theorem modAdd_bounds (a b p : U256) (ha : lt a p) (hb : lt b p) :
    lt (modAdd a b p) p := by
  sorry  -- Proof obligation: show result < p

/-- Constant-time select returns correct value -/
theorem ctSelect_zero (a b : U256) : ctSelect a b 0 = a := by
  sorry  -- Proof: when mask = 0, XOR produces a

theorem ctSelect_one (a b : U256) : ctSelect a b 1 = b := by
  sorry  -- Proof: when mask = all 1s, XOR produces b

/-- Constant-time equality is reflexive -/
theorem ctEq_refl (a : U256) : ctEq a a = true := by
  simp [ctEq]
  -- All XORs produce 0, OR of zeros is 0, 0 == 0 is true

end Proofs

end FieldU256
