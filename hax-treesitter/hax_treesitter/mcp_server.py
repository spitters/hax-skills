#!/usr/bin/env python3
"""
MCP server exposing the hax tree-sitter pre-check and the cargo-hax frontend.

Tools:
- hax_syntax_check: tree-sitter pre-check for hax restriction violations
- hax_frontend_check: `cargo hax json` (full frontend validation, no backend)
- hax_extract: `cargo hax into <backend>`
- hax_supported_features: summary of supported and unsupported Rust features

Installation (the package provides the `hax-mcp-server` console script):
    pip install "hax-treesitter[mcp] @ git+https://github.com/spitters/hax-skills#subdirectory=hax-treesitter"
    claude mcp add hax-tools hax-mcp-server

Or in .claude/mcp.json:
    {
      "servers": {
        "hax-tools": {
          "command": "python",
          "args": ["-m", "hax_treesitter.mcp_server"]
        }
      }
    }

Requirements:
    pip install mcp tree-sitter tree-sitter-rust
"""
from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
except ImportError:
    print("Error: mcp package not installed. Run: pip install mcp", file=sys.stderr)
    sys.exit(1)

# Import our linter
try:
    from hax_treesitter.lint import HaxLinter, Violation
except ImportError:
    # Fallback for direct script execution
    try:
        from .lint import HaxLinter, Violation
    except ImportError:
        print("Error: Could not import HaxLinter", file=sys.stderr)
        sys.exit(1)


# Initialize server
server = Server("hax-tools")

# Backends accepted by `cargo hax into`. `lean-refines` is provided by the
# cryspen/hax fork used by hax-lean.
HAX_BACKENDS = ["lean", "lean-refines", "fstar", "coq", "ssprove", "easycrypt", "proverif"]

# `cargo hax into` subcommand per backend name.
_BACKEND_SUBCOMMAND = {b: b for b in HAX_BACKENDS}
_BACKEND_SUBCOMMAND["proverif"] = "pro-verif"

INSTALL_HINT = (
    "Error: 'cargo hax' not found. Install per https://github.com/cryspen/hax: "
    "git clone https://github.com/cryspen/hax && cd hax && ./setup.sh"
)

# Initialize linter (lazy)
_linter: HaxLinter | None = None


