# Lean 4 Integration for Hax

This document describes how to extract hax-compatible Rust to Lean 4, build the
result, and prove properties about it.

## Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Rust Code     │     │  Extracted      │     │    Proven       │
│   (Hax-compat)  │────►│  Lean 4 Code    │────►│  Properties     │
│                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
    cargo hax            lean-lsp-mcp           lean4-theorem-
    into lean            for feedback           proving skill
```

## Prerequisites

### 1. Install Hax

Hax requires the Rust nightly pinned in its `rust-toolchain.toml`; `cargo hax`
selects it through that file, so the commands below need no explicit `+nightly`
override.

```bash
git clone https://github.com/cryspen/hax && cd hax && ./setup.sh
```

### 2. Install Lean 4

```bash
# Install elan (Lean version manager)
curl https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh -sSf | sh

# Verify installation
lean --version
lake --version
```

The Lean toolchain for a project is pinned by its `lean-toolchain` file; use the
version that hax-lib's Lean library declares so the extracted code and the library
elaborate under the same compiler.

### 3. Install lean-lsp-mcp (for Claude integration)

```bash
# Add to Claude Code
claude mcp add lean-lsp uvx lean-lsp-mcp

# Or configure in .claude/mcp.json
```

```json
{
  "servers": {
    "lean-lsp": {
      "type": "stdio",
      "command": "uvx",
      "args": ["lean-lsp-mcp"]
    }
  }
}
```

The server describes its own tools (goal state, diagnostics, lemma search,
multi-tactic attempts, profiling) in the instructions it sends the client; consult
those rather than a copy here.

### 4. Optional: Install lean4-theorem-proving skill

The [lean4-theorem-proving skill](https://github.com/cameronfreer/lean4-theorem-proving-skill) provides Claude with specialized tactics knowledge.

## Extraction Workflows

### Standard Lean Backend

#### Step 1: Check the Rust Code with the Hax Frontend

```bash
# Frontend only: reports unsupported constructs without running a backend
cargo hax json
```

#### Step 2: Extract to Lean 4

```bash
# Extract entire crate
cargo hax into lean

# Extract specific modules
cargo hax -i "+my_module::**" into lean
```

#### Step 3: Build Extracted Code

```bash
cd proofs/lean
lake build
```

### Lean-Refines Backend (Dual Pure/Imperative)

The `lean-refines` backend generates both pure functional and imperative (StateM)
definitions, plus equivalence proofs. It lives on a fork of hax, not in the
upstream release. See `references/LEAN_REFINES_BACKEND.md` for details.

```bash
cargo hax into lean-refines
# Output: proofs/lean-refines/extraction/<Crate_name>.lean
```

Each Rust function `f` produces 3 declarations: `f_pure`, `f_state`, `f_equiv`.

## Understanding Extracted Code

### Type Mappings

| Rust Type | Lean Type |
|-----------|-----------|
| `u8`, `u16`, `u32`, `u64` | `UInt8`, `UInt16`, `UInt32`, `UInt64` |
| `i8`, `i16`, `i32`, `i64` | `Int8`, `Int16`, `Int32`, `Int64` |
| `usize` | `USize` |
| `bool` | `Bool` |
| `[T; N]` | `Vector T N` |
| `(T1, T2)` | `T1 × T2` |
| `Option<T>` | `Option T` |
| `Result<T, E>` | `Except E T` |

### Function Extraction

Rust:
```rust
fn add_u32(a: u32, b: u32) -> u32 {
    a.wrapping_add(b)
}
```

Lean:
```lean
def add_u32 (a b : UInt32) : UInt32 :=
  a + b  -- Lean UInt32 wraps by default
```

### Struct Extraction

Rust:
```rust
#[derive(Clone, Copy)]
struct Point {
    x: u32,
    y: u32,
}
```

Lean:
```lean
structure Point where
  x : UInt32
  y : UInt32
  deriving Repr, DecidableEq
```

### Hax Contracts → Lean Specifications

Rust:
```rust
#[hax::requires(b != 0)]
#[hax::ensures(|result| result * b <= a)]
fn divide(a: u32, b: u32) -> u32 {
    a / b
}
```

Lean:
```lean
def divide (a b : UInt32) (h : b ≠ 0) : UInt32 :=
  a / b

theorem divide_spec (a b : UInt32) (h : b ≠ 0) :
  (divide a b h) * b ≤ a := by
  sorry  -- Proof obligation
```

## Common Proof Patterns

### Proving Arithmetic Properties

```lean
-- Extracted from Rust: commutativity of wrapping add
theorem add_comm (a b : UInt32) : a + b = b + a := by
  simp [UInt32.add_comm]

-- Associativity
theorem add_assoc (a b c : UInt32) : (a + b) + c = a + (b + c) := by
  simp [UInt32.add_assoc]
