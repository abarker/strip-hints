#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Testfile for stripping hints.

"""

from __future__ import print_function, division, absolute_import

# Below is from:
# https://stackoverflow.com/questions/42733877/remove-type-hints-in-python-source-programmatically


e=3

"""Triple string"""

xxx: int
xxx = list: ggg
print(xxx); print(e)

def default_combine_chars_fun_ZZ(elem_list: List[float], egg: int=4) -> List[str]: # TODO: remove annotations test
    pass

def in_fun():
    e=3
    xxx: int
    xxx = list: ggg
    print(xxx)

def foo(bar: Dict[T, List[T]],
        baz: Callable[[T], int] = 444 + 4,
        **kwargs) -> List[T]:
    pass


def foo(bar: Dict[T, List[T]],
        baz: Callable[[T], int] = lambda x: (x+3)/7,
        **kwargs) -> List[T]:
    pass