def get_linter() -> HaxLinter:
    global _linter
    if _linter is None:
        query_path = Path(__file__).parent / "queries" / "hax-lint.scm"
        _linter = HaxLinter(query_path)
    return _linter


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available Hax tools."""
    return [
        Tool(
            name="hax_syntax_check",
            description="Syntax-level check for hax restriction violations using tree-sitter. "
                        "Run before hax_frontend_check; findings in #[cfg(test)] modules and "
                        "#[test] functions are suppressed unless include_tests is set.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to Rust file to check"
                    },
                    "source": {
                        "type": "string",
                        "description": "Rust source code to check (alternative to file_path)"
                    },
                    "errors_only": {
                        "type": "boolean",
                        "description": "If true, only return errors, not warnings",
                        "default": False
                    },
                    "include_tests": {
                        "type": "boolean",
                        "description": "Also report findings inside test-only code",
                        "default": False
                    }
                },
            },
        ),
        Tool(
            name="hax_frontend_check",
            description="Run 'cargo hax json' for full frontend validation of a crate "
                        "(the frontend export without any backend). Slower than "
                        "hax_syntax_check; reports what the frontend rejects.",
            inputSchema={
                "type": "object",
                "properties": {
                    "crate_path": {
                        "type": "string",
                        "description": "Path to crate directory (containing Cargo.toml)"
                    },
                    "package": {
                        "type": "string",
                        "description": "Specific package to check in workspace"
                    }
                },
            },
        ),
        Tool(
            name="hax_extract",
            description="Extract Rust code with 'cargo hax into <backend>'. "
                        "Run hax_syntax_check and hax_frontend_check first.",
            inputSchema={
                "type": "object",
                "properties": {
                    "crate_path": {
                        "type": "string",
                        "description": "Path to crate directory"
                    },
                    "backend": {
                        "type": "string",
                        "enum": HAX_BACKENDS,
                        "description": "hax backend name"
                    },
                    "output_dir": {
                        "type": "string",
                        "description": "Output directory for extracted files"
                    },
                    "modules": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Item patterns to extract with their dependencies "
                                       "(passed as `-i '+pat ...'`; optional)"
                    }
                },
                "required": ["backend"]
            },
        ),
        Tool(
            name="hax_supported_features",
            description="Get documentation of Hax-supported Rust features and restrictions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": ["types", "control_flow", "allocation", "traits", "all"],
                        "description": "Feature category to query",
                        "default": "all"
                    }
                },
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""

    if name == "hax_syntax_check":
        return await handle_syntax_check(arguments)
    elif name == "hax_frontend_check":
        return await handle_frontend_check(arguments)
    elif name == "hax_extract":
        return await handle_extract(arguments)
    elif name == "hax_supported_features":
        return await handle_supported_features(arguments)
    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def handle_syntax_check(args: dict[str, Any]) -> list[TextContent]:
    """Fast tree-sitter based syntax check."""
    linter = get_linter()

    file_path = args.get("file_path")
    source = args.get("source")
    errors_only = args.get("errors_only", False)
    linter.include_tests = bool(args.get("include_tests", False))

    if file_path:
        path = Path(file_path)
        if not path.exists():
            return [TextContent(type="text", text=f"Error: File not found: {file_path}")]
        violations = list(linter.lint_file(path))
    elif source:
        violations = list(linter.lint_string(source))
    else:
        return [TextContent(type="text", text="Error: Provide either file_path or source")]

    if errors_only:
        violations = [v for v in violations if v.severity == "error"]

    if not violations:
        return [TextContent(type="text", text="No Hax restriction violations found.")]

    # Format output
    result = {
        "total": len(violations),
        "errors": sum(1 for v in violations if v.severity == "error"),
        "warnings": sum(1 for v in violations if v.severity == "warning"),
        "violations": [v.to_dict() for v in violations]
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_frontend_check(args: dict[str, Any]) -> list[TextContent]:
    """Run `cargo hax json`: the full frontend without a backend."""
    crate_path = args.get("crate_path", ".")
    package = args.get("package")

    cmd = ["cargo", "hax"]
    if package:
        cmd.extend(["-C", "-p", package, ";"])
    cmd.append("json")

    try:
        result = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=crate_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await result.communicate()

        output = {
            "success": result.returncode == 0,
            "return_code": result.returncode,
            "stdout": stdout.decode("utf-8"),
            "stderr": stderr.decode("utf-8"),
        }

        return [TextContent(type="text", text=json.dumps(output, indent=2))]

    except FileNotFoundError:
        return [TextContent(type="text", text=INSTALL_HINT)]
    except Exception as e:
        return [TextContent(type="text", text=f"Error running cargo hax: {e}")]


async def handle_extract(args: dict[str, Any]) -> list[TextContent]:
    """Extract to proof backend."""
    crate_path = args.get("crate_path", ".")
    backend = args["backend"]
    output_dir = args.get("output_dir")
    modules = args.get("modules", [])

    if backend not in HAX_BACKENDS:
        return [TextContent(
            type="text",
            text=f"Error: unknown backend '{backend}'. Known backends: {', '.join(HAX_BACKENDS)}",
        )]

    # Options of `into` precede the backend subcommand.
    cmd = ["cargo", "hax", "into"]

    if output_dir:
        cmd.extend(["--output-dir", output_dir])

    if modules:
        cmd.extend(["-i", " ".join(f"+{m}" for m in modules)])

    cmd.append(_BACKEND_SUBCOMMAND[backend])

    try:
        result = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=crate_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await result.communicate()

        output = {
            "success": result.returncode == 0,
            "backend": backend,
            "return_code": result.returncode,
            "stdout": stdout.decode("utf-8"),
            "stderr": stderr.decode("utf-8"),
        }

        return [TextContent(type="text", text=json.dumps(output, indent=2))]

    except FileNotFoundError:
        return [TextContent(type="text", text=INSTALL_HINT)]
    except Exception as e:
        return [TextContent(type="text", text=f"Error running extraction: {e}")]


async def handle_supported_features(args: dict[str, Any]) -> list[TextContent]:
    """Return Hax feature documentation."""
    category = args.get("category", "all")

    features = {
        "types": {
            "supported": [
                "Primitive types: bool, u8-u128, i8-i128, usize, isize",
                "Arrays: [T; N] with const generic N",
                "Tuples: (T1, T2, ...)",
                "References: &T, &mut T",
                "Slices: &[T], &mut [T] (with known bounds)",
                "Structs and enums",
                "Option<T>, Result<T, E>",
            ],
            "not_supported": [
                "Vec<T>, Box<T>, String (heap allocation)",
                "Rc<T>, Arc<T> (reference counting)",
                "HashMap, HashSet, BTreeMap, etc.",
                "Raw pointers: *const T, *mut T",
                "Trait objects: dyn Trait",
                "f32, f64 (backend dependent)",
            ]
        },
        "control_flow": {
            "supported": [
                "if/else expressions",
                "match expressions",
                "for i in 0..N loops (bounded)",
                "for item in array.iter() (bounded)",
                "Early return",
            ],
            "not_supported": [
                "loop {} (unbounded)",
                "while condition {} (unbounded)",
                "while let (unbounded)",
                "async/await",
                "Recursion (backend dependent)",
            ]
        },
        "allocation": {
            "supported": [
                "Stack allocation only",
                "Const generics for array sizes",
                "Static constants (immutable)",
            ],
            "not_supported": [
                "Box::new(), Vec::new()",
                "String::new(), format!()",
                "Any heap allocation",
                "static mut (mutable globals)",
            ]
        },
        "traits": {
            "supported": [
                "Trait definitions and implementations",
                "Generic bounds: T: Trait",
                "Associated types",
                "Derive macros (some)",
            ],
            "not_supported": [
                "Trait objects: dyn Trait",
                "impl Trait in argument position (sometimes)",
                "Drop (backend dependent)",
                "Deref/DerefMut (may cause issues)",
            ]
        },
    }

    if category == "all":
        result = features
    elif category in features:
        result = {category: features[category]}
    else:
        return [TextContent(type="text", text=f"Unknown category: {category}")]

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
