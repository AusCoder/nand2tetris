from collections import deque
from dataclasses import dataclass
from typing import Any, List, Optional, Tuple
from xml.etree.ElementTree import Element, ElementTree

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


def token_to_xml(token):
    e = Element(token.__class__.__name__)
    e.text = f" {token.value} "
    return e


# TODO: line_num is derivable from token values
# We could introspect them as the first element of the __dict__?
# Seems like a bit of a hack
# Even better, use metaclasses to use an OrderedDict...
@dataclass
class Node:
    line_num: int

    def to_xml(self):
        self_element = Element(self.__class__.__name__)
        # Order matters here! Can I force self.__dict__ to be an OrderedDict?
        for k, v in self.__dict__.items():
            if isinstance(v, Token):
                e = token_to_xml(v)
                self_element.append(e)
            elif isinstance(v, Node):
                self_element.append(v.to_xml())
            elif isinstance(v, list) and all(isinstance(n, Node) for n in v):
                for n in v:
                    self_element.append(n.to_xml())
            elif isinstance(v, list) and all(isinstance(t, tuple) for t in v):
                for t in v:
                    for n in t:
                        if isinstance(n, Token):
                            self_element.append(token_to_xml(n))
                        elif isinstance(n, Node):
                            self_element.append(n.to_xml())
        return self_element


@dataclass
class ClassVarDec(Node):
    modifier: Token
    type_: Token
    name: Token


@dataclass
class ParameterList(Node):
    parameters: List[Tuple[Token, Token]]


@dataclass
class VarDec(Node):
    type_: Token
    name: Token


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
    index: Any


@dataclass
class SubroutineCallTerm(Term):
    qualifier: Optional[Token]  # Class.method(x) or someVar.method(x)
    name: Token
    arguments: Any


@dataclass
class ParenTerm(Term):
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
class Statements(Node):
    statements: List[Statement]


@dataclass
class LetStatement(Statement):
    name: str
    idx_expression: Optional[Any]
    expression: Expression


@dataclass
class IfStatement(Statement):
    condition: Expression
    true_statements: Statements
    false_statements: Statements


@dataclass
class WhileStatement(Statement):
    condition: Expression
    body: Statements


@dataclass
class DoStatement(Statement):
    term: SubroutineCallTerm


@dataclass
class ReturnStatement(Statement):
    expression: Optional[Expression]


@dataclass
class SubroutineBody(Node):
    var_decs: List[VarDec]
    statements: Statements


@dataclass
class SubroutineDec(Node):
    modifier: Token  # constructor, function, method
    type_: Token  # or void
    name: Token
    parameters: ParameterList
    body: SubroutineBody


