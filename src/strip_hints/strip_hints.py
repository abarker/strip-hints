#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""

This module contains the function `strip_type_hints_from_file` which is used to
strip type hints from a Python file.  When run as a script it takes a filename
argument and prints the processed, stripped file to stdout.

The details of the processing operations and the algorithm to do it are
described below.

Python's grammar
----------------

The Python 3.7 grammar for function declarations is given in
https://docs.python.org/3/reference/grammar.html.  There are three parts that
we are concerned with:

1. function definitions: `funcdef`

2. type function parameter definitions: `tfpdef`

and

3. annotated assignments in expression statements: `anassign` in `expr_stmt`

Some things to note about the grammar:

* The `def` keyword is sufficient to recognize a function.

* Function definitions and assignments are never inside braces (parens, brackets,
  or curly braces).  We are only interested in top-level commas, colons, function
  argument list parens, and arrows as delimiters.  So everything nested inside
  parens, brackets, and curly braces can either be copied over directly (default
  values) or converted to whitespace (type hints).

* Lambdas take `varargslist`, not `typedargslist` and so they cannot have type
  hints.  They also cannot have assignments inside them.

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

1. Split into logical lines on `NEWLINE`, `ENDMARKER`, `INDENT`, and `DEDENT`
   tokens.

2. Sequentially split on tokens with string value `"def"` to find function
   definitions.

   a. Split on top-nesting-level parentheses to get the arguments and the
      return type part.

   b. White out the return type part if present, up to colon.  Disallow
      `NL` tokens in the whited-out code.

   c. Split the arguments on top-nesting-level comma tokens, ignoring any
      which are inside lambda arguments.

   d. For each argument, split it once on either top-level colon or top-level
      equals.  If the split is on a colon then split the right part again on
      equals.  White out the type declaration part.

3. While sequentially looking for function definitions, also look for a
   logical line that starts with a `NAME` token, followed immediately by
   a colon.  Process these lines using the same method as was used for
   individual function parameters.  If it is only a type definition
   (without an assignment) then turn it into a comment by changing the
   first character to pound sign.  Disallow `NL` tokens in whited-out
   code.


Possible enhancements
---------------------

Could maybe write out a stub file from the data, too.  Just take the actual
text of the function def up to the ending colon and write it out with ... for body.
Note that variable annotation might still need to be comments.

Or could the full, annotated source also serve as the stub file?  OK to put
extra stuff?  If so just symlink it or copy it...

#####################################

General info
------------

From: https://docs.python.org/3/reference/lexical_analysis.html
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

