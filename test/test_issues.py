"""Tests for reported GitHub issues and other known bugs.

Tests marked `xfail` with `strict=True` document bugs that are still open.  They
start failing as XPASS once the bug is fixed, as a reminder to remove the marker.
"""

import ast
import subprocess
import sys

import pytest

from strip_hints import strip_string_to_string as strip, strip_file_to_string

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


def cli_output_bytes(tmp_path, code_bytes, to_outfile):
    """Run the command line on a file containing `code_bytes` and return the
    output bytes, written to stdout or to an output file."""
    infile, outfile = tmp_path / "code.py", tmp_path / "out.py"
    infile.write_bytes(code_bytes)
    script = TEST_DIR.parent / "bin" / "strip_hints.py"
    args = [sys.executable, str(script), str(infile)]
    args += ["-o", str(outfile)] if to_outfile else []
    proc = subprocess.run(args, check=True, stdout=subprocess.PIPE)
    return outfile.read_bytes() if to_outfile else proc.stdout


@pytest.mark.parametrize("to_outfile", [False, True])
def test_issue_20_crlf_preserved_by_command_line(tmp_path, to_outfile):
    """CRLF line endings are kept by the command line, on stdout and in a file."""
    output = cli_output_bytes(tmp_path, CRLF_CODE.encode("utf-8"), to_outfile)
    assert output == CRLF_STRIPPED.encode("utf-8")


LATIN1_CODE = '# -*- coding: latin-1 -*-\nx: int = 1\ns = "caf\xe9"\n'
LATIN1_STRIPPED = '# -*- coding: latin-1 -*-\nx      = 1\ns = "caf\xe9"\n'


def test_declared_encoding_used_for_file(tmp_path):
    """A file is decoded with the encoding in its coding comment."""
    infile = tmp_path / "code.py"
    infile.write_bytes(LATIN1_CODE.encode("latin-1"))
    assert strip_file_to_string(str(infile)) == LATIN1_STRIPPED


def test_declared_encoding_ignored_for_string():
    """A string is not decoded again using the encoding in its coding comment."""
    assert strip(LATIN1_CODE) == LATIN1_STRIPPED


@pytest.mark.parametrize("to_outfile", [False, True])
@pytest.mark.parametrize("code_bytes, expected", [
    (LATIN1_CODE.encode("latin-1"), LATIN1_STRIPPED.encode("latin-1")),
    ('x: int = 1\ns = "caf\xe9"\n'.encode("utf-8-sig"),
     'x      = 1\ns = "caf\xe9"\n'.encode("utf-8-sig")),
])
def test_encoding_preserved_by_command_line(tmp_path, to_outfile, code_bytes, expected):
    """The command line writes the output in the encoding of the code file,
    including a UTF-8 byte order mark."""
    assert cli_output_bytes(tmp_path, code_bytes, to_outfile) == expected


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


@pytest.mark.parametrize("code", [
    'def f(a: int) -> str:\n    return f"{a}\\n{{literal}}"\n',
    'def f(a: int) -> str:\n    return f"\\n{{{a}}}"\n',
])
def test_fstring_escaped_braces_after_escape_unchanged(code):
    """F-strings with escaped braces after a backslash escape are copied unchanged.
    Python's untokenize, used by 0.1.13 and the legacy output, breaks them on some
    Python 3.12 patch releases."""
    assert strip(code).splitlines()[1] == code.splitlines()[1]


@pytest.mark.parametrize("code, expected", [
    ('def w(self, g: str = f"x ({v})"\n):\n    pass\n',
     'def w(self, g      = f"x ({v})"\n):\n    pass\n'),
    ('x = f"{a}def"\ny: int = 1\n', 'x = f"{a}def"\ny      = 1\n'),
    ('def f(a: int = f"{x},{y}", b: int = 2): pass\n',
     'def f(a      = f"{x},{y}", b      = 2): pass\n'),
    ('d[f"{k}]"]: int = 1\n', 'd[f"{k}]"]      = 1\n'),
])
def test_fstring_text_not_taken_as_operator(code, expected):
    """F-string text that looks like an operator or `def` is not taken as one.
    In Python 3.12 and later such text is a separate token."""
    assert strip(code) == expected


@pytest.mark.parametrize("fstring", ['f"{{"', 'f"}}"'])
def test_fstring_escaped_braces_do_not_change_nesting(fstring):
    """Escaped braces in an f-string do not affect stripping of later lines."""
    code = 'a = {0}\nd["k"]: int = 1\n'.format(fstring)
    assert strip(code) == 'a = {0}\nd["k"]      = 1\n'.format(fstring)
