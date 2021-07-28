# -*- coding: utf-8 -*-
"""

This module contains the class `HintStripper` which is used to strip type hints
from a Python file.  It also contains the function `process_command_line` which
is used to run the program as a command-line script.  When run as a script the
program takes a filename argument and any other arguments and prints the
processed, stripped file to stdout.

In most cases type hints can be stripped to leave valid code by converting both
the colon or arrow that always starts the hint, and the hint that follows it,
into whitespace.  Linebreaks inside the removed parts that are not inside
brackets, braces, or parens already need to either raise an exception or
implement a slightly more-complicated transformation.  But basically we only
need to identify the starting colon or arrow of each type hint and the end of
the hint.

The details of the processing operations and the algorithm to do it are
described below.

Python's grammar
----------------

Type hints, PEP-484: https://www.python.org/dev/peps/pep-0484/

Variable annotation, PEP-526: https://www.python.org/dev/peps/pep-0526/

The Python 3.7 grammar for function declarations is given in
https://docs.python.org/3/reference/grammar.html.  There are three parts that
we are concerned with:

1. function definitions: `funcdef`

2. type function parameter definitions: `tfpdef`

and

3. annotated assignments in expression statements: `anassign` in `expr_stmt`

Some things to note about the grammar:

* The `def` keyword is sufficient to recognize a function.

* Function definitions and assignment statements are never inside braces
  (parens, brackets, or curly braces).  We are only interested in top-level
  commas, colons, parens of function parameter lists, and arrows as delimiters.
  So everything nested inside parens, brackets, and curly braces can either be
  copied over directly (default values) or converted to whitespace (type hints).

* Lambdas take `varargslist`, not `typedargslist` and so they cannot have type
  hints.  They also cannot have assignments inside them.

* Colons in a parameter list, at the top nesting level for the list, can only
  occur in type hints and in lambdas.  Similarly for commas.

* Equal signs in a parameter list, at the top nesting level for the list, can
  only occur as default value assignments.

* Colons in the code, after a `NAME` that starts a logical line and in the
  outer nesting level for that line, only occur for keywords, type definitions
  and annotated assignments.

Algorithm
---------

Note that the token type NEWLINE delimits logical lines, while NL delimits the
remaining, non-logical linebreaks.

0. Tokenize the code into a TokenList.

1. Split into logical lines on `NEWLINE`, `ENDMARKER`, `INDENT`, and `DEDENT`
   tokens.

2. Sequentially split on tokens with string value `"def"` to find function
   definitions.

   a. Split on top-nesting-level parentheses to get the parameters and the
      return type part.

   b. White out the return type part if present, up to colon.  Disallow
      `NL` tokens in the whited-out code.

   c. Split the parameters on top-nesting-level comma tokens, ignoring any
      which are inside lambda parameters.

   d. For each parameter, split it once on either top-level colon or top-level
      equal sign.  If the split is on a colon then split the right part again on
      equal sign.  White out the type declaration part.

3. While sequentially looking for function definitions, also look for a logical
   line that starts with a `NAME` token, followed immediately by a colon (i.e., a
   simple annotated variable).  Process these lines using the same
   method as was used for individual function parameters.  If it is only a type
   definition (without an assignment) then turn it into a comment by changing the
   first character to pound sign.  Disallow `NL` tokens in whited-out code.
   If an annotated assignment then comments in the typedef are also whited out
   to avoid the syntax errors they cause.

The algorithm only handles simple annotated expressions in step 3 that start
with a name, e.g., not ones like `(x) : int`.

"""

from __future__ import print_function, division, absolute_import
import sys
import tokenize
import ast
import keyword
import argparse

if __name__ == "__main__":
    print("Run the console script 'strip-hints' if installed with pip, otherwise"
          "\nrun the Python script 'strip-hints.py' in the 'bin' directory.")

from .token_list import (TokenList, print_list_of_token_lists, ignored_types_set,
                         version, StripHintsException)
