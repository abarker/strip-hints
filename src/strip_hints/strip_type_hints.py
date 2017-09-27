#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
strip_hints
===========

This module strips type hints from Python code, leaving runnable code without
the hints and keeping the same line and column spacing.

Rather than doing a full parse, it works on the tokens produced by the Python
tokenizer.  Locating the relevant parts to remove is a much simpler task than
parsing the program in full generality.  This allows an ad hoc approach based
on splitting groups of tokens, taking into account the nesting level of the
tokens to potentially split on.  Nesting level is based on the level inside
parentheses, brackets, and curly braces.

1. The tokenizer for Python 2 works on code with type hints, as introduced in
   Python 3.

2. Type hints can be removed simply by turning some tokens into whitespace
   (preserving line and column numbers in the files).

The sequence of tokens is never changed; some tokens just have their string
values set to whitespace before the untokenize operation.

Function parameter annotations
------------------------------

The Python 3.7 grammar for function declarations is given in
https://docs.python.org/3/reference/grammar.html.  We are concerned with:

1. function definitions `funcdef`

2. type function parameter definitions `tfpdef`

and

3. annotated assignments `anassign`.

Some things to note about the grammar:

* Function definitions and assignments are never inside braces (parens, brackets,
  or curly braces).  We are only interested in top-level commas, colons, function
  argument list parens, and arrows as delimiters.  So everything nested inside
  parens, brackets, and curly braces can either be copied over directly (default
  values) or converted to whitespace (type hints).

* Lambdas take `varargslist`, not `typedargslist` and so they cannot have type
  hints.  They also cannot have assignments in them.

* Colons in a parameter list, at the top nesting level for the list, can only
  occur in type hints and in lambdas.  Similarly for commas.

* Equal signs in a parameter list, at the top nesting level for the list, can
  only occur as default value assignments.

* Colons in the code, after a `NAME` that starts a logical line and in the
  outer nesting level for that line, only occur for keywords and for type
  definitions and annotated assignments.

Type hints can be stripped to leave valid code by converting both the colon or
arrow that always starts the hint and the hint that follows it into whitespace
(assuming no linebreaks removed parts that are not inside parens already).  So
we only need to identify the starting colon or arrow of a type hint and the end
of the type hint.

From the Python grammar, the only place that a colon can occur at the top level
in a `typedarglist`, other than before the `suite` or in a `tpfdef`, is in a
lambda definition.  Similarly for top-level commas.

The only place in the top-level of an `expr_stmt` other than in an annotated
assignment `annassign` is also in a lambda.  But the lambda can only occur as
the assigned value.

Algorithm
---------

1. Split into logical lines on `RETURN`, then on semicolons, then on indents
   and other unnecessary parts.

2. Go through the statements looking for "def" starting a
Variable annotations (annotated assignment)
-------------------------------------------

Name followed by a colon not inside curly braces or in a lambda.


Later

Could maybe write out a stub file from the data, too.  Just take the actual
text of the function def up to the ending colon and write it out with ... for body.
Note that variable annotation might still need to be comments.

Or could the full, annotated source also serve as the stub file?  OK to put
extra stuff?  If so just symlink it or copy it...

#####################################

General info
------------

https://docs.python.org/3/reference/lexical_analysis.html
    2.1.1. Logical lines

    The end of a logical line is represented by the token NEWLINE. Statements
    cannot cross logical line boundaries except where NEWLINE is allowed by the
    syntax (e.g., between statements in compound statements). A logical line is
    constructed from one or more physical lines by following the explicit or
    implicit line joining rules.  2.1.2. Physical lines

    A physical line is a sequence of characters terminated by an end-of-line
    sequence. In source files, any of the standard platform line termination
    sequences can be used - the Unix form using ASCII LF (linefeed), the
    Windows form using the ASCII sequence CR LF (return followed by linefeed),
    or the old Macintosh form using the ASCII CR (return) character. All of
    these forms can be used equally, regardless of platform.

    When embedding Python, source code strings should be passed to Python APIs
    using the standard C conventions for newline characters (the \n character,
    representing ASCII LF, is the line terminator).

Problems
--------

linebreak in removed part
~~~~~~~~~~~~~~~~~~~~~~~~~

What if a line split happens because of a paren inside a thing that is
whitespaced out!  May be killer for keeping lines the same.

ONLY in the return type does it make a difference, since fun's parens cover the
arg case.  Just delete it and warn them, maybe?  Might mess up the tokens,
though, or just take first two elements.

Maybe forbid it, and check for NL inside things deleted?

class type declaration without assignment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class egg(object):
    x = int: 4 # Legal, works.
    x: int # Legal, works Python3
    x # Not legal, error.

