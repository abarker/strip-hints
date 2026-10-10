"""

The simple cases are handled EXCEPT the last one in parentheses.
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

# TODO: Found a bug, this keeps the comment before the `= 0` assignment on the line.
# Need to move it BEFORE the comment, not after.
d['c']: List[ # This works, but adds all the whitespace before the `= 0`
        int,  # part on the first line (the `=` is moved up).
        int] = 0

# Note that even a parenthesized name is considered an expression, not a simple name:

(x): int      # Annotates x with int, (x) treated as expression by compiler.
(y): int = 0  # Same situation here.


