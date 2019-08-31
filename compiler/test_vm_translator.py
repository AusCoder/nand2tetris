"""This requires pytest:

pip install pytest
"""
import pytest

from vm_translator import CommandType, Parser


@pytest.mark.parametrize(
    "case, expected",
    [
        ("  // abc\n", (CommandType.NONE, (None, None))),
        ("push local 1\n", (CommandType.PUSH, ("local", 1))),
        ("push argument 2\n", (CommandType.PUSH, ("argument", 2))),
        ("push this 34\n", (CommandType.PUSH, ("this", 34))),
        ("push that 456\n", (CommandType.PUSH, ("that", 456))),
        ("  push static 123456\n", (CommandType.PUSH, ("static", 123456))),
        ("\tpush constant 0\n", (CommandType.PUSH, ("constant", 0))),
        ("label ABC_DEF\n", (CommandType.LABEL, ("ABC_DEF", None))),
        ("label A$.:\n", (CommandType.LABEL, ("A$.:", None))),
        ("goto ABC_DEF\n", (CommandType.GOTO, ("ABC_DEF", None))),
        ("if-goto ABC_DEF\n", (CommandType.IFGOTO, ("ABC_DEF", None))),
        ("function fn 3\n", (CommandType.FUNCTION, ("fn", 3))),
        ("call fn 1\n", (CommandType.CALL, ("fn", 1))),
        ("return\n", (CommandType.RETURN, (None, None))),
    ],
)
def test_parser(case, expected):
    expected_command_type, expected_arguments = expected
    p = Parser(iter([case]))
    assert p.has_next_command()
    assert p.advance() == expected_command_type
    assert p.arguments() == expected_arguments
    assert not p.has_next_command()
