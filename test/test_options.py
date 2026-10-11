"""Tests for the stripping options and the command-line interface."""

import subprocess
import sys

import pytest

from strip_hints import (StripHintsException, strip_file_to_string,
                         strip_string_to_string as strip)
from strip_hints.strip_hints_main import HintStripper

from test_strip_hints import TEST_DIR

FUNDEF_RETURN_NL = "def f(a) -> List[\n    int]:\n    pass\n"
ANNASSIGN_NL = "x: List[\n    int] = []\n"
PARAM_NL = "def f(a: List[\n    int]) -> None:\n    pass\n"
FUNDEF_AND_ASSIGN = "def f(a: int) -> int:\n    return a\nx: int = 1\n"
INVALID = "x = 1 +\n" # Tokenizes, but is not valid Python.
TAB_CODE = "x: int = 1\t# A tab before the comment.\n"
TO_EMPTY_CODE = "def f(a: int, b: str = 'x') -> None: pass\nx: int = 1\n"


def run_cli(*args):
    """Run the command-line script with `args` and return the completed process."""
    script = TEST_DIR.parent / "bin" / "strip_hints.py"
    return subprocess.run([sys.executable, str(script)] + [str(a) for a in args],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def test_only_assigns_and_defs():
    """Function signatures are kept but annotated assignments are stripped."""
    expected = "def f(a: int) -> int:\n    return a\nx      = 1\n"
    assert strip(FUNDEF_AND_ASSIGN, only_assigns_and_defs=True) == expected


@pytest.mark.parametrize("code, changes", [("x = 1\n", False), ("x: int = 1\n", True)])
def test_only_test_for_changes(code, changes):
    """Only a boolean telling whether anything would be stripped is returned."""
    assert strip(code, only_test_for_changes=True) is changes


def test_colon_move():
    """The colon moves up to fix a line break in a return hint."""
    assert strip(FUNDEF_RETURN_NL) == "def f(a):         \n        \n    pass\n"


def test_no_colon_move_raises():
    """With colon moving disabled a line break in a return hint raises."""
    with pytest.raises(StripHintsException):
        strip(FUNDEF_RETURN_NL, no_colon_move=True)


def test_equal_move():
    """The assignment moves up to fix a line break in a hint, keeping the line count."""
    assert strip(ANNASSIGN_NL) == "x                = []\n\n"


def test_no_equal_move_raises():
    """With equal moving disabled a line break in an annotation raises."""
    with pytest.raises(StripHintsException):
        strip(ANNASSIGN_NL, no_equal_move=True)


def test_line_break_in_parameter_hint_kept():
    """A line break inside a nested parameter hint is kept by default."""
    assert strip(PARAM_NL) == "def f(a       \n        )        :\n    pass\n"


def test_strip_nl():
    """With `strip_nl` a line break inside a parameter hint is removed."""
    assert strip(PARAM_NL, strip_nl=True) == "def f(a               )        :\n    pass\n"


def test_to_empty():
    """With `to_empty` the hints and the whitespace before them are removed."""
    assert strip(TO_EMPTY_CODE, to_empty=True) == "def f(a, b = 'x'): pass\nx = 1\n"


def test_to_empty_multiline_hints():
    """With `to_empty` the lines inside multiline hints become empty, and the
    line count is kept unless `strip_nl` is also used."""
    code = "def f(a: int,\n      b: List[int] = []) -> Dict[str,\n          int]:\n    pass\n"
    assert strip(code, to_empty=True) == "def f(a,\n      b = []):\n\n    pass\n"
    assert strip(code, to_empty=True, strip_nl=True) == (
            "def f(a,\n      b = []):\n    pass\n")


def test_to_empty_keeps_line_continuation():
    """A backslash line continuation in removed whitespace is kept."""
    code = "def f(a) -> \\\n        int:\n    pass\n"
    assert strip(code, to_empty=True) == "def f(a)\\\n:\n    pass\n"


def test_legacy_output():
    """The legacy output turns tabs between tokens into spaces, and leaves spaces
    with `to_empty`."""
    assert strip(TAB_CODE) == "x      = 1\t# A tab before the comment.\n"
    assert strip(TAB_CODE, legacy_output=True) == "x      = 1 # A tab before the comment.\n"
    assert strip(TO_EMPTY_CODE, to_empty=True, legacy_output=True) == (
            "def f(a , b  = 'x')  : pass\nx  = 1\n")


def test_syntax_error_says_input_cannot_be_parsed(tmp_path):
    """When the input code cannot be parsed either, the error message says so."""
    with pytest.raises(SyntaxError, match="input code also cannot be parsed"):
        strip(INVALID)
    infile = tmp_path / "code.py"
    infile.write_bytes(INVALID.encode("utf-8"))
    with pytest.raises(SyntaxError, match="input code also cannot be parsed"):
        strip_file_to_string(str(infile))


def test_syntax_error_says_probable_bug(monkeypatch):
    """When only the stripped code cannot be parsed, the error message says it is
    probably a bug."""
    monkeypatch.setattr(HintStripper, "strip_type_hints_from_string",
                        lambda self, code: "x = (\n")
    with pytest.raises(SyntaxError, match="probably a bug in strip-hints"):
        strip("x = 1\n")


def test_no_ast():
    """With `no_ast` the output is not checked by parsing it."""
    with pytest.raises(SyntaxError):
        strip(INVALID)
    assert strip(INVALID, no_ast=True) == INVALID


@pytest.mark.parametrize("code, output, exit_code", [
    ("x = 1\n", "False", 1),
    ("x: int = 1\n", "True", 0),
])
def test_cli_only_test_for_changes(tmp_path, code, output, exit_code):
    """The command line prints the change status and sets the exit code."""
    infile = tmp_path / "code.py"
    infile.write_bytes(code.encode("utf-8"))
    proc = run_cli(infile, "--only-test-for-changes")
    assert proc.stdout.decode().strip() == output
    assert proc.returncode == exit_code


def test_cli_outfile(tmp_path):
    """The `--outfile` option writes the result to a file, not stdout."""
    infile, outfile = tmp_path / "code.py", tmp_path / "out.py"
    infile.write_bytes(b"x: int = 1\n")
    proc = run_cli(infile, "--outfile", outfile)
    assert proc.returncode == 0 and proc.stdout == b""
    assert outfile.read_text() == "x      = 1\n"


def test_cli_inplace(tmp_path):
    """The `--inplace` option overwrites the input file."""
    infile = tmp_path / "code.py"
    infile.write_bytes(b"x: int = 1\n")
    assert run_cli(infile, "--inplace").returncode == 0
    assert infile.read_text() == "x      = 1\n"


@pytest.mark.parametrize("flag, code", [
    ("--to-empty", FUNDEF_AND_ASSIGN),
    ("--strip-nl", PARAM_NL),
    ("--only-assigns-and-defs", FUNDEF_AND_ASSIGN),
    ("--no-ast", INVALID),
    ("--legacy-output", TAB_CODE),
])
def test_cli_flags(tmp_path, flag, code):
    """Each flag gives the same output as the matching function argument, and
    differs from the default, so options passed in the wrong order are caught."""
    infile = tmp_path / "code.py"
    infile.write_bytes(code.encode("utf-8"))
    expected = strip(code, **{flag[2:].replace("-", "_"): True})
    proc = run_cli(infile, flag)
    assert proc.returncode == 0, proc.stderr.decode()
    assert proc.stdout.decode() == expected
    assert run_cli(infile).stdout.decode() != expected


@pytest.mark.parametrize("flag, code", [
    ("--no-equal-move", ANNASSIGN_NL),
    ("--no-colon-move", FUNDEF_RETURN_NL),
])
def test_cli_invalid_output_fails(tmp_path, flag, code):
    """Code that cannot be stripped to valid code gives a nonzero exit code."""
    infile = tmp_path / "code.py"
    infile.write_bytes(code.encode("utf-8"))
    assert run_cli(infile).returncode == 0
    proc = run_cli(infile, flag)
    assert proc.returncode != 0
    assert b"StripHintsException" in proc.stderr
