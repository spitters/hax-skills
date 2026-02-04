"""Hax Tree-sitter lint - Fast syntax-level validation for Hax-compatible Rust"""

from pathlib import Path

__version__ = "0.1.0"

# Path to queries directory
QUERIES_DIR = Path(__file__).parent / "queries"
HAX_LINT_QUERY = QUERIES_DIR / "hax-lint.scm"