"""

# Note that the token type NEWLINE delimits logical lines, while NL delimits
# the remaining, non-logical linebreaks.

from __future__ import print_function, division, absolute_import
import sys
import tokenize
import io
import os
import collections
import ast
from token_list import (Token, TokenList, print_list_of_token_lists, ignored_types_set,
                        version, StripHintsException)

map_hints_to_empty_strings = True   # Easier to read than spaces, but more changes.
parse_processed_code_to_ast = True # Whether to parse the processed code.
try_to_fix_linebreaks_on_whited_tokens = True # Try to put backslash before breaks.

keywords_followed_by_colon = {"else", "try", "finally", "lambda"}

def check_whited_out_line_breaks(token_list):
    """Check that a `TokenList` instance to be whited-out does not include a
    newline (since it would no longer be nested and valid)."""
    # Issues with backslash in untokenize, and two distinct modes:
    # https://bugs.python.org/issue12691
    prev_token = None
    success_fixing = False
    for t in token_list:
        if t.type_name == "NL":
            # First case of the "if" below is disabled for now; haven't figured
            # out how to insert a backslash.  Issues with backslash in untokenize,
            # and two distinct modes: https://bugs.python.org/issue12691
            # Apparently only works in full mode, and doesn't store the "\"
            # except implicitly in the start and end c
            if (False and try_to_fix_linebreaks_on_whited_tokens and prev_token and
                    prev_token.type_name != "NL"):
                prev_token.string = "\\"
            else:
                raise StripHintsException("Line break occurred inside a whited-out,"
                   " unnested part of type hint.\nThe error occurred on line {0}"
                   " of file {1}:\n{2}".format(t.start[1], t.filename, t.line))
                raise StripHintsException(err_msg)
        prev_token = t

def process_single_parameter(parameter, nesting_level, annassign=False):
    """Process a single parameter in a function definition.  Setting `annassign`
    makes slight changes to handle annotated assignments."""
    #print("\nparameter being processed is:\n", parameter)
    assert isinstance(parameter, TokenList)

    #
    # Split on colon or equal.
    #

    split_on_colon_or_equal, splits = parameter.split(token_values=":=",
                                                      only_nestlevel=nesting_level,
                                                      sep_on_left=False, max_split=1,
                                                      return_splits=True)
    #print_list_of_token_lists(split_on_colon_or_equal, "split_on_colon_or_equal")
    if len(split_on_colon_or_equal) == 1: # Just a variable name.
        if annassign:
            check_whited_out_line_breaks(split_on_colon_or_equal[0])
            for t in split_on_colon_or_equal[0]:
                t.to_whitespace(empty=map_hints_to_empty_strings)
        return
    assert len(split_on_colon_or_equal) == 2
    assert len(splits) == 1
    right_part = split_on_colon_or_equal[1]

    if splits[0].string == "=":
        return # Parameter is just a var and a regular default value.

    #
    # Split right part on equal.
    #

    #print("right part of parameter is:", right_part)
    split_on_equal = right_part.split(token_values="=",
                                      only_nestlevel=nesting_level,
                                      max_split=1, sep_on_left=False)
    if len(split_on_equal) == 1: # Got a type def, no assignment or default.
        if annassign: # Make into a comment (if not a fun parameter).
            for t in parameter.iter_with_skips(skip_types=ignored_types_set):
                t.string = "#" + t.string[1:]
                return

    #print_list_of_token_lists(split_on_equal, "Split right part on equal:")
    type_def = split_on_equal[0]
    #print("type_def is", type_def)
    if annassign:
        check_whited_out_line_breaks(type_def)
    for t in type_def:
        t.to_whitespace(empty=map_hints_to_empty_strings)

def process_parameters(parameters, nesting_level):
    """Process the parameters to a function."""
    # Split on commas, but note that lambdas can have commas, which need to be
    # ignored.  Lambdas can also have parentheses, but those are always at a
    # higher nesting level.
    prev_comma_plus_one = 0
    inside_lambda = False
    for count, t in enumerate(parameters):
        if t.string == "lambda":
            inside_lambda = True
        elif t.string == ":" and inside_lambda:
            inside_lambda = False
        elif ((t.string == "," and t.nesting_level == nesting_level and not inside_lambda)):
            process_single_parameter(parameters[prev_comma_plus_one:count],
                                     nesting_level=nesting_level)
            prev_comma_plus_one = count + 1
        elif count == len(parameters) - 1:
            process_single_parameter(parameters[prev_comma_plus_one:count+1],
                                     nesting_level=nesting_level)
            prev_comma_plus_one = count + 1


def process_return_part(return_part):
    """Process the return part of the function definition (which may just be a
    colon if no `->` is used."""
    if not return_part:
        return # Error condition, but ignore.
    for i in reversed(range(len(return_part))):
        if return_part[i].string == ":":
            break
    return_type_spec = return_part[:i]
    check_whited_out_line_breaks(return_type_spec)
    for t in return_type_spec:
        #print(t.type_name)
        t.to_whitespace(empty=map_hints_to_empty_strings)

def process_funcdef_without_suite(funcdef_logical_line):
    """Process the top line of a `funcdef` function definition."""
    #print("function def being processed is", funcdef_logical_line)
    nesting_level = funcdef_logical_line[0].nesting_level + 1
    split_on_parens = funcdef_logical_line.split(token_values="()",
                         only_nestlevel=nesting_level,
                         max_split=2, ignore_separators=True)
    #print_list_of_token_lists(split_on_parens, "split on parens is")
    assert len(split_on_parens) == 3
    process_parameters(split_on_parens[1], nesting_level) # The parameters.
    process_return_part(split_on_parens[2]) # The return part.

def process_annassign(annotated_logical_line):
    """Process an annotated assignment or a simple type declaration not in a
    function definition."""
    #print("processing definition or aug assign", annotated_logical_line)
    nesting_level = annotated_logical_line[0].nesting_level
    # Almost the same code works as for single parameters in function definitions.
    process_single_parameter(annotated_logical_line, nesting_level,
                             annassign=True)

logical_lines_split_types = [tokenize.NEWLINE, tokenize.ENDMARKER,
                             tokenize.INDENT, tokenize.DEDENT]
logical_lines_split_values = [";"]

if version == 3:
    logical_lines_split_types.append(tokenize.ENCODING)

def strip_type_hints_from_file(filename):
    """Main program to strip type hints."""
    #
    # Get the tokens and split the lines into logical lines, etc.
    #

    tokens = TokenList(filename=filename, compat_mode=False)
    #print("Original tokens:\n", tokens, sep="")
    logical_lines = tokens.split(token_types=logical_lines_split_types,
                                 token_values=logical_lines_split_values,
                                 isolated_separators=True, no_empty=True)
    #print_list_of_token_lists(logical_lines, "Logical lines:")

    #
    # Sequentially process the tokens.
    #

    for t_list in logical_lines:

        # Check for a function definition; process it separately if one is found.
        split_on_def = t_list.split(token_values=["def"], sep_on_left=False, max_split=1)
        if len(split_on_def) == 2:
            process_funcdef_without_suite(split_on_def[1])
            continue

        # Check for an annassign.  Only recognizes a top-level NAME that is not
        # a keyword, that starts the line, and is followed by a colon.
        non_ignored_toks = [t for t in t_list.iter_with_skips(skip_types=ignored_types_set)]
        #print("Non-ignored toks:", non_ignored_toks)
        if (len(non_ignored_toks) >= 3 and non_ignored_toks[0].type_name == "NAME"
                and non_ignored_toks[1].string == ":"):
            process_annassign(t_list)
            continue

    #
    # Return the result.
    #

    #print("\nProcessed tokens:\n", tokens, sep="")
    #print("\nProcessed program is:")
    return tokens.untokenize()

#
# Run as script.
#

#TokenList.__str__ = TokenList.full_repr
#TokenList.__repr__ = TokenList.full_repr

if __name__ == "__main__":

    # Process command-line arguments (needs argparse).
    filename = sys.argv[0]
    if "--to-empty" in sys.argv:
        map_hints_to_empty_strings = True
        sys.argv.remove("--to-empty")
    if "--no-ast" in sys.argv:
        parse_processed_code_to_ast = False
        sys.argv.remove("--no-ast")

    # Process the code.
    processed_code = strip_type_hints_from_file(sys.argv[1])

    # Parse the code.
    if parse_processed_code_to_ast:
        if version == 2:
            ast.parse(processed_code.encode("latin-1"))
        else:
            ast.parse(processed_code, filename=filename)

    # Print to stdout.
    print(processed_code)

