"""Tests for the `TokenList` class."""

import tokenize

import pytest

from strip_hints import StripHintsException
from strip_hints.token_list import TokenList

# Code that Python's untokenize does not always reproduce exactly.
ROUND_TRIP_CODE = [
    "x = 1\t# A tab before a comment.\n",
    "y = (1 +\n\t2)\n",
    "z = 1 + \\\n    2\n",
    'w = "a" "b"\n',
    't = f"{a}\\n{{literal}}"\n',
    'u = f"\\n{{{a}}}"\n',
    "v = 1\r\nif v:\r\n    v = 2\r\n",
    "no_final_newline = 1",
]


def token_list(code):
    """Return a `TokenList` for the string `code`."""
    return TokenList(code_string=code, compat_mode=False)


@pytest.mark.parametrize("code", ROUND_TRIP_CODE)
def test_to_source_round_trip(code):
    """Without modified tokens the source is returned unchanged."""
    assert token_list(code).to_source() == code


@pytest.mark.parametrize("raw", [
    b'# -*- coding: latin-1 -*-\ns = "caf\xe9"\n',
    b'\xef\xbb\xbfs = "caf\xc3\xa9"\n',
])
def test_to_source_round_trip_file(tmp_path, raw):
    """A file is returned unchanged, decoded with its declared encoding."""
    path = tmp_path / "code.py"
    path.write_bytes(raw)
    with open(str(path), "rb") as f:
        encoding = tokenize.detect_encoding(f.readline)[0]
    expected = raw.decode(encoding) # Also removes any BOM.
    assert TokenList(filename=str(path), compat_mode=False).to_source() == expected


def test_to_source_removes_bom_from_string():
    """A BOM character at the start of a string is removed, as by the tokenizer."""
    assert token_list('\ufeffs = "caf\xe9"\n').to_source() == 's = "caf\xe9"\n'


def test_to_source_round_trip_declared_encoding_in_string():
    """A string with a coding comment for another encoding is returned unchanged."""
    code = '# -*- coding: latin-1 -*-\ns = "caf\xe9"\n'
    assert token_list(code).to_source() == code


def find(tokens, string):
    """Return the first token in `tokens` with the string `string`."""
    return next(t for t in tokens.token_list if t.string == string)


def test_to_source_substitutes_modified_tokens():
    """Modified tokens are substituted, and tabs and other spacing are kept."""
    tokens = token_list("x\t= old  # Comment.\n")
    find(tokens, "old").string = "new_value"
    assert tokens.to_source() == "x\t= new_value  # Comment.\n"


def test_to_source_drop_space_before_emptied():
    """The whitespace before an emptied token is removed only when requested."""
    tokens = token_list("f(a,   b)\n")
    find(tokens, "b").string = ""
    assert tokens.to_source() == "f(a,   )\n"
    assert tokens.to_source(drop_space_before_emptied=True) == "f(a,)\n"


def test_to_source_drop_space_keeps_line_continuation():
    """A backslash line continuation in removed whitespace is kept."""
    tokens = token_list("x = 1 + \\\n    2\n")
    find(tokens, "2").string = ""
    assert tokens.to_source(drop_space_before_emptied=True) == "x = 1 +\\\n\n"


def test_to_source_needs_source():
    """A `TokenList` built from token tuples has no source to copy."""
    tokens = TokenList(token_list("x = 1\n").token_list)
    with pytest.raises(StripHintsException):
        tokens.to_source()
