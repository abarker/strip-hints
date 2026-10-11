strip-hints
===========

.. image:: https://github.com/abarker/strip-hints/actions/workflows/tests.yml/badge.svg
   :target: https://github.com/abarker/strip-hints/actions/workflows/tests.yml
   :alt: Tests

This package provides a command-line command and a corresponding importable
function that strips type hints from Python code files.  The stripping process
leaves runnable code, assuming the rest of the code is runnable in the
interpreter version.  The program tries to make as few changes as possible to
the processed code so that line and column numbers in error messages for the
processed code file also correspond to those for the original code file.  In
most cases, with the default options, both the line and column numbers are
preserved.

This program was originally written to strip hints from Python 2 code to allow
for developing such code on Python 3 but running it with Python 2.  Python 2
is no longer supported, and the program now requires Python 3.6 or later.  The
last version that runs on Python 2 is 0.1.10.

This project also contains a general-purpose class named ``TokenList`` which
allows lists of Python tokens to be operated on using an interface similar to
that of Python strings.  In particular, a ``split`` method is used for much of
the processing in stripping hints, and a ``to_source`` method returns the
source code with any changed token strings substituted in.  This module could
be useful for doing other things with Python at the token level.

Installing the code
-------------------

To install from PyPI using pip use::

   pip install strip-hints

To install the most-recent development version from `this GitHub repository
<https://github.com/abarker/strip-hints>`_ use::

   pip install git+https://github.com/abarker/strip-hints

Alternately, you can clone or download the repository and install it with pip::

   cd <pathToMainProjectDirectory>
   pip install .  # use -e for development mode

If you are using the development repo you can also just run the file
``strip_hints.py`` in the ``bin`` directory of the repo::

   python strip_hints.py your_file_with_hints.py

Running the code
----------------

After installing with pip you can run the console script ``strip-hints``::

   strip-hints your_file_with_hints.py

The processed code is written to stdout, in the same encoding and with the
same line endings as the input file.  The AST checker that is run on the
processed code checks the code against whatever version of Python the script is
run with.

The command-line options are as follows.  None of them are set by default.

``--outfile`` (``-o``)
   Write the output to a file with the pathname passed in.  Files will be
   silently overwritten if they already exist.
   If this argument is omitted the output is written to stdout.

``--inplace``
   Modify the input code file inplace; code will be replaced with the stripped
   code.  This is the same as passing in the code file's name as the output file.

``--to-empty``
   Map removed code to empty strings rather than spaces, and also remove the
   whitespace before it.  This is easier to read, but does not preserve columns.
   Line numbers are still preserved.

``--strip-nl``
   Also strip non-logical newline tokens inside type hints.  These occur, for
   example, when a type-hint function like ``List`` in a function parameter
   list has line breaks inside its own arguments list.  The default is to keep
   the newline tokens in order to preserve line numbers between the stripped
   and non-stripped files.  Selecting this option no longer guarantees a direct
   correspondence.

``--no-ast``
   Do not parse the resulting code with the Python ``ast`` module to check it.

``--only-assigns-and-defs``
   Only strip annotated assignments and standalone type definitions, keeping
   function signature annotations.  This is useful for code that will run with
   Python 3.5, which has function annotations but not variable annotations.

``--only-test-for-changes``
   Only test if any changes would be made.  If any stripping would be done then
   it prints ``True`` and exits with code 0.  Otherwise it prints ``False`` and
   exits with code 1.

``--keep-class-annotations NAMES``
   Keep the annotations in the bodies of classes where they define fields, for
   the standard classes and also for the classes named in ``NAMES``, a
   comma-separated list.  See the section on dataclasses below.

``--keep-std-class-annotations`` (``-k``)
   Keep the annotations in the bodies of classes where they define fields, for
   the standard classes only, such as dataclasses.  See the section on
   dataclasses below.

``--no-colon-move``
   Do not move colons to fix line breaks that occur in the hints for the
   function return type.  See the Limitations section below for more
   information.  Not recommended.

``--no-equal-move``
   Do not move the assignment with ``=`` when needed to fix annotated
   assignments that include newlines in the type hints.  When they are moved
   the total number of lines is kept the same in order to preserve line number
   correspondence between the stripped and non-stripped files.  If this option
   is selected and such a situation occurs an exception is raised.  See the
   Limitations section below for more information.  Not recommended.

