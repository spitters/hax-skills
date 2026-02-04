# Lean 4 Integration for Hax

This document describes how to work with Hax-extracted Lean 4 code, including tooling setup and proof workflows.

## Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Rust Code     │     │  Extracted      │     │    Proven       │
│   (Hax-compat)  │────►│  Lean 4 Code    │────►│  Properties     │
│                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
    cargo hax            lean-lsp-mcp           lean4-theorem-
    into lean4           for feedback           proving skill
```

## Prerequisites

### 1. Install Hax

```bash
# Requires Rust nightly
cargo +nightly install --git https://github.com/cryspen/hax hax-engine
```

### 2. Install Lean 4

```bash
# Install elan (Lean version manager)
curl https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh -sSf | sh

# Verify installation
lean --version
lake --version
```

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

### 4. Optional: Install lean4-theorem-proving skill

The [lean4-theorem-proving skill](https://github.com/cameronfreer/lean4-theorem-proving-skill) provides Claude with specialized tactics knowledge.

## Extraction Workflow

### Step 1: Prepare Rust Code

Ensure your code passes `cargo hax check`:

```bash
# Quick syntax check (if using hax-treesitter)
python hax_lint.py src/lib.rs

# Full Hax validation
cargo hax check
```

### Step 2: Extract to Lean 4

```bash
# Extract entire crate
cargo hax into lean4

# Extract specific modules
cargo hax into lean4 --include my_module

# Specify output directory
cargo hax into lean4 -o proofs/lean
```

### Step 3: Build Extracted Code

```bash
cd proofs/lean
lake build
```

## Understanding Extracted Code

### Type Mappings

| Rust Type | Lean Type |
|-----------|-----------|
| `u8`, `u16`, `u32`, `u64` | `UInt8`, `UInt16`, `UInt32`, `UInt64` |
| `i8`, `i16`, `i32`, `i64` | `Int8`, `Int16`, `Int32`, `Int64` |
| `usize` | `USize` |
| `bool` | `Bool` |
| `[T; N]` | `Array T N` or `Vector T N` |
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

## lean-lsp-mcp Tools

The lean-lsp-mcp provides these tools for interactive proof development:

### Diagnostic Tools

| Tool | Purpose |
|------|---------|
| `lean_file_outline` | Get file structure (imports, definitions) |
| `lean_diagnostic_messages` | Get all errors, warnings |
| `lean_goal` | Get proof state at position |
| `lean_hover_info` | Get type/documentation for symbol |

### Search Tools

| Tool | Purpose |
|------|---------|
| `lean_leansearch` | Natural language theorem search |
| `lean_loogle` | Type-based lemma search |
| `lean_local_search` | Search project + stdlib |
| `lean_hammer_premise` | Auto-discover relevant premises |

### Execution Tools

| Tool | Purpose |
|------|---------|
| `lean_run_code` | Execute isolated Lean code |
| `lean_multi_attempt` | Try multiple tactics in parallel |
| `lean_profile_proof` | Find slow tactics |

## Common Proof Patterns

### Proving Arithmetic Properties

```lean
-- Extracted from Rust: commutativity of wrapping add
theorem add_comm (a b : UInt32) : a + b = b + a := by
  -- UInt32 addition is commutative by definition
  simp [UInt32.add_comm]

-- Associativity
theorem add_assoc (a b c : UInt32) : (a + b) + c = a + (b + c) := by
  simp [UInt32.add_assoc]
```

### Proving Array Bounds

```lean
-- Proving array access is safe
theorem array_access_safe {n : Nat} (arr : Array UInt8 n) (i : Nat) (h : i < n) :
  ∃ v, arr[i]'h = v := by
  exact ⟨arr[i]'h, rfl⟩

-- Loop invariant preservation
theorem sum_loop_invariant (arr : Array UInt32 n) (i : Nat) (acc : UInt32)
  (h : i ≤ n) : i ≤ n := h
```

### Using lean_multi_attempt

When stuck on a proof, use the MCP tool to try multiple tactics:

```
Tool: lean_multi_attempt
Input: {
  "file_path": "MyProof.lean",
  "line": 42,
  "tactics": ["simp", "ring", "omega", "decide", "native_decide"]
}
```

### Using lean_leansearch

For finding relevant lemmas:

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
cargo hax into lean4 -o proofs/lean/MyProject/Extracted.lean

# Build
cd proofs/lean
lake build
```

### 2. Check for Sorries

The extraction may include `sorry` placeholders for unproven obligations:

```bash
# Find all sorries
grep -r "sorry" proofs/lean/
```

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
# Success = all proofs type-check
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
