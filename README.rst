
strip_hints
===========

This module strips type hints from Python code, leaving runnable code without
the hints and keeping the same line and column spacing.  This is intended to
make error messages for the processed file also correspond to the original
file.  With preprocessing this would allow the use of the new type hint syntax
in Python 2.  The main intended application is for code which is being
developed in Python 3 but which needs backward compatibility to Python 2.

This project also contains a class `TokenList` which allows lists of Python
tokens to be operated on using an interface similar to that of Python strings.
In particular, a `split` method is used for much of the processing of stripping
hints.  This module could be useful for people doing other things with
token-level Python.

Getting and installing the code
-------------------------------

As of now, just clone or download the project from this GitHub page.

Running the code
----------------

Run the module `strip_hints.py`, passing it the name of the file to
process::

    python strip_hints.py your_file_with_hints.py

The code runs with Python 2 and Python 3.  The processed code is written to
stdout.

How it works
------------

Rather than doing a full, roundtrip parse, this module works on the tokens
produced by the Python tokenizer.  Locating the relevant parts to remove is a
much simpler task than parsing a program in full generality.  This allows an ad
hoc approach based on splitting groups of tokens, taking into account the
nesting level of the tokens to potentially split on.  Nesting level is based on
the level inside parentheses, brackets, and curly braces.

* The tokenizer for Python 2 also works on code with type hints, as introduced in
  Python 3.

* Type hints can be removed simply by turning some tokens into whitespace,
  preserving line and column numbers in the files.  An exception is raised
  if whiting-out a section of code would make a line break in that code
  section invalid.

The sequence of tokens originally read from the file is never changed; some
tokens just have their string values set to whitespace or to a pound sign
before the untokenize operation.

The gory details of the algorithm are discussed in the docstring for
`strip_hints.py`.  The method should be fairly robust.