"""

# Note that the token type NEWLINE delimits logical lines, while NL delimits
# the remaining, non-logical linebreaks.

from __future__ import print_function, division, absolute_import
import sys
import tokenize
import io
import collections
from token_list import Token, TokenList, print_list_of_token_lists

# TODO:
#
# 1) Handle multi-arg lambdas with commas in them.  Note lambdas can have parens,
#    but the nesting level is higher.
# 2) Detect when whited-out code crosses a line break at outer level of nesting
#    Put a backslash at the end of the breakpoint.
# 3) Make sure type def without assignment is deleted or turned into comment.

def process_single_parameter(parameter, nesting_level, no_single_name=False):
    split_on_colon_or_equal, splits = parameter.split(token_values=":=",
                                                      only_nestlevel=nesting_level,
                                                      sep_on_left=False, max_split=1,
                                                      return_splits=True)
    if len(split_on_colon_or_equal) == 1:
        if no_single_name:
            for t in split_on_colon_or_equal[0]:
                t.to_whitespace()
        return
    #print_list_of_token_lists(split_on_colon_or_equal, "Split on colon or equal:")
    assert len(split_on_colon_or_equal) == 2
    assert len(splits) == 1
    if splits[0].string == "=":
        return # Just a regular default value.
    else:
        splits[0].to_whitespace() # White out the colon.
    right_part = split_on_colon_or_equal[1]
    split_on_equal = right_part.split(token_values="=",
                                      only_nestlevel=nesting_level,
                                      max_split=1, ignore_separators=True)
    type_def = split_on_equal[0]
    for t in type_def:
        t.to_whitespace()

def process_parameters(parameters, nesting_level):
    """Process the parameters to a function."""
    # Note that lambdas can have commas, which need to be dealt with.  They can also
    # have parentheses, but those are always at a higher nesting level.
    prev_comma = 0
    inside_lambda = False
    for count, t in enumerate(parameters):
        if t.string == "lambda":
            inside_lambda = True
        elif t.string == ":" and inside_lambda:
            inside_lambda = False
        if t.string == "," and t.nesting_level == nesting_level and not inside_lambda:
            process_single_parameter(parameters[prev_comma+1:count],
                                     nesting_level=nesting_level)
            prev_comma = count


def process_return_part(return_part):
    """Process the return part of the function definition (which may just be a
    colon if no `->` is used."""
    if len(return_part) > 1:
        for i in range(len(return_part)-1):
            return_part[i].to_whitespace()

def process_funcdef_without_suite(funcdef_logical_line):
    nesting_level = funcdef_logical_line[0].nesting_level + 1
    split_on_parens = funcdef_logical_line.split(token_values="()",
                         only_nestlevel=nesting_level,
                         max_split=2, ignore_separators=True)
    assert len(split_on_parens) == 3
    process_parameters(split_on_parens[1], nesting_level) # The parameters.
    process_return_part(split_on_parens[2]) # The return part.

def process_tfpdef_and_annassign(annotated_logical_line):
    nesting_level = annotated_logical_line[0].nesting_level
    # Almost the same code works as for single parameters in function definitions.
    process_single_parameter(annotated_logical_line, nesting_level, no_single_name=True)

def strip_type_hints_from_file(filename):
    ignored_set = {tokenize.NL, tokenize.INDENT, tokenize.DEDENT, tokenize.NEWLINE,
                   tokenize.COMMENT}
    keywords_followed_by_colon = {"else", "try", "finally", "lambda"}

    tokens = TokenList(file=filename)
    print("Original untokenize:\n")
    print(tokens.untokenize())
    #print("Original tokens:\n", tokens)
    logical_lines = tokens.split(
                        token_types=[tokenize.NEWLINE, tokenize.SEMI, tokenize.ENDMARKER,
                                     tokenize.INDENT, tokenize.DEDENT],
                        isolated_separators=True, no_empty=True)
    print_list_of_token_lists(logical_lines, "logical lines:")

    for t_list in logical_lines:

        # Check for a function definition; process it separately if one is found.
        split_on_def = t_list.split(token_values=["def"], sep_on_left=False, max_split=1)
        if len(split_on_def) == 2:
            process_funcdef_without_suite(split_on_def[1])
            continue

        # Check for an tfpdef or annassign.  Only recognizes a top-level NAME
        # that is not a keyword, that starts the line, and is followed by a colon.
        found_candidate = False
        non_ignored_toks = [t for t in t_list.iter_with_skips(skip_types=ignored_set)]
        if (len(non_ignored_toks) >= 3 and non_ignored_toks[0].type_name == "NAME"
                and non_ignored_toks[1].string == ":"):
            process_tfpdef_and_annassign(t_list)
            continue

    print("\nProcessed program is:\n", tokens.untokenize())

#
# Run as script.
#

if __name__ == "__main__":

    #original_token_tuples = [t[0] for t in tokenize_file(sys.argv[1])]
    #tokens = TokenList(file=sys.argv[1])
    #saved_token_tuples = [t.token_tuple for t in tokens]
    #assert len(original_token_tuples) == len(saved_token_tuples)
    #print("Raw untokenize:\n", untokenize(t[0] for t in token_tuples))
    strip_type_hints_from_file(sys.argv[1])

