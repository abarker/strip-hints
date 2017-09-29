
strip-hints
===========

This package provides a command-line command and a corresponding importable
function which strip type hints from Python code file.  The stripping process
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

This project also contains a class ``TokenList`` which allows lists of Python
tokens to be operated on using an interface similar to that of Python strings.
In particular, a ``split`` method is used for much of the processing in stripping
hints.  This module could be useful for people doing other things with
Python at the token level.

Getting, installing, and running the code
-----------------------------------------

First clone or download the project from this GitHub repository.

After getting the repo you can just run the file ``strip_hints.py`` in the
``bin`` directory of the repo::

   python strip_hints.py your_file_with_hints.py

Alternately, you can install with pip::

   cd <pathToMainProjectDirectory> # Go to the main project directory.
   pip install .

After installing with pip you can run the console script ``strip-hints``::

   strip-hints your_file_with_hints.py

The code runs with Python 2 and Python 3.  The processed code is written to
stdout.  The AST checker that is run on the processed code checks the code
against whatever version of Python the script is run with.

The command-line options are as follows:

``--to-empty``
   Map deleted code to empty strings rather than spaces.  Easier to read,
   but does not preserve columns.  Default is false.

``--no-ast``
   Do not parse the resulting code with the Python ``ast`` module to check it.
   Default is false.

``--no-colon-move``
   Do not move colons to fix line breaks that occur in the hints for the
   function return type.  Default is false.

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

* Better argument handling with argparse.

* Import hooks to automatically convert code on import.

* Generate stubs for Python 2. (Unless the annotated files themselves will work as
  stubs; I haven't checked.)

* Better packaging.

* More options.

* Better error warnings (raising with messages rather than failing assertions).