@dataclass
class Class(Node):
    name: Token
    class_var_decs: List[ClassVarDec]
    subroutine_decs: List[SubroutineDec]


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.look_ahead = deque()

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
            elif self._is_type(tok, Keyword, "static", "field"):
                class_var_decs.extend(self.parse_class_var_decs())
            elif self._is_type(tok, Keyword, "constructor", "function", "method"):
                subroutine_decs.append(self.parse_subroutine_dec())
            else:
                raise ParseError(f"{tok.line_num}. Unexpected token: {tok}")
        return class_var_decs, subroutine_decs

    def parse_class_var_decs(self):
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
        param_list_line_num = self._parse_next(Symbol, "(").line_num

        parameters = []
        while True:
            tok = self._peek()
            if self._is_type(tok, Symbol, ")"):
                break
            elif self._is_type(tok, Symbol, ","):
                self._next()
            param_type_ = self.parse_type()
            param_name = self._parse_next(Identifier)
            parameters.append((param_type_, param_name))
        param_list = ParameterList(line_num=param_list_line_num, parameters=parameters)
        self._parse_next(Symbol, ")")

        body = self.parse_subroutine_body()
        return SubroutineDec(
            line_num=modifier.line_num,
            modifier=modifier,
            type_=type_,
            name=name,
            parameters=param_list,
            body=body,
        )

    def parse_subroutine_body(self):
        var_decs = []
        statements_list = []
        line_num = self._parse_next(Symbol, "{").line_num
        while True:
            tok = self._peek()
            if self._is_type(tok, Symbol, "}"):
                break
            elif self._is_type(tok, Keyword, "var"):
                var_decs.extend(self.parse_var_decs())
            else:
                statements_list.append(self.parse_statement())
        self._parse_next(Symbol, "}")
        statements = Statements(line_num=line_num, statements=statements_list)
        return SubroutineBody(
            line_num=line_num, var_decs=var_decs, statements=statements
        )

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
        elif self._is_type(tok, Keyword, "if"):
            return self.parse_if_statement()
        elif self._is_type(tok, Keyword, "while"):
            return self.parse_while_statement()
        elif self._is_type(tok, Keyword, "do"):
            return self.parse_do_statement()
        elif self._is_type(tok, Keyword, "return"):
            return self.parse_return_statement()
        else:
            raise ParseError(f"{tok.line_num}. Unexpected token: {tok}")

    def parse_statements(self):
        line_num = self._parse_next(Symbol, "{").line_num
        statements = []
        while True:
            tok = self._peek()
            if self._is_type(tok, Symbol, "}"):
                break
            statements.append(self.parse_statement())
        self._parse_next(Symbol, "}")
        return Statements(line_num=line_num, statements=statements)

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

    def parse_if_statement(self):
        line_num = self._parse_next(Keyword, "if").line_num
        self._parse_next(Symbol, "(")
        condition = self.parse_expression()
        self._parse_next(Symbol, ")")
        true_statements = self.parse_statements()

        tok = self._peek()
        if self._is_type(tok, Keyword, "else"):
            self._next()
            false_statements = self.parse_statements()

        else:
            false_statements = []

        return IfStatement(
            line_num=line_num,
            condition=condition,
            true_statements=true_statements,
            false_statements=false_statements,
        )

    def parse_while_statement(self):
        line_num = self._parse_next(Keyword, "while").line_num
        self._parse_next(Symbol, "(")
        condition = self.parse_expression()
        self._parse_next(Symbol, ")")
        body = self.parse_statements()
        return WhileStatement(line_num=line_num, condition=condition, body=body)

    def parse_do_statement(self):
        line_num = self._parse_next(Keyword, "do").line_num
        identifier = self._parse_next(Identifier)
        subroutine_call_term = self._parse_subroutine_call(identifier)
        self._parse_next(Symbol, ";")
        return DoStatement(line_num=line_num, term=subroutine_call_term)

    def parse_return_statement(self):
        line_num = self._parse_next(Keyword, "return").line_num
        tok = self._peek()
        if self._is_type(tok, Symbol, ";"):
            expression = None
        else:
            expression = self.parse_expression()
        self._parse_next(Symbol, ";")
        return ReturnStatement(line_num=line_num, expression=expression)

    def parse_expression(self):
        term = self.parse_term()
        tail = self._parse_expression_tail()
        return Expression(line_num=term.line_num, term=term, tail=tail)

    def parse_term(self):
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
        elif self._is_type(tok, Identifier):
            term = self._parse_term_with_identifier()
        elif self._is_type(tok, Symbol, "("):
            self._next()
            exp = self.parse_expression()
            self._parse_next(Symbol, ")")
            term = ParenTerm(line_num=tok.line_num, expression=exp)
        elif self._is_type(tok, Symbol, "-", "~"):
            self._next()
            subterm = self.parse_term()
            term = UnaryOpTerm(line_num=tok.line_num, op=tok, term=subterm)
        else:
            raise ParseError(f"{tok.line_num}: Unexpected token: {tok}")
        return term

    def _parse_term_with_identifier(self):
        ident = self._parse_next(Identifier)
        tok = self._peek()
        if self._is_type(tok, Symbol, "["):  # index expression
            self._next()
            index = self.parse_expression()
            self._parse_next(Symbol, "]")
            return VarIndexTerm(line_num=ident.line_num, name=ident, index=index)
        elif self._is_type(tok, Symbol, "(", "."):
            return self._parse_subroutine_call(ident)
        else:
            return VarTerm(line_num=ident.line_num, name=ident)

    def _parse_subroutine_call(self, identifier):
        """If you think about it, passing this identifier is letting
        us peek 2 ahead. This is necessary because we currently don't
        have the ability to peek more than 1 ahead.
        """
        tok = self._peek()
        if self._is_type(tok, Symbol, "("):  # function call
            arguments = self._parse_argument_list()
            return SubroutineCallTerm(
                line_num=identifier.line_num,
                qualifier=None,
                name=identifier,
                arguments=arguments,
            )
        elif self._is_type(tok, Symbol, "."):  # method call
            self._next()
            name = self._parse_next(Identifier)
            arguments = self._parse_argument_list()
            return SubroutineCallTerm(
                line_num=identifier.line_num,
                qualifier=identifier,
                name=name,
                arguments=arguments,
            )
        raise ParseError(f"{tok.line_num}: Unexpected token: {tok}")

    def _parse_argument_list(self):
        arguments = list()
        self._parse_next(Symbol, "(")
        while True:
            tok = self._peek()
            if self._is_type(tok, Symbol, ")"):
                break
            elif self._is_type(tok, Symbol, ","):
                self._next()
                arguments.append(self.parse_expression())
            else:
                arguments.append(self.parse_expression())
        self._parse_next(Symbol, ")")
        return arguments

    def _parse_expression_tail(self):
        tail = []
        while True:
            tok = self._peek()
            if not self._is_type(
                tok, Symbol, "+", "-", "*", "/", "&", "|", "<", ">", "="
            ):
                break
            self._next()
            term = self.parse_term()
            tail.append((tok, term))
        return tail

    def _is_type(self, tok, type_, *values):
        correct_type = isinstance(tok, type_)
        if values:
            return correct_type and tok.value in values
        else:
            return correct_type

    def _parse_next(self, type_, *values):
        tok = self._peek()
        if not self._is_type(tok, type_, *values):
            val_msg = f" with value {values}" if values else ""
            raise ParseError(f"{tok.line_num}: Expected {type_.__name__}{val_msg}")
        self._next()
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
