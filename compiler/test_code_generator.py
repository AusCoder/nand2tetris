from tokenizer import (
    gen_tokens_for_lines,
)
from parser import (
    Parser,
)
from code_generator import CodeGenerator
from symbol_table import Kind, TypeInt


def test_expression_with_ops():
    toks = gen_tokens_for_lines(lines=["1 * 2 + 3;"])
    parsed = Parser(toks).parse_expression()
    code_gen = CodeGenerator()
    code = code_gen.generate_expression(parsed)
    assert code == [
        "push constant 1",
        "push constant 2",
        "push constant 3",
        "add",
        "call Math.multiply",
    ]


def test_expression_with_ops_and_fn_call():
    toks = gen_tokens_for_lines(lines=["x + g(2, y, -z) * 5;"])
    parsed = Parser(toks).parse_expression()
    code_gen = CodeGenerator()
    code_gen._symbol_tables.push_new()
    code_gen._symbol_tables.add("x", TypeInt(), Kind.ARGUMENT)
    code_gen._symbol_tables.add("y", TypeInt(), Kind.ARGUMENT)
    code_gen._symbol_tables.add("z", TypeInt(), Kind.ARGUMENT)
    code = code_gen.generate_expression(parsed)
    assert code == [
        "push argument 0",
        "push constant 2",
        "push argument 1",
        "push argument 2",
        "neg",
        "call g",
        "push constant 5",
        "call Math.multiply",
        "add",
    ]
