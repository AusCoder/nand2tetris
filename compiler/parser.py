from collections import deque
from dataclasses import dataclass
from typing import Any, List, Optional, Tuple

from tokenizer import (
    Token,
    Keyword,
    Symbol,
    Identifier,
    IntegerConstant,
    StringConstant,
)


class ParseError(Exception):
    pass


# TODO: line_num is derivable with some introspection shenanigans
@dataclass
class Node:
    line_num: int


# TODO: type annotations wrong
@dataclass
class ClassVarDec(Node):
    modifier: str  # static, field
    type_: str
    name: str


@dataclass
class Parameter:
    type_: str
    name: str


@dataclass
class VarDec(Node):
    type_: str
    name: str


@dataclass
class Term(Node):
    pass


@dataclass
class ConstantTerm(Term):
    value: Token


@dataclass
class VarTerm(Term):
    name: Token


@dataclass
class VarIndexTerm(Term):
    name: Token
    expression: Any


@dataclass
class SubroutineCallTerm(Term):
    name: Token
    arguments: Any
    # TODO: or class.method(x, y, z)


@dataclass
class ExpressionTerm(Term):
    expression: Any


@dataclass
class UnaryOpTerm(Term):
    op: Token
    term: Term


@dataclass
class Expression(Node):
    term: Term
    tail: List[Tuple[Symbol, Term]]


@dataclass
class Statement(Node):
    pass


@dataclass
class LetStatement(Statement):
    name: str
    idx_expression: Optional[Any]
    expression: Any


@dataclass
class SubroutineBody(Node):
    var_decs: List[VarDec]
    statements: List[Statement]


@dataclass
class SubroutineDec(Node):
    modifier: str  # constructor, function, method
    type_: str  # or void
    name: str
    parameters: List[Parameter]
    body: SubroutineBody


