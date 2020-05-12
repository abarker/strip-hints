
strip-hints
===========

This package provides a command-line command and a corresponding importable
function that strips type hints from Python code files.  The stripping process
leaves runnable code, assuming the rest of the code is runnable in the
interpreter version.  The program tries to make as few changes as possible to
the processed code so that line and column numbers in error messages for the
processed code file also correspond to those for the original code file.  In
most cases, with the default options, both the line and column numbers are
preserved.

The stripping operation can be used as a preprocessor to allow the new type
hint syntax to be used in Python 2.  The main intended application is for code
which is being developed in Python 3 but which needs backward compatibility to
Python 2.

This project also contains a general-purpose class named ``TokenList`` which
allows lists of Python tokens to be operated on using an interface similar to
that of Python strings.  In particular, a ``split`` method is used for much of
the processing in stripping hints.  This module could be useful for doing other
things with Python at the token level.

Installing the code
-------------------

To install from PyPI using pip use::

   pip install strip-hints

To install the most-recent development version first clone or download the
project from `this GitHub repository
<https://github.com/abarker/strip-hints>`_.

Running the code
----------------

After installing with pip you can run the console script ``strip-hints``::

   strip-hints your_file_with_hints.py

The code runs with Python 2 and Python 3.  The processed code is written to
stdout.  The AST checker that is run on the processed code checks the code
against whatever version of Python the script is run with.

The command-line options are as follows:

``--to-empty``
   Map removed code to empty strings rather than spaces.  This is easier to read,
   but does not preserve columns.  Default is false.

``--strip-nl``
   Also strip non-logical newline tokens inside type hints.  These occur, for
   example, when a type-hint function like ``List`` in a function parameter
   list has line breaks inside its own arguments list.  The default is to keep
   the newline tokens in order to preserve line numbers between the stripped
   and non-stripped files.  Selecting this option no longer guarantees a direct
   correspondence.

``--no-ast``
   Do not parse the resulting code with the Python ``ast`` module to check it.
   Default is false.

``--no-colon-move``
   Do not move colons to fix line breaks that occur in the hints for the
   function return type.  Default is false.  See the Limitations section below
   for more information.

``--no-equal-move``
   Do not move the assignment with ``=`` when needed to fix annotated
   assignments that include newlines in the type hints.  When they are moved
   the total number of lines is kept the same in order to preserve line number
   correspondence between the stripped and non-stripped files.  If this option
   is selected and such a situation occurs an exception is raised.  See the
   Limitations section below for more information.

``--only-assigns-and-defs``
   Only strip annotated assignments and standalone type definitions, keeping
   function signature annotations.  Python 3.5 and earlier do not implement
   these; they first appeared in Python 3.6.  The default is false.

``--only-test-for-changes``
   Only test if any changes would be made.  If any stripping would be done then
   it prints ``True`` and exits with code 0.  Otherwise it prints ``False`` and
   exits with code 1.

If you are using the development repo you can just run the file
``strip_hints.py`` in the ``bin`` directory of the repo::

   python strip_hints.py your_file_with_hints.py

Alternately, you can install the development repo with pip::

   cd <pathToMainProjectDirectory> 
   pip install .  # use -e for development mode

Automatically running on import
-------------------------------

A function can be called to automatically strip the type hints from all future
imports that are in the same directory as the calling module.  For a package
the function call can be placed in ``__init__.py``, for example.

The function can be called as follows, with options set as desired (these
are the default settings):

.. code-block:: python

   from strip_hints import strip_on_import
   strip_on_import(__file__, to_empty=False, no_ast=False, no_colon_move=False,
                   only_assigns_and_defs=False, py3_also=False)

By default Python 3 code is ignored unless ``py3_also`` is set.  The first
argument is the file path of the calling module.

Calling from a Python program
-----------------------------

To strip the comments from a source file from within a Python program,
returning a string containing the code, the functional interface is as follows.
The option settings here are all the default values:

.. code-block:: python

   from strip_hints import strip_file_to_string
   code_string = strip_file_to_string(filename, to_empty=False, strip_nl=False,
                                      no_ast=False, no_colon_move=False,
                                      no_equal_move=False,
                                      only_assigns_and_defs=False,
                                      only_test_for_changes=False)

To strip code that is originally in a string, rather than reading from a file,
the function ``strip_string_to_string`` takes the same arguments as
``strip_file_to_string`` except that the first argument is ``code_string``.

If ``only_test_for_changes`` is true then a boolean is returned which is true iff
some changes would be made.

Limitations
-----------

Ordinarily the program simply converts type hints to whitespace and the
resulting code is still syntactically correct.  There are a couple of
situations, though, where further transformations are required to preserve
syntactical correctness.

One example is when a line break occurs in the argument list of a type
hint in an annotated assignment:

.. code-block:: python
 
   x: List[int,
           int] = [1,2]

The program currently handles this by moving the line with ``=`` (and the
following lines) to the end of the line with ``x``.  Empty lines are added to
the end to keep to total number of lines the same.  The ``--no-equal-move``
argument turns this off, in which case situations like those above raise
exceptions.  (As a workaround if necessary with ``--no-equal-move``, using an
explicit backslash line continuation seems to work.)

A similar situation can occur in return type specifications:

.. code-block:: python

   def f() -> List[int,
                   int]:
       pass

This is handled by moving the colon up to the line with the closing paren.  The
situation does not occur inside function parameter lists because they are
always nested inside parentheses.

The program currently only handles simple annotated expressions (e.g.,
it handles ``my_class.x: int`` and ``my_list[2]: int`` but not ``(x): int``).

How it works
------------

Rather than doing a full, roundtrip parse, this module works on the tokens
produced by the Python tokenizer.  Locating the relevant parts to remove is a
much simpler task than parsing a program in full generality.  This allows an ad
hoc approach based on splitting groups of tokens, taking into account the
nesting level of the tokens to potentially split on.  Nesting level is based on
the level count inside parentheses, brackets, and curly braces.

* The tokenizer for Python 2 also works on code with type hints, as introduced in
  Python 3.

* Type hints can be removed, in most cases, simply by turning some tokens into
  whitespace.  This preserves line and column numbers in the files.  Whiting-out a
  section of code with a non-nested line break either raises an exception or
  performs a slightly more-complicated transformation.

In the most basic usage the sequence of tokens originally read from the file is
never changed; some tokens just have their string values set to whitespace or
to a pound sign before the untokenize operation.

The gory details of the algorithm are discussed in the docstring for
``strip_hints_main.py``.  The method should be fairly robust.

Bugs
----

The code has been run on the Mypy source code and on some other examples, with
the results parsed into ASTs and also visually inspected via diff.  Some edge
cases may well remain to cause problems.  There is a Bash script in the ``test``
directory which runs the program on files and shows the diffs.

Possible enhancements
---------------------

* Formal tests.
  
* Better argument-handling, help, etc. with argparse.

* Better error warnings (raising exceptions with messages rather than just failing
  assertions in some places).

