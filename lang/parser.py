import string
import enum
from .nodes import *

class TokenType(enum.Enum):
    EOF = 0

    IDEN = 1
    STR = 2
    INT = 3
    FLOAT = 4
    KEYWORD = 5

    AT = "@"

    LPAR = "("
    RPAR = ")"
    LBRK = "["
    RBRK = "]"
    LANG = "<"
    RANG = ">"

    DOT = "."
    COMMA = ","
    SEMICOLON = ";"

    PLUS = "+"
    MINUS = 50
    MULTIPLY = "*"
    DIVIDE = "/"
    MOD = "%"

    ASSIGN = 100

    EQ = 120
    NEQ = 121
    GT = 122
    LT = 123
    GTE = 124
    LTE = 125

    NOT = 140
    LOGIC_AND = 141
    LOGIC_OR = 142
    
    BIN_AND = 150
    BIN_OR = 151
    BIN_XOR = 152

    PIPE_FIRST = 160
    PIPE_LAST = 161

class Keyword(enum.Enum):
    IF = "if"
    IMPORT = "import"
    AS = "as"
    LAMBDA = "lambda"
    THEN = "then"
    ELSE = "else"
    FN = "fn"
    END = "end"
    AWAIT = "await"

TOKENTYPES = [i.value for i in TokenType]
KEYWORDS = [i.value for i in Keyword]

class Token:
    def __init__(self, token_type, line, offset, value=None):
        self.type = token_type
        self.line = line
        self.offset = offset
        self.value = value
    def __repr__(self):
        return f"<{self.type}{(' : ' + repr(self.value)) if self.value is not None else ''}>"
    
class Lexer:
    def __init__(self, src):
        self.idx = -1
        self.line = 1
        self.rel = 0
        self.ch = None
        self.text = src + " "
        self._next()
    def _next(self, step=1):
        self.idx += step
        self.rel += step
        self.ch = self.text[self.idx] if self.idx < len(self.text) else None
        if self.ch == "\n":
            self.line += 1
            self.rel = 1
        return self.ch

    def get_next(self):
        if self.ch is None:
            return Token(TokenType.EOF, -1, 0)
        while self.ch in " \t\r\n":
            self._next()
            if self.ch is None:
                return Token(TokenType.EOF, -1, 0)
        if self.ch in TOKENTYPES:
            v = Token(TokenType(self.ch), self.line, self.rel)
            self._next()
            return v
        if self.ch in "0123456789":
            n = ""
            rel = self.rel
            while self.ch in "0123456789.":
                n += self.ch
                self._next()
            if "." in n:
                try:
                    return Token(TokenType.FLOAT, self.line, rel, float(n))
                except ValueError:
                    raise SyntaxError(f"Invalid float '{n}'")
            return Token(TokenType.INT, self.line, rel, int(n))
        if self.ch in "\"'":
            s = ""
            rel = self.rel
            quote = self.ch
            self._next()
            while self.ch != quote:
                s += self.ch
                self._next()
            self._next()
            return Token(TokenType.STR, self.line, rel, s)
        if self.ch in string.ascii_letters + "_":
            i = ""
            rel = self.rel
            while self.ch in string.ascii_letters + "_123456789":
                i += self.ch
                self._next()
            if i in KEYWORDS:
                return Token(TokenType.KEYWORD, self.line, rel, Keyword(i))
            return Token(TokenType.IDEN, self.line, rel, i)
        if self.ch == "=":
            self._next()
            if self.ch == "=":
                self._next()
                return Token(TokenType.EQ, self.line, self.rel-2)
            return Token(TokenType.ASSIGN, self.line, self.rel-1)
        if self.ch == "!":
            self._next()
            if self.ch == "=":
                self._next()
                return Token(TokenType.NEQ, self.line, self.rel-2)
            return Token(TokenType.NOT, self.line, self.rel-1)
        if self.ch == ">":
            self._next()
            if self.ch == "=":
                self._next()
                return Token(TokenType.GTE, self.line, self.rel-2)
            return Token(TokenType.GT, self.line, self.rel-1)
        if self.ch == "-":
            self._next()
            if self.ch == "-":
                while self.ch is not None and self.ch != "\n":
                    self._next()
                return self.get_next()
            return Token(TokenType.MINUS, self.line, self.rel-1)
        if self.ch == "<":
            self._next()
            if self.ch == "=":
                self._next()
                return Token(TokenType.LTE, self.line, self.rel-2)
            return Token(TokenType.LT, self.line, self.rel-1)
        if self.ch == "|":
            self._next()
            if self.ch == "|":
                self._next()
                return Token(TokenType.LOGIC_OR, self.line, self.rel-2)
            elif self.ch == ">":
                self._next()
                if self.ch == ">":
                    self._next()
                    return Token(TokenType.PIPE_LAST, self.line, self.rel-3)
                return Token(TokenType.PIPE_FIRST, self.line, self.rel-2)
            return Token(TokenType.BIN_OR, self.line, self.rel-1)
        raise SyntaxError(f"Invalid character '{self.ch}'")

