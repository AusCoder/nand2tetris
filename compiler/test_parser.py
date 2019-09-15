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
from parser import (Parser, Statement, LetStatement, Expression, ConstantTerm, ExpressionTerm, UnaryOpTerm)


@pytest.mark.parametrize("lines, expected_term_type", [
    (["1"], ConstantTerm),
    (["(1)"], ExpressionTerm),
    (["-1"], UnaryOpTerm),
])
def test_parser_expression(lines, expected_term_type):
    toks = gen_tokens_for_lines(lines=lines)
    parsed = Parser(toks).parse_expression()
    assert isinstance(parsed, Expression)
    assert isinstance(parsed.term, expected_term_type)


@pytest.mark.parametrize("lines", [
    ["let x = 1;"],
    ["let x[2] = 1;"],
    ["let x = 1 + 1;"],
])
def test_parser_let(lines):
    toks = gen_tokens_for_lines(lines=lines)
    assert isinstance(Parser(toks).parse_let_statement(), LetStatement)
