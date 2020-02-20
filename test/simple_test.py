

def simp(x: int, y: bool) -> bool:
    def q(x: int=4):
        x: int=4

egg : int

def foo(bar: Dict[T, List[T]], egg=lambda x,y: 4*(3+3),
        egg2: int= lambda: (4),
        baz: Callable[[T], int] = 444 + 4,
        **kwargs) -> List[T]:
    pass

#
# Below test some cases that might get confused with an annotated variable or assignment.
#

m = 2
string = 4
if m == ")": string += m
else: string = m + string

if m == ")": \
    string += m
else: \
    string = m + string

if m == ")": \
    string += m
else: \
    string = m + string

if m == ")": # comment
    string += m
else: # comment
    string = m + string

