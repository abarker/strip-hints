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
import codecs
import contextlib
import locale

tok_name = tokenize.tok_name # A dict mapping token values to names.
version = sys.version_info[0]

if version == 2:
    call_tokenize = tokenize.generate_tokens
    # See pages below for mod to sys.stdout to avoid unicode errors.
    #http://blog.mathieu-leplatre.info/python-utf-8-print-fails-when-redirecting-stdout.html
    #https://wiki.python.org/moin/PrintFails
    sys.stdout = codecs.getwriter(locale.getpreferredencoding())(sys.stdout)
    import StringIO
else:
    call_tokenize = tokenize.tokenize

#
# Low-level utility functions.
#

def get_textfile_stream(filename, encoding):
    """Open a file in read only mode using the encoding `encoding`.  Return
    a text stream with a reader compatible with `tokenize.tokenize`."""
    if version == 2:
        stream = io.open(filename, "r", encoding=encoding)
        return stream
    else:
        byte_stream = open(filename, "rb")
        return byte_stream

def get_string_stream(string, encoding):
    """Open and return a string stream with a file-like `readline()` interface."""
    if version == 2:
        stream = StringIO.StringIO(string)
        return stream
    else:
        byte_stream = io.BytesIO(bytes(string, encoding=encoding))
        return byte_stream

def print_list_of_token_lists(lst, header=None):
    """Used for debugging output."""
    print()
    if header is None:
        header = "List of token lists:"
    print(header)
    for l in lst:
        print(l)
        print()
    print("\n")

#
# Token class.
#

ignored_types_set = {tokenize.NL, tokenize.INDENT, tokenize.DEDENT, tokenize.NEWLINE,
                     tokenize.COMMENT}

class Token(object):
    """Represents a token from the Python tokenizer.

    The tokens are mutable via changing the named attributes such as `type` and
    `string`.  Accessing the `token_tuple` property or converting to type `tuple`
    returns a tuple of the current values (the format Python's `untokenize`
    function expects)."""

    def __init__(self, token_iterable, nesting_level=None, filename=None,
                 compat_mode=False):
        """Pass in an iterable which produces the token elements.  The `nesting_level`
        and `filename` can optionally be set and will simply be saved as attributes.

        If `compat_mode` is true then the tokenizer compatability mode is used.
        This only uses the first two token components, type and string.  The
        default is false, and full mode is used with the full five components."""
        if compat_mode:
            token_elements = []
            for count, t in enumerate(token_iterable):
                token_elements.append(t)
                if count == 2:
                    break
            token_elements += [None]*3
        else:
            token_elements = [t for t in token_iterable]
        self.type = token_elements[0]
        self.string = token_elements[1]
        self.start = token_elements[2]
        self.end = token_elements[3]
        self.line = token_elements[4]
        self.type_name = tok_name[self.type]
        self.nesting_level = nesting_level
        self.filename = filename
        self.compat_mode = compat_mode

    @property
    def value(self):
        """The `value` property is an alias for the `string` attribute."""
        return self.string

    @value.setter
    def value(self, value):
        self.string = value

    @property
    def token_tuple(self):
        if self.compat_mode:
            current_tuple = (self.type, self.string)
        else:
            current_tuple = (self.type, self.string, self.start, self.end, self.line)
        return current_tuple

    def to_whitespace(self, empty=False, strip_nl=False, strip_comments=False):
        """Convert the string or value of the token to a string of spaces of
        the same length as the original string.

        If `empty` is true then an empty string is used for the replacement.

        If `strip_nl` is true then NL tokens (non-logical line breaks) are also
        removed (converted to empty strings)."""
        if strip_nl and self.type == tokenize.NL:
            self.string = ""
            return
        if strip_comments and self.type == tokenize.COMMENT:
            self.string = ""
            return
        if self.type in ignored_types_set:
            return
        if empty:
            self.string = ""
        else:
            self.string = " " * len(self.token_tuple[1])

    def __tuple__(self):
        return self.token_tuple

    def __repr__(self):
        return self.simple_repr()
        # The __repr__ is used when lists of tokens are printed, and below is
        # standard but doesn't look very good in that situation.
        #return "Token({0})".format(self.token_tuple) #

    def __str__(self):
        return self.simple_repr()

    def simple_repr(self):
        return "<{0}, {1}, {2}>".format(self.type_name, self.type, repr(self.string))

    def full_repr(self):
        return "<{0}, {1}, {2}, {3}, {4}, {5}>".format(self.type_name, self.type,
                                   repr(self.string), self.start, self.end, self.line)

#
# TokenList class.
#

