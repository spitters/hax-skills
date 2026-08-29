# hax-treesitter

Syntax-level pre-check for hax-compatible Rust, implemented as tree-sitter
queries over the Rust grammar. It runs before `cargo hax json` (the hax
frontend, which is the authoritative check) and reports constructs that the
hax frontend rejects or that make functions partial.

## What it checks

| Category | Examples | Severity |
|----------|----------|----------|
| Unsafe code | `unsafe {}` | Error |
| Raw pointers | `*const T`, `*mut T` | Error |
| Trait objects | `dyn Trait`, `Box<dyn T>` | Error |
| Heap allocation | `Vec`, `Box`, `String`, `Rc`, `Arc`, `HashMap`, `HashSet`, `vec!`, `format!` | Error |
| Unbounded loops | `loop {}`, `while cond {}` | Error |
| Async/await | `.await` | Error |
| Interior mutability | `Cell`, `RefCell`, `Mutex`, `RwLock` | Error |
| Global mutable state | `static mut` | Error |
| Unions, FFI | `union`, `extern "C" {}` | Error |
| Atomics | `AtomicU32`, ... | Error |
| Floating point | `f32`, `f64` | Warning |
| Panicking | `panic!`, `todo!`, `unimplemented!`, `unreachable!`, `.unwrap()`, `.expect()` | Warning |
| I/O | `println!`, `print!`, `dbg!` | Warning |

The full list is `hax_treesitter/queries/hax-lint.scm`; `tests/violations.rs`
exercises every pattern and `tests/test_lint.py` pins the reported categories.

Findings inside `#[cfg(test)]` modules and `#[test]` functions are suppressed
by default, since hax does not extract test code. Pass `--include-tests` to
report them.

## Installation

```bash
pip install "git+https://github.com/spitters/hax-skills#subdirectory=hax-treesitter"
```

This installs the `hax-lint` and `hax-mcp-server` console scripts. Python
3.10 or later, `tree-sitter >= 0.25` and `tree-sitter-rust >= 0.23` are
required. For the MCP server add the `mcp` extra:

```bash
pip install "hax-treesitter[mcp] @ git+https://github.com/spitters/hax-skills#subdirectory=hax-treesitter"
```

## Usage

```bash
hax-lint src/lib.rs               # human-readable report; exit 1 on any error
hax-lint --errors-only src/*.rs   # warnings suppressed (CI setting)
hax-lint --json src/lib.rs        # machine-readable
hax-lint --summary src/lib.rs     # counts by category
hax-lint --include-tests src/lib.rs
hax-lint --query my-queries.scm src/lib.rs
```

The exit code is 1 when at least one error is reported, otherwise 0.
Warnings do not affect the exit code.

From Python:

```python
from hax_treesitter.lint import HaxLinter

for v in HaxLinter().lint_file(Path("src/lib.rs")):
    print(v.line, v.severity, v.category, v.message)
```

## MCP server

`hax-mcp-server` (module `hax_treesitter.mcp_server`) exposes four tools over
stdio:

- `hax_syntax_check(file_path | source, errors_only, include_tests)`: this pre-check.
- `hax_frontend_check(crate_path, package)`: runs `cargo hax json`, the full
  hax frontend without a backend.
- `hax_extract(crate_path, backend, output_dir, modules)`: runs
  `cargo hax into <backend>`; backends are `lean`, `lean-refines`, `fstar`,
  `coq`, `ssprove`, `easycrypt`, `proverif`.
- `hax_supported_features(category)`: a summary of supported and
  unsupported Rust features.

Registration with Claude Code:

```bash
claude mcp add hax-tools hax-mcp-server
```

`cargo hax` is installed from https://github.com/cryspen/hax
(`git clone https://github.com/cryspen/hax && cd hax && ./setup.sh`, or the
Nix profile described in that README).

## Query structure

Queries use tree-sitter's S-expression pattern matching:

```scheme
;; Capture unsafe blocks as errors
(unsafe_block) @error.unsafe_block

;; Capture specific type identifiers
((type_identifier) @error.heap_vec
  (#eq? @error.heap_vec "Vec"))

;; Capture macro invocations by name
((macro_invocation
  macro: (identifier) @error.vec_macro)
  (#eq? @error.vec_macro "vec"))
```

Capture names determine severity: `@error.*` is reported as an error,
`@warning.*` as a warning. The messages are in `MESSAGES` in
`hax_treesitter/lint.py`.

The query file can also be used directly with the tree-sitter CLI or with an
editor that loads custom queries (Neovim's `nvim-treesitter`, Helix).

## Limitations

The check is purely syntactic. It does not see type information, macro
expansions, feature gates, or other files, so it misses restrictions that
depend on them (trait resolution, termination of `for` loops over
non-range iterators, integer overflow) and it reports a type named `Vec`
regardless of its origin. `cargo hax json` is the check to run before
committing.

## Development

```bash
pip install -e ".[dev]"
python -m pytest tests -q
```

To add a pattern: write the query in `queries/hax-lint.scm`, add a message
for its capture name to `MESSAGES` in `lint.py`, add a case to
`tests/violations.rs`, and update `EXPECTED_CATEGORIES` in
`tests/test_lint.py`.

## License

MIT
