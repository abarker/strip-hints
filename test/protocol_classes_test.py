"""

Test `Protocol` classes (a pass is added to the first type annotation to
avoid invalid syntax.

"""

from typing import Protocol
class Style(Protocol):
    color: str
    effect: str

    name: Callable[[T],
            int]
