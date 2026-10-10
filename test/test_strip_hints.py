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
    # Newer patch releases of Python's untokenize keep this whitespace, while older
    # ones drop it.  This can be removed once output no longer uses untokenize.
    return re.sub(r"[ \t]+\\(?=\r?\n)", r"\\", code)


def expected_results(case):
    """Return the normalized saved stripped results for the case file `case`."""
    return normalize(read_exact(CASES_DIR / (case + ".results")))


@pytest.mark.parametrize("case", CASES)
def test_strip_file_to_string(case):
    """Stripping a case file gives the saved results."""
    stripped = strip_hints.strip_file_to_string(str(CASES_DIR / case))
    assert normalize(stripped) == expected_results(case)


@pytest.mark.parametrize("case", CASES)
def test_strip_string_to_string(case):
    """Stripping a case file's contents as a string gives the saved results."""
    code = read_exact(CASES_DIR / case)
    assert normalize(strip_hints.strip_string_to_string(code)) == expected_results(case)


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
    assert normalize(proc.stdout.decode("utf-8")) == expected_results(case)


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
        "assert hinted.x == 2 and hinted.f(3) == 3\n")
    env = dict(os.environ, PYTHONPATH=str(SRC_DIR))
    subprocess.run([sys.executable, str(tmp_path / "runner.py")], env=env, check=True)
