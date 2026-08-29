# Panic-Freedom Proofs over hax-lib's `RustM` (the `legacy-lean` backend)

The `legacy-lean` backend extracts Rust to monadic `RustM` computations from
hax-lib's Lean library; the `lean` backend (Aeneas pipeline) produces pure
functions whose obligations are covered by the hax manual's
[panic-freedom tutorial](https://hax.cryspen.com/manual/lean/tutorial/panic-freedom/).
For `RustM` code, panic freedom is
stated as a Hoare triple `⦃ ⌜ P ⌝ ⦄ f ⦃ ⇓ r => ⌜ Q r ⌝ ⦄` or as a `Spec` structure
with `pureRequires`, `pureEnsures`, and `contract` fields. This document describes
the decision procedures that close those goals and when each applies.

## The Tactic Cascade

Apply the steps in order and stop as soon as the goal closes.

```
mvcgen [fn_name, ...]       -- decompose Hoare triple into VCs
  <;> first
    | omega                  -- linear Nat/Int arithmetic (array bounds, loop indices)
    | grind                  -- congruence closure + LIA + ring (logical structure)
    | simp_all; omega        -- simplify then retry arithmetic
    | hax_bv_decide          -- SAT-based bitvector decision (loop-free functions)
```

## `hax_bv_decide` — Bitvector SAT Solving

Defined in hax-lib's Lean library, `Tactic/HaxBVDecide.lean`. It runs
`simp only [hax_bv_decide] at *; bv_decide`: `RustM` computations are normalized
into `BVRustM` (a BitVec-encoded monad) and then bitblasted to SAT. The result is
kernel-checked and needs no external solver.

Applies to loop-free functions with bounded integer arithmetic, which is the shape
of Rust checked operations (`+?`, `-?`, `*?`, `<<<?`, `>>>?`, `&&&?`, `^^^?`).

```lean
set_option maxHeartbeats 800000 in
theorem my_spec (x : u32) (n : u8) (hn : n = 4 ∨ n = 10) :
    ⦃ ⌜ True ⌝ ⦄ my_fn x n ⦃ ⇓ _ => ⌜ True ⌝ ⦄ := by
  -- Case-split on the finite precondition, then bitblast each case
  rcases hn with rfl | rfl <;>
  (unfold my_fn helper_fn; hax_bv_decide (timeout := 120))
```

Requirements:

1. The function is loop-free (no `fold_range`, no recursion).
2. After case-splitting and unfolding, all values reduce to concrete `BitVec` terms.
3. All operations lie in `bv_decide`'s vocabulary.

Limitation: cross-type shifts. `bv_decide` handles
`HShiftLeft (BitVec w) (BitVec w) (BitVec w)` (same width), but a Rust checked shift
such as `u64 <<<? u8` produces `HShiftLeft (BitVec 64) Nat (BitVec 64)` once the
shift guard is resolved, leaving `Nat.toUInt64` terms that `bv_decide` treats as
opaque. The formulas for `u32` normalize completely; for `u64` use exhaustive
evaluation (next section) when the input type is small.

Complex functions may need `set_option maxRecDepth 4096` for the simp step to
complete.

## `native_decide` — Exhaustive Evaluation for Finite Inputs

Compiles the function to native code and evaluates it on every input value, proving
panic freedom by enumeration rather than symbolic reasoning. Applies when
`hax_bv_decide` fails on `u64` arithmetic and the input type is small enough to
enumerate (`u8`: 256 values; `u16`: 65536 values). `u32` and wider inputs are not
enumerable; use `hax_bv_decide` or a manual proof.

The bridge from a Boolean check to a Hoare triple is a small set of lemmas that
are easy to state locally:

```lean
theorem RustM.triple_true_of_isOk (f : RustM α) (h : f.isOk = true) :
    ⦃ ⌜ True ⌝ ⦄ f ⦃ ⇓ _ => ⌜ True ⌝ ⦄ := ...

theorem UInt16.eq_ofBitVec_toFin (x : UInt16) :
    x = UInt16.ofBitVec (BitVec.ofFin x.toBitVec.toFin) := ...
```

Pattern for a function with `u64` intermediate arithmetic and `u16` input:

```lean
-- Step 1: Boolean checker
private def compress_is_ok (cb : u8) (fe : u16) : Bool := (compress cb fe).isOk

-- Step 2: exhaustive success for each concrete parameter value
private theorem compress_ok_4 :
    ∀ i : Fin 65536, compress_is_ok 4 (UInt16.ofBitVec (BitVec.ofFin i)) = true :=
  by native_decide

-- Step 3: assemble the Hoare triple
@[spec]
theorem compress.spec (coefficient_bits : u8) (fe : u16)
    (hcb : coefficient_bits = 4 ∨ coefficient_bits = 5 ∨ ...) (hfe : fe.toNat < 3329) :
    ⦃ ⌜ True ⌝ ⦄ compress coefficient_bits fe ⦃ ⇓ _ => ⌜ True ⌝ ⦄ := by
  apply RustM.triple_true_of_isOk
  show compress_is_ok coefficient_bits fe = true
  rw [UInt16.eq_ofBitVec_toFin fe]
  rcases hcb with rfl | rfl | rfl | rfl
  · exact compress_ok_4 fe.toBitVec.toFin
  · exact compress_ok_5 fe.toBitVec.toFin
  ...
```

`native_decide` needs a `Decidable` instance for the quantified statement. Quantify
over `Fin N` (decidable) rather than `UInt16`, and connect the two through
`UInt16.ofBitVec (BitVec.ofFin i)`.

`native_decide` adds the compiler to the trusted base (the proof carries a
`Lean.ofReduceBool` axiom); `hax_bv_decide` does not.

## Choosing a procedure

| Situation | Approach |
|-----------|----------|
| `u32` arithmetic, loop-free | `hax_bv_decide` (symbolic) |
| `u64` arithmetic with `u8`/`u16` input | `native_decide` (exhaustive) |
| `u64` arithmetic with `u32` or wider input | Manual proof or split into parts |
| Loop-bearing functions | `mvcgen` + `omega`/`grind` per VC |

## `mvcgen` — Monadic Verification Condition Generator

Decomposes Hoare triples into individual verification conditions. Pass the
definitions to unfold:

```lean
mvcgen [function_name, helper1, helper2]
```

Handles sequential monadic composition (`do` blocks), `if`/`else`, and checked
operations. `fold_range` loops are not decomposed; the loop body is left as an
open goal, and a loop invariant must be supplied.

For the `Spec` structure fields:

- `pureRequires`: `constructor; mvcgen [Machine_int.lt, ...]`
- `pureEnsures`: `constructor; intros; intro result; mvcgen [Machine_int.eq, Slice.Impl.len, ...]`
- `contract`: `mvcgen [fn_name, ...] <;> omega`

## `grind`

Congruence closure, linear integer arithmetic, and ring algebra; no bitvector
support (use `bv_decide` for that). Suited to the logical structure left after
`mvcgen`, equality and inequality chains, and simple postconditions.

```lean
-- With lemma hints
grind [Vector.toArray_size, Nat.lt_of_lt_of_le]

-- With options
grind (splits := 20) (ematch := 10)
```

## Three-Pass Overflow Pattern

For functions with many checked arithmetic operations (wrapping adds, shifts,
indexing), `mvcgen` produces many small VCs, each a precondition check (no overflow,
no out-of-bounds). Close them in three passes:

```lean
theorem my_fn.spec ... :
    ⦃ ⌜ True ⌝ ⦄ my_fn args ⦃ ⇓ _ => ⌜ True ⌝ ⦄ := by
  unfold my_fn helper1 helper2
  mvcgen [...]
  -- Pass 1: trivial goals
  all_goals first | trivial | decide | (simp [...]; omega) | skip
  -- Pass 2: simplify the remainder
  all_goals try simp_all [relevant_defs]
  -- Pass 3: arithmetic
  all_goals omega
```

Useful simp lemmas for pass 2: `Slice.Impl.len`, `Array.size_toArray` (array
length), `Vector.toArray_size`, `Fin.val_mk` (bounded index types),
`Nat.lt_of_lt_of_le`, `Nat.add_lt_add` (index arithmetic).

## Correspondence with F* Verification

| F* mechanism | Lean equivalent |
|-------------|-----------------|
| Refinement type `requires P` | `Spec` with `pureRequires` proving `P` |
| `--z3rlimit N` on bitvector goals | `hax_bv_decide (timeout := N)` |
| `--z3rlimit N` on arithmetic goals | `omega` or `grind` |
| `logand_mask_lemma` | Subsumed by `hax_bv_decide` (same-width types) |
| `fold_range` + trivial invariant | Supply the invariant; `mvcgen` does not infer it |
| `Prims.l_True` postcondition | `fun _ => pure True` in ensures |

## Decision Procedure Landscape

| Tool | Bitvectors | Proof-checked | Install |
|------|-----------|--------------|---------|
| `bv_decide` | Yes (SAT) | Yes (kernel) | Built into Lean |
| `grind` | No | Yes (kernel) | Built into Lean |
| `omega` | No (Nat/Int) | Yes | Built into Lean |
| `lean-smt` (cvc5) | Translation complete; reconstruction partial | Partial | External |
| `lean-auto` (z3/cvc5) | Via backend | No (trusted) | External |
| `duper` | No | Yes | External |

Use `bv_decide`, `grind`, and `omega` first: they are built in and kernel-checked.
External SMT tools track a specific Lean version and, for bitvectors, either trust
the solver or reconstruct only part of the theory; check a tool's own
compatibility statement against the Lean version pinned by hax-lib before
adopting it. `lean-smt` is the one to watch for bitvector proof reconstruction:
when its bitvector test suite passes without `sorry` for multiplication and
shifts, it would cover the `u64` cases that currently need `native_decide`.
