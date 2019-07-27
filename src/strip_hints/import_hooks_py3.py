# -*- coding: utf-8 -*-
"""

Code to set up import hooks for Python 3 to automatically strip hints from
modules when they are loaded.

The import hook part of the code is based on an example from here:
   https://stackoverflow.com/questions/43571737/how-to-implement-an-import-hook-that-can-modify-the-source-code-on-the-fly-using/43573798#43573798

"""

from __future__ import print_function, division, absolute_import

import sys
import os
from importlib import invalidate_caches
from importlib.abc import SourceLoader
from importlib.machinery import FileFinder

version = sys.version_info[0]

stripper_funs = {}
registered = False

class StripHintsSourceLoader(SourceLoader):
    def __init__(self, fullname, path):
        self.fullname = fullname
        self.path = path

    def get_filename(self, fullname):
        return self.path

    def get_data(self, module_path):
        """Get the source code and modify it if necessary; `exec_module` is already
        defined."""
        assert not os.path.isdir(module_path) # Assume a file module is passed.
        canonical_module_dir_path = os.path.dirname(os.path.realpath(module_path))

        if canonical_module_dir_path in stripper_funs:
            stripper_fun_to_use = stripper_funs[canonical_module_dir_path]
            source = stripper_fun_to_use(module_path)
        else:
            with open(module_path) as f:
                source = f.read()
        return source

def install(loader_details):
    # Insert the path hook ahead of other path hooks.
    sys.path_hooks.insert(0, FileFinder.path_hook(loader_details))
    # Clear any loaders that might already be in use by the FileFinder.
    sys.path_importer_cache.clear()
    invalidate_caches()

def register_stripper_fun(calling_module_file, stripper_fun, py3_also=False):
    """The function called from a module `__init__` or from a script file to
    declare that all later imports from that directory should be processed on
    import to strip type hints.  This is based on the `realpath` of the
    directory of the module."""
    if version != 3:
        raise ImportError("Importing wrong `register_stripper_fun` for Python 2.")
    if not py3_also:
        return

    global registered
    if not registered:
        loader_details = StripHintsSourceLoader, [".py"]
        install(loader_details)
        registered = True

    canonical_dir_path = os.path.dirname(os.path.realpath(calling_module_file))
    stripper_funs[canonical_dir_path] = stripper_fun

