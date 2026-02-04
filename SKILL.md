# Hax-Compatible Rust Code Generation

Generate Rust code that passes the Hax type checker and can be extracted to formal verification backends (F*, Lean 4, Coq, ProVerif).

## Overview

Hax extracts a subset of Safe Rust to proof assistants for formal verification. This skill teaches you to:
- Write Rust code that passes Hax extraction
- Use tooling for fast feedback (tree-sitter, cargo hax)
- Prove properties in Lean 4 using extracted code

## Architecture

This skill works as a **layer on top of** the standard Rust tooling:

```
┌─────────────────────────────────────────────────────────────┐
│                    PROOF BACKENDS                           │
│  ┌─────────────┐                                           │
│  │ lean-lsp-mcp│  + lean4-theorem-proving skill            │
│  │ (Lean 4)    │                                           │
│  └──────┬──────┘                                           │
│         │                                                   │
├─────────┼───────────────────────────────────────────────────┤
│         │           HAX SKILL (this)                        │
│  ┌──────┴─────────────────────────────────────────────┐    │
│  │  • Extraction constraints (RESTRICTIONS.md)        │    │
│  │  • Repair patterns (REPAIR.md)                     │    │
│  │  • hax-treesitter for instant validation           │    │
│  │  • cargo hax integration                           │    │
│  └──────┬─────────────────────────────────────────────┘    │
│         │                                                   │
├─────────┼───────────────────────────────────────────────────┤
│         │        RUST ANALYZER LSP                          │
│  ┌──────┴─────────────────────────────────────────────┐    │
│  │  • Code navigation, completion                     │    │
│  │  • Type checking, diagnostics                      │    │
│  │  • Refactoring, formatting                         │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## Quick Reference

| Need | Approach |
|------|----------|
| Install Hax | `cargo +nightly install --git https://github.com/cryspen/hax hax-engine` |
| Fast syntax check | `python hax_lint.py src/*.rs` (tree-sitter) |
| Full validation | `cargo hax check` |
| Extract to Lean 4 | `cargo hax into lean4` |
| Fix errors | See [REPAIR.md](references/REPAIR.md) |
| Understand restrictions | See [RESTRICTIONS.md](references/RESTRICTIONS.md) |
| Prove in Lean | See [LEAN_INTEGRATION.md](LEAN_INTEGRATION.md) |

## Tooling Setup

### 1. Hax Compiler

```bash
# Requires Rust nightly
cargo +nightly install --git https://github.com/cryspen/hax hax-engine
```

### 2. Fast Tree-sitter Validation (Optional but Recommended)

```bash
# Install Python dependencies
pip install tree-sitter tree-sitter-rust

# Run instant syntax-level check
python hax-treesitter/hax_lint.py src/lib.rs
```

The tree-sitter linter catches ~80% of Hax violations in <100ms, before running the slower `cargo hax check`.

### 3. MCP Integration (Optional)

```bash
# Add Hax tools to Claude Code
claude mcp add hax-tools python /path/to/hax-treesitter/mcp/hax_mcp_server.py

# Add Lean 4 tools for proof development
claude mcp add lean-lsp uvx lean-lsp-mcp
```

## Supported Rust Subset

### Supported Features

| Feature | Status | Notes |
|---------|--------|-------|
| Primitive types (`u8`-`u128`, `bool`) | ✅ | Full support |
| Fixed-size arrays `[T; N]` | ✅ | Preferred over Vec |
| Tuples | ✅ | |
| Structs, Enums | ✅ | With `#[derive(Clone, Copy)]` |
| Pattern matching | ✅ | |
| `for i in 0..N` loops | ✅ | Bounded iteration |
| References `&T`, `&mut T` | ✅ | |
| Generics with trait bounds | ✅ | |
| Const generics | ✅ | Key for array sizes |
| `Option<T>`, `Result<T,E>` | ✅ | |
| Trait implementations | ✅ | No trait objects |

### Not Supported

| Feature | Alternative |
|---------|-------------|
| `unsafe` blocks | Safe implementations only |
| Raw pointers `*const T` | Use references or indices |
| `dyn Trait` | Use generics or enums |
| `Vec<T>`, `Box<T>`, `String` | Use `[T; N]`, stack allocation |
| `while` loops | Use bounded `for` loops |
| `loop` (unbounded) | Use bounded iteration |
| `async`/`await` | Not supported |
| `Cell`, `RefCell`, `Mutex` | Pass state explicitly |
| `static mut` | Pure functions only |

## Writing Hax-Compatible Code

### Arithmetic: Always Use Wrapping Operations

```rust
// ✅ CORRECT
fn add_safe(a: u32, b: u32) -> u32 {
    a.wrapping_add(b)
}

// ❌ WRONG - can panic on overflow
fn add_unsafe(a: u32, b: u32) -> u32 {
    a + b
}
```

### Arrays: Prove Bounds or Use Contracts

