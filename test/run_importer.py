#!/usr/bin/env python3
"""

Try transforming on import by setting the import hook.

"""

from __future__ import print_function, division, absolute_import

import strip_hints

strip_hints.strip_on_import(__file__, py3_also=True)

import testfile_strip_hints

