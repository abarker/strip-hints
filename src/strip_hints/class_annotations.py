"""Find the classes whose annotations are runtime fields rather than hints.

The annotations in the body of a dataclass, a `NamedTuple` or `TypedDict`
subclass, or a class from a library such as pydantic or attrs define the
fields of the class, so they need to be kept for the code to work.  These
classes are found by resolving their decorators and base classes through the
imports in the file, and comparing the qualified names with the names passed
to the `--keep-class-annotations` option.
"""

import tokenize

from .token_list import ignored_types_set

STANDARD_NAMES = ("dataclasses.dataclass", "typing.NamedTuple", "typing.TypedDict",
                  "typing_extensions.NamedTuple", "typing_extensions.TypedDict")

def parse_keep_names(value):
    """Return the set of names to match for a `keep_class_annotations` value, or
    `None` if the option is off.  The value can be true for only the standard
    names, or a comma-separated string or a sequence of names to add to them."""
    if value is None or value is False:
        return None
    if value is True:
        value = ()
    elif isinstance(value, str):
        value = value.split(",")
    return set(STANDARD_NAMES).union(n.strip() for n in value if n.strip())

def significant_tokens(logical_line):
    """Return a list of the tokens in a logical line, without comments or newlines."""
    return list(logical_line.iter_with_skips(skip_types=ignored_types_set))

def split_on_commas(tokens):
    """Split a list of tokens on the commas at the nesting level of the first one,
    dropping any empty parts."""
    parts = [[]]
    for t in tokens:
        if t.is_op(",") and t.nesting_level == tokens[0].nesting_level:
            parts.append([])
        else:
            parts[-1].append(t)
    return [p for p in parts if p]

def dotted_name(tokens):
    """Return the dotted name, such as `a.b.c`, at the start of a list of tokens."""
    parts = []
    for t in tokens:
        expect_name = len(parts) % 2 == 0
        if not (t.type == tokenize.NAME if expect_name else t.is_op(".")):
            break
        parts.append(t.string)
    return "".join(parts).rstrip(".")

def add_imports(tokens, import_map):
    """Add the local names bound by an import statement to `import_map`, which
    maps each local name to the set of qualified names it can refer to."""
    strings = [t.string for t in tokens]
    if strings[0] == "import":
        for item in split_on_commas(tokens[1:]):
            name = dotted_name(item)
            if len(item) > 2 and item[-2].string == "as":
                import_map.setdefault(item[-1].string, set()).add(name)
            else: # Only the first name is bound, e.g. `a` for `import a.b`.
                first = name.split(".")[0]
                import_map.setdefault(first, set()).add(first)
    elif strings[0] == "from" and "import" in strings:
        i = strings.index("import")
        module = "".join(strings[1:i]) # Relative modules start with dots.
        separator = "" if module.endswith(".") else "."
        names = [t for t in tokens[i+1:] if t.string not in ("(", ")")]
        for item in split_on_commas(names):
            if item[0].string != "*": # The last name is the alias, if any.
                import_map.setdefault(item[-1].string, set()).add(
                                              module + separator + item[0].string)

def resolve(name, import_map):
    """Return the set of qualified names that a dotted name can refer to.  A name
    that was not imported refers to itself."""
    first, dot, rest = name.partition(".")
    return {q + dot + rest for q in import_map.get(first, {first})}

def name_matches(qualified_name, keep_names):
    """Return true if a qualified name is one of `keep_names` or is inside one of
    them, so that `pydantic` matches `pydantic.BaseModel`."""
    return any(qualified_name == k or qualified_name.startswith(k + ".")
               for k in keep_names)

def class_bases(tokens):
    """Return the dotted names of the base classes in the tokens of a class
    statement.  Keyword arguments such as `metaclass=M` are skipped."""
    i = 2
    if i < len(tokens) and tokens[i].is_op("["): # Skip PEP 695 type parameters.
        while not (tokens[i].is_op("]") and tokens[i].nesting_level == 1):
            i += 1
        i += 1
    if i >= len(tokens) or not tokens[i].is_op("("):
        return []
    end = i + 1
    while not (tokens[end].is_op(")") and tokens[end].nesting_level == 1):
        end += 1
    bases = []
    for item in split_on_commas(tokens[i+1:end]):
        if not any(t.is_op("=") and t.nesting_level == 1 for t in item):
            bases.append(dotted_name(item))
    return [b for b in bases if b]

class ClassMatcher(object):
    """Match the class statements whose annotations are kept, one logical line at
    a time, keeping the decorators seen so far."""

    def __init__(self, logical_lines, keep_names):
        """Build the import map from all the logical lines of a file.  The set
        `keep_names` holds the qualified names to match."""
        self.keep_names = set(keep_names)
        self.import_map = {}
        self.decorators = []
        for line in logical_lines:
            tokens = significant_tokens(line)
            if tokens and tokens[0].string in ("import", "from"):
                add_imports(tokens, self.import_map)

    def starts_kept_body(self, tokens):
        """Return true if the tokens of a logical line are a matching class statement
        which is followed by an indented body."""
        if not tokens:
            return False
        if tokens[0].is_op("@"): # Decorators are the logical lines before a class.
            self.decorators.append(dotted_name(tokens[1:]))
            return False
        decorators, self.decorators = self.decorators, []
        if tokens[0].string != "class" or len(tokens) < 2:
            return False
        names = decorators + class_bases(tokens)
        if not any(name_matches(q, self.keep_names)
                   for n in names for q in resolve(n, self.import_map)):
            return False
        self.keep_names.add(tokens[1].string) # Match local subclasses by the name.
        return tokens[-1].string == ":"
