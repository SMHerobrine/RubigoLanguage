from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Node:
    line: int
    column: int


@dataclass(slots=True)
class Program(Node):
    functions: list[Function] = field(default_factory=list)
    raw_items: list[RawRust] = field(default_factory=list)


@dataclass(slots=True)
class TypeName(Node):
    name: str
    arguments: list[TypeName] = field(default_factory=list)


@dataclass(slots=True)
class Parameter(Node):
    name: str
    type_name: TypeName
    mutable: bool = False


@dataclass(slots=True)
class Function(Node):
    name: str
    parameters: list[Parameter]
    return_type: TypeName | None
    body: list[Statement]
    public: bool = False


class Statement(Node):
    pass


@dataclass(slots=True)
class Let(Statement):
    name: str
    value: Expression
    type_name: TypeName | None = None
    mutable: bool = False


@dataclass(slots=True)
class Assign(Statement):
    target: Expression
    value: Expression


@dataclass(slots=True)
class CompoundAssign(Statement):
    target: Expression
    operator: str
    value: Expression


@dataclass(slots=True)
class Print(Statement):
    values: list[Expression]


@dataclass(slots=True)
class If(Statement):
    branches: list[tuple[Expression, list[Statement]]]
    otherwise: list[Statement] | None = None


@dataclass(slots=True)
class While(Statement):
    condition: Expression
    body: list[Statement]


@dataclass(slots=True)
class ForEach(Statement):
    name: str
    iterable: Expression
    body: list[Statement]


@dataclass(slots=True)
class ForRange(Statement):
    name: str
    start: Expression
    end: Expression
    inclusive: bool
    body: list[Statement]


@dataclass(slots=True)
class Return(Statement):
    value: Expression | None
    type_name: TypeName | None = None


@dataclass(slots=True)
class Break(Statement):
    pass


@dataclass(slots=True)
class Continue(Statement):
    pass


@dataclass(slots=True)
class ExpressionStatement(Statement):
    expression: Expression


@dataclass(slots=True)
class RawRust(Statement):
    code: str


class Expression(Node):
    pass


@dataclass(slots=True)
class Name(Expression):
    value: str


@dataclass(slots=True)
class Literal(Expression):
    value: object
    kind: str


@dataclass(slots=True)
class ListLiteral(Expression):
    values: list[Expression]


@dataclass(slots=True)
class Unary(Expression):
    operator: str
    operand: Expression


@dataclass(slots=True)
class Binary(Expression):
    left: Expression
    operator: str
    right: Expression


@dataclass(slots=True)
class Call(Expression):
    callee: Expression
    arguments: list[Expression]


@dataclass(slots=True)
class Index(Expression):
    target: Expression
    index: Expression


@dataclass(slots=True)
class Field(Expression):
    target: Expression
    name: str
