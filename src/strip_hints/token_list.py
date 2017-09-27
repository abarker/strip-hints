#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""

Classes for tokens and list of tokens that can be operated on similar to Python
strings.

"""

from __future__ import print_function, division, absolute_import
import sys
import tokenize
import io
import collections

tok_name = tokenize.tok_name # A dict mapping token values to names.
version = sys.version_info[0]

if version == 2:
    call_tokenize = tokenize.generate_tokens
else:
    call_tokenize = tokenize.tokenize

#
# Low-level utility functions.
#

def get_textfile_reader(filename, encoding):
    """Open a file in read only mode using the encoding `encoding`.  Return
    a text reader compatible with `tokenize.tokenize`."""
    if version == 2:
        stream = io.open(filename, "r", encoding=encoding)
        return stream.readline
    else:
        byte_stream = open(filename, "rb")
        return byte_stream.readline

nest_open = {"(", "[", "{"}
nest_close = {")", "]", "}"}

def tokenize_file(filename, encoding="utf-8"):
    """Read the file `filename` and return a list of tuples containing
    a token and its nesting level."""
    reader = get_textfile_reader(filename, encoding)
    tok_generator = call_tokenize(reader)

    nesting_level = 0
    lower_nest_level = False
    result = []
    for tok in tok_generator:
        if lower_nest_level:
            nesting_level -= 1
            lower_nest_level = False
        if tok[1] in nest_open:
            nesting_level += 1
        elif tok[1] in nest_close:
            lower_nest_level = True # Lower for next token.
        result.append((tok, nesting_level))
    return result

def untokenize(token_tuple_list, encoding="utf-8"):
    """Takes a list of token tuples and returns the untokenized text."""
    return tokenize.untokenize(token_tuple_list).decode(encoding)

def token_to_whitespace(token):
    """Return a copy of the token with its value set to spaces of the same length."""
    new_token = list(token)
    new_token[1] = " "*len(token[1])
    return tuple(new_token)

def named_token(token):
    """Return the token with the token type nuber replaced by the type name."""
    tok, nesting_level = token
    new_tok = [tok_name[tok[0]]] + list(tok[1:])
    return (tuple(new_tok), nesting_level)

def print_list_of_token_lists(lst, header=None):
    if header is None:
        header = "List of token lists:"
    print(header)
    for l in lst:
        print(l)
        print()
    print("\n")

class Token(object):
    """Represents a token from the Python tokenizer.  The tokens are mutable
    via changing the named attributes such as `type` and `string`.  Accessing
    `token_tuple` returns a tuple of the current values."""
    def __init__(self, token_iterable, nesting_level=None):
        token_elements = [t for t in token_iterable]
        self.type = token_elements[0]
        self.string = token_elements[1]
        self.start = token_elements[2]
        self.end = token_elements[3]
        self.line = token_elements[4]
        self.type_name = tok_name[self.type]
        self.nesting_level = nesting_level

    @property
    def value(self):
        """The `value` property is an alias for the `string` attribute."""
        return self.string

    @value.setter
    def value(self, value):
        self.string = value

    @property
    def token_tuple(self):
        current_tuple = (self.type, self.string, self.start, self.end, self.line)
        return current_tuple


    ignored_set = {tokenize.NL, tokenize.INDENT, tokenize.DEDENT, tokenize.NEWLINE,
                   tokenize.COMMENT}
    def to_whitespace(self, empty=False):
        """Convert the string or value of the token to spaces, of the same length
        as the original string.  If `empty` is true then an empty string is used."""
        if self.type in self.ignored_set:
            return
        new_token = list(self.token_tuple)
        if empty:
            self.string = ""
        else:
            self.string = " " * len(self.token_tuple[1])
        self.string = " " * len(self.string)

    def __repr__(self):
        return "Token({0})".format(self.token_tuple)

    def __str__(self):
        return self.simple_repr()

    def simple_repr(self):
        return "<{0}, {1}, {2}>".format(self.type_name, self.type, repr(self.string))

class TokenList(object):
    """Class for a list of `Token` objects.  The interface is similar to that of
    strings, but the objects are lists of tokens."""
    nest_open = {"(", "[", "{"}
    nest_close = {")", "]", "}"}

    def __init__(self, *iterables, **kwargs):
        """Pass in any number of iterables which return tokens to initialize
        the `TokenList`.  The returned tokens can be either `Token` instances
        or iterables of token elements.  The keyword `file=filename.py` can be
        set to read from a file, in which case any iterables are ignored."""
        if "file" in kwargs:
            self.read_from_file(kwargs["file"])
        else:
            self.set_from_iterables(*iterables)

    def set_from_iterables(self, *iterables):
        """Iterables must each have the same kind of object and iterate to produce
        token tuples or `Token` instances."""
        self.token_list = []
        for t_iter in iterables:
            tokens = [t for t in t_iter]
            if not tokens:
                continue
            if not isinstance(tokens[0], Token):
                tokens = [Token(t) for t in tokens]
            self.token_list += tokens

    def _index_tokens(self):
        # TODO: consider, maybe use this on the tokens...
        for index, t in enumerate(self.token_list):
            t.index = index

    def read_from_file(self, filename, encoding="utf-8"):
        """Read the file `filename` and return a list of tuples containing
        a token and its nesting level."""
        # TODO: nesting level is only set here for tokens, make note...
        reader = get_textfile_reader(filename, encoding)
        tok_generator = call_tokenize(reader)

        self.token_list = []
        nesting_level = 0
        lower_nest_level = False
        for tok in tok_generator:
            if lower_nest_level:
                nesting_level -= 1
                lower_nest_level = False
            if tok[1] in self.nest_open:
                nesting_level += 1
            elif tok[1] in self.nest_close:
                lower_nest_level = True # Lower for next token.

            self.token_list.append(Token(tok, nesting_level=nesting_level))

    def untokenize(self, encoding="utf-8"):
        token_tuples = [t.token_tuple for t in self.token_list]
        result = tokenize.untokenize(token_tuples).decode(encoding)
        return result

    def iter_with_skips(self, skip_types=None, skip_type_names=None, skip_values=None):
        """Return an iterator which skips tokens matching the given criteria."""
        for t in self.token_list:
            if skip_types and t.type in skip_types:
                continue
            if skip_type_names and t.type_name in skip_type_names:
                continue
            if skip_values and t.value in skip_values:
                continue
            yield t

    def split(self, token_type_names=None, token_types=None, token_values=None,
              only_nestlevel=None, max_split=None, isolated_separators=False,
              ignore_separators=False, disjunction=True, no_empty=False,
              sep_on_left=True, return_splits=False):
        """Split a list of tokens (with nesting info) into separate `TokenList`
        instances.  Returns a list of the instances.

        Lists of properties of the tokens to split on are passed to the method.
        The resulting splits will be on tokens which satisfy any of the
        criteria.  If `disjunction` is false then the conjunction of the
        separate lists is used (but disjunction is still used within any list,
        since those properties are mutually exclusive).

        Separators are part of the `TokenList` to the left unless
        `isolated_separators` is true, in which case separators have their own
        `TokenList` instances.  They can also be ignored.

        If `return_splits` is true then two values are returned: the list of
        token lists and a list of tokens where splits were made."""
        # Would be nice to split on sequences, too, with skipping.
        result = []
        splits = []
        i = -1
        last_split = 0
        num_splits = 0
        while True:
            i += 1
            if i == len(self.token_list) or (max_split and num_splits >= max_split):
                final_piece = self.token_list[last_split:]
                result.append(TokenList(final_piece))
                break

            tok = self.token_list[i]
            if only_nestlevel != None and tok.nesting_level != only_nestlevel:
                continue
            if disjunction:
                do_split = ((token_type_names and tok.type_name in token_type_names)
                           or (token_types and tok.type in token_types)
                           or (token_values and tok.value in token_values))
            else: # Conjunction.
                do_split = ((token_type_names and tok.type_name in token_type_names)
                           and (token_types and tok.type in token_types)
                           and (token_values and tok.value in token_values))
            if do_split:
                num_splits += 1
                splits.append(self.token_list[i])
                if ignore_separators:
                    result.append(TokenList(self.token_list[last_split:i]))
                    last_split = i + 1
                elif isolated_separators:
                    result.append(TokenList(self.token_list[last_split:i]))
                    result.append(TokenList(self.token_list[i:i+1]))
                    last_split = i + 1
                elif sep_on_left:
                    result.append(TokenList(self.token_list[last_split:i+1]))
                    last_split = i + 1
                else: # Put separator with the right piece.
                    result.append(TokenList(self.token_list[last_split:i]))
                    last_split = i
                did_split = True
        if no_empty:
            result = [r for r in result if r]
        if return_splits:
            return result, splits
        return result

    def __getitem__(self, index):
        """Index the individual `Tokens` in the list.  Slices and negative indices are
        allowed.  Slices return `TokenList` objects, while integer indices return
        `Token` instances."""
        if isinstance(index, slice):
            return TokenList(self.token_list[index.start:index.stop:index.step])
        if index < 0: # Handle negative indices.
            index += len(self)
        return self.token_list[index]

    def __add__(self, token_list_instance):
        return TokenList(self.token_list, token_list_instance.token_list)

    def __iadd__(self, token_list_instance):
        self.token_list.extend(token_list_instance.token_list)
        return self

    def __iter__(self):
        for t in self.token_list:
            yield t

    def __len__(self):
        return len(self.token_list)

    def __repr__(self):
        return "TokenList({0})".format(self.token_list)

    def __str__(self):
        return self.simple_repr()

    def simple_repr(self):
        combo = "\n".join(t.simple_repr() for t in self.token_list)
        if not self.token_list:
            return "TokenList([])"
        return "TokenList([\n{0}\n])".format(combo)

#
# Run as script, simple test.
#

if __name__ == "__main__":

    original_token_tuples = [t[0] for t in tokenize_file(sys.argv[1])]
    tokens = TokenList(file=sys.argv[1])
    saved_token_tuples = [t.token_tuple for t in tokens]
    assert len(original_token_tuples) == len(saved_token_tuples)
    print("Untokenized tokens:", tokens.untokenize())

