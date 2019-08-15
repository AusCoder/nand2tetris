"""This requires pytest:

pip install pytest
"""
import pytest

from vm_translator import (
    CommandType,
    Parser,
)

@pytest.mark.parametrize(
    "case, expected",
    [
        ("push local 1\n", (CommandType.PUSH, ("local", 1))),
        ("push argument 2\n", (CommandType.PUSH, ("argument", 2))),
        ("push this 34\n", (CommandType.PUSH, ("this", 34))),
        ("push that 456\n", (CommandType.PUSH, ("that", 456))),
        ("push static 123456\n", (CommandType.PUSH, ("static", 123456))),
        ("push constant 0\n", (CommandType.PUSH, ("constant", 0))),
    ],
)
def test_parser(case, expected):
    expected_command_type, expected_arguments = expected
    p = Parser(iter([case]))
    assert p.has_next_command()
    assert p.advance() == expected_command_type
    assert p.arguments() == expected_arguments
    assert not p.has_next_command()
