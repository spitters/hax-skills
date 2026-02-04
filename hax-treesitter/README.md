# Hax Tree-sitter Lint

Fast, syntax-level validation of Hax-compatible Rust code using tree-sitter queries.

## Purpose

Provides instant feedback on Hax restriction violations **before** running `cargo hax check`. Catches ~80% of common issues at the syntax level with sub-100ms latency.

## What It Catches

| Category | Examples | Severity |
|----------|----------|----------|
| Unsafe code | `unsafe {}`, `unsafe fn`, `unsafe impl` | Error |
| Raw pointers | `*const T`, `*mut T` | Error |
| Trait objects | `dyn Trait`, `Box<dyn T>` | Error |
| Heap allocation | `Vec`, `Box`, `String`, `HashMap` | Error |
| Unbounded loops | `loop {}`, `while cond {}` | Error |
| Async/await | `async {}`, `.await` | Error |
| Interior mutability | `Cell`, `RefCell`, `Mutex` | Error |
| FFI | `extern "C"`, `#[no_mangle]` | Error |
| Floating point | `f32`, `f64` | Warning |
| Panicking | `panic!`, `.unwrap()`, `.expect()` | Warning |
| I/O operations | `println!`, `std::io`, `std::fs` | Warning |

## Installation

### Requirements

- tree-sitter CLI or library bindings
- tree-sitter-rust grammar

### Using tree-sitter CLI

```bash
# Install tree-sitter CLI
cargo install tree-sitter-cli

# Clone tree-sitter-rust (if not already available)
git clone https://github.com/tree-sitter/tree-sitter-rust

# Run queries
tree-sitter query hax-lint.scm path/to/file.rs --captures
```

### Using Python bindings

```bash
pip install tree-sitter tree-sitter-rust
```

```python
import tree_sitter_rust as ts_rust
from tree_sitter import Language, Parser, Query

parser = Parser(Language(ts_rust.language()))
query = Query(Language(ts_rust.language()), open("queries/hax-lint.scm").read())

tree = parser.parse(open("example.rs", "rb").read())
captures = query.captures(tree.root_node)

for node, name in captures:
    print(f"{name}: line {node.start_point[0]+1}: {node.text.decode()}")
```

## Editor Integration

### Neovim (nvim-treesitter)

Copy `queries/hax-lint.scm` to your Neovim queries directory and configure highlights:

```lua
-- In after/queries/rust/highlights.scm or via setup
vim.treesitter.query.set("rust", "hax-lint", [[
  ;; ... contents of hax-lint.scm
]])
```

### Helix

Add queries to `~/.config/helix/runtime/queries/rust/`.

### VSCode

Use a tree-sitter extension that supports custom queries, or integrate via MCP.

## MCP Integration

See `mcp/` directory for Model Context Protocol server that exposes:

- `hax_syntax_check(file_path)` - Returns list of violations
- `hax_quick_fix(file_path, line)` - Suggests fixes for violations

## Query Structure

Queries use tree-sitter's S-expression pattern matching:

```scheme
;; Capture unsafe blocks as errors
(unsafe_block) @error.unsafe_block

;; Capture specific type identifiers
((type_identifier) @error.heap_vec
  (#eq? @error.heap_vec "Vec"))

;; Capture patterns with predicates
((macro_invocation
  macro: (identifier) @error.vec_macro)
  (#eq? @error.vec_macro "vec"))
```

### Capture Naming Convention

- `@error.*` - Definite Hax extraction failure
- `@warning.*` - Potential issue, verify with `cargo hax`

## Limitations

Tree-sitter is purely syntactic. These require `cargo hax check`:

- Type inference / trait resolution
- Loop termination analysis
- Integer overflow detection
- Feature-gated code
- Macro expansion analysis
- Cross-file analysis

## Relationship to Other Tools

```
┌─────────────────────────────────────────────────────────────┐
│                     Feedback Speed                          │
│                                                             │
│  hax-treesitter    rust-analyzer      cargo hax check       │
│     <100ms            ~1-5s              5-30s              │
│                                                             │
│  ────────────────────────────────────────────────────────►  │
│     Syntax only      + Types          + Full extraction     │
│                                                             │
└─────────────────────────────────────────────────────────────┘

Use all three in combination:
1. hax-treesitter for instant feedback while typing
2. rust-analyzer for type checking and navigation
3. cargo hax check before committing
```

## Contributing

To add new patterns:

1. Identify the Hax restriction
2. Find the corresponding tree-sitter-rust node type
3. Write a query pattern in `queries/hax-lint.scm`
4. Add test cases in `tests/`
5. Document in this README

## License

MIT
