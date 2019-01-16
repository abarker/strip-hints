"""

These aren't currently handled (except the simplest dotted access), but shouldn't
be too difficult to add.

The examples are from PEP-526.

"""

class Cls:
    pass

c = Cls()
c.x: int = 0  # Annotates c.x with int.
c.y: int      # Annotates c.y with int.

d = {}
d['a']: int = 0  # Annotates d['a'] with int.
d['b']: int      # Annotates d['b'] with int.

# Note that even a parenthesized name is considered an expression, not a simple name:

(x): int      # Annotates x with int, (x) treated as expression by compiler.
(y): int = 0  # Same situation here.


