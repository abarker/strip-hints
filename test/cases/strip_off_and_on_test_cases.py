"""

Also applies to namedtuples...

"""

from dataclasses import dataclass
from typing import NamedTuple

#
# Dataclass test.
#

x: int
y: float

def fun(x: int):
    pass

@dataclass
class Point:
    # strip-hints: off
    x: int
    y: int
    # strip-hints: on

x: int
y: float

def fun(x: int):
    pass

#
# NamedTuple test.
#

x: int
y: float

def fun(x: int):
    pass

class Employee(NamedTuple):
    # strip-hints: off
    name: str
    id: int = 3
    # strip-hints: on


x: int
y: float

def fun(x: int):
    pass

# strip-hints: off

class Employee(NamedTuple):
    name: str
    id: int = 3

x: int
y: float

def fun(x: int):
    pass

# strip-hints: on

x: int
y: float

def fun(x: int):
    pass

# This is the standard form of namedtule without hints; code could potentially be rewritten.
employee = Employee('Guido')
assert employee.id == 3

import typing, collections
Employee = typing.NamedTuple('Employee', [('name', str), ('id', int)])
Employee = collections.namedtuple('Employee', ['name', 'id'])

