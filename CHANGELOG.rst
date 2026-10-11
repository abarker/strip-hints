.. :changelog:

Changelog
=========

0.2.0 (unreleased)
------------------

Changes to the output:

* Everything except the stripped hints is now copied exactly from the input
  file.  Previously the output was rebuilt from the tokens with Python's
  ``tokenize.untokenize``, which could change lines without hints: tabs
  between tokens became spaces, and the spacing before backslash line
  continuations and between adjacent string literals could change, depending
  on the Python version.  The new ``--legacy-output`` option restores the old
  method.

* With ``--to-empty`` the hints are now removed along with the whitespace
  before them, so ``def f(a: int, b: str = 'x') -> None:`` becomes
  ``def f(a, b = 'x'):`` instead of ``def f(a , b  = 'x')  :`` (#14).

New features:

* The ``--keep-std-class-annotations`` (``-k``) option keeps the annotations
  in the bodies of dataclasses and ``NamedTuple`` and ``TypedDict``
  subclasses, where they define fields.  The ``--keep-class-annotations``
  option takes a comma-separated list of further names, such as ``pydantic``
  or ``attrs`` (#15, #16).

* The ``--legacy-output`` option, described above.

Bug fixes:

* Files ending in a comment without a final newline no longer crash on
  Python 3.7 and 3.8 (#4).

* Escaped braces in f-strings (``{{`` and ``}}``) no longer cause later
  annotations to be left unstripped on Python 3.12 and later.

* Text in f-strings that looks like an operator or ``def``, such as the
  ``)`` in ``f"x ({y})"``, is no longer taken as one on Python 3.12 and
  later.  This caused a ``SyntaxError``, a crash, or an unstripped
  annotation.

* F-strings with escaped braces after a backslash escape no longer cause a
  ``SyntaxError`` on some Python 3.12 patch releases.

* Files with a coding comment for an encoding other than UTF-8 no longer
  crash.

* The command line writes its output in the encoding of the input file and
  keeps its line endings, so CRLF line endings are no longer doubled on
  Windows and a UTF-8 BOM is kept (#20).

* Extension modules can be imported again after ``strip_on_import`` is
  called.

Other changes:

* Python 3.6 or later is now required.  The last version that runs on Python
  2 is 0.1.10.

* The unneeded runtime dependency on ``wheel`` was removed.

0.1.13 (2025-02-20)
-------------------

New features:

* Standalone comment lines that start with ``# strip-hints: off`` now turn off
  hint-stripping.  Standalone comments that start with ``# strip-hints: on`` turn
  it back on.  This can be used as a workaround with, for example, dataclasses.

0.1.12 (2025-02-15)
-------------------

Bug fixes:

* Added a ``pass`` statement before commented-out annotations so ``Protocol``
  classes work now.

0.1.11 (2025-02-15)
-------------------

Updated to ``pyproject.toml`` instead of ``setup.py``.

0.1.10 (2021-07-20)
-------------------

Added the options ``--outfile`` and ``--inplace``, along with ``--help``.

Bug fixes:

* Fixed a bug where comments in function return hints that contain both newlines
  and comments cause syntax error when the ``--strip-nl`` option is used.

* Fixed a bug in multiline annotated expressions with comments on the lines.

0.1.9 (2020-05-06)
------------------

Added the options ``--strip-nl`` and ``--no-equal-move``.  Fixing annotated
assignments with newlines in type hints by moving the line with ``=`` was
added.

0.1.8 (2019-2-21)
-----------------

Added a new Python interface function ``strip_string_to_string`` which works
just the same as ``strip_file_to_string`` except it takes a code string
argument instead of a file name.

0.1.7 (2019-6-16)
-----------------

Added an `importlib` stripper for strip-on-import for Python 3.

0.1.6 (2019-6-16)
-----------------

Fixed strip-on-import for Python 2.

0.1.5 (2019-6-16)
-----------------

Fixed a unicode decoding bug when running under Python 2 on a file containing a
unicode string.

0.1.4 (2019-1-18)
-----------------

Consolidated the functional interface function ``strip_file_to_string`` so it
now accepts ``only_test_for_changes`` as an argument.

0.1.3 (2019-1-17)
------------------

Now handles annotated expressions of the form ``d["key"]: int`` and ``d["key"]: int == 4``.

Add an option ``--only-test-for-changes`` to just test for changes.

Fixed a nasty bug introduced in last version, keywords like "try" mistaken for
annotated variables.

0.1.2 (2019-1-15)
------------------

Now handles annotated dotted-access assignments (a simple form of annotated
expressions).  For example, ``x.y.z : int``.

0.1.1 (2017-11-03)
------------------

New Features:

   * The new ``strip_on_import`` function allows stripping Python 2 files on import.

Bug Fixes: None.

Other changes:

   * Expanded README documentation.

0.1.0 (2017-10-25)
------------------

Initial release.


