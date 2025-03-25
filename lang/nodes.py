from typing import Any, Literal
import enum

class Node:
    lineno: int
    col_offset: int

    def __init__(self, *a, **k):
        annotations = self.__annotations__.copy() | {"lineno": int, "col_offset": int}
        assert len(a) <= len(annotations), "Too many arguments"
        for arg, annotation in zip(a, list(annotations)):
            del annotations[annotation]
            setattr(self, annotation, arg)
        for key, val in k.items():
            del annotations[key]
            setattr(self, key, val)
        assert len(annotations) == 0, f"Missing arguments {annotations}"
    def __repr__(self):
        attrs = {x: getattr(self, x) for x in dir(self) if not x.startswith("__")}
        attr_pairs = map(lambda x: f"{x[0]}={repr(x[1])}", attrs.items())
        return f"{self.__class__.__name__}({', '.join(attr_pairs)})"

class NodeStmt(Node):
    node: Node
class NodeExpr(Node):
    node: Node

class BinOp(enum.Enum):
    ADD = 1
    SUB = 2
    DIV = 3
    MUL = 4

class Comparator(enum.Enum):
    EQ = 5
    NEQ = 6
    GT = 7
    LT = 8
    GTE = 9
    LTE = 10
class UnaryOp(enum.Enum):
    NOT = 1
    POS = 2
    NEG = 3

class NodeBinOp(Node):
    left: Node
    op: BinOp
    right: Node
class NodeCompare(Node):
    left: Node
    op: BinOp
    right: Node
class NodeUnaryOp(Node):
    op: UnaryOp
    right: Node

class NodeIden(Node):
    iden: str
    context: Literal['load'] | Literal['store']

class NodeConst(Node):
    value: str | int | float

class NodeSlice(Node):
    lower: Node
    upper: Node
    step: Node

class NodeAttr(Node):
    left: Node
    right: str
    context: Literal['load'] | Literal['store']

class NodeIndex(Node):
    left: Node
    index: Node
    context: Literal['load'] | Literal['store']

class NodeCall(Node):
    called: Node
    args: list[Node]
    kwargs: dict[str, Node]

class NodePipe(Node):
    left: Node
    right: NodeCall
    is_first: bool

class NodeIf(Node):
    test: Node
    body: list[Node]
    orelse: list[Node]

class NodeFunc(Node):
    name: str
    args: list[str]
    attrs: list[str]
    body: list[Node]
    decorators: list[Node]
class NodeLambda(Node):
    args: list[str]
    attrs: list[str]
    body: list[Node]
class NodeReturn(Node):
    value: Node
class NodeAwait(Node):
    value: Node
class NodeList(Node):
    values: list[Node]
    context: Literal['load'] | Literal['store']
class NodeDict(Node):
    keys: list[Node]
    values: list[Node]
class NodeTuple(Node):
    values: list[Node]
    context: Literal['load'] | Literal['store']
class NodeAssign(Node):
    targets: list[Node]
    value: Node
class NodeClassDef(Node):
    name: str
    body: list[Node]
    bases: list[Node]
    decorators: list[Node]

class NodeImportRadon(Node):
    what: list[str]
    as_name: str | None

class FuncArg:
    pass
class PosArg(FuncArg):
    def __init__(self, name):
        self.name = name
class KwArg(FuncArg):
    def __init__(self, name, default):
        self.name = name
        self.default = default
class PosVarArg(FuncArg):
    def __init__(self, name):
        self.name = name
class KwVarArg(FuncArg):
    def __init__(self, name):
        self.name = name