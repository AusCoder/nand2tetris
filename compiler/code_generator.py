import itertools
from collections import deque
from symbol_table import (
    SymbolNotFoundError,
    SymbolTables,
    Kind,
    Type,
    TypeInt,
    TypeChar,
    TypeBool,
    TypeClass,
)
from tokenizer import Token, IntegerConstant, StringConstant, Keyword, Symbol
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
    DoStatement,
    WhileStatement,
    ReturnStatement,
)


class CodeGeneratorError(Exception):
    pass


class CodeGenerator:
    def __init__(self):
        self._uniq_label = 0
        self._cur_class_name = None
        self._subroutine_type = None
        self._symbol_tables = SymbolTables()

    def generate(self, class_: Class):
        self._cur_class_name = class_.name.value
        self._symbol_tables.push_new()
        for var_dec in class_.class_var_decs:
            self._symbol_tables.add(
                name=var_dec.name.value,
                type_=self._gen_type(var_dec.type_),
                kind=self._gen_class_var_kind(var_dec.modifier),
            )
        code = list(
            itertools.chain.from_iterable(
                self.generate_subroutine(dec) for dec in class_.subroutine_decs
            )
        )
        self._symbol_tables.pop()
        return code

    def generate_subroutine(self, dec: SubroutineDec):
        self._subroutine_type = dec.modifier.value
        self._symbol_tables.push_new()
        for type_, name in dec.parameters.parameters:
            self._symbol_tables.add(
                name=name.value, type_=self._gen_type(type_), kind=Kind.ARGUMENT
            )
        for type_, name in dec.body.var_decs:
            self._symbol_tables.add(
                name=name.value, type_=self._gen_type(type_), kind=Kind.LOCAL
            )

        num_locals = len(dec.body.var_decs)
        code = [f"function {self._cur_class_name}.{dec.name.value} {num_locals}"]
        if dec.modifier.value == "method":
            code.extend(["push argument 0", "pop pointer 0"])
        elif dec.modifier.value == "constructor":
            size = len([s for s in self._symbol_tables if s.kind == Kind.FIELD])
            code.extend(
                [
                    f"push constant {size}",
                    "call Memory.alloc 1",
                    "pop pointer 0",  # TODO: Is this correct? Need to set the this addr correctly
                ]
            )
        is_void_subroutine = (
            isinstance(dec.type_, Keyword) and dec.type_.value == "void"
        )
        code.extend(
            itertools.chain.from_iterable(
                self.generate_statement(stm, is_void_subroutine)
                for stm in dec.body.statements.statements
            )
        )
        self._symbol_tables.pop()

        # TODO: rm debug
        code.extend(["", ""])

        return code

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

    def generate_statement(self, statement: Statement, is_void_subroutine: bool):
        code = list()
        uniq_label = self._uniq_label
        self._uniq_label += 1

        if isinstance(statement, LetStatement):
            symbol = self._symbol_tables.lookup(statement.name.value)
            mem_segment = self._gen_memory_segment(symbol.kind)
            if statement.idx_expression:
                code.append(f"push {mem_segment} {symbol.index}")
                code.extend(self.generate_expression(statement.idx_expression))
                code.append("add")
                code.extend(self.generate_expression(statement.expression))
                # This is required to handle multiple array access
                # with array assignment.
                code.extend(
                    ["pop temp 0", "pop pointer 1", "push temp 0", "pop that 0"]
                )
            else:
                code.extend(self.generate_expression(statement.expression))
                code.append(f"pop {mem_segment} {symbol.index}")
            return code
        elif isinstance(statement, IfStatement):
            false_label = f"IF{uniq_label}.FALSE"
            end_label = f"IF{uniq_label}.END"
            code.extend(self.generate_expression(statement.condition))
            code.extend(["not", f"if-goto {false_label}"])
            for stm in statement.true_statements.statements:
                code.extend(self.generate_statement(stm, is_void_subroutine))
            code.extend([f"goto {end_label}", f"label {false_label}"])
            for stm in statement.false_statements.statements:
                code.extend(self.generate_statement(stm, is_void_subroutine))
            code.append(f"label {end_label}")
            return code
        elif isinstance(statement, WhileStatement):
            start_label = f"WHILE{uniq_label}.START"
            end_label = f"WHILE{uniq_label}.END"
            code.append(f"label {start_label}")
            code.extend(self.generate_expression(statement.condition))
            code.extend(["not", f"if-goto {end_label}"])
            for stm in statement.body.statements:
                code.extend(self.generate_statement(stm, is_void_subroutine))
            code.extend([f"goto {start_label}", f"label {end_label}"])
            return code
        elif isinstance(statement, DoStatement):
            code.extend(self._gen_subroutine_call(statement.term))
            code.append("pop temp 0")
            return code
        elif isinstance(statement, ReturnStatement):
            if is_void_subroutine and statement.expression:
                raise CodeGeneratorError(
                    f"void subroutine cannot return a value: {statement}"
                )
            elif is_void_subroutine:
                code.append("push constant 0")
            elif statement.expression:
                code.extend(self.generate_expression(statement.expression))
            else:
                raise CodeGeneratorError(
                    f"Expected subroutine to either be void or return a value: {statement}"
                )
            code.append("return")
            return code
        raise CodeGeneratorError(f"Unknown statement: {statement}")

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
                # An alternative would be to rewrite as SubroutineCallTerms
                # but this might be more efficient?
                code = [f"push constant {len(term.value.value)}", "call String.new 1"]
                for c in term.value.value:
                    code.extend([f"push constant {ord(c)}", "call String.appendChar 2"])
                return code
            elif isinstance(term.value, Keyword) and term.value.value == "true":
                return ["push constant 1", "neg"]
            elif isinstance(term.value, Keyword) and term.value.value in [
                "false",
                "null",
            ]:
                return ["push constant 0"]
            elif isinstance(term.value, Keyword) and term.value.value == "this":
                return ["push pointer 0"]
        elif isinstance(term, VarTerm):
            symbol = self._symbol_tables.lookup(term.value.value)
            mem_segment = self._gen_memory_segment(symbol.kind)
            return [f"push {mem_segment} {symbol.index}"]
        elif isinstance(term, VarIndexTerm):
            symbol = self._symbol_tables.lookup(term.name.value)
            mem_segment = self._gen_memory_segment(symbol.kind)
            code = [f"push {mem_segment} {symbol.index}"]
            code.extend(self.generate_expression(term.index))
            code.extend(["add", "pop pointer 1", "push that 0"])
            return code
        elif isinstance(term, SubroutineCallTerm):
            return self._gen_subroutine_call(term)
        elif isinstance(term, ParenTerm):
            return self.generate_expression(term.expression)
        elif isinstance(term, UnaryOpTerm):
            term_code = self.generate_term(term.term)
            if term.op.value == "-":
                return term_code + ["neg"]
            elif term.op.value == "~":
                return term_code + ["not"]
        raise CodeGeneratorError(f"Unknown term: {term}")

    def _gen_subroutine_call(self, term: SubroutineCallTerm):
        if term.qualifier:
            try:
                # Method on an object
                symbol = self._symbol_tables.lookup(term.qualifier.value)
                if isinstance(symbol.type_, TypeClass):
                    subroutine_cls_name = symbol.type_.value
                    mem_segment = self._gen_memory_segment(symbol.kind)
                    code = [f"push {mem_segment} {symbol.index}"]
                    num_args = 1
                else:
                    raise CodeGeneratorError(f"Type {symbol.type_} has no subroutines")
            except SymbolNotFoundError:
                # Static function or constructor
                subroutine_cls_name = term.qualifier.value
                code = list()
                num_args = 0
        else:
            # Subroutine in current class
            subroutine_cls_name = self._cur_class_name
            code = list()
            num_args = 0

        num_args += len(term.arguments)
        code.extend(
            itertools.chain.from_iterable(
                self.generate_expression(e) for e in term.arguments
            )
        )
        code.append(f"call {subroutine_cls_name}.{term.name.value} {num_args}")
        return code

    def _gen_op(self, op: Token):
        if op.value == "+":
            return ["add"]
        elif op.value == "-":
            return ["sub"]
        elif op.value == "*":
            return ["call Math.multiply 2"]
        elif op.value == "/":
            return ["call Math.divide 2"]
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
        raise CodeGeneratorError(f"Unknown op: {op}")

    def _gen_memory_segment(self, kind: Kind):
        if kind == Kind.FIELD:
            return "this"
        elif kind == Kind.STATIC:
            return "static"
        elif kind == Kind.LOCAL:
            return "local"
        elif kind == Kind.ARGUMENT:
            return "argument"
        raise CodeGeneratorError(f"Unknown kind: {kind}")