@dataclass
class Class(Node):
    name: str
    class_var_decs: List[ClassVarDec]
    subroutine_decs: List[SubroutineDec]


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.look_ahead = deque()

    def run(self):
        pass

    def parse_class(self):
        tok = self._parse_next(Keyword, "class")
        line_num = tok.line_num
        class_name = self._parse_next(Identifier)
        self._parse_next(Symbol, "{")
        class_var_decs, subroutine_decs = self.parse_class_vars_and_subroutines()
        self._parse_next(Symbol, "}")
        class_node = Class(
            line_num=line_num,
            name=class_name,
            class_var_decs=class_var_decs,
            subroutine_decs=subroutine_decs,
        )
        return class_node

    def parse_class_vars_and_subroutines(self):
        class_var_decs = []
        subroutine_decs = []
        while True:
            tok = self._peek()
            if self._is_type(tok, Symbol, "}"):
                break
            elif self._is_type(tok, Keyword, "static", "fields"):
                class_var_decs.append(self.parse_class_var_dec())
            elif self._is_type(tok, Keyword, "constructor", "function", "method"):
                subroutine_decs.append(self.parse_subroutine_dec())
            else:
                raise ParseError(f"{tok.line_num}. Unexpected token: {tok}")
        return class_var_decs, subroutine_decs

    def parse_class_var_dec(self):
        modifier = self._parse_next(Keyword, "static", "field")
        type_ = self.parse_type()
        var_names = self._parse_var_identifier_list()
        return [
            ClassVarDec(
                line_num=name.line_num, modifier=modifier, type_=type_, name=name
            )
            for name in var_names
        ]

    def parse_subroutine_dec(self):
        modifier = self._parse_next(Keyword, "constructor", "function", "method")
        type_ = self.parse_type_or_void()
        name = self._parse_next(Identifier)
        self._parse_next(Symbol, "(")

        parameters = []
        while True:
            tok = self._peek()
            if self._is_type(tok, Symbol, ")"):
                break
            elif self._is_type(tok, Symbol, ","):
                self._next()
            param_type_ = self.parse_type()
            param_name = self._parse_next(Identifier)
            parameters.append(Parameter(type_=param_type_, name=param_name))
        self._parse_next(Symbol, ")")

        body = self.parse_subroutine_body()
        return SubroutineDec(
            line_num=modifier.line_num,
            modifier=modifier,
            type_=type_,
            name=name,
            parameters=parameters,
            body=body,
        )

    def parse_subroutine_body(self):
        var_decs = []
        self._parse_next(Symbol, "{")
        while True:
            tok = self._peek()
            if self._is_type(tok, Symbol, "}"):
                break
            elif self._is_type(tok, Keyword, "var"):
                var_decs.extend(self.parse_var_decs())
            else:
                raise ParseError(f"{tok.line_num}. Unexpected token: {tok}")
        self._parse_next(Symbol, "}")
        return var_decs

    def parse_type(self):
        try:
            return self._parse_next(Keyword, "int", "char", "boolean")
        except ParseError:
            return self._parse_next(Identifier)

    def parse_type_or_void(self):
        try:
            return self._parse_next(Keyword, "void")
        except ParseError:
            return self.parse_type()

    def parse_var_decs(self):
        self._parse_next(Keyword, "var")
        type_ = self.parse_type()
        var_names = self._parse_var_identifier_list()
        return [
            VarDec(line_num=name.line_num, type_=type_, name=name) for name in var_names
        ]

    def _parse_var_identifier_list(self):
        var_names = [self._parse_next(Identifier)]
        while True:
            tok = self._peek()
            if self._is_type(tok, Symbol, ";"):
                break
            self._parse_next(Symbol, ",")
            var_names.append(self._parse_next(Identifier))
        self._parse_next(Symbol, ";")
        return var_names

    def parse_statement(self):
        tok = self._peek()
        if self._is_type(tok, Keyword, "let"):
            return self.parse_let_statement()
        else:
            raise ParseError(f"{tok.line_num}. Unexpected token: {tok}")

    def parse_let_statement(self):
        line_num = self._parse_next(Keyword, "let").line_num
        var_name = self._parse_next(Identifier)

        tok = self._peek()
        if self._is_type(tok, Symbol, "["):
            self._next()
            idx_exp = self.parse_expression()
            self._parse_next(Symbol, "]")
        else:
            idx_exp = None

        self._parse_next(Symbol, "=")
        exp = self.parse_expression()
        self._parse_next(Symbol, ";")
        return LetStatement(
            line_num=line_num, name=var_name, idx_expression=idx_exp, expression=exp
        )

    def parse_expression(self):
        tok = self._peek()
        if self._is_type(tok, IntegerConstant):
            self._next()
            term = ConstantTerm(line_num=tok.line_num, value=tok)
        elif self._is_type(tok, StringConstant):
            self._next()
            term = ConstantTerm(line_num=tok.line_num, value=tok)
        elif self._is_type(tok, Keyword, "true", "false", "null", "this"):
            self._next()
            term = ConstantTerm(line_num=tok.line_num, value=tok)
        # TODO: varName, varName[idx_exp], subroutineCall
        # elif self._is_type(tok, Identifier):
        #     self._next()
        #     term = VarTerm(line_num=tok.line_num, name=tok)
        elif self._is_type(tok, Symbol, "("):
            self._next()
            exp = self.parse_expression()
            self._parse_next(Symbol, ")")
            term = ExpressionTerm(line_num=tok.line_num, expression=exp)
        else:
            raise ParseError(f"{tok.line_num}: Unexpected token: {tok}")
        return Expression(
            line_num=term.line_num,
            term=term,
            tail=list(),
        )

    def _parse_expression_tail(self):
        tail = []
        while True:
            tok = self._peek()
            if not self._is_type(
                tok, Symbol, "+", "-", "*", "/", "&", ", ", "<", ">", "="
            ):
                break
            self._next()
            exp = self.parse_expression()
            tail.append((tok, exp))
        return tail

    def _is_type(self, tok, type_, *values):
        correct_type = isinstance(tok, type_)
        if values:
            return correct_type and tok.value in values
        else:
            return correct_type

    def _parse_next(self, type_, *values):
        tok = self._next()
        if not self._is_type(tok, type_, *values):
            val_msg = f" with value {values}" if values else ""
            raise ParseError(f"{tok.line_num}: Expected {type_.__name__}{val_msg}")
        return tok

    def _next(self):
        try:
            return self.look_ahead.popleft()
        except IndexError:
            return next(self.tokens)

    def _peek(self):
        try:
            return self.look_ahead[0]
        except IndexError:
            tok = self._next()
            self.look_ahead.append(tok)
            return tok
