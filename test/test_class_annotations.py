"""Tests for the `--keep-class-annotations` option."""

import subprocess
import sys

import pytest

from strip_hints import strip_string_to_string as strip
from strip_hints.token_list import TokenList
from strip_hints.strip_hints_main import (logical_lines_split_types,
                                          logical_lines_split_values)
from strip_hints.class_annotations import (ClassMatcher, significant_tokens, resolve,
                                           name_matches, class_bases, parse_keep_names,
                                           STANDARD_NAMES)

from test_issues import exec_code
from test_strip_hints import TEST_DIR


def logical_lines(code):
    """Split `code` into logical lines the same way as the stripper does."""
    tokens = TokenList(code_string=code, compat_mode=False)
    return tokens.split(token_types=logical_lines_split_types,
                        token_values=logical_lines_split_values,
                        isolated_separators=True, no_empty=True)


def first_line_tokens(code):
    """Return the significant tokens of the first statement in `code`."""
    return significant_tokens(logical_lines(code)[1])


#
# The matching functions.
#

@pytest.mark.parametrize("code, expected", [
    ("import a.b", {"a": {"a"}}),
    ("import a.b as m, c", {"m": {"a.b"}, "c": {"c"}}),
    ("from a.b import c as d, e", {"d": {"a.b.c"}, "e": {"a.b.e"}}),
    ("from a import (b,\n    c,)", {"b": {"a.b"}, "c": {"a.c"}}),
    ("from . import m", {"m": {".m"}}),
    ("from ..p import q", {"q": {"..p.q"}}),
    ("from a import *", {}),
    ("try:\n    from typing import T\nexcept ImportError:\n"
     "    from typing_extensions import T\n", {"T": {"typing.T", "typing_extensions.T"}}),
])
def test_import_map(code, expected):
    """Imported names are mapped to the qualified names they refer to."""
    assert ClassMatcher(logical_lines(code), ()).import_map == expected


@pytest.mark.parametrize("name, expected", [
    ("dc.dataclass", {"dataclasses.dataclass"}),
    ("m.x.Y", {"a.b.x.Y"}),
    ("T", {"typing.T", "typing_extensions.T"}),
    ("local", {"local"}),
])
def test_resolve(name, expected):
    """Names are resolved through the first component."""
    import_map = {"dc": {"dataclasses"}, "m": {"a.b"},
                  "T": {"typing.T", "typing_extensions.T"}}
    assert resolve(name, import_map) == expected


@pytest.mark.parametrize("name, expected", [
    ("pydantic", True),
    ("pydantic.BaseModel", True),
    ("pydantic.dataclasses.dataclass", True),
    ("pydantic_settings.BaseSettings", False),
    ("dataclasses.dataclass", True),
    ("dataclasses.field", False),
    ("dataclass", False),
])
def test_name_matches(name, expected):
    """A name matches an option name it equals or is inside of."""
    assert name_matches(name, {"pydantic", "dataclasses.dataclass"}) == expected


@pytest.mark.parametrize("code, expected", [
    ("class A: pass", []),
    ("class A(): pass", []),
    ("class A(B, m.C[int], metaclass=M, *rest): pass", ["B", "m.C"]),
    ("class A(TypedDict, total=False): pass", ["TypedDict"]),
    ("class A[T: (int, str)](B): pass", ["B"]),
])
def test_class_bases(code, expected):
    """Base classes are found and keyword arguments are skipped."""
    assert class_bases(first_line_tokens(code)) == expected


@pytest.mark.parametrize("value, expected", [
    (None, None),
    (False, None),
    (True, set(STANDARD_NAMES)),
    ("", set(STANDARD_NAMES)),
    ("pydantic, attrs", set(STANDARD_NAMES) | {"pydantic", "attrs"}),
    (["pydantic"], set(STANDARD_NAMES) | {"pydantic"}),
])
def test_parse_keep_names(value, expected):
    """The option value can be true, a comma-separated string, or a sequence."""
    assert parse_keep_names(value) == expected


#
# Stripping with the option.
#

DATACLASS_CODE = """\
import dataclasses as dc
from typing import ClassVar

@dc.dataclass(frozen=True)
# A comment between the decorator and the class.
class Point:
    x: int
    y: int = 0
    count: ClassVar[int] = 0
    def scaled(self, k: int) -> "Point":
        z: int = k
        return Point(self.x * z, self.y * z)

class Point3(Point):
    w: int = 0

p: Point = Point(1, 2)
"""


def test_off_by_default():
    """Without the option the output is unchanged."""
    assert strip(DATACLASS_CODE) == strip(DATACLASS_CODE, keep_class_annotations=None)
    assert "    x: int\n" not in strip(DATACLASS_CODE)


