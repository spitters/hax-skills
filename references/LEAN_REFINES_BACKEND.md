# Lean-Refines Backend Reference

The **lean-refines** backend (`cargo hax into lean-refines`) extracts Rust code to
Lean 4 with dual pure/imperative definitions connected by machine-checked equivalence
proofs.

This backend lives on a fork of hax and is not in upstream `cryspen/hax`; the
upstream release provides only the `lean` backend.

## Overview

For each Rust function `f`, the backend generates three Lean declarations:

```lean
-- 1. Functional definition (nested let, equational reasoning)
def f_pure (args...) : σ → α × σ :=
  fun s =>
    let (v₁, s) := ...
    ...
    (result, s)

-- 2. Imperative definition (do notation, Hoare triple reasoning)
def f_state (args...) : StateM F.State α := do
  let v₁ ← ...
  ...
  return result

-- 3. Equivalence theorem (often closed by simp)
theorem f_equiv (args...) : (f_state args).run = f_pure args := by
  simp [f_state, f_pure, StateT.run, StateT.bind, StateT.get, StateT.set]
```

## When to Use

| Scenario | Recommended Backend |
|----------|-------------------|
| Pure functional verification | Standard `lean` backend |
| pRHL cryptographic proofs in Coq | `ssprove` backend |
| Dual reasoning (equational + Hoare) | **`lean-refines`** backend |
| Need totality guarantee (no `partial`) | **`lean-refines`** backend |
| Std.Do Hoare triple verification | **`lean-refines`** backend |

## The `Refines` Type

The core type is defined in `Hax/Refines.lean`:

```lean
structure Refines (σ α : Type) where
  pure_fn    : σ → α × σ           -- functional form
  state_comp : StateM σ α          -- imperative form
  equiv      : state_comp.run = pure_fn  -- extensional equality
```

### Why the equivalence is cheap

`StateM σ α = σ → α × σ`. The pure and imperative views have the same underlying
type and differ only in presentation, so equivalence proofs are often `rfl`.

### Core Combinators

```lean
-- Pure return: proof is rfl
Refines.ret (a : α) : Refines σ α

-- Bind: proof by funext + simp + component equivs
Refines.bind (x : Refines σ α) (f : α → Refines σ β) : Refines σ β

-- State operations: all proofs are rfl
Refines.get : Refines σ σ
Refines.set (s : σ) : Refines σ Unit
Refines.modify (f : σ → σ) : Refines σ Unit
```

### Monad Instance

`Refines σ` has `Monad` and `LawfulMonad` instances, so Lean's `do` notation works:

```lean
def example_computation : Refines Nat String := do
  let s ← Refines.get
  Refines.set (s + 1)
  pure (toString s)
```

### Stateless Computations

```lean
-- For pure functions with no state
abbrev PureRefines (α : Type) := Refines Unit α
```

## Loop Combinators

Defined in `Hax/Refines/StateLoop.lean`:

### For-Index Loop (`foldi`)

```lean
-- Iterates over [lo, hi) threading state
Refines.foldi (lo hi : Nat) (init : β)
    (body_pure : Nat → β → σ → β × σ)
    (body_state : Nat → β → StateM σ β)
    (body_equiv : ∀ i b, (body_state i b).run = fun s => body_pure i b s) :
    Refines σ β
```

### Fold Over List (`fold_list`)

```lean
Refines.fold_list (xs : List α) (init : β)
    (body_pure : α → β → σ → β × σ)
    (body_state : α → β → StateM σ β)
    (body_equiv : ∀ x b, (body_state x b).run = fun s => body_pure x b s) :
    Refines σ β
```

### While Loop (`while_loop`)

```lean
Refines.while_loop (fuel : Nat)
    (cond_pure : β → σ → Bool × σ) (body_pure : β → σ → β × σ)
    (cond_state : β → StateM σ Bool) (body_state : β → StateM σ β)
    (cond_equiv : ∀ b, (cond_state b).run = fun s => cond_pure b s)
    (body_equiv : ∀ b, (body_state b).run = fun s => body_pure b s)
    (init : β) : Refines σ β
```

### Specification Theorems

```lean
-- Loop invariant preservation
theorem Refines.foldi_spec
    (inv : Nat → β → σ → Prop)
    (h_init : ∀ s, inv lo init s)
    (h_step : ∀ i b s, lo ≤ i → i < hi →
      inv i b s → inv (i + 1) (body_pure i b s).1 (body_pure i b s).2)
    (s : σ) :
    let r := (foldi lo hi init body_pure body_state body_equiv).pure_fn s
    inv hi r.1 r.2

-- While loop termination + invariant
theorem Refines.while_loop_spec
    (inv : β → σ → Prop) (term : β → σ → Nat)
    (h_init : inv init s)
    (h_step : ...) (h_fuel : fuel ≥ term init s) :
    let r := (while_loop ...).pure_fn s
    inv r.1 r.2 ∧ (cond_pure r.1 r.2).1 = false
```

