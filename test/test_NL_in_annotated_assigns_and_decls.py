
from typing import List, NamedTuple

def foo(
  param1: int,
  param2: str = "zzz",
) -> namedtuple('outputs', [
  ('out1', str),
  ('out2', int),
]):
  pass

# x1
def foo(
  param1: int,
  param2: str = "zzz",
) -> namedtuple('outputs', [
  ('out1', str),
  ('out2', int),
]):
  # x2
  pass
# x3

egg: List[

        int

        ]

# Just before.
egg: List[

        int

        ] = 3
# Just after.

# before 2
egg: List[int] = 3
# after 2

# before 3
egg: List[int]
# after 3

# before 4
egg: List[

        int

        ]
# after 4

x = 3
egg: List[int]
x = 3

egg

def f():
    egg: List[int]

    pass

def f():
    # f 1
    egg: List[int]
    # f 2

    pass
