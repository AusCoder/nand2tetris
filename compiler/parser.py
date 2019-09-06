from collections import deque
from dataclasses import dataclass
from typing import Any, List, Optional

from tokenizer import (
    Keyword,
    Symbol,
    Identifier,
    IntegerConstant,
    StringConstant,
)


class ParseError(Exception):
    pass


@dataclass
class Node:
    line_num: int


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
class Statement(Node):
    pass


@dataclass
class LetStatement(Statement):
    name: str
    idx_exp: Optional[Any]
    exp: Any


@dataclass
class SubroutineBody(Node):
    var_decs: List[VarDec]
    statements: List[Statement]


@dataclass
class SubroutineDec(Node):
    modifier: str  # constructor, function, method
    type_: str  # or void
    name: str
    param_list: List[Parameter]
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
        tok = self._next_and_verify(Keyword, ["class"])
        line_num = tok.line_num
        class_name = self._next_and_verify(Identifier).name
        class_var_decs = []
        subroutine_decs = []
        return Class(
            line_num=line_num,
            name=class_name,
            class_var_decs=class_var_decs,
            subroutine_decs=subroutine_decs,
        )

    def parse_class_vars_or_subroutines(self):
        class_vars = []
        subroutines = []
        while True:
            tok = self._peek()
            if self._is_subroutine(tok):
                pass
            elif self._is_class_var_dec(tok):
                pass
            else:
                raise ParseError
        return class_vars, subroutines

    def parse_class_var(self):
        modifier = self._next_and_verify(Keyword, ["static", "field"]).value
        # type_ = self._next_and_verify("")

    def parse_type(self):
        tok = self._next()
        if isinstance()


    def _next(self):
        try:
            return self.look_ahead[0]
        except IndexError:
            return next(self.tokens)

    def _peek(self):
        try:
            return self.look_ahead[0]
        except IndexError:
            tok = self._next()
            self.look_ahead.append(tok)
            return tok

    def _is_subroutine(self, tok):
        return self._is_type(tok, Keyword, ["constructor", "function", "method"])

    def _is_class_var_dec(self, tok):
        return self._is_type(tok, Keyword, ["static", "fields"])

    def _next_and_verify(self, type_, values=None):
        tok = self._next()
        if not self._is_type(tok, type_, values):
            val_msg = f" with value {values}" if values else ""
            raise ParseError(f"{tok.line_num}: Expected {type_.__name__}{val_msg}")
        return tok

    def _is_type(self, tok, type_, values=None):
        correct_type = isinstance(tok, type_)
        if values:
            return correct_type and tok.value in values
        else:
            return correct_type
