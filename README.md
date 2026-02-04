# Hax Skills

Claude skills and tooling for writing Hax-compatible Rust code that can be extracted to formal verification backends (Lean 4, F*, Coq, ProVerif).

## Contents

### Skill (`hax-rust`)

The main skill for generating Hax-compatible Rust code:

- `SKILL.md` - Main documentation and quick reference
- `LEAN_INTEGRATION.md` - Lean 4 proof workflow
- `references/` - Detailed restrictions, repair patterns, code patterns
- `examples/` - Standalone examples (field arithmetic in Rust + Lean)

### Tooling (`hax-treesitter/`)

Fast tree-sitter based linting for instant feedback:

```bash
# Install
pip install -e hax-treesitter/

# Use
hax-lint src/*.rs
hax-lint --summary src/
```

Catches ~80% of Hax violations in <100ms (vs 5-30s for `cargo hax check`).

## Installation

### Skill

Copy the skill files to your Claude skills directory or reference them directly.

### Tree-sitter Linter

```bash
cd hax-treesitter
pip install -e .
```

### MCP Server (for Claude Code)

```bash
claude mcp add hax-tools python /path/to/hax-skills/hax-treesitter/hax_treesitter/mcp_server.py
```

## Integration with Lean

For extracted code verification, install:

- [lean-lsp-mcp](https://github.com/oOo0oOo/lean-lsp-mcp) - Lean 4 language server MCP
- [lean4-theorem-proving-skill](https://github.com/cameronfreer/lean4-theorem-proving-skill) - Proof tactics skill

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
│  │  • hax-treesitter (instant validation)             │    │
│  │  • cargo hax (full validation)                     │    │
│  │  • Extraction to Lean 4                            │    │
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