if version == 2:
    from . import import_hooks
else:
    from . import import_hooks_py3 as import_hooks

# These are the default option values to the command-line interface only.
default_to_empty = False   # Map hints to empty strings.  Easier to read; more changes.
default_strip_nl = False   # Also strips NL tokens (nonlogical newlines) in type hints.
default_no_ast = False # Whether to parse the processed code to AST.
default_no_colon_move = False # Whether to move colon to fix linebreaks in return.
default_no_equal_move = False # Whether to move = to fix deleted linebreaks in annotatated assigns.
default_only_assigns_and_defs = False # Whether to keep fundef annotations, strip rest.
default_only_test_for_changes = False # Print True and exit 0 if changes, otherwise False and 1.

DEBUG = False # Print debugging information if true.

logical_lines_split_types = [tokenize.NEWLINE, tokenize.ENDMARKER,
                             tokenize.INDENT, tokenize.DEDENT]
logical_lines_split_values = [";"]

if version == 3:
    logical_lines_split_types.append(tokenize.ENCODING)

class HintStripper(object):
    """Class holding the main stripping functions and the options as instance state."""
    def __init__(self, to_empty, strip_nl, no_ast,  no_colon_move, no_equal_move,
                 only_assigns_and_defs):
        """Initialize, passing in options for how to process hints (see the default
        values above for details)."""
        self.to_empty = to_empty
        self.strip_nl = strip_nl
        self.no_ast = no_ast
        self.no_colon_move = no_colon_move
        self.no_equal_move = no_equal_move
        self.only_assigns_and_defs = only_assigns_and_defs

    def check_whited_out_line_breaks(self, token_list, rpar_and_colon=None):
        """Check that a `TokenList` instance to be whited-out does not include a
        newline (since the newlines would no longer be nested).  This routine
        also moves the colon if `rpar_and_colon` is passed the corresponding token
        # list (except if the `--no-colon-move` option is selected)."""
        # Note this check is used
        #    1) when the `--no-equal-move` option is selected
        #       to check annotated assignments
        #    2) to check and possibly fix function return annotations.
        #
        # Breaks could also be fixed by inserting a backslash line continuation,
        # but I haven't figured out how to insert a backslash.  It is complicated
        # in tokenizer.  Issues with backslash in untokenize, and two distinct
        # modes: https://bugs.python.org/issue12691
        # Restoring backslash apparently only works in full mode, and doesn't store
        # the "\" except implicitly in the start and end component numbers.
        # For some info, see these issues with backslash in untokenize and the two
        # distinct modes: https://bugs.python.org/issue12691
        #
        # Annotated expressions with assignment are different because you cannot
        # just move the = sign like the colon (it has an expression after it).

        if self.strip_nl:
            if not any(t.type_name == "COMMENT" for t in token_list):
                return # NL tokens will be set to empty strings, OK with no comments.

        moved_colon = False
        for t in token_list:
            if t.type_name == "NL":
                if (not self.no_colon_move) and rpar_and_colon:
                    if moved_colon:
                        continue
                    rpar, colon = rpar_and_colon
                    rpar.string = rpar.string + ":"
                    colon.string = ""
                    moved_colon = True
                else:
                    raise StripHintsException("Line break occurred inside a whited-out,"
                       " unnested part of type hint.\nThe error occurred on line {0}"
                       " of the file {1}:\n{2}".format(t.start[0], t.filename, t.line))

    def process_single_parameter(self, parameter, nesting_level, annassign=False):
        """Process a single parameter in a function definition.  Setting `annassign`
        makes slight changes to instead handle annotated assignments."""

        #
        # First do exactly one split on the first colon or equal sign.
        #

        split_on_colon_or_equal, splits = parameter.split(token_values=":=",
                                                          only_nestlevel=nesting_level,
                                                          sep_on_left=False, max_split=1,
                                                          return_splits=True)
        if len(split_on_colon_or_equal) == 1: # Just a variable name, no type or annotation.
            return
        assert len(split_on_colon_or_equal) == 2
        assert len(splits) == 1

        right_part = split_on_colon_or_equal[1]

        if splits[0].string == "=":
            return # Parameter is just a variable with a regular default value.

        #
        # At this point we have an annotation (maybe with assignment) or a
        # typed parameter (maybe with default).  Now do exactly one split of
        # the right part, on equal, to test for an assignment or default value.
        #

        split_on_equal = right_part.split(token_values="=",
                                          only_nestlevel=nesting_level,
                                          max_split=1, sep_on_left=False)
        if len(split_on_equal) == 1: # Got a type def, no assignment or default value.
            if annassign: # Make into a comment (if not a fun parameter).
                skip_set = ignored_types_set.copy()
                skip_set.remove(tokenize.NL)
                annassign_token_list = list(parameter.iter_with_skips(skip_types=skip_set))

                first_non_nl_token = False
                for t in annassign_token_list: # Make each line start with '#' char.
                    if t.type == tokenize.NL:
                        if not first_non_nl_token:
                            continue # Preceding comments are in token list; don't double the '#'.
                        t.string = "\n#"
                    if not first_non_nl_token:
                        t.string = "#" + t.string # was t.string[1:]
                        first_non_nl_token = True
                return

        #
        # At this point we have an annotated assignment or typed param with default.
        #

        type_def = split_on_equal[0]
        has_assignment = len(split_on_equal) > 1

        if annassign and self.no_equal_move:
            self.check_whited_out_line_breaks(type_def)

        # Loop through counting newlines while whiting-out the type def part.
        nl_count = 0
        for t in type_def:
            if t.type == tokenize.NL:
                nl_count += 1
            strip_nl = self.strip_nl
            strip_comments = False
            if annassign and not self.no_equal_move:
                strip_nl = True # Use strip_nl to move annassign's `= ...` part (if needed).
                strip_comments = True # Comments can cause syntax errors with strip_nl.
            t.to_whitespace(empty=self.to_empty,
                            strip_nl=strip_nl, strip_comments=strip_comments)

        # Replace any stripped newlines so line numbers match after the change.
        if annassign and not self.no_equal_move and has_assignment:
            split_on_equal[1][-1].string += "\n" * nl_count

    def process_parameters(self, parameters, nesting_level):
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
            elif (t.string == "," and t.nesting_level == nesting_level
                                  and not inside_lambda):
                self.process_single_parameter(parameters[prev_comma_plus_one:count],
                                              nesting_level=nesting_level)
                prev_comma_plus_one = count + 1
            elif count == len(parameters) - 1:
                self.process_single_parameter(parameters[prev_comma_plus_one:count+1],
                                              nesting_level=nesting_level)
                prev_comma_plus_one = count + 1

    def process_return_part(self, return_part, rpar_token):
        """Process the return part of the function definition (which may just be a
        colon if no `->` is used."""
        colon_token = None
        if not return_part:
            return # Error condition, but ignore.
        for i in reversed(range(len(return_part))):
            if return_part[i].string == ":":
                colon_token = return_part[i]
                break
        if colon_token is None:
            raise StripHintsException("Error: colon_token not set in process_return_part.")
        return_type_spec = return_part[:i]
        self.check_whited_out_line_breaks(return_type_spec,
                                     rpar_and_colon=(rpar_token, colon_token))
        for t in return_type_spec:
            t.to_whitespace(empty=self.to_empty, strip_nl=self.strip_nl)

    def process_funcdef_without_suite(self, funcdef_logical_line):
        """Process the top line of a `funcdef` function definition."""
        if DEBUG: print("function def being processed is", funcdef_logical_line)
        nesting_level = funcdef_logical_line[0].nesting_level + 1
        split_on_parens, splits = funcdef_logical_line.split(token_values="()",
                                  only_nestlevel=nesting_level, return_splits=True,
                                  max_split=2, ignore_separators=True)
        if DEBUG: print_list_of_token_lists(split_on_parens, "Split on parens is:")
        assert len(split_on_parens) == 3
        rpar = splits[-1]
        assert rpar.string == ")"
        self.process_parameters(split_on_parens[1], nesting_level) # The parameters.
        self.process_return_part(split_on_parens[2], rpar_token=rpar) # The return part.

    def process_annassign(self, annotated_logical_line):
        """Process an annotated assignment or a simple type declaration not in a
        function definition."""
        if DEBUG: print("Processing typedef or ann assignment:", annotated_logical_line)
        nesting_level = annotated_logical_line[0].nesting_level
        # Almost the same code works as for single parameters in function definitions.
        self.process_single_parameter(annotated_logical_line, nesting_level,
                                      annassign=True)

    def strip_type_hints_from_file(self, filename):
        """Strip the type hints from a file named `filename`."""
        tokens = TokenList(filename=filename, compat_mode=False)
        return self.strip_type_hints_from_TokenList(tokens)

    def strip_type_hints_from_string(self, code_string):
        """Strip the type hints from a string containing code."""
        tokens = TokenList(code_string=code_string, compat_mode=False)
        return self.strip_type_hints_from_TokenList(tokens)

    def strip_type_hints_from_TokenList(self, tokens):
        """The main program to strip type hints from the given `TokenList` instance.
        Returns the stripped code as a string."""
        # Get the tokens and split the lines into logical lines, etc.
        if DEBUG: print("Original tokens:\n", tokens, sep="")
        logical_lines = tokens.split(token_types=logical_lines_split_types,
                                     token_values=logical_lines_split_values,
                                     isolated_separators=True, no_empty=True)
        if DEBUG: print_list_of_token_lists(logical_lines, "Logical lines:")

        # Sequentially process the tokens.
        for t_list in logical_lines:

            # Check for a function definition; process it separately if one is found.
            if not self.only_assigns_and_defs:
                split_on_def = t_list.split(token_values=["def"],
                                            sep_on_left=False, max_split=1)
                if len(split_on_def) == 2:
                    self.process_funcdef_without_suite(split_on_def[1])
                    continue

            # Check for an annassign.  Only recognizes a top-level NAME that is not
            # a keyword, that starts the line.
            non_ignored_toks = [
                    t for t in t_list.iter_with_skips(skip_types=ignored_types_set)]
            if not non_ignored_toks or keyword.iskeyword(non_ignored_toks[0].string):
                continue

            # Process the remaining part of the hint.  Low-level C-style loop.
            i = 0
            while non_ignored_toks[i].type_name == "NAME":
                i += 1
                if i >= len(non_ignored_toks):
                    break

                # Skip past all dotted attributes after the initial name, e.g.
                #    var.x.y: int
                if non_ignored_toks[i].string == ".":
                    i += 1
                    if i >= len(non_ignored_toks):
                        break
                    continue

                # Past this point the loop always breaks.

                # Skip past all stuff inside brackets after the initial name, e.g.
                #   d["key"]: int
                elif non_ignored_toks[i].string == "[":
                    while True:
                        i += 1
                        if i >= len(non_ignored_toks):
                            break
                        if (non_ignored_toks[i].string == "]"
                                and non_ignored_toks[i].nesting_level == 1):
                            break
                    i += 1
                    if i >= len(non_ignored_toks):
                        break

                # If we are at a colon but we are not at the end then process
                # as annotated assignment (end check is redundant but doesn't hurt).
                if non_ignored_toks[i].string == ":" and i != len(non_ignored_toks) - 1:
                    self.process_annassign(t_list)
                break

        # Get the result and return it.
        if DEBUG: print("\nProcessed tokens:\n", tokens, sep="")
        result = tokens.untokenize()
        return result