class Parser:
    def __init__(self, src):
        self.lexer = Lexer(src)
        self.tok: Token = None
        self.next_tok()
    def next_tok(self):
        self.tok = self.lexer.get_next()
    def next_ch(self):
        return self.lexer._next()
    def run(self):
        body = []
        while self.tok.type != TokenType.EOF:
            body.append(self.statement())
        return body
    def statement(self):
        while self.tok.type == TokenType.SEMICOLON:
            self.next_tok()
        if self.tok.type == TokenType.KEYWORD:
            if self.tok.value == Keyword.IF:
                return self.kw_if()
            elif self.tok.value == Keyword.FN:
                return self.func()
            elif self.tok.value == Keyword.IMPORT:
                return self.kw_import()
            elif self.tok.value in (Keyword.LAMBDA, Keyword.AWAIT):
                pass
            else:
                assert False, f"keyword {self.tok} cannot be used here"
        v = self.expr()
        if self.tok.type == TokenType.ASSIGN:
            if isinstance(v, (NodeIden, NodeAttr, NodeIndex)):
                v.context = "store"
            else:
                assert False, "assignment to this expression is not supported"
            self.next_tok()
            v = NodeAssign([v], self.expr(), lineno=v.lineno, col_offset=v.col_offset)
        assert self.tok.type == TokenType.SEMICOLON, f"';' expected, got {self.tok}"
        self.next_tok()
        return NodeExpr(v, lineno=v.lineno, col_offset=v.col_offset)
    
    def kw_import(self):
        assert self.tok.value == Keyword.IMPORT, f"'import' expected, got {self.tok}"
        ln, co = self.tok.line, self.tok.offset
        self.next_tok()

        iden = []
        assert self.tok.type == TokenType.IDEN, f"identifier expected"
        iden.append(self.tok.value)
        self.next_tok()

        while self.tok.type == TokenType.DOT:
            self.next_tok()
            assert self.tok.type == TokenType.IDEN, f"identifier expected"
            iden.append(self.tok.value)
            self.next_tok()
        
        as_name = None
        if self.tok.type == TokenType.KEYWORD and self.tok.value == Keyword.AS:
            self.next_tok()
            assert self.tok.type == TokenType.IDEN, f"identifier expected"
            as_name = self.tok.value
            self.next_tok()
        
        assert self.tok.type == TokenType.SEMICOLON, f"';' expected, got {self.tok}"
        self.next_tok()

        return NodeExpr(NodeImportRadon(iden, as_name, lineno=ln, col_offset=co), lineno=ln, col_offset=co)
        
    def kw_if(self):
        assert self.tok.value == Keyword.IF, f"'if' expected, got {self.tok}"
        ln, co = self.tok.line, self.tok.offset
        self.next_tok()
        expr = self.expr()

        assert self.tok.type == TokenType.KEYWORD and self.tok.value == Keyword.THEN, f"'then' expected, got {self.tok}"
        self.next_tok()

        body = []
        orelse = []
        while True:
            assert self.tok.type != TokenType.EOF, f"'end' expected for an if-statement"
            if self.tok.type == TokenType.KEYWORD:
                if self.tok.value == Keyword.END:
                    self.next_tok()
                    break
                elif self.tok.value == Keyword.ELSE:
                    self.next_tok()
                    if self.tok.value == Keyword.IF:
                        orelse = [self.kw_if()]
                        break
                    else:
                        while True:
                            assert self.tok.type != TokenType.EOF, f"'end' expected for an if-statement"
                            if self.tok.type == TokenType.KEYWORD:
                                if self.tok.value == Keyword.END:
                                    self.next_tok()
                                    break
                            orelse.append(self.statement())
                        break
            body.append(self.statement())
        return NodeIf(expr, body, orelse, lineno=ln, col_offset=co)

    def expr(self):
        return self.expr_compare()
    def expr_compare(self):
        left = self.expr_pipe()
        while self.tok.type in (TokenType.EQ, TokenType.NEQ, TokenType.GT, TokenType.LT, TokenType.GTE, TokenType.LTE):
            op = getattr(Comparator, self.tok.type.name)
            self.next_tok()
            left = NodeCompare(left, op, self.expr_compare(), lineno=left.lineno, col_offset=left.col_offset)
        return left
    def expr_pipe(self):
        left = self.expr_add_sub()
        while self.tok.type in (TokenType.PIPE_FIRST, TokenType.PIPE_LAST):
            is_first = self.tok.type == TokenType.PIPE_FIRST
            self.next_tok()
            right = self.expr_add_sub()
            if not isinstance(right, NodeCall):
                right = NodeCall(right, [], {}, lineno=right.lineno, col_offset=right.col_offset)
            left = NodePipe(left, right, is_first, lineno=left.lineno, col_offset=left.col_offset)
        return left
    def expr_add_sub(self):
        left = self.expr_mul_div()
        while self.tok.type in (TokenType.PLUS, TokenType.MINUS):
            op = {TokenType.PLUS: BinOp.ADD, TokenType.MINUS: BinOp.SUB}[self.tok.type]
            self.next_tok()
            left = NodeBinOp(left, op, self.expr_add_sub(), lineno=left.lineno, col_offset=left.col_offset)
        return left
    def expr_mul_div(self):
        left = self.expr_idx_attr_call()
        while self.tok.type in (TokenType.MULTIPLY, TokenType.DIVIDE):
            op = {TokenType.MULTIPLY: BinOp.MUL, TokenType.DIVIDE: BinOp.DIV}[self.tok.type]
            self.next_tok()
            left = NodeBinOp(left, op, self.expr_mul_div(), lineno=left.lineno, col_offset=left.col_offset)
        return left    
    def expr_idx_attr_call(self):
        left = self.expr_final()
        while self.tok.type in (TokenType.DOT, TokenType.LPAR, TokenType.LBRK):
            if self.tok.type == TokenType.DOT:
                self.next_tok()
                assert self.tok.type == TokenType.IDEN, f"identifier expected, got {self.tok}"
                left = NodeAttr(left, self.tok.value, "load", lineno=self.tok.line, col_offset=self.tok.offset)
                self.next_tok()
            elif self.tok.type == TokenType.LBRK:
                self.next_tok()
                index = self.expr()
                assert self.tok.type == TokenType.RBRK, f"']' expected, got {self.tok}"
                self.next_tok()
                left = NodeIndex(left, index, "load", lineno=self.tok.line, col_offset=self.tok.offset)
            elif self.tok.type == TokenType.LPAR:
                self.next_tok()
                args = []
                kwargs = {}
                while True:
                    if self.tok.type == TokenType.RPAR:
                        self.next_tok()
                        break
                    expr = self.expr()
                    if self.tok.type == TokenType.ASSIGN:
                        assert isinstance(expr, NodeIden), "identifier expected as a keyword argument"
                        self.next_tok()
                        kwargs[expr.iden] = self.expr()
                    else:
                        args.append(expr)
                    assert self.tok.type in (TokenType.RPAR, TokenType.COMMA), f"',' or ')' expected, got {self.tok}"
                    if self.tok.type == TokenType.RPAR:
                        self.next_tok()
                        break
                    else:
                        self.next_tok()
                left = NodeCall(left, args, kwargs, lineno=self.tok.line, col_offset=self.tok.offset)
            else:
                raise NotImplementedError(f"expr7 {self.tok}")
        return left
    
    def expr_final(self):
        if self.tok.type in (TokenType.INT, TokenType.STR, TokenType.FLOAT):
            v = NodeConst(self.tok.value, lineno=self.tok.line, col_offset=self.tok.offset)
            self.next_tok()
            return v
        elif self.tok.type == TokenType.IDEN:
            v = NodeIden(self.tok.value, "load", lineno=self.tok.line, col_offset=self.tok.offset)
            self.next_tok()
            return v
        elif self.tok.type == TokenType.LPAR:
            self.next_tok()
            data = []
            data.append(self.expr())
            while self.tok.type == TokenType.COMMA:
                self.next_tok()
                if self.tok.type == TokenType.RPAR:
                    self.next_tok()
                    return NodeTuple(data)
                data.append(self.expr())
            assert self.tok.type == TokenType.RPAR, "')' expected"
            self.next_tok()
            if len(data) == 1:
                return data[0]
            return NodeTuple(data)
        elif self.tok.type == TokenType.LBRK:
            ln, co = self.tok.line, self.tok.offset
            self.next_tok()
            args = []
            while True:
                if self.tok.type == TokenType.RBRK:
                    self.next_tok()
                    break
                args.append(self.expr())
                assert self.tok.type in (TokenType.RBRK, TokenType.COMMA), "',' or ']' expected"
                if self.tok.type == TokenType.RBRK:
                    self.next_tok()
                    break
                else:
                    self.next_tok()
            return NodeList(args, "load", lineno=ln, col_offset=co)
        elif self.tok.type == TokenType.KEYWORD:
            if self.tok.value == Keyword.LAMBDA:
                return self.kw_lambda()
            elif self.tok.value == Keyword.AWAIT:
                ln, co = self.tok.line, self.tok.offset
                self.next_tok()
                return NodeAwait(self.expr(), lineno=ln, col_offset=co)
            else:
                assert False, f"Keyword {self.tok.value} cannot be used in expression"
        elif self.tok.type == TokenType.NOT:
            self.next_tok()
            return NodeUnaryOp(UnaryOp.NOT, self.expr())
        assert False, (f"Expected atom, got {self.tok}")
    
    def parse_func_args(self):
        assert self.tok.type == TokenType.LPAR, f"'(' expected"
        self.next_tok()

        args = []
        while True:
            if self.tok.type == TokenType.RPAR:
                self.next_tok()
                break
            if self.tok.type == TokenType.IDEN:
                i = self.get_iden()
                if self.tok.type == TokenType.ASSIGN:
                    self.next_tok()
                    args.append(KwArg(i, self.expr()))
                else:
                    args.append(PosArg(i))
            elif self.tok.type == TokenType.MULTIPLY:
                self.next_tok()
                if self.tok.type == TokenType.MULTIPLY:
                    self.next_tok()
                    i = self.get_iden()
                    args.append(KwVarArg(i))
                else:
                    i = self.get_iden()
                    args.append(PosVarArg(i))
            else:
                assert False, f"invalid fn/lambda argument"
            assert self.tok.type in (TokenType.RPAR, TokenType.COMMA), "',' or ')' expected"
            if self.tok.type == TokenType.RPAR:
                self.next_tok()
                break
            self.next_tok()
        
        attrs = []
        while self.tok.type == TokenType.AT:
            self.next_tok()
            attrs.append(self.expr())
        return args, attrs

    def func(self):
        assert self.tok.type == TokenType.KEYWORD and self.tok.value == Keyword.FN, f"'fn' expected"
        ln, co = self.tok.line, self.tok.offset
        self.next_tok()

        name = self.get_iden()
        args, attrs = self.parse_func_args()
        
        body = []
        while True:
            assert self.tok.type != TokenType.EOF, f"'end' expected for an fn-statement"
            if self.tok.type == TokenType.KEYWORD and self.tok.value == Keyword.END:
                self.next_tok()
                break
            body.append(self.statement())
        
        return NodeFunc(name, args, attrs, body, [], lineno=ln, col_offset=co)
    
    def kw_lambda(self):
        assert self.tok.type == TokenType.KEYWORD and self.tok.value == Keyword.LAMBDA, f"'lambda' expected"
        ln, co = self.tok.line, self.tok.offset
        self.next_tok()

        args, attrs = self.parse_func_args()
        
        body = []
        while True:
            assert self.tok.type != TokenType.EOF, f"'end' expected for a lambda-statement"
            if self.tok.type == TokenType.KEYWORD and self.tok.value == Keyword.END:
                self.next_tok()
                break
            body.append(self.statement())
        return NodeLambda(args, attrs, body, lineno=ln, col_offset=co)
    
    def get_iden(self):
        assert self.tok.type == TokenType.IDEN, f"identifier expected"
        v = self.tok.value
        self.next_tok()
        return v
    