import ast
import random
from .nodes import *

class Context:
    def __init__(self):
        self.ctx_id = "".join([random.choice("0123456789abcdef") for _ in range(12)])
        self.ctr = 0
        self.preinit_statements = []
    
    def get_unique_name(self):
        self.ctr += 1
        return f"_radon_{self.ctx_id}_local_{self.ctr}"

    def add_preinit(self, stmt):
        self.preinit_statements.append(stmt)

class Translator:
    def __init__(self):
        self.contexts: list[Context] = []

    def run(self, c_ast: list[Node]):
        self.contexts.append(Context())
        body = list(map(self.visit, c_ast))
        v = ast.Module(self.contexts[-1].preinit_statements + body, type_ignores=[])
        self.contexts.pop()
        return v
    
    def no_visitor(self, node: Node):
        raise NotImplementedError(f"Visitor for node {node} is not implemented!")
    def visit(self, node: Node):
        return getattr(self, "visit_" + node.__class__.__name__, self.no_visitor)(node)
    
    def visit_NodeCall(self, node: NodeCall):
        return ast.Call(self.visit(node.called), list(map(self.visit, node.args)), [ast.keyword(arg=kw, value=self.visit(kw_val), lineno=node.lineno, col_offset=node.col_offset) for kw, kw_val in node.kwargs.items()], lineno=node.lineno, col_offset=node.col_offset)
    def visit_NodeIden(self, node: NodeIden):
        return ast.Name(node.iden, ctx=ast.Load() if node.context == "load" else ast.Store(), lineno=node.lineno, col_offset=node.col_offset)
    def visit_NodeConst(self, node: NodeConst):
        return ast.Constant(node.value, lineno=node.lineno, col_offset=node.col_offset)
    def visit_NodeStmt(self, node: NodeStmt):
        return node.node
    def visit_NodeExpr(self, node: NodeExpr):
        x = self.visit(node.node)
        return ast.Expr(x, lineno=node.lineno, col_offset=node.col_offset) if not isinstance(x, (ast.FunctionDef, ast.Assign)) else x
    def visit_NodeBinOp(self, node: NodeBinOp):
        return ast.BinOp(self.visit(node.left), {
            BinOp.ADD: ast.Add(),
            BinOp.SUB: ast.Sub(),
            BinOp.MUL: ast.Mult(),
            BinOp.DIV: ast.Div()
        }[node.op], self.visit(node.right), lineno=node.lineno, col_offset=node.col_offset)
    def visit_NodeClassDef(self, node: NodeClassDef):
        return ast.ClassDef(name=node.name, bases=list(map(self.visit, node.bases)), keywords=[], body=list(map(self.visit, node.body)) if len(node.body) > 0 else [ast.Pass(lineno=node.lineno, col_offset=node.col_offset)], decorator_list=[], lineno=node.lineno, col_offset=node.col_offset)
    def visit_NodeCompare(self, node: NodeCompare):
        return ast.Compare(self.visit(node.left), [{
            Comparator.EQ: ast.Eq(),
            Comparator.NEQ: ast.NotEq(),
            Comparator.GT: ast.Gt(),
            Comparator.LT: ast.Lt(),
            Comparator.GTE: ast.GtE(),
            Comparator.LTE: ast.LtE(),
        }[node.op]], [self.visit(node.right)], lineno=node.lineno, col_offset=node.col_offset)
    def visit_NodeIf(self, node: NodeIf):
        return ast.If(self.visit(node.test), list(map(self.visit, node.body)), list(map(self.visit, node.orelse)), lineno=node.lineno, col_offset=node.col_offset)

    def process_func_body(self, body: list[Node]):
        if len(body) > 0:
            if isinstance(body[-1], NodeExpr):
                body = body.copy()
                body[-1] = NodeReturn(body[-1].node, lineno=body[-1].lineno, col_offset=body[-1].col_offset)
        return list(map(self.visit, body))
    def process_func_args(self, node: Node, args: list[FuncArg]):
        # ast.arguments([], list(map(lambda x: ast.arg(x, lineno=node.lineno, col_offset=node.col_offset), node.args)), None, [], [], None, [])
        "Module(body=[FunctionDef(name='x', args=arguments(posonlyargs=[], args=[arg(arg='a'), arg(arg='b')], vararg=arg(arg='c'), kwonlyargs=[arg(arg='d'), arg(arg='e')], kw_defaults=[Constant(value=1), Constant(value=2)], kwarg=arg(arg='f'), defaults=[]), body=[Pass()], decorator_list=[], type_params=[])], type_ignores=[])"
        posargs = []
        kwargs = []
        kwdefaults = []
        defaults = []
        vararg = None
        kwarg = None

        can_do_posargs = True
        can_do_kwargs = True
        for arg in args:
            if isinstance(arg, PosArg):
                assert can_do_posargs, "positional arguments cannot go after vararg / kwargs!"
                posargs.append(ast.arg(arg=arg.name, lineno=node.lineno, col_offset=node.col_offset))
            elif isinstance(arg, PosVarArg):
                assert vararg is None, "only 1 vararg is allowed!"
                vararg = ast.arg(arg=arg.name, lineno=node.lineno, col_offset=node.col_offset)
                can_do_posargs = False
            elif isinstance(arg, KwArg):
                assert can_do_kwargs, "kwargs cannot follow kw-vararg!"
                if vararg is None:
                    posargs.append(ast.arg(arg=arg.name, lineno=node.lineno, col_offset=node.col_offset))
                    defaults.append(self.visit(arg.default))
                else:
                    kwargs.append(ast.arg(arg=arg.name, lineno=node.lineno, col_offset=node.col_offset))
                    kwdefaults.append(self.visit(arg.default))
                can_do_posargs = False
            elif isinstance(arg, KwVarArg):
                assert kwarg is None, "only 1 vararg is allowed!"
                kwarg = ast.arg(arg=arg.name, lineno=node.lineno, col_offset=node.col_offset)
                can_do_posargs = False
                can_do_kwargs = False
        
        return ast.arguments([], posargs, vararg, kwargs, kwdefaults, kwarg, defaults)

    def visit_NodeFunc(self, node: NodeFunc):
        """
        "Module(body=[FunctionDef(name='x', args=arguments(posonlyargs=[], args=[arg(arg='a'), arg(arg='b')], kwonlyargs=[], kw_defaults=[], defaults=[]), body=[Pass()], decorator_list=[], type_params=[])], type_ignores=[])"
        """
        attrs, decos = self.process_fnattrs(node.attrs)

        fndef = ast.FunctionDef if not attrs[0] else ast.AsyncFunctionDef

        self.contexts.append(Context())
        body = self.process_func_body(node.body)
        v = fndef(node.name, self.process_func_args(node, node.args), self.contexts[-1].preinit_statements + body, decos, type_params=[], lineno=node.lineno, col_offset=node.col_offset)
        self.contexts.pop()
        return v
    
    def process_fnattrs(self, attrs):
        is_async = False
        custom_name = None
        rest = []
        for attr in attrs:
            if isinstance(attr, NodeIden) and attr.iden == "async":
                is_async = True
            elif isinstance(attr, NodeCall) and isinstance(attr.called, NodeIden) and attr.called.iden == "def":
                assert len(attr.args) == 1 and isinstance(attr.args[0], NodeConst) and isinstance(attr.args[0].value, str), "@def('...') expected"
                custom_name = attr.args[0].value
            else:
                rest.append(self.visit(attr))
        return [is_async, custom_name], rest

    def visit_NodeLambda(self, node: NodeFunc):
        """
        "Module(body=[FunctionDef(name='x', args=arguments(posonlyargs=[], args=[arg(arg='a'), arg(arg='b')], kwonlyargs=[], kw_defaults=[], defaults=[]), body=[Pass()], decorator_list=[], type_params=[])], type_ignores=[])"
        """
        
        attrs, decos = self.process_fnattrs(node.attrs)

        fndef = ast.FunctionDef if not attrs[0] else ast.AsyncFunctionDef
        name = (self.contexts[-1].get_unique_name()) if attrs[1] is None else attrs[1]

        v = fndef(name, self.process_func_args(node, node.args), self.process_func_body(node.body), decorator_list=decos, type_params=[], lineno=node.lineno, col_offset=node.col_offset)

        for deco in decos:
            v = ast.Call(self.visit(deco), [v], [], lineno=node.lineno, col_offset=node.col_offset)
        self.contexts[-1].add_preinit(v)
        return ast.Name(name, ast.Load(), lineno=node.lineno, col_offset=node.col_offset)
    def visit_NodeReturn(self, node: NodeReturn):
        return ast.Return(self.visit(node.value), lineno=node.lineno, col_offset=node.col_offset)
    def visit_NodeList(self, node: NodeList):
        return ast.List(list(map(self.visit, node.values)), ctx=ast.Load() if node.context == "load" else ast.Store(), lineno=node.lineno, col_offset=node.col_offset)
    def visit_NodeDict(self, node: NodeDict):
        return ast.Dict(list(map(self.visit, node.keys)), list(map(self.visit, node.values)), lineno=node.lineno, col_offset=node.col_offset)
    def visit_NodeAttr(self, node: NodeAttr):
        return ast.Attribute(self.visit(node.left), node.right, ctx=ast.Load() if node.context == "load" else ast.Store(), lineno=node.lineno, col_offset=node.col_offset)
    def visit_NodePipe(self, node: NodePipe):
        call_node = node.right
        if node.is_first:
            call_node.args.insert(0, node.left)
        else:
            call_node.args.append(node.left)
        return self.visit(call_node)
    def visit_NodeAssign(self, node: NodeAssign):
        return ast.Assign(list(map(self.visit, node.targets)), value=self.visit(node.value), lineno=node.lineno, col_offset=node.col_offset)
    def visit_NodeAwait(self, node: NodeAwait):
        return ast.Await(self.visit(node.value), lineno=node.lineno, col_offset=node.col_offset)
    def visit_NodeIndex(self, node: NodeIndex):
        return ast.Subscript(self.visit(node.left), self.visit(node.index), ctx=ast.Load() if node.context == "load" else ast.Store(), lineno=node.lineno, col_offset=node.col_offset)
    def visit_NodeImportRadon(self, node: NodeImportRadon):
        call = ast.Call(ast.Name("_global_radon_se_import", ctx=ast.Load(), lineno=node.lineno, col_offset=node.col_offset), [
            ast.List(list(ast.Constant(x, lineno=node.lineno, col_offset=node.col_offset) for x in node.what), ctx=ast.Load(), lineno=node.lineno, col_offset=node.col_offset),
            ast.Constant(node.as_name, lineno=node.lineno, col_offset=node.col_offset)
        ], [], lineno=node.lineno, col_offset=node.col_offset)
        return ast.Assign([ast.Name(node.what[-1] if node.as_name is None else node.as_name, ast.Store(), lineno=node.lineno, col_offset=node.col_offset)], call, lineno=node.lineno, col_offset=node.col_offset)

    def visit_NodeSlice(self, node: NodeSlice):
        return ast.Slice(self.visit(node.lower) if node.lower else None, self.visit(node.upper) if node.upper else None, self.visit(node.step) if node.step else None, lineno=node.lineno, col_offset=node.col_offset)