#
# The main functional interfaces.
#

def strip_file_to_string(filename, to_empty=False, strip_nl=False, no_ast=False,
                         no_colon_move=False, no_equal_move=False,
                         only_assigns_and_defs=False, only_test_for_changes=False):
    """Functional interface to strip hints from file `filename`.
    The remaining arguments are the same as the command-line arguments, except
    with underscores.

    Returns a string containing the stripped code unless
    `only_test_for_changes` is true, in which case a boolean is returned."""
    # Todo: The extra processing of arguments here could be moved to
    # `HintStripper` and `stripper.strip_hints_from_file`, for consistency.
    # As it is the strip-on-import function cannot do an AST check (but one
    # will be done anyway in parsing the code).
    #
    # Todo: could take an encoding argument; default utf-8 is used.

    # Create the HintStripper and call its stripping method.
    stripper = HintStripper(to_empty, strip_nl, no_ast, no_colon_move, no_equal_move,
                            only_assigns_and_defs)
    processed_code = stripper.strip_type_hints_from_file(filename)

    # Parse the code into an AST as an error check.
    if not stripper.no_ast:
        if version == 2:
            #ast.parse(processed_code.encode("latin-1")) # Make ASCII, not unicode.
            ast.parse(processed_code.encode("utf-8"))
        else:
            ast.parse(processed_code, filename=filename)

    # Return the result.
    if not only_test_for_changes:
        return processed_code
    else:
        # Need to tokenize and untokenize because tokenizer's round-trip guarantee does
        # not guarantee spaces within lines (but usually works).
        original_tokens = TokenList()
        original_tokens.read_from_file(filename)
        original_tokens_untokenized = original_tokens.untokenize()
        return not original_tokens_untokenized == processed_code

