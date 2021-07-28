#!/usr/bin/env python3
"""

Usage: strip_from_string_test.py <filename>

The file is read as a string, the string is stripped, and the output is compared
with the result read directly from the file.

"""

from __future__ import print_function, division, absolute_import

import codecs
import sys
sys.path.insert(1, "../src")

import strip_hints

if len(sys.argv) < 2:
    print("Filename required as the argument.", file=sys.stderr)
    sys.exit(1)

filename = sys.argv[1]
with codecs.open(filename, encoding='utf-8') as code_file:
    code_string = code_file.read()

stripped_string_from_file = strip_hints.strip_file_to_string(filename, only_test_for_changes=False)
stripped_string_from_string = strip_hints.strip_string_to_string(code_string, only_test_for_changes=False)

#print(stripped_string_from_string, end="", sep="")

if stripped_string_from_file != stripped_string_from_string:
    print("Error, the final stripped strings differ.")
else:
    print("The final stripped strings are identical.")

