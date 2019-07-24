"""

The simple cases are handled except the last one in parentheses.
Run without syntax checking to check vs. the result file.

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