def strip_string_to_string(code_string, to_empty=False, strip_nl=False, no_ast=False,
                           no_colon_move=False, no_equal_move=False,
                           only_assigns_and_defs=False, only_test_for_changes=False):
    """Functional interface to strip hints from the string `code_string`.
    The remaining arguments are the same as the command-line arguments, except
    with underscores.

    Returns a string containing the stripped code unless
    `only_test_for_changes` is true, in which case a boolean is returned."""
    # Todo: Code redundancy, duplication from strip_file_to_string, could be cleaned up.

    # Create the HintStripper and call its stripping method.
    stripper = HintStripper(to_empty, strip_nl, no_ast,  no_colon_move, no_equal_move,
                            only_assigns_and_defs)
    processed_code = stripper.strip_type_hints_from_string(code_string)

    # Parse the code into an AST as an error check.
    if not stripper.no_ast:
        if version == 2:
            ast.parse(processed_code.encode("utf-8"))
        else:
            ast.parse(processed_code)

    # Return the result.
    if not only_test_for_changes:
        return processed_code
    else:
        # Need to tokenize and untokenize because tokenizer's round-trip guarantee does
        # not guarantee spaces within lines (but usually works).
        original_tokens = TokenList()
        original_tokens.read_from_string(code_string)
        original_tokens_untokenized = original_tokens.untokenize()
        return not original_tokens_untokenized == processed_code