class TokenList(object):
    """Class for a list of `Token` objects.  The interface is similar to that of
    strings, but the objects are lists of tokens."""
    nest_open = {"(", "[", "{"}
    nest_close = {")", "]", "}"}

    def __init__(self, *iterables, **kwargs):
        """Pass in any number of iterables which return tokens.  They are used
        sequentially to initialize the `TokenList`.  The tokens returned by
        these iterators can be either `Token` instances or iterables of token
        elements.

        The keyword `filename=filename.py` can be set to read from a file, in
        which case any iterables are ignored.

        The keyword `code_string` can be set to read from a string, in
        which case any iterables are ignored.

        The keyword `encoding` can be passed in to save as the unicode encoding.
        The default is UTF-8.

        The keyword `compat_mode` can be used to create tokens in the
        tokenizer's compatability mode (two-element token tuples) rather than
        the default full mode (five-element token tuples).

        Nesting levels are currently only set when reading from a string or
        file.  Nesting levels start at zero and increase on any character in
        `nest_open` (class attribute above) and decrease just after any
        character in `nest_close`."""
        if "encoding" in kwargs:
            self.encoding = kwargs["encoding"]
        else:
            self.encoding = "utf-8"

        if "compat_mode" in kwargs and kwargs["compat_mode"]:
            self.compat_mode = True
        else:
            self.compat_mode = False

        if "filename" in kwargs:
            self.read_from_file(kwargs["filename"])
        elif "code_string" in kwargs:
            self.read_from_string(kwargs["code_string"])
        else:
            self.set_from_iterables(*iterables)

    def set_from_iterables(self, *iterables, **kwargs):
        """Pass in any number of iterables.  Each each must iterate to produce
        either token tuples or `Token` instances.

        Keyword options are `encoding` and `compat_mode`."""
        if "encoding" in kwargs:
            self.encoding = kwargs["encoding"]
        else:
            self.encoding = "utf-8"
        if "compat_mode" in kwargs:
            if kwargs["compat_mode"]:
                self.compat_mode = True
            else:
                self.compat_mode = False
        self.token_list = []
        for t_iter in iterables:
            tokens = [t for t in t_iter]
            if not tokens:
                continue
            if not isinstance(tokens[0], Token):
                tokens = [Token(t, compat_mode=self.compat_mode) for t in tokens]
            self.token_list += tokens

    def read_from_file(self, filename, encoding="utf-8", compat_mode=False):
        """Read the file `filename` and return a list of tuples containing
        a token and its nesting level."""
        # Nesting level is only ever set here and `read_from_string`, nowhere else as of now.
        self.encoding = encoding
        if compat_mode:
            self.compat_mode = compat_mode
        with contextlib.closing(get_textfile_stream(filename, encoding)) as stream:
            return self.read_from_readline_interface(stream.readline, filename, compat_mode=compat_mode)

    def read_from_string(self, code_string, encoding="utf-8", compat_mode=False):
        """Read from the string `code_string` and return a list of tuples containing
        a token and its nesting level."""
        # Nesting level is only ever set here and `read_from_file`, nowhere else as of now.
        if compat_mode:
            self.compat_mode = compat_mode
        with contextlib.closing(get_string_stream(code_string, encoding)) as stream:
            return self.read_from_readline_interface(stream.readline, compat_mode=compat_mode)

    def read_from_readline_interface(self, readline, filename=None, compat_mode=False):
        """Read from an object implementing the `readline` interface. Return a
        list of tuples containing a token and its nesting level."""
        # Todo: Compat mode arg handling could be cleaned up in this method and class.
        if compat_mode:
            self.compat_mode = compat_mode
        tok_generator = call_tokenize(readline)

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

            self.token_list.append(Token(tok, nesting_level=nesting_level,
                           filename=filename, compat_mode=self.compat_mode))

    def untokenize(self, encoding=None):
        """Convert the current list of tokens into a code string and return it.
        If no `encoding` is supplied the one stored with the list from when
        it was created is used."""
        if not encoding:
            encoding = self.encoding
        if not self.token_list:
            raise StripHintsException("Attempt to untokenize when the `TokenList`"
                          " instance has not been initialized with any tokens.")
        token_tuples = [t.token_tuple for t in self.token_list]
        result = tokenize.untokenize(token_tuples)
        if version == 2: # Decoding below causes a unicode error in Python 2.
            return result
        decoded_result = result if isinstance(result, str) else result.decode(encoding)
        return decoded_result

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
              sep_on_left=False, return_splits=False):
        """Split a list of tokens (with nesting info) into separate `TokenList`
        instances.  Returns a list of the instances.

        Lists of properties (type names, types, or values) of the tokens to
        split on are passed to the method.  The resulting splits will be on
        tokens which satisfy any of the criteria.  If `disjunction` is false
        then the conjunction of the separate lists is used instead (but
        disjunction is still used within any list since those properties are
        mutually exclusive).

        Separators are part of the `TokenList` to the right unless
        `sep_on_left` is true.  If `isolated_separators` is true separators are
        placed in their own `TokenList` instances.  They can also be ignored.

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
            if only_nestlevel is not None and tok.nesting_level != only_nestlevel:
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
                elif sep_on_left: # Separator on left piece.
                    result.append(TokenList(self.token_list[last_split:i+1]))
                    last_split = i + 1
                else: # Separator on the right piece.
                    result.append(TokenList(self.token_list[last_split:i]))
                    last_split = i
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

    def full_repr(self):
        combo = "\n".join(t.full_repr() for t in self.token_list)
        if not self.token_list:
            return "TokenList([])"
        return "TokenList([\n{0}\n])".format(combo)


#
# Exceptions.
#

class StripHintsException(Exception):
    pass

#
# Run as script, simple test.
#

if __name__ == "__main__":

    tokens = TokenList(filename=sys.argv[1])
    print("Untokenized tokens:", tokens.untokenize())