``--legacy-output``
   Use the output method of strip-hints 0.1.13 and earlier.  That method
   rebuilds the whole file from its tokens with Python's
   ``tokenize.untokenize`` function, so lines that contain no hints can come
   out slightly different from the input file: tabs between tokens become
   spaces, the spacing before backslash line continuations and between
   adjacent string literals can change, and on some Python 3.12 patch releases
   f-strings with escaped braces cause a ``SyntaxError``.  These differences
   depend on the Python version.  With ``--to-empty``, extra spaces are also
   left where hints were removed.  The default method copies everything except
   the stripped hints exactly as in the input file.  This option may be
   removed in a future version.

Dataclasses and similar classes
-------------------------------

In some classes the annotations in the class body define the fields of the
class and are used at runtime, so stripping them changes what the code does.
Two options keep the annotations directly in the bodies of these classes.
Method signatures, and everything outside the class bodies, are still
stripped.

A class is matched by its decorators and base classes, which are resolved
through the imports in the file.  The ``--keep-std-class-annotations`` option
(``-k``) matches only the standard classes: ``dataclasses.dataclass``,
``typing.NamedTuple``, and ``typing.TypedDict``, and the
``typing_extensions`` versions of the last two.  The
``--keep-class-annotations`` option takes a comma-separated list of names to
match in addition to the standard classes:

.. code-block:: bash

   strip-hints --keep-class-annotations pydantic,attr,attrs your_file.py

A name matches itself and any name inside it, so ``pydantic`` matches
``pydantic.BaseModel`` and ``pydantic.dataclasses.dataclass``.  Names are the
names used in imports, not the package names on PyPI.  Your own decorators and
base classes can be given by their qualified names, such as
``myapp.models.Base``, or by their bare names if they are defined in the same
file.  Classes defined later in the same file that inherit from a matched class
are also matched.

Since matching uses the imports, a decorator named ``dataclass`` that is
defined in the file itself is not matched as ``dataclasses.dataclass``.  The
matching does not follow star imports, names that are reassigned, or classes
from other files that inherit from a matched class (unless those classes are
given by name).  The comments described in the next section can be used in
those cases.

Disabling for sections of code
------------------------------

Any comment line that starts with ``# strip-hints: off`` will turn off
stripping until another comment line that starts with ``# strip-hints: on``.
For example, these examples would turn off stripping for the dataclass
(the ``--keep-std-class-annotations`` option can also be used in this case):

.. code-block:: python

    @dataclass
    class Point:
        # strip-hints: off
        x: int
        y: int
        # strip-hints: on

    # strip-hints: off
    @dataclass
    class Point:
        x: int
        y: int
    # strip-hints: on

Automatically running on import
-------------------------------

A function can be called to automatically strip the type hints from all future
imports that are in the same directory as the calling module.  For a package
the function call can be placed in ``__init__.py``, for example.  This can be
used to run code with hints such as ``list[int]`` or ``int | None`` on Python
versions that cannot evaluate them.

The function can be called as follows, with options set as desired (these
are the default settings, except for ``py3_also``):

.. code-block:: python

   from strip_hints import strip_on_import
   strip_on_import(__file__, to_empty=False, strip_nl=False, no_ast=False,
                   no_colon_move=False, no_equal_move=False,
                   only_assigns_and_defs=False, py3_also=True,
                   keep_class_annotations=None, legacy_output=False)

The ``py3_also`` argument must be set true, since otherwise the function does
nothing.  The function dates from when strip-hints was used to run code with
type hints under Python 2, and the default is kept false for backward
compatibility.  The first argument is the file path of the calling module.

Calling from a Python program
-----------------------------

To strip the type hints from a source file from within a Python program,
returning a string containing the code, the functional interface is as follows.
The option settings here are all the default values:

.. code-block:: python

   from strip_hints import strip_file_to_string
   code_string = strip_file_to_string(filename, to_empty=False, strip_nl=False,
                                      no_ast=False, no_colon_move=False,
                                      no_equal_move=False,
                                      only_assigns_and_defs=False,
                                      only_test_for_changes=False,
                                      keep_class_annotations=None,
                                      legacy_output=False)

