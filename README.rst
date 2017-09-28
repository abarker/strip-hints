
strip_hints
===========

This module strips type hints from Python code, leaving runnable code without
the hints and making as few changes as possible.  This is intended to make
error messages for the processed file also correspond to the original file.  In
most cases with the default options both the line and column numbers are
preserved.

Using this script as a preprocessor allow the new type hint syntax to be used
in Python 2.  The main intended application is for code which is being
developed in Python 3 but which needs backward compatibility to Python 2.

This project also contains a class `TokenList` which allows lists of Python
tokens to be operated on using an interface similar to that of Python strings.
In particular, a `split` method is used for much of the processing in stripping
hints.  This module could be useful for people doing other things with
Python at the token level.

Getting and installing the code
-------------------------------

As of now, just clone or download the project from this GitHub page and run the
file `strip_hints.py`.

Running the code
----------------

Run the module `strip_hints.py`, passing it the name of the file to
process::

    python strip_hints.py your_file_with_hints.py

The code runs with Python 2 and Python 3.  The processed code is written to
stdout.

The options are as follows:

`--to-empty`
   Map deleted code to empty strings rather than spaces.  Easier to read,
   but does not preserve columns.  Default is false.

`--no-ast`
   Do not parse the resulting code with the Python `ast` module to check it.
   Default is false.

`--no-colon-move`
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

* Type hints can be removed in most cases simply by turning some tokens into
  whitespace, preserving line and column numbers in the files.  Whiting-out a
  section of code with a non-nested line break either raises an exception or
  performs a slightly more-complicated transformation.

In the most basic usage the sequence of tokens originally read from the file is
never changed; some tokens just have their string values set to whitespace or
to a pound sign before the untokenize operation.

The gory details of the algorithm are discussed in the docstring for
`strip_hints.py`.  The method should be fairly robust.

Bugs
----

The code has been run against the Mypy source code, with the results parsed
into ASTs and also visually inspected via diff.  Some edge cases are probably
still cause problems.  There is a Bash script in the test directory to run
the program and show the diffs.

Pull requests with bug fixes are welcome.

Possible enhancements
---------------------

* Better argument handling with argparse.

* Import hooks to automatically convert code on import.

* Generate stubs for Python 2 (Unless the annotated files themselves will work as
  stubs; I haven't checked.)

* Better packaging.

* More options.

* Better error warnings (raising with messages rather than using assertions).

