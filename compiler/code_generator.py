import itertools
from collections import deque
from symbol_table import (
    SymbolTables,
    Kind,
    Type,
    TypeInt,
    TypeChar,
    TypeBool,
    TypeClass,
)
from tokenizer import (
    Token,
    IntegerConstant,
    StringConstant,
    Keyword,
    Symbol,
)
from parser import (
    Class,
    SubroutineDec,
    Term,
    ConstantTerm,
    VarTerm,
    VarIndexTerm,
    SubroutineCallTerm,
    ParenTerm,
    UnaryOpTerm,
    Expression,
    Statement,
    LetStatement,
    IfStatement,
    WhileStatement,
    DoStatement,
    WhileStatement,
)


class CodeGenerator:
    def __init__(self):
        self._uniq_label = 0
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
        # TODO: push this if we are in a method!
        for type_, name in dec.body.var_decs:
            self._symbol_tables.add(
                name=name.value,
                type_=self._gen_type(type_),
                kind=Kind.LOCAL,
            )
        for statement in dec.body.statements.statements:
            self.generate_statement(statement)
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

    def generate_statement(self, statement: Statement):
        code = list()
        uniq_label = self._uniq_label
        self._uniq_label += 1
        if isinstance(statement, LetStatement):
            symbol = self._symbol_tables.lookup(statement.name.value)
            code.extend(
                self.generate_expression(statement.expression)
            )
            if statement.idx_expression:
                raise NotImplementedError
            else:
                mem_segment = self._gen_memory_segment(symbol.kind)
                code.append(
                    f"pop {mem_segment} {symbol.index}"
                )
            return code
        elif isinstance(statement, IfStatement):
            false_label = f"IF{uniq_label}.FALSE"
            end_label = f"IF{uniq_label}.END"
            code.extend(
                self.generate_expression(statement.condition)
            )
            code.extend([
                "not",
                f"if-goto {false_label}",
            ])
            # TODO false_statements code
            code.extend([
                f"goto {end_label}",
                f"label {false_label}",
            ])
            # TODO true_statements code
            code.append(f"label {end_label}")
            return code
        elif isinstance(statement, WhileStatement):
            start_label = f"WHILE{uniq_label}.START"
            end_label = f"WHILE{uniq_label}.END"
            code.append(f"label {start_label}")
            code.extend(
                self.generate_expression(statement.condition)
            )
            code.append(f"if-goto {end_label}")
            # TODO body statements code
            code.extend([
                f"goto {start_label}",
                f"label {end_label}",
            ])
            return code
        elif isinstance(statement, DoStatement):
            call_term = statement.term
            for arg in call_term.arguments:
                code.extend(
                    self.generate_expression(arg)
                )
            code.extend([
                f"call {call_term.name.value}",
                "pop temp 0",
            ])
            return code
        elif isinstance(statement, ReturnStatement):
            pass
        raise NotImplementedError

    def generate_expression(self, exp: Expression):
        op_stack = deque()
        code = list()
        code.extend(self.generate_term(exp.term))
        for symbol, term in exp.tail:
            op_stack.append(symbol)
            code.extend(self.generate_term(term))
        while op_stack:
            symbol = op_stack.pop()
            code.extend(self._gen_op(symbol))
        return code

    def generate_term(self, term: Term):
        if isinstance(term, ConstantTerm):
            if isinstance(term.value, IntegerConstant):
                return [f"push constant {int(term.value.value)}"]
            elif isinstance(term.value, StringConstant):
                # TODO: requires multiple calls to String methods
                raise NotImplementedError
            elif isinstance(term.value, Keyword) and term.value.value == "true":
                return ["push constant 1", "neg"]
            elif isinstance(term.value, Keyword) and term.value.value == "false":
                return ["push constant 0"]
        elif isinstance(term, VarTerm):
            symbol = self._symbol_tables.lookup(term.value.value)
            mem_segment = self._gen_memory_segment(symbol.kind)
            return [f"push {mem_segment} {symbol.index}"]
        elif isinstance(term, VarIndexTerm):
            raise NotImplementedError
        elif isinstance(term, SubroutineCallTerm):
            # TODO: how to handle methods?
            # Need to add this as an argument
            # Also need to lookup if a function is a method
            code = list(itertools.chain.from_iterable(
                self.generate_expression(e) for e in term.arguments
            ))
            code.append(f"call {term.name.value}")
            return code
        elif isinstance(term, ParenTerm):
            return self.generate_expression(term.value)
        elif isinstance(term, UnaryOpTerm):
            term_code = self.generate_term(term.term)
            if term.op.value == "-":
                return term_code + ["neg"]
            elif term.op.value == "~":
                return term_code + ["not"]
        raise RuntimeError

    def _gen_op(self, op: Token):
        if op.value == "+":
            return ["add"]
        elif op.value == "-":
            return ["sub"]
        elif op.value == "*":
            return ["call Math.multiply"]
        elif op.value == "/":
            return ["call Math.divide"]
        elif op.value == "&":
            return ["and"]
        elif op.value == "|":
            return ["or"]
        elif op.value == "<":
            return ["lt"]
        elif op.value == ">":
            return ["gt"]
        elif op.value == "=":
            return ["eq"]
        raise RuntimeError

    def _gen_memory_segment(self, kind: Kind):
        if kind == Kind.FIELD:
            return "this"
        elif kind == Kind.STATIC:
            return "static"
        elif kind == Kind.LOCAL:
            return "local"
        elif kind == Kind.ARGUMENT:
            return "argument"
        raise RuntimeError