```rust
use hax_lib as hax;

// ✅ CORRECT - bounds proven by loop structure
fn sum<const N: usize>(arr: &[u32; N]) -> u32 {
    let mut sum = 0u32;
    for i in 0..N {
        sum = sum.wrapping_add(arr[i]);  // i < N is proven
    }
    sum
}

// ✅ CORRECT - bounds specified by contract
#[hax::requires(index < arr.len())]
fn get_element(arr: &[u8; 32], index: usize) -> u8 {
    arr[index]
}
```

### Loops: Always Bounded

```rust
// ✅ CORRECT - range-based
for i in 0..256 {
    process(arr[i]);
}

// ✅ CORRECT - iterator over fixed array
for item in arr.iter() {
    process(item);
}

// ❌ WRONG - unbounded
while condition {
    // ...
}

// ❌ WRONG - infinite
loop {
    // ...
}
```

### Data Structures: Fixed-Size, Stack-Allocated

```rust
// ✅ CORRECT - fixed-size buffer
#[derive(Clone, Copy)]
struct Buffer<const N: usize> {
    data: [u8; N],
    len: usize,
}

// ❌ WRONG - heap allocation
struct DynamicBuffer {
    data: Vec<u8>,  // Not supported
}
```

## Hax Contracts

Use `hax_lib` attributes for specifications that become proof obligations:

```rust
use hax_lib as hax;

// Precondition
#[hax::requires(b != 0)]
fn divide(a: u32, b: u32) -> u32 {
    a / b
}

// Postcondition
#[hax::ensures(|result| result >= a && result >= b)]
fn max(a: u32, b: u32) -> u32 {
    if a >= b { a } else { b }
}

// Loop invariant
fn sum_to_n(n: u32) -> u32 {
    let mut sum = 0u32;
    let mut i = 0u32;
    #[hax::loop_invariant(|sum, i| i <= n)]
    while i < n {
        sum = sum.wrapping_add(i);
        i = i.wrapping_add(1);
    }
    sum
}
```

## Verification Workflow

### 1. Write Hax-Compatible Rust

```rust
// src/lib.rs
#![cfg_attr(feature = "hax", feature(register_tool))]
#![cfg_attr(feature = "hax", register_tool(hax))]

use hax_lib as hax;

#[hax::requires(index < 32)]
pub fn safe_access(arr: &[u8; 32], index: usize) -> u8 {
    arr[index]
}
```

### 2. Validate with Tree-sitter (Fast)

```bash
python hax_lint.py src/lib.rs
# Instant feedback on syntax-level violations
```

### 3. Validate with Cargo Hax (Complete)

```bash
cargo hax check
# Full semantic validation
```

### 4. Extract to Lean 4

```bash
cargo hax into lean4 -o proofs/lean
```

### 5. Build and Prove in Lean

```bash
cd proofs/lean
lake build
# Fix any `sorry` placeholders with actual proofs
```

See [LEAN_INTEGRATION.md](LEAN_INTEGRATION.md) for detailed Lean workflow.

## Common Errors and Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `Unsupported: unsafe` | `unsafe` block | Remove, use safe alternatives |
| `Unsupported: dyn` | Trait objects | Use generics with bounds |
| `Unbounded loop` | `while`/`loop` | Use `for i in 0..N` |
| `Type not extractable` | `Vec`, `String` | Use `[T; N]` |
| `Panic possible` | Division, indexing | Add `#[hax::requires]` or check bounds |
| `Heap allocation` | `Box::new`, `vec!` | Stack allocate with fixed size |

For detailed repair patterns, see [REPAIR.md](references/REPAIR.md).

## Project Setup

### Cargo.toml

```toml
[package]
name = "my-hax-project"
version = "0.1.0"
edition = "2021"

[dependencies]
hax-lib = "0.1"

[features]
hax = []

# Optional: Configure extraction backends
[package.metadata.hax]
backend.fstar.into = "proofs/fstar"
backend.lean4.into = "proofs/lean"
```

### Directory Structure

```
my-project/
├── Cargo.toml
├── src/
│   └── lib.rs              # Hax-compatible Rust
├── proofs/
│   └── lean/               # Extracted Lean code + proofs
│       ├── lakefile.toml
│       └── MyProject/
└── hax-treesitter/         # Optional: fast linting
    └── queries/
        └── hax-lint.scm
```

## References

- **Restrictions**: [RESTRICTIONS.md](references/RESTRICTIONS.md) - Complete feature support
- **Repair Patterns**: [REPAIR.md](references/REPAIR.md) - Fixing Hax errors
- **Code Patterns**: [PATTERNS.md](references/PATTERNS.md) - Reusable designs
- **Lean Integration**: [LEAN_INTEGRATION.md](LEAN_INTEGRATION.md) - Proof workflow
- **Example**: [examples/field_u256.rs](examples/field_u256.rs) - 256-bit field arithmetic

## External Resources

- [Hax Documentation](https://hax.rs)
- [Hax GitHub](https://github.com/cryspen/hax)
- [lean-lsp-mcp](https://github.com/oOo0oOo/lean-lsp-mcp)
- [lean4-theorem-proving-skill](https://github.com/cameronfreer/lean4-theorem-proving-skill)
