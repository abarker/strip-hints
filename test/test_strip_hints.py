"""Tests comparing stripped case files in `cases` against their saved results."""

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

import strip_hints

TEST_DIR = Path(__file__).resolve().parent
CASES_DIR = TEST_DIR / "cases"
SRC_DIR = TEST_DIR.parent / "src"
CASES = sorted(p.name for p in CASES_DIR.glob("*.py"))


def read_exact(path):
    """Read a UTF-8 file without any newline translation."""
    return path.read_bytes().decode("utf-8")


def normalize(code):
    """Remove whitespace before line-continuation backslashes in `code`."""
    # Python's untokenize, used by the legacy output, keeps or drops this whitespace
    # depending on the Python version.
    return re.sub(r"[ \t]+\\(?=\r?\n)", r"\\", code)


def expected_results(case):
    """Return the saved stripped results for the case file `case`."""
    return read_exact(CASES_DIR / (case + ".results"))


@pytest.mark.parametrize("case", CASES)
def test_strip_file_to_string(case):
    """Stripping a case file gives the saved results."""
    assert strip_hints.strip_file_to_string(str(CASES_DIR / case)) == expected_results(case)


@pytest.mark.parametrize("case", CASES)
def test_strip_string_to_string(case):
    """Stripping a case file's contents as a string gives the saved results."""
    code = read_exact(CASES_DIR / case)
    assert strip_hints.strip_string_to_string(code) == expected_results(case)


@pytest.mark.parametrize("case", CASES)
def test_legacy_output(case):
    """The legacy output matches the saved results, apart from the whitespace before
    line continuations."""
    stripped = strip_hints.strip_file_to_string(str(CASES_DIR / case), legacy_output=True)
    assert normalize(stripped) == normalize(expected_results(case))


@pytest.mark.parametrize("case", CASES)
def test_line_count_preserved(case):
    """Stripping in the default mode keeps the number of lines the same."""
    code = read_exact(CASES_DIR / case)
    assert len(strip_hints.strip_string_to_string(code).splitlines()) == len(code.splitlines())


@pytest.mark.parametrize("case", CASES)
def test_command_line(case):
    """The command-line script prints the saved results to stdout."""
    script = TEST_DIR.parent / "bin" / "strip_hints.py"
    proc = subprocess.run([sys.executable, str(script), str(CASES_DIR / case)],
                          stdout=subprocess.PIPE, check=True)
    assert proc.stdout.decode("utf-8") == expected_results(case)


def test_strip_on_import(tmp_path):
    """Modules imported after `strip_on_import` is called have their hints stripped."""
    # The undefined names in the hints raise `NameError` unless they are stripped.
    (tmp_path / "hinted.py").write_text(
        "x: Undefined = 2\n"
        "def f(a: Undefined) -> Undefined:\n"
        "    return a\n")
    (tmp_path / "runner.py").write_text(
        "import strip_hints\n"
        "strip_hints.strip_on_import(__file__, py3_also=True)\n"
        "import hinted\n"
        "assert hinted.x == 2 and hinted.f(3) == 3\n"
        "import ctypes\n")  # Extension modules must still import after the hook.
    env = dict(os.environ, PYTHONPATH=str(SRC_DIR))
    proc = subprocess.run([sys.executable, str(tmp_path / "runner.py")], env=env,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert proc.returncode == 0, proc.stderr.decode()