To strip code that is originally in a string, rather than reading from a file,
the function ``strip_string_to_string`` takes the same arguments as
``strip_file_to_string`` except that the first argument is ``code_string``.

If ``only_test_for_changes`` is true then a boolean is returned which is true if
some changes would be made.  The ``keep_class_annotations`` argument can be
``True`` for the standard names, or a comma-separated string or a list of names
to add to them.

If the stripped code cannot be parsed then a ``SyntaxError`` is raised, unless
``no_ast`` is true.  Its message says whether the input code itself can be
parsed.  If ``no_colon_move`` or ``no_equal_move`` is true and a hint has a
line break that would need the move, a ``StripHintsException`` is raised.  It
can be imported from ``strip_hints``.

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

The program currently handles this by removing the newlines up to the ``=``
sign.  Any comments on those lines are also stripped, since otherwise they
cause syntax errors.  Empty lines are added to the end to keep the total number
of lines the same.  The ``--no-equal-move`` argument turns this off, in which
case situations like those above raise exceptions.  (As a workaround if
necessary to use ``--no-equal-move``, using an explicit backslash line
continuation seems to work.)

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

Only the hints are removed.  Imports, such as those from ``typing``, are kept,
as are runtime uses of typing such as ``cast(...)``, ``TypeVar``, and
``@overload``.  Unused imports can be removed afterward with a tool such as
``autoflake`` or ``ruff check --select F401 --fix``.

The stripped code is checked by parsing it with the Python version that runs
strip-hints, so strip-hints must be run with a version that can parse the input
code.  Only hints are removed, and newer syntax is left unchanged.  This
includes the type parameter lists and ``type`` statements of Python 3.12
(``def first[T](xs: list[T]) -> T:`` becomes ``def first[T](xs         )     :``),
so code using them still needs Python 3.12 or later after stripping.  If the
check fails, the error message says whether the input code itself can be
parsed by the running Python.

How it works
------------

Rather than doing a full, roundtrip parse, this module works on the tokens
produced by the Python tokenizer.  Locating the relevant parts to remove is a
much simpler task than parsing a program in full generality.  This allows an ad
hoc approach based on splitting groups of tokens, taking into account the
nesting level of the tokens to potentially split on.  Nesting level is based on
the level count inside parentheses, brackets, and curly braces.

* Type hints can be removed, in most cases, simply by turning some tokens into
  whitespace.  This preserves line and column numbers in the files.  Whiting-out a
  section of code with a non-nested line break either raises an exception or
  performs a slightly more-complicated transformation.

In the most basic usage the sequence of tokens originally read from the file is
never changed; some tokens just have their string values set to whitespace or
to a pound sign.  The output is the original code with the new strings of
those tokens substituted in, so everything else is copied exactly.

The gory details of the algorithm are discussed in the docstring for
``strip_hints_main.py``.  The method should be fairly robust.

Testing and bugs
----------------

The tests use pytest and are in the ``test`` directory.  They cover the
options, the command line, the functional interfaces, the reported issues, and
a set of case files in ``test/cases`` whose stripped output is compared with
saved results.  To run them from the repository root::

   pip install pytest
   python -m pytest

The tests are run by GitHub Actions on Python 3.7 to 3.15 on Linux and on one
Python version on Windows.  Python 3.6 is supported but no longer tested, since
GitHub no longer provides it.

Before version 0.2.0 the program was also run on the 5,580 Python files of the
Python 3.12 standard library and two sets of installed packages, and all of
them were stripped to code that parses.  Earlier versions were run on the Mypy
source code.  The Bash script ``test/strip_and_colordiff.bash`` runs the
program on one or more files and shows the differences with ``colordiff``, for
inspection.

Some edge cases may well remain to cause problems.  Please report bugs on the
GitHub issues page.

Changes and license
-------------------

The changes in each version are listed in the `changelog
<https://github.com/abarker/strip-hints/blob/master/CHANGELOG.rst>`_.  The code
is released under the `MIT license
<https://github.com/abarker/strip-hints/blob/master/LICENSE.txt>`_.
