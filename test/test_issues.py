"""Tests for reported GitHub issues and other known bugs.

Tests marked `xfail` with `strict=True` document bugs that are still open.  They
start failing as XPASS once the bug is fixed, as a reminder to remove the marker.
"""

import ast
import subprocess
import sys

import pytest

from strip_hints import strip_string_to_string as strip

from test_strip_hints import TEST_DIR


def exec_code(code):
    """Execute `code` and return its namespace dict."""
    namespace = {}
    exec(compile(code, "<stripped>", "exec"), namespace)
    return namespace


@pytest.mark.parametrize("code, expected", [
    ("#", "#"),
    ("x: int = 1", "x      = 1"),
    ("x: int = 1\n# end", "x      = 1\n# end"),
    ("def f(a: int):\n    pass\n# end", "def f(a     ):\n    pass\n# end"),
])
def test_issue_4_no_trailing_newline(code, expected):
    """Code without a final newline is stripped without error."""
    assert strip(code) == expected


@pytest.mark.xfail(strict=True, reason="Issue #14, untokenize restores the whitespace.")
def test_issue_14_to_empty_removes_whitespace():
    """With `to_empty` no whitespace is left where the hints were."""
    code = "def f(a: int, b: str = 'x') -> None: pass\n"
    assert strip(code, to_empty=True) == "def f(a, b = 'x'): pass\n"


@pytest.mark.skipif(sys.version_info < (3, 8), reason="Protocol needs 3.8.")
def test_issue_15_protocol_class_body():
    """A class body containing only declarations stays valid after stripping."""
    code = ("from typing import Protocol\n"
            "class Style(Protocol):\n"
            "    color: str\n"
            "    effect: str\n")
    exec_code(strip(code))


@pytest.mark.skipif(sys.version_info < (3, 7), reason="Dataclasses need 3.7.")
def test_issue_16_dataclass_fields_kept():
    """Dataclass fields still work after stripping with `keep_class_annotations`."""
    code = ("from dataclasses import dataclass\n"
            "@dataclass\n"
            "class Point:\n"
            "    x: int\n"
            "    y: int = 0\n")
    point = exec_code(strip(code, keep_class_annotations=True))["Point"](1, 2)
    assert (point.x, point.y) == (1, 2)


def test_issue_16_namedtuple_fields_kept():
    """Class-syntax `NamedTuple` fields still work after stripping with
    `keep_class_annotations`."""
    code = ("from typing import NamedTuple\n"
            "class Employee(NamedTuple):\n"
            "    name: str\n"
            "    id: int = 3\n")
    employee = exec_code(strip(code, keep_class_annotations=True))["Employee"]("Guido")
    assert (employee.name, employee.id) == ("Guido", 3)


CRLF_CODE = "x: int = 1\r\ndef f(a: int) -> int:\r\n    return a\r\n"
CRLF_STRIPPED = "x      = 1\r\ndef f(a     )       :\r\n    return a\r\n"


def test_issue_20_crlf_preserved_in_string():
    """CRLF line endings are kept by the string interface."""
    assert strip(CRLF_CODE) == CRLF_STRIPPED


def test_issue_20_crlf_preserved_in_outfile(tmp_path):
    """CRLF line endings are kept in a file written by the command line."""
    infile, outfile = tmp_path / "crlf.py", tmp_path / "out.py"
    infile.write_bytes(CRLF_CODE.encode("utf-8"))
    script = TEST_DIR.parent / "bin" / "strip_hints.py"
    subprocess.run([sys.executable, str(script), str(infile), "-o", str(outfile)],
                   check=True)
    assert outfile.read_bytes() == CRLF_STRIPPED.encode("utf-8")


@pytest.mark.skipif(sys.version_info < (3, 11), reason="Starred subscripts need 3.11.")
def test_issue_22_starred_subscript_unchanged():
    """Non-hint syntax such as a starred subscript passes through unchanged."""
    code = "c = m(p[0, :, *b, :], axis=0)\n"
    assert strip(code) == code


@pytest.mark.skipif(sys.version_info < (3, 12), reason="PEP 695 syntax needs 3.12.")
def test_issue_23_pep695_function_hints_stripped():
    """Hints are stripped from a function with a PEP 695 type parameter list."""
    code = "def f[F: Callable[..., Any]](w: F) -> F:\n    return w\n"
    stripped = strip(code)
    ast.parse(stripped)
    assert "w: F" not in stripped and "-> F" not in stripped


@pytest.mark.parametrize("fstring", ['f"{{"', 'f"}}"'])
def test_fstring_escaped_braces_do_not_change_nesting(fstring):
    """Escaped braces in an f-string do not affect stripping of later lines."""
    code = 'a = {0}\nd["k"]: int = 1\n'.format(fstring)
    assert strip(code) == 'a = {0}\nd["k"]      = 1\n'.format(fstring)
