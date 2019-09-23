from symbol_table import (
    SymbolTables,
    Kind,
    Type,
    TypeInt,
    TypeChar,
    TypeBool,
    TypeClass,
)
from tokenizer import Token
from parser import Class, SubroutineDec


class CodeGenerator:
    def __init__(self):
        self._symbol_tables = SymbolTables()

    def generate(self, class_: Class):
        self._symbol_tables.push_new()
        for var_dec in class_.class_var_decs:
            self._symbol_tables.add(
                name=var_dec.name.value,
                type_=self._gen_type(var_dec.type_),
                kind=self._gen_class_var_kind(var_dec.modifier),
            )
        for subroutine_dec in class_.subroutine_decs:
            self.generate_subroutine(
                subroutine_dec
            )
        self._symbol_tables.pop()

    def generate_subroutine(self, dec: SubroutineDec):
        self._symbol_tables.push_new()
        for type_, name in dec.parameters.parameters:
            self._symbol_tables.add(
                name=name.value,
                type_=self._gen_type(type_),
                kind=Kind.ARGUMENT,
            )
        for tab in self._symbol_tables._tables:
            print(tab._table)
        self._symbol_tables.pop()

    def _gen_class_var_kind(self, token: Token) -> Kind:
        if token.value == "static":
            return Kind.STATIC
        elif token.value == "field":
            return Kind.FIELD
        raise RuntimeError

    def _gen_type(self, token: Token) -> Type:
        if token.value == "int":
            return TypeInt()
        elif token.value == "char":
            return TypeChar()
        elif token.value == "boolean":
            return TypeBool()
        else:
            return TypeClass(token.value)
