"""Tests of stripping on various forms of Python syntax."""

import sys

import pytest

from strip_hints import strip_string_to_string as strip


PY38 = pytest.mark.skipif(sys.version_info < (3, 8), reason="Syntax needs 3.8.")


@pytest.mark.parametrize("code, expected", [
    # Function definitions.
    pytest.param("def f(a: int, /, b: int, *, c: int = 1, **kw: str) -> int: pass\n",
                 "def f(a     , /, b     , *, c      = 1, **kw     )       : pass\n",
                 marks=PY38),
    ("async def f(a: int) -> int:\n    return a\n",
     "async def f(a     )       :\n    return a\n"),
    ("def f(cb: Callable = lambda a, b: a, z: int = 2): pass\n",
     "def f(cb           = lambda a, b: a, z      = 2): pass\n"),
    ("def f(a: str = f\"{x:>2}\") -> None: pass\n",
     "def f(a      = f\"{x:>2}\")        : pass\n"),
    ("class A:\n    def m(self, x: 'A') -> 'A': ...\n",
     "class A:\n    def m(self, x     )       : ...\n"),
    # Annotated assignments and declarations.
    pytest.param("x: int = (y := 3)\n", "x      = (y := 3)\n", marks=PY38),
    ("x: str = f\"{b:>3} {c!r:{w}}\"\n", "x      = f\"{b:>3} {c!r:{w}}\"\n"),
    ("c.x: int = 0\n", "c.x      = 0\n"),
    ("d[1, 2]: int = 3\n", "d[1, 2]      = 3\n"),
    ("x: int\n", "pass #x: int\n"),
    ("x: int = 1; y: str = 'a'\n", "x      = 1; y      = 'a'\n"),
    ("try:\n    x: int = 1\nexcept E:\n    pass\n",
     "try:\n    x      = 1\nexcept E:\n    pass\n"),
    # Code without hints is unchanged.
    ("d = {'a': 1}\nf = lambda x: x\nx = y[1:2]\n",
     "d = {'a': 1}\nf = lambda x: x\nx = y[1:2]\n"),
])
def test_syntax(code, expected):
    """The code is stripped to the expected result."""
    assert strip(code) == expected


@pytest.mark.skipif(sys.version_info < (3, 10), reason="Match statements need 3.10.")
def test_match_statement_unchanged():
    """A match statement, whose soft keywords look like names, is unchanged."""
    code = ("match x:\n"
            "    case Point(x=0):\n"
            "        pass\n"
            "    case y:\n"
            "        pass\n")
    assert strip(code) == code
