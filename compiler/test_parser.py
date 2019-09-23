import pytest

from tokenizer import (
    Token,
    Keyword,
    Symbol,
    Identifier,
    IntegerConstant,
    StringConstant,
    gen_tokens_for_lines,
)
from parser import (Parser, Statement, LetStatement, Expression, ConstantTerm, ParenTerm, UnaryOpTerm)


def test_parser_expression_paren_term():
    toks = gen_tokens_for_lines(lines=["(1);"])
    parsed = Parser(toks).parse_expression()
    assert isinstance(parsed.term, ParenTerm)


def test_parser_expression_unary_term():
    toks = gen_tokens_for_lines(lines=["-1;"])
    parsed = Parser(toks).parse_expression()
    assert isinstance(parsed.term, UnaryOpTerm)
    assert parsed.term.op.value == "-"


def test_parser_expression_with_tail():
    toks = gen_tokens_for_lines(lines=["1 + 1 + 1;"])
    parsed = Parser(toks).parse_expression()
    assert isinstance(parsed.term, ConstantTerm)
    assert all(isinstance(t, ConstantTerm) for _, t in parsed.tail)
    assert all(o.value == "+" for o, _ in parsed.tail)


@pytest.mark.parametrize("lines", [
    ["let x = 1;"],
    ["let x[2] = 1;"],
    ["let x = 1 + 1;"],
])
def test_parser_let(lines):
    toks = gen_tokens_for_lines(lines=lines)
    assert isinstance(Parser(toks).parse_let_statement(), LetStatement)
