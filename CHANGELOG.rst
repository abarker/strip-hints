.. :changelog:

Changelog
=========

0.1.6 (2019-6-16)
------------------

Fixed strip-on-import for Python 2.

0.1.5 (2019-6-16)
------------------

Fixed a unicode decoding bug when running under Python 2 on a file containing a
unicode string.


0.1.4 (2019-1-18)
------------------

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


