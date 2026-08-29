# Hax Skills

Claude skill and tooling for writing Rust in the hax subset, extractable to
formal verification backends (F*, Lean 4, Coq/SSProve, EasyCrypt, ProVerif).

## Contents

### Skill (`hax-rust`)

- `SKILL.md` — the skill: frontmatter, quick reference, coding rules, workflow
- `LEAN_INTEGRATION.md` — Lean 4 proof workflow over extracted code
- `references/` — restrictions, repair patterns, code patterns, the
  `lean-refines` backend
- `examples/` — standalone examples (field arithmetic in Rust + Lean)
- `hax-local.md` — per-machine paths and build instructions; gitignored, create
  your own

### Tooling (`hax-treesitter/`)

Tree-sitter linting for feedback before the hax frontend runs:

```bash
pip install -e hax-treesitter/
hax-lint src/*.rs
hax-lint --summary src/
```

The linter is syntax-level; `cargo hax json` is the frontend check and
`cargo hax into <backend>` the full extraction.

## Installation

### Skill

Copy the skill directory into your Claude skills directory or reference it
directly.

### Tree-sitter linter

```bash
cd hax-treesitter
pip install -e .
```

This installs the `hax-lint` and `hax-mcp-server` scripts.

### MCP server (Claude Code)

```bash
claude mcp add hax-tools hax-mcp-server
# or, without installing the package:
claude mcp add hax-tools python /path/to/hax-skills/hax-treesitter/hax_treesitter/mcp_server.py
```

## Integration with Lean

For proofs over extracted code, install:

- [lean-lsp-mcp](https://github.com/oOo0oOo/lean-lsp-mcp) — Lean 4 language server MCP
- [lean4-theorem-proving-skill](https://github.com/cameronfreer/lean4-theorem-proving-skill) — proof tactics skill

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    PROOF BACKENDS                           │
│  ┌─────────────┐                                           │
│  │ lean-lsp-mcp│  + lean4-theorem-proving skill            │
│  └──────┬──────┘                                           │
├─────────┼───────────────────────────────────────────────────┤
│         │           HAX SKILL                               │
│  ┌──────┴─────────────────────────────────────────────┐    │
│  │  • hax-treesitter (syntax-level lint)              │    │
│  │  • cargo hax json / into (frontend, extraction)    │    │
│  │  • Extraction to Lean 4 and the other backends     │    │
│  └──────┬─────────────────────────────────────────────┘    │
├─────────┼───────────────────────────────────────────────────┤
│         │        RUST ANALYZER LSP                          │
│  ┌──────┴─────────────────────────────────────────────┐    │
│  │  • Code navigation, completion, diagnostics        │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## License

MIT