```

### Proving Array Bounds

```lean
-- Array access with an in-bounds proof
theorem array_access_safe {n : Nat} (arr : Vector UInt8 n) (i : Nat) (h : i < n) :
  ∃ v, arr[i]'h = v := by
  exact ⟨arr[i]'h, rfl⟩
```

### Trying several tactics at once

When stuck on a proof, use the MCP tool to try multiple tactics:

```
Tool: lean_multi_attempt
Input: {
  "file_path": "MyProof.lean",
  "line": 42,
  "tactics": ["simp", "ring", "omega", "decide", "native_decide"]
}
```

### Finding lemmas

```
Tool: lean_leansearch
Input: {
  "query": "addition is commutative for natural numbers"
}
```

## Project Structure

Recommended structure for a Hax project with Lean verification:

```
my-project/
├── Cargo.toml
├── src/
│   └── lib.rs              # Hax-compatible Rust
├── proofs/
│   └── lean/
│       ├── lakefile.toml   # Lean project config
│       ├── MyProject/
│       │   ├── Extracted.lean    # Auto-generated
│       │   └── Proofs.lean       # Manual proofs
│       └── lake-manifest.json
└── hax-treesitter/         # Optional: fast linting
    └── queries/
        └── hax-lint.scm
```

### lakefile.toml

```toml
name = "my-project-proofs"
version = "0.1.0"
defaultTargets = ["MyProject"]

[[require]]
name = "mathlib"
git = "https://github.com/leanprover-community/mathlib4"
rev = "master"

[[lean_lib]]
name = "MyProject"
```

## Verification Workflow

### 1. Extract and Build

```bash
# Extract
cargo hax into lean --output-dir proofs/lean/MyProject

# Build
cd proofs/lean
lake build
```

### 2. Check for Sorries

The extraction may include `sorry` placeholders for unproven obligations. Lean
reports each one during the build; check the `lake build` output for
`declaration uses 'sorry'` warnings. A text search over the sources also matches
comments and is not a substitute.

### 3. Prove Obligations

Create a separate proofs file:

```lean
-- proofs/lean/MyProject/Proofs.lean
import MyProject.Extracted

namespace MyProject

-- Prove the extracted specification
theorem divide_correct (a b : UInt32) (h : b ≠ 0) :
    (Extracted.divide a b h) * b ≤ a := by
  -- Your proof here
  sorry

end MyProject
```

### 4. Verify All Proofs

```bash
lake build
# Success = all proofs type-check and no sorry warnings remain
```

## Tips for Proving Extracted Code

### 1. Start with `decide` for Decidable Props

```lean
example : (5 : UInt32) + 3 = 8 := by decide
```

### 2. Use `simp` with Extracted Definitions

```lean
theorem foo : myExtractedFn x = expected := by
  simp [myExtractedFn]
```

### 3. Use `omega` for Linear Arithmetic

```lean
theorem bound_check (i : Nat) (h : i < 10) : i + 1 ≤ 10 := by omega
```

### 4. Use `ring` for Polynomial Identities

```lean
theorem field_identity (x y : Int) : (x + y)^2 = x^2 + 2*x*y + y^2 := by ring
```

### 5. Use `native_decide` for Computable Decidable Props

```lean
example : (1000000 : Nat) < 2000000 := by native_decide
```

`native_decide` trusts the compiler; prefer `decide` or `bv_decide` where they
finish.

## Panic-Freedom Proofs

The `lean` backend states panic freedom as Hoare triples over `RustM`. The
decision procedures that close them (`mvcgen`, `omega`, `grind`, `hax_bv_decide`
from hax-lib's `Tactic/HaxBVDecide.lean`, exhaustive `native_decide`) and the
three-pass overflow pattern are described in `references/PANIC_FREEDOM.md`.

## Troubleshooting

### "unknown identifier" errors

The extracted code may use Hax-specific definitions. Ensure you import:

```lean
import Hax.Lib  -- Hax standard library for Lean
```

### Type mismatches

Hax may extract types differently. Check:
- Signedness (UInt vs Int)
- Bit width (UInt32 vs UInt64)
- Array representation

### Missing Mathlib lemmas

If you need Mathlib:

```toml
# lakefile.toml
[[require]]
name = "mathlib"
git = "https://github.com/leanprover-community/mathlib4"
```

Then: `lake update && lake build`

## Resources

- [Hax Documentation](https://hax.rs)
- [Lean 4 Documentation](https://lean-lang.org/lean4/doc/)
- [lean-lsp-mcp](https://github.com/oOo0oOo/lean-lsp-mcp)
- [lean4-theorem-proving-skill](https://github.com/cameronfreer/lean4-theorem-proving-skill)
- [Mathlib4](https://github.com/leanprover-community/mathlib4)