## Equivalence Tactics

Defined in `Hax/Refines/Equiv.lean`:

### `refines_equiv`

The primary tactic for closing equivalence goals. Strategy:
1. `funext` to introduce state variable
2. Unfold `StateT.run`, `StateT.bind`, `StateT.get`, `StateT.set`
3. `simp` with `Refines` lemmas
4. Try `rfl`

```lean
theorem my_equiv : (f_state args).run = f_pure args := by
  refines_equiv
```

### `refines_auto`

More aggressive version that additionally:
- Unfolds user definitions
- Tries `simp_all`
- Uses `omega` for arithmetic subgoals

```lean
theorem complex_equiv : (f_state args).run = f_pure args := by
  refines_auto
```

## Extraction Workflow

### 1. Write Hax-Compatible Rust

```rust
fn sum_array(arr: &[u32; 8]) -> u32 {
    let mut sum = 0u32;
    for i in 0..8 {
        sum = sum.wrapping_add(arr[i]);
    }
    sum
}
```

### 2. Extract

```bash
cargo hax into lean-refines
```

### 3. Generated Lean Code

```lean
abbrev SumArray.State := UInt32  -- mutable variable: sum

def sum_array_pure (arr : Array UInt32 8) : SumArray.State → UInt32 × SumArray.State :=
  fun s =>
    let s := 0
    Nat.fold (fun i (acc : UInt32 × SumArray.State) =>
      let (_, s) := acc
      let s := s + arr[i]
      ((), s)) 8 ((), s)
    |> fun (_, s) => (s, s)

def sum_array_state (arr : Array UInt32 8) : StateM SumArray.State UInt32 := do
  StateT.set 0
  for i in List.range 8 do
    let sum ← StateT.get
    StateT.set (sum + arr[i])
  StateT.get

theorem sum_array_equiv (arr : Array UInt32 8) :
    (sum_array_state arr).run = sum_array_pure arr := by
  simp [sum_array_state, sum_array_pure, StateT.run, StateT.bind, StateT.get, StateT.set]
```

### 4. Prove Properties

```lean
-- Equational reasoning via pure_fn
theorem sum_array_comm (arr : Array UInt32 8) (s : SumArray.State) :
    (sum_array_pure arr s).1 = ... := by
  simp [sum_array_pure]
  ...

-- Hoare triple reasoning via state_comp
@[spec]
theorem sum_array_spec (arr : Array UInt32 8) :
    ⦃⌜True⌝⦄
      sum_array_state arr
    ⦃⇓ r => ⌜r = arr.foldl (· + ·) 0⌝⦄ := by
  ...
```

## Comparison with Other Backends

### vs. Standard Lean Backend

| Aspect | `lean` | `lean-refines` |
|--------|---------|----------------|
| Output style | Pure functional | Dual pure + imperative |
| Loops | Functionalized (fold) | Structured (loop combinators) |
| Totality | `partial` allowed | Total only |
| State | `RustM` monad | `StateM σ` (concrete state type) |
| Hoare triples | Via `RustM` WPMonad | Via `StateM` WPMonad |
| Equational reasoning | Direct | Via `pure_fn` |

### vs. SSProve Backend (Coq)

| Aspect | `ssprove` (Coq) | `lean-refines` |
|--------|-----------------|----------------|
| Language | Coq | Lean 4 |
| Core type | `both A` | `Refines σ α` |
| State model | SSProve `RawCode` | `StateM σ` |
| Probabilistic | Yes (via SSProve) | No (deterministic only) |
| Automation | Manual proof | `simp` / `refines_equiv` |
| pRHL support | Native | None (deterministic programs only) |

## Source Layout

Paths relative to the root of the hax fork:

| Component | Path |
|-----------|------|
| Refines type | `hax-lib/proof-libs/lean/Hax/Refines.lean` |
| Loop combinators | `hax-lib/proof-libs/lean/Hax/Refines/StateLoop.lean` |
| Equiv tactics | `hax-lib/proof-libs/lean/Hax/Refines/Equiv.lean` |
| OCaml backend | `engine/backends/lean/lean_refines/lean_refines_backend.ml` |
| Lean AST | `engine/backends/lean/lean_refines/lean_ast.ml` |
| Backend registration | `engine/lib/diagnostics.ml` (`LeanRefines` variant) |
| Engine dispatch | `engine/bin/lib.ml` |

## Build and Extraction Commands

### Prerequisites
- The Rust nightly pinned in the fork's `rust-toolchain.toml`
- An OCaml switch with the hax engine dependencies (see the hax `README`)
- The `cargo-hax` and `hax-engine` binaries on `PATH`

### Build the Backend
```bash
# After modifying lean_refines_backend.ml, from the engine directory:
dune build bin/native_driver.exe
```

### Run Extraction
```bash
cd /path/to/rust-project
cargo hax into lean-refines
# Output: proofs/lean-refines/extraction/<Crate_name>.lean
```