def strip_on_import(calling_module_filename, to_empty=False, strip_nl=False, no_ast=False,
                    no_colon_move=False, no_equal_move=False, only_assigns_and_defs=False,
                    py3_also=False):
    """The function can usually just be called with `__file__` for the
    `module_filename` argument.  It runs `strip_hints` with the specified
    options on all files that are imported.

    Does nothing when run under Python 3 unless `py3_also` is set true."""
    # Could also have an option to load a '.py.stripped' file instead of the
    # actual file, to reduce overhead for actual version not in development.
    stripper = HintStripper(to_empty, strip_nl, no_ast,  no_colon_move, no_equal_move,
                            only_assigns_and_defs)
    import_hooks.register_stripper_fun(calling_module_filename,
                                       stripper.strip_type_hints_from_file,
                                       py3_also=py3_also)

def parse_command_line():
    """Create and return the argparse object to read the command line."""

    parser = argparse.ArgumentParser(description="Strip the hints from a Python module.")

    parser.add_argument("code_file", type=str, nargs=1, metavar="PYTHONFILE",
                        default=None, help="The Python file to strip hints out of.")
    parser.add_argument("--outfile", "-o", type=str, nargs=1, metavar="OUTPUTFILE",
                        default=None,
                        help="""Write the output to a file with the pathname passed in.
                        Files will be silently overwritten if they already
                        exist.  If this argument is omitted the output is
                        written to stdout.""")
    parser.add_argument("--inplace", action="store_true", default=False,
                        help="""Modify the input code file inplace; code will be
                        replaced with the stripped code.  This is the same as
                        passing in the code file's name as the output file.""")
    parser.add_argument("--to-empty", action="store_true", default=default_to_empty,
                        help="""Map removed code to empty strings rather than spaces.
                        This is easier to read, but does not preserve columns.
                        Default is false.""")
    parser.add_argument("--strip-nl", action="store_true", default=default_strip_nl,
                        help="""Also strip non-logical newline tokens inside type
                        hints.  These occur, for example, when a type-hint
                        function like `List` in a function parameter list has
                        line breaks inside its own arguments list.  The default
                        is to keep the newline tokens in order to preserve line
                        numbers between the stripped and non-stripped files.
                        Selecting this option no longer guarantees a direct
                        correspondence.""")
    parser.add_argument("--no-ast", action="store_true", default=default_no_ast,
                        help="""Do not parse the resulting code with the Python `ast`
                        module to check it.  Default is false.""")
    parser.add_argument("--no-colon-move", action="store_true", default=default_no_colon_move,
                        help="""Do not move colons to fix line breaks that occur in the
                        hints for the function return type.  Default is false.""")
    parser.add_argument("--no-equal-move", action="store_true", default=default_no_equal_move,
                        help="""Do not move the assignment with `=` when needed to
                        fix annotated assignments that include newlines in the
                        type hints.  When they are moved the total number of
                        lines is kept the same in order to preserve line number
                        correspondence between the stripped and non-stripped
                        files.  If this option is selected and such a situation
                        occurs an exception is raised.""")
    parser.add_argument("--only-assigns-and-defs", action="store_true",
                        default=default_only_assigns_and_defs,
                        help="""Only strip annotated assignments and standalone type
                        definitions, keeping function signature annotations.
                        Python 3.5 and earlier do not implement these; they
                        first appeared in Python 3.6.  The default is false.""")
    parser.add_argument("--only-test-for-changes", action="store_true",
                        default=default_only_test_for_changes, help="""
                        Only test if any changes would be made.  If any
                        stripping would be done then it prints `True` and
                        exits with code 0.  Otherwise it prints `False` and
                        exits with code 1.""")

    cmdline_args = parser.parse_args()
    return cmdline_args

#
# Run as a script or entry point.
#

def process_command_line():
    """Process the file on the command line when run as a script or entry point."""

    args = parse_command_line()
    code_file = args.code_file[0]
    processed_code = strip_file_to_string(code_file, args.to_empty, args.strip_nl,
                          args.no_ast, args.no_colon_move, args.no_equal_move,
                          args.only_assigns_and_defs, args.only_test_for_changes)

    if args.inplace:
        args.outfile = [code_file]

    if not args.only_test_for_changes:
        if not args.outfile:
            print(processed_code, end="")
        else:
            with open(args.outfile[0], "w") as f:
                f.write(str(processed_code))
    else:
        if processed_code: # The variable processed_code will be boolean in this case.
            print("True")
            exit_code = 0
        else:
            print("False")
            exit_code = 1
        sys.exit(exit_code)

