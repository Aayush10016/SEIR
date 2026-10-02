"""Plain data structures shared by every stage of the Software Analysis pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


# Relationship kinds, roughly ordered from strongest to weakest coupling.
EXTENDS = "extends"
IMPLEMENTS = "implements"
ENCLOSED_BY = "enclosed_by"          # nested type -> its outer type
FIELD = "field"
INSTANTIATION = "instantiation"
METHOD_CALL = "method_call"
STATIC_CALL = "static_call"
STATIC_REFERENCE = "static_reference"
PARAMETER = "parameter"
RETURN_TYPE = "return_type"
LOCAL_VARIABLE = "local_variable"
ANNOTATION = "annotation"
TYPE_REFERENCE = "type_reference"    # generics, casts, instanceof, throws, catch, X.class ...
IMPORT = "import"

RELATIONSHIP_KINDS = (
    EXTENDS, IMPLEMENTS, ENCLOSED_BY, FIELD, INSTANTIATION, METHOD_CALL, STATIC_CALL,
    STATIC_REFERENCE, PARAMETER, RETURN_TYPE, LOCAL_VARIABLE, ANNOTATION, TYPE_REFERENCE, IMPORT,
)


@dataclass
class ImportDecl:
    path: str            # e.g. "com.shop.payment.PaymentService" or "java.util" for wildcards
    static: bool
    wildcard: bool
    line: int


@dataclass
class MethodDecl:
    name: str
    line: int
    end_line: int
    parameter_types: list[str] = field(default_factory=list)
    return_type: str | None = None


@dataclass
class TypeDecl:
    """A class / interface / enum / record / annotation type declared in the repository."""

    fqn: str
    name: str
    kind: str            # class | interface | enum | record | annotation
    package: str
    file: str
    line: int
    end_line: int
    outer: str | None = None
    modifiers: list[str] = field(default_factory=list)
    annotations: list[str] = field(default_factory=list)
    methods: list[MethodDecl] = field(default_factory=list)
    fields: dict[str, str | None] = field(default_factory=dict)
    is_test: bool = False

    @property
    def loc(self) -> int:
        return self.end_line - self.line + 1


@dataclass
class SymbolReference:
    """An unresolved reference to a type, found by the AST analyzer.

    `name` is the type name exactly as written in source ("PaymentService",
    "Map.Entry", "com.shop.Money"); the extractor resolves it to a declared type.
    """

    owner: str           # FQN of the type the reference appears in
    name: str
    kind: str
    line: int
    member: str | None = None   # enclosing method ("<init>" for constructors, "<field>" ...)
    detail: str | None = None   # called method / referenced field name


@dataclass
class FileFacts:
    path: str
    package: str
    imports: list[ImportDecl] = field(default_factory=list)
    types: list[TypeDecl] = field(default_factory=list)
    references: list[SymbolReference] = field(default_factory=list)
    has_syntax_errors: bool = False


@dataclass(frozen=True)
class Relationship:
    """A resolved dependency: `source` depends on `target`."""

    source: str
    target: str
    kind: str
    file: str
    line: int
    member: str | None = None
    detail: str | None = None

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None}
