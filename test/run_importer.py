#!/usr/bin/env python3
"""

Try transforming on import by setting the import hook.

"""

from __future__ import print_function, division, absolute_import

import strip_hints

strip_hints.strip_on_import(__file__, py3_also=False)

import testfile_strip_hints

# Some general import tests below.
import sys
import xml.etree.ElementTree
print(sys.modules.keys())
assert "xml" in sys.modules
assert "xml.etree" in sys.modules
assert "xml.etree.ElementTree" in sys.modules
import xml # Make sure other imports work...
print("\ndir(xml)", dir(xml))
import xml.parsers # Make sure other imports work...
x = xml.parsers
from xml import parsers
assert "xml.parsers" in sys.modules
print("\ndir(xml.parsers)", dir(xml.parsers))
#import xml.etree
#print("\ndir(xml.etree)", xml.etree.__dict__.keys())
from xml.etree import ElementTree


