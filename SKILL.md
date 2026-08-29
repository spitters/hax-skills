---
name: hax-rust
description: |
  Generate Rust code that compiles and passes the hax extraction for formal
  verification. Use when (1) writing Rust for hax extraction to Lean 4, F*,
  Coq/SSProve, EasyCrypt, or ProVerif; (2) creating formally verifiable
  cryptographic implementations; (3) converting existing Rust to the hax
  subset; (4) building high-assurance security software. This skill is a
  layer on top of rust-analyzer, not a replacement for it; hax accepts a
  subset of safe Rust with specific restrictions.
---

# Hax-Compatible Rust Code Generation

Hax extracts a subset of safe Rust to proof assistants: F*, Lean 4, Coq (and
its SSProve library), EasyCrypt, and ProVerif. This skill covers writing Rust
that hax extracts, checking it quickly, and starting a proof over the output.

Machine-specific paths and build instructions belong in `hax-local.md`, which
is gitignored (see `README.md`).

## Quick reference

| Need | Approach |
|------|----------|
| Install hax | clone `https://github.com/cryspen/hax` and run `./setup.sh` (or `nix profile install github:cryspen/hax`) |
| Fast syntax check | `hax-lint src/*.rs` (tree-sitter, see `hax-treesitter/`) |
| Frontend check, no backend | `cargo hax json` |
| Full extraction | `cargo hax into <backend>` |
| Extract to Lean 4 | `cargo hax into lean` |
| Extract to Lean 4 through a verified pipeline | `cargo hax json`, then `haxpipeT` from [hax-lean](https://github.com/spitters/hax-lean) |
| Fix errors | [references/REPAIR.md](references/REPAIR.md) |
| Restrictions | [references/RESTRICTIONS.md](references/RESTRICTIONS.md) |
| Reusable designs | [references/PATTERNS.md](references/PATTERNS.md) |
| Prove in Lean | [LEAN_INTEGRATION.md](LEAN_INTEGRATION.md) |

Connecting an extraction to a CatCrypt security proof is the `rust-to-uc`
skill (internal).

## Tooling

### hax

```bash
git clone https://github.com/cryspen/hax && cd hax && ./setup.sh
cargo hax --help
```

`setup.sh` needs `opam`, `rustup`, `nodejs`, and `jq`; it installs `cargo-hax`
into `$HOME/.cargo/bin`. The subcommands are `into <backend>` (extract),
`json` (run the frontend and write the export, no backend), and `serialize`.

### Tree-sitter linter

```bash
pip install -e hax-treesitter/
hax-lint src/lib.rs
```

The linter is a syntax-level pass: it flags `unsafe`, `while`/`loop`, `dyn`,
heap types, and the other constructs in `references/RESTRICTIONS.md` before
the frontend runs. It does not type-check and does not replace `cargo hax`.

### MCP (Claude Code)

```bash
claude mcp add hax-tools hax-mcp-server          # tree-sitter lint + cargo hax
claude mcp add lean-lsp uvx lean-lsp-mcp         # Lean 4 proof development
```

## Writing hax-compatible code

Supported and unsupported features, with alternatives, are in
[references/RESTRICTIONS.md](references/RESTRICTIONS.md); the rules below are
the ones that decide most extractions.

### Arithmetic: wrapping operations

```rust
fn add(a: u32, b: u32) -> u32 { a.wrapping_add(b) }   // ✅
fn add(a: u32, b: u32) -> u32 { a + b }               // ❌ overflow panic obligation
```

### Arrays: prove bounds or state a contract

```rust
// bounds follow from the loop range
fn sum<const N: usize>(arr: &[u32; N]) -> u32 {
    let mut sum = 0u32;
    for i in 0..N {
        sum = sum.wrapping_add(arr[i]);
    }
    sum
}

// bounds stated as a precondition
#[hax_lib::requires(index < arr.len())]
fn get_element(arr: &[u8; 32], index: usize) -> u8 {
    arr[index]
}
```

### Loops: bounded

```rust
for i in 0..256 { process(arr[i]); }     // ✅ range
for item in arr.iter() { process(item); } // ✅ iterator over a fixed array
while condition { … }                     // ❌ no static bound
loop { … }                                // ❌
```

A counting `while` is rewritten as `for i in 0..n`; a data-dependent exit with
a static bound runs the full bound and masks the iterations after the exit.

### Data structures: fixed-size, stack-allocated

```rust
#[derive(Clone, Copy)]
struct Buffer<const N: usize> { data: [u8; N], len: usize }   // ✅

struct DynamicBuffer { data: Vec<u8> }                        // ❌ heap
```

### Mutable references

`&mut T` parameters are accepted; `&mut` in return types or aliased `&mut`
borrows are not. Prefer value-passing (`x = f(x)`) for state threaded across
calls.

## Contracts

`hax_lib` attributes become proof obligations in the backend:

```rust
#[hax_lib::requires(b != 0)]
fn divide(a: u32, b: u32) -> u32 { a / b }

#[hax_lib::ensures(|result| result >= a && result >= b)]
fn max(a: u32, b: u32) -> u32 { if a >= b { a } else { b } }

fn sum_to_n(n: u32) -> u32 {
    let mut sum = 0u32;
    for i in 0..n {
        hax_lib::loop_invariant!(|i: u32| sum as u64 <= (i as u64) * (n as u64));
        sum = sum.wrapping_add(i);
    }
    sum
}
```

A loop invariant is the `hax_lib::loop_invariant!` macro on the first line of
the loop body, taking a closure over the loop variable.

## Verification workflow

### 0. Obtain hax-compatible Rust

If the crate you start from (RustCrypto, ring, dalek, …) uses `unsafe`, SIMD,
trait objects, or heap allocation, write a hax-compatible reference
implementation: a clean-room, spec-level rewrite from the RFC or standard,
validated against the original with test vectors. Crates already in the hax
subset (libcrux, bertie, hpke-spec) are used directly.

### 1. Write the Rust

```rust
// src/lib.rs
#[hax_lib::requires(index < 32)]
pub fn safe_access(arr: &[u8; 32], index: usize) -> u8 {
    arr[index]
}
```

### 2. Lint

```bash
hax-lint src/lib.rs
```

### 3. Check the frontend

```bash
cargo hax json
```

This runs the Rust frontend and writes the hax export without invoking a
backend; it is the fast way to find constructs outside the subset.

### 4. Extract

```bash
cargo hax into lean
```

### 5. Build and prove

```bash
cd proofs/lean && lake build
```

[LEAN_INTEGRATION.md](LEAN_INTEGRATION.md) covers the Lean side; error
messages and their fixes are in [references/REPAIR.md](references/REPAIR.md).

## Project setup

```toml
# Cargo.toml
[dependencies]
hax-lib = "0.1"
```

Extraction configuration lives in a `hax.toml` at the workspace root: tool
version pins (`cargo hax tools pin` writes them) and named proof scenarios,
each storing a complete extraction configuration:

```toml
# hax.toml
[scenario.lean]
backend = "lean"
```

`cargo hax extract lean` runs that scenario into `proofs/lean/`; a bare
`cargo hax into lean` extracts the whole crate with the defaults. For the
`lean` backend the output is a complete Lean package:

```
my-project/
├── Cargo.toml
├── hax.toml
├── src/lib.rs                    # hax-compatible Rust
└── proofs/lean/
    ├── lakefile.toml             # generated, versions pinned to the extraction
    ├── lean-toolchain
    └── MyProject/
        ├── Extraction/           # generated, rewritten on every run
        ├── Verification/         # handwritten proofs, never touched by hax
        └── Assumptions/          # models of external definitions, seeded once
```

The `hax.toml` reference (tool pins, per-crate overrides, scenarios) is the
[tools page](https://hax.cryspen.com/manual/tools/) of the hax manual.

## Extraction backends

| Backend | Command | Target | Style |
|---------|---------|--------|-------|
| `fstar` | `cargo hax into fstar` | F* | WP-based effects, automated verification; documented in the [manual](https://hax.cryspen.com/manual/fstar/quick_start/) |
| `lean` | `cargo hax into lean` | Lean 4 | the [Aeneas](https://github.com/AeneasVerif/aeneas) pipeline (charon + aeneas, fetched by `cargo hax tools install`); emits a complete Lean package; documented in the [manual](https://hax.cryspen.com/manual/lean/quick_start/) |
| Cryspen hax Lean backend | `cargo hax into legacy-lean` | Lean 4 | the [hax-engine Lean backend](https://github.com/cryspen/hax/tree/main/engine/backends/lean) over [hax-lib's Lean library](https://github.com/cryspen/hax/tree/main/hax-lib/proof-libs/lean) (`RustM`, `hax_bv_decide`, `hax_mvcgen`); the subcommand name is upstream's |
| `coq` | `cargo hax into coq` | Coq | pure |
| `ssprove` | `cargo hax into ssprove` | Coq / SSProve | `both` type (pure + SSProve code) for game-based proofs |
| `easycrypt` | `cargo hax into easycrypt` | EasyCrypt | marked work in progress upstream; no manual page or example |
| `proverif` | `cargo hax into proverif` | ProVerif | symbolic protocol model; marked work in progress upstream; documented by one example, `examples/proverif-psk` (a PSK protocol with a handwritten `.pv` for comparison and `proverif::replace()` for symbolic replacements), no manual page |
| [hax-lean](https://github.com/spitters/hax-lean) `haxpipeT` | `cargo hax json`, then `haxpipeT --hax export.json --emit-certified --name M` | Lean 4 | verified pipeline: the imperative `ImpExpr` is lowered to a purely functional form with a machine-checked `denote`-preservation proof; consumes the frontend export rather than running a hax engine backend |

The backend list and status labels are those of `cryspen/hax` `main`
(`hax-types/src/cli_options/mod.rs`, `enum Backend`).

## References

- [references/RESTRICTIONS.md](references/RESTRICTIONS.md) — feature support
- [references/REPAIR.md](references/REPAIR.md) — fixing extraction errors
- [references/PATTERNS.md](references/PATTERNS.md) — reusable designs
- [LEAN_INTEGRATION.md](LEAN_INTEGRATION.md) — proof workflow
- [references/PANIC_FREEDOM.md](references/PANIC_FREEDOM.md) — proving panic freedom over extracted code
- [hax-lean](https://github.com/spitters/hax-lean) — verified extraction pipeline to Lean 4
- [examples/field_u256.rs](examples/field_u256.rs) — 256-bit field arithmetic
- [hax documentation](https://hax.rs), [hax on GitHub](https://github.com/cryspen/hax)
- [lean-lsp-mcp](https://github.com/oOo0oOo/lean-lsp-mcp),
  [lean4-theorem-proving-skill](https://github.com/cameronfreer/lean4-theorem-proving-skill)
