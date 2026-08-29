"""Tests for the hax tree-sitter pre-check."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from hax_treesitter.lint import HaxLinter

TESTS = Path(__file__).parent
VIOLATIONS = TESTS / "violations.rs"

# Categories the query file reports on violations.rs (25 errors, 21 warnings).
EXPECTED_CATEGORIES = {
    "atomic", "dbg", "dyn_trait", "expect", "extern_block", "float_f32",
    "float_f64", "format_macro", "heap_arc", "heap_box", "heap_hashmap",
    "heap_hashset", "heap_rc", "heap_string", "heap_vec", "interior_cell",
    "interior_refcell", "panic", "print", "println", "raw_pointer",
    "static_mut", "todo", "unbounded_loop", "unimplemented", "union",
    "unreachable", "unsafe_block", "unwrap", "vec_macro", "while_loop",
}

CLEAN_SOURCE = """
pub fn add(a: &[u8; 4], b: &[u8; 4]) -> [u8; 4] {
    let mut out = [0u8; 4];
    for i in 0..4 {
        out[i] = a[i].wrapping_add(b[i]);
    }
    out
}
"""

TEST_MODULE_SOURCE = CLEAN_SOURCE + """
#[cfg(test)]
mod tests {
    #[test]
    fn t() {
        let v: Vec<u8> = vec![1];
        let _ = v.first().unwrap();
    }
}

#[test]
fn top_level_test() {
    let _ = Some(1).unwrap();
}
"""


def run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "hax_treesitter.lint", *args],
        capture_output=True, text=True, check=False,
    )


def test_violations_categories():
    found = list(HaxLinter().lint_file(VIOLATIONS))
    assert {v.category for v in found} == EXPECTED_CATEGORIES
    assert sum(v.severity == "error" for v in found) == 25
    assert sum(v.severity == "warning" for v in found) == 21


def test_json_output_parses():
    proc = run_cli("--json", str(VIOLATIONS))
    assert proc.returncode == 1  # errors present
    data = json.loads(proc.stdout)
    assert {v["category"] for v in data} == EXPECTED_CATEGORIES
    assert all({"file", "line", "column", "severity", "category", "code", "message"} <= v.keys() for v in data)


def test_clean_source_has_no_findings():
    assert list(HaxLinter().lint_string(CLEAN_SOURCE)) == []


def test_clean_file_exit_code(tmp_path):
    f = tmp_path / "clean.rs"
    f.write_text(CLEAN_SOURCE)
    proc = run_cli("--json", str(f))
    assert proc.returncode == 0
    assert json.loads(proc.stdout) == []


def test_test_code_suppressed_by_default():
    assert list(HaxLinter().lint_string(TEST_MODULE_SOURCE)) == []
    with_tests = list(HaxLinter(include_tests=True).lint_string(TEST_MODULE_SOURCE))
    assert {v.category for v in with_tests} == {"heap_vec", "vec_macro", "unwrap"}
    assert sum(v.category == "unwrap" for v in with_tests) == 2


def test_include_tests_flag(tmp_path):
    f = tmp_path / "t.rs"
    f.write_text(TEST_MODULE_SOURCE)
    assert json.loads(run_cli("--json", str(f)).stdout) == []
    assert len(json.loads(run_cli("--json", "--include-tests", str(f)).stdout)) == 4