@pytest.mark.skipif(sys.version_info < (3, 7), reason="Dataclasses need 3.7.")
def test_dataclass():
    """Dataclass fields are kept, and the methods and later code are stripped."""
    stripped = strip(DATACLASS_CODE, keep_class_annotations=True)
    for kept in ["x: int", "y: int = 0", "count: ClassVar[int] = 0", "w: int = 0"]:
        assert kept in stripped
    for removed in ["k: int", "-> ", "z: int", "p: Point"]:
        assert removed not in stripped
    namespace = exec_code(stripped)
    assert namespace["Point"](1).scaled(2) == namespace["Point"](2, 0)
    assert namespace["Point3"].__annotations__ == {"w": int}
    assert [f.name for f in namespace["dc"].fields(namespace["Point"])] == ["x", "y"]


@pytest.mark.skipif(sys.version_info < (3, 8), reason="TypedDict needs 3.8.")
def test_namedtuple_and_typeddict():
    """Fields of `NamedTuple` and `TypedDict` subclasses are kept."""
    code = ("from typing import NamedTuple, TypedDict\n"
            "class Employee(NamedTuple):\n"
            "    name: str\n"
            "    id: int = 3\n"
            "class Movie(TypedDict, total=False):\n"
            "    title: str\n")
    namespace = exec_code(strip(code, keep_class_annotations=True))
    assert namespace["Employee"]("Guido") == ("Guido", 3)
    assert namespace["Movie"].__annotations__.keys() == {"title"}


def test_local_lookalike_not_matched():
    """A decorator defined in the file is not the standard `dataclass`."""
    code = ("def dataclass(c):\n"
            "    return c\n"
            "@dataclass\n"
            "class A:\n"
            "    x: int = 1\n")
    assert "x: int" not in strip(code, keep_class_annotations=True)


def test_user_names():
    """Package, qualified, and local bare names can be given."""
    code = ("from pydantic import BaseModel, Field\n"
            "from myapp.models import Base\n"
            "def my_record(c):\n"
            "    return c\n"
            "class A(BaseModel):\n"
            "    a: int = Field(1)\n"
            "class B(Base):\n"
            "    b: int\n"
            "@my_record\n"
            "class C:\n"
            "    c: int\n"
            "class D:\n"
            "    d: int = Field(1)\n")
    stripped = strip(code, keep_class_annotations="pydantic,myapp.models.Base,my_record")
    for kept in ["a: int", "b: int", "c: int"]:
        assert kept in stripped
    assert "d: int" not in stripped
    assert "a: int" not in strip(code, keep_class_annotations=True)


def test_nested_classes():
    """Nested classes are matched on their own decorators and bases."""
    code = ("from dataclasses import dataclass\n"
            "@dataclass\n"
            "class Outer:\n"
            "    a: int = 1\n"
            "    class Plain:\n"
            "        b: int = 1\n"
            "    @dataclass\n"
            "    class Inner:\n"
            "        c: int = 1\n"
            "    d: int = 1\n"
            "class Plain2:\n"
            "    @dataclass\n"
            "    class Inner2:\n"
            "        e: int = 1\n"
            "    f: int = 1\n")
    stripped = strip(code, keep_class_annotations=True)
    for kept in ["a: int", "c: int", "d: int", "e: int"]:
        assert kept in stripped
    for removed in ["b: int", "f: int"]:
        assert removed not in stripped


def test_one_line_class_does_not_keep_next_block():
    """A one-line class body does not cause the next block to be kept."""
    code = ("from typing import NamedTuple\n"
            "class E(NamedTuple): b: int\n"
            "if True:\n"
            "    v: int = 1\n")
    assert strip(code, keep_class_annotations=True) == (
            "from typing import NamedTuple\n"
            "class E(NamedTuple): b: int\n"
            "if True:\n"
            "    v      = 1\n")


#
# The command line.
#

def run_command_line(tmp_path, args):
    """Run the command line on `DATACLASS_CODE` in a file, which replaces `{file}`
    in `args`, and return the completed process."""
    infile = tmp_path / "point.py"
    infile.write_bytes(DATACLASS_CODE.encode("utf-8"))
    script = TEST_DIR.parent / "bin" / "strip_hints.py"
    args = [a.format(file=infile) for a in args]
    return subprocess.run([sys.executable, str(script)] + args, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, universal_newlines=True)


@pytest.mark.parametrize("args", [
    ["{file}", "--keep-std-class-annotations"],
    ["-k", "{file}"],
    ["--keep-class-annotations", "attrs", "{file}"],
    ["{file}", "--keep-class-annotations=attrs"],
    ["--keep-class-annotations", "attrs", "-k", "{file}"],
])
def test_command_line(tmp_path, args):
    """Both options work, before or after the file."""
    result = run_command_line(tmp_path, args)
    assert result.returncode == 0, result.stderr
    assert result.stdout == strip(DATACLASS_CODE, keep_class_annotations=True)


def test_command_line_names_option_needs_value(tmp_path):
    """The names option without a value is an error."""
    assert run_command_line(tmp_path, ["{file}", "--keep-class-annotations"]).returncode != 0
