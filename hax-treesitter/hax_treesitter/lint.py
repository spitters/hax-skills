#!/usr/bin/env python3
"""
hax_lint.py - Tree-sitter based Hax restriction checker

Usage:
    python hax_lint.py <file.rs>
    python hax_lint.py --json <file.rs>
    python hax_lint.py --summary <file.rs>

Requirements:
    pip install tree-sitter tree-sitter-rust
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Iterator

try:
    import tree_sitter_rust as ts_rust
    from tree_sitter import Language, Parser, Query, QueryCursor
except ImportError:
    print("Error: Required packages not installed.", file=sys.stderr)
    print("Run: pip install tree-sitter tree-sitter-rust", file=sys.stderr)
    sys.exit(1)


@dataclass
class Violation:
    """A single Hax restriction violation."""
    file: str
    line: int
    column: int
    end_line: int
    end_column: int
    category: str
    severity: str  # "error" or "warning"
    code: str  # The violating source code
    message: str

    def to_dict(self) -> dict:
        return {
            "file": self.file,
            "line": self.line,
            "column": self.column,
            "severity": self.severity,
            "category": self.category,
            "code": self.code,
            "message": self.message,
        }


# Messages for each capture type
MESSAGES = {
    # Unsafe
    "error.unsafe_block": "unsafe blocks are not supported in Hax - all code must be safe Rust",
    "error.unsafe_fn": "unsafe functions are not supported in Hax",
    "error.unsafe_trait": "unsafe traits are not supported in Hax",
    "error.unsafe_impl": "unsafe impl blocks are not supported in Hax",

    # Pointers
    "error.raw_pointer": "raw pointers (*const T, *mut T) are not supported - use references or indices",
    "error.ptr_module": "std::ptr operations are not supported in Hax",

    # Trait objects
    "error.dyn_trait": "trait objects (dyn Trait) are not supported - use generics or enums",
    "error.boxed_dyn": "Box<dyn Trait> is not supported - use enum dispatch or generics",

    # Heap allocation
    "error.heap_vec": "Vec<T> is not supported - use fixed-size arrays [T; N] with const generics",
    "error.heap_box": "Box<T> is not supported - use stack allocation or references",
    "error.heap_string": "String is not supported - use &str or [u8; N] for fixed-size strings",
    "error.heap_rc": "Rc<T> is not supported - use indices into arrays for shared ownership patterns",
    "error.heap_arc": "Arc<T> is not supported in Hax",
    "error.heap_cow": "Cow<T> is not supported - use owned or borrowed types directly",
    "error.heap_vecdeque": "VecDeque is not supported - use fixed-size ring buffer with const generics",
    "error.heap_linkedlist": "LinkedList is not supported - use index-based structures in arrays",
    "error.heap_hashmap": "HashMap/HashSet not supported - use fixed-size arrays with linear search",
    "error.heap_btree": "BTreeMap/BTreeSet not supported - use sorted fixed-size arrays",
    "error.heap_binaryheap": "BinaryHeap not supported - use fixed-size array-based heap",

    # Loops
    "error.unbounded_loop": "unbounded 'loop' is not supported - use 'for i in 0..BOUND' with explicit bound",
    "error.while_loop": "while loops are not supported - convert to bounded 'for' loop",
    "error.while_let": "while let is not supported - use bounded iteration or match in a for loop",

    # Async
    "error.async_block": "async blocks are not supported in Hax",
    "error.await_expr": ".await is not supported in Hax",
    "error.async_fn": "async functions are not supported in Hax",

    # Floating point
    "warning.float_f32": "f32 may not be supported depending on Hax backend",
    "warning.float_f64": "f64 may not be supported depending on Hax backend",
    "warning.float_literal": "floating point literals may not extract correctly",

    # Interior mutability
    "error.interior_cell": "Cell<T> (interior mutability) is not supported - use explicit state passing",
    "error.interior_refcell": "RefCell<T> is not supported - use explicit mutable references",
    "error.interior_unsafecell": "UnsafeCell<T> is not supported in Hax",
    "error.interior_mutex": "Mutex<T> is not supported - Hax code should be single-threaded and pure",
    "error.interior_rwlock": "RwLock<T> is not supported in Hax",
    "error.interior_once": "OnceCell/OnceLock are not supported - use const initialization",
    "error.interior_lazy": "LazyCell/LazyLock are not supported in Hax",

    # Global state
    "error.static_mut": "static mut is not supported - Hax code must be pure",
    "error.lazy_static": "lazy_static! is not supported - use const or pass state explicitly",
    "error.thread_local": "thread_local! is not supported in Hax",

    # Assembly
    "error.asm": "asm! (inline assembly) is not supported - use pure Rust",
    "error.global_asm": "global_asm! is not supported in Hax",

    # Union
    "error.union": "union types are not supported - use enum with explicit variants",

    # FFI
    "error.extern_block": "extern blocks (FFI) are not supported - implement in pure Rust",
    "error.extern_fn": "extern functions are not supported in Hax extraction",
    "error.no_mangle": "#[no_mangle] suggests FFI usage which is not supported",

    # Panicking
    "warning.panic": "panic! makes functions partial - consider returning Result or Option",
    "warning.todo": "todo! will panic at runtime - implement before extraction",
    "warning.unimplemented": "unimplemented! will panic - provide implementation",
    "warning.unreachable": "unreachable! may need proof of unreachability",
    "warning.unwrap": ".unwrap() can panic - consider pattern matching",
    "warning.expect": ".expect() can panic - consider pattern matching",

    # Dynamic
    "error.any_type": "std::any (runtime type information) is not supported",
    "error.typeid": "TypeId (runtime type identification) is not supported",

    # Traits
    "warning.drop_impl": "Drop implementations may not extract correctly",
    "warning.deref_impl": "Deref/DerefMut may cause extraction issues",

    # I/O
    "error.io_module": "std::io operations are not supported - Hax code must be pure",
    "error.fs_module": "std::fs operations are not supported - Hax code must be pure",
    "error.net_module": "std::net operations are not supported in Hax",
    "warning.print_macro": "print macros have I/O side effects - remove before extraction",
    "warning.dbg": "dbg! has I/O side effects - remove before extraction",

    # Threading
    "error.thread_module": "std::thread is not supported - Hax extraction is single-threaded",
    "error.sync_module": "std::sync primitives are not supported in Hax",
    "error.atomic": "Atomic types are not supported - Hax code is single-threaded",

    # Allocation functions
    "error.box_new": "Box::new() allocates on heap - use stack allocation",
    "error.vec_new": "Vec construction not supported - use fixed-size arrays",
    "error.vec_macro": "vec! macro not supported - use array literals [a, b, c]",
    "error.string_new": "String construction not supported - use &str or [u8; N]",
    "error.format_macro": "format! macro allocates String - not supported",

    # Other
    "warning.impl_trait_return": "impl Trait return types may have extraction issues",
    "warning.capturing_closure": "closures capturing variables may have extraction issues",
    "warning.division": "division can panic on zero - consider checked_div",
    "warning.modulo": "modulo can panic on zero - consider checked_rem",
    "warning.indexing": "indexing can panic - consider .get() or ensure bounds",
}


class HaxLinter:
    """Tree-sitter based Hax restriction linter."""

    def __init__(self, query_path: Path | None = None):
        self.language = Language(ts_rust.language())
        self.parser = Parser(self.language)

        # Load query from file or use default location
        if query_path is None:
            query_path = Path(__file__).parent / "queries" / "hax-lint.scm"

        if not query_path.exists():
            raise FileNotFoundError(f"Query file not found: {query_path}")

        query_text = query_path.read_text()
        self.query = Query(self.language, query_text)

    def _process_captures(self, tree, filename: str) -> Iterator[Violation]:
        """Process query captures and yield violations."""
        cursor = QueryCursor(self.query)
        matches = cursor.matches(tree.root_node)

        for _pattern_index, captures_dict in matches:
            for capture_name, nodes in captures_dict.items():
                # Skip internal captures (those starting with _)
                if capture_name.startswith("_"):
                    continue

                # Parse severity from capture name
                if capture_name.startswith("error."):
                    severity = "error"
                    category = capture_name[6:]  # Remove "error." prefix
                elif capture_name.startswith("warning."):
                    severity = "warning"
                    category = capture_name[8:]  # Remove "warning." prefix
                else:
                    continue  # Skip non-diagnostic captures

                # Get message
                message = MESSAGES.get(capture_name, f"Hax restriction: {category}")

                for node in nodes:
                    # Get source code snippet
                    try:
                        code = node.text.decode("utf-8")
                        # Truncate long code snippets
                        if len(code) > 60:
                            code = code[:57] + "..."
                    except:
                        code = "<unable to decode>"

                    yield Violation(
                        file=filename,
                        line=node.start_point[0] + 1,
                        column=node.start_point[1] + 1,
                        end_line=node.end_point[0] + 1,
                        end_column=node.end_point[1] + 1,
                        category=category,
                        severity=severity,
                        code=code,
                        message=message,
                    )

    def lint_file(self, file_path: Path) -> Iterator[Violation]:
        """Lint a single Rust file and yield violations."""
        source = file_path.read_bytes()
        tree = self.parser.parse(source)
        yield from self._process_captures(tree, str(file_path))

    def lint_string(self, source: str, filename: str = "<string>") -> Iterator[Violation]:
        """Lint a string of Rust source code."""
        tree = self.parser.parse(source.encode("utf-8"))
        yield from self._process_captures(tree, filename)


def format_violation(v: Violation, color: bool = True) -> str:
    """Format a violation for terminal output."""
    if color:
        if v.severity == "error":
            severity_str = "\033[91merror\033[0m"
        else:
            severity_str = "\033[93mwarning\033[0m"
        location = f"\033[1m{v.file}:{v.line}:{v.column}\033[0m"
    else:
        severity_str = v.severity
        location = f"{v.file}:{v.line}:{v.column}"

    return f"{location}: {severity_str}[{v.category}]: {v.message}\n    --> {v.code}"


def main():
    parser = argparse.ArgumentParser(
        description="Check Rust files for Hax restriction violations"
    )
    parser.add_argument("files", nargs="+", type=Path, help="Rust files to check")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--summary", action="store_true", help="Show summary only")
    parser.add_argument("--no-color", action="store_true", help="Disable colored output")
    parser.add_argument("--errors-only", action="store_true", help="Show only errors, not warnings")
    parser.add_argument("--query", type=Path, help="Path to custom query file")

    args = parser.parse_args()

    try:
        linter = HaxLinter(args.query)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    all_violations = []

    for file_path in args.files:
        if not file_path.exists():
            print(f"Warning: File not found: {file_path}", file=sys.stderr)
            continue

        violations = list(linter.lint_file(file_path))

        if args.errors_only:
            violations = [v for v in violations if v.severity == "error"]

        all_violations.extend(violations)

    if args.json:
        print(json.dumps([v.to_dict() for v in all_violations], indent=2))
    elif args.summary:
        errors = sum(1 for v in all_violations if v.severity == "error")
        warnings = sum(1 for v in all_violations if v.severity == "warning")
        print(f"Found {errors} errors and {warnings} warnings in {len(args.files)} file(s)")

        # Category breakdown
        from collections import Counter
        categories = Counter(v.category for v in all_violations)
        if categories:
            print("\nBy category:")
            for cat, count in categories.most_common():
                print(f"  {cat}: {count}")
    else:
        for v in all_violations:
            print(format_violation(v, color=not args.no_color))
            print()

    # Exit with error code if there are errors
    errors = sum(1 for v in all_violations if v.severity == "error")
    sys.exit(1 if errors > 0 else 0)


if __name__ == "__main__":
    main()
