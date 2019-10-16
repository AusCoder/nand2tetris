import pytest

from assembler import (
    ParseError,
    AInstructionNumeric,
    AInstructionSymbolic,
    CInstruction,
    Symbol,
    parse_a_instruction_numeric,
    parse_a_instruction_symbolic,
    parse_c_instruction,
    parse_symbol,
)


@pytest.mark.parametrize(
    "case, expected",
    [
        ("@1", 1),
        ("   @1  ", 1),
        ("\t@1  ", 1),
        ("\t@1\t", 1),
        ("\t@1123  // comment", 1123),
    ],
)
def test_parse_a_instruction_numeric(case, expected):
    result = parse_a_instruction_numeric(case, 0)
    assert isinstance(result, AInstructionNumeric)
    assert result.address == expected


@pytest.mark.parametrize(
    "case, expected",
    [
        ("  @a1  ", "a1"),
        ("  @sys.init  ", "sys.init"),
        ("  @sys.init$if_false2  ", "sys.init$if_false2"),
        ("  @sys.init:something  ", "sys.init:something"),
    ],
)
def test_parse_a_instruction_symbolic(case, expected):
    result = parse_a_instruction_symbolic(case, 0)
    assert isinstance(result, AInstructionSymbolic)
    assert result.symbol == expected


@pytest.mark.parametrize(
    "case, expected",
    [
        ("0;JMP", (None, "0", "JMP")),
        ("1;JGT", (None, "1", "JGT")),
        ("D=M", ("D", "M", None)),
        (" D=M", ("D", "M", None)),
        (" D =!M", ("D", "!M", None)),
        (" D =-M", ("D", "-M", None)),
        (" M =M - 1", ("M", "M-1", None)),
        (" A =  M", ("A", "M", None)),
        ("D=D-M", ("D", "D-M", None)),
        ("M=D-1", ("M", "D-1", None)),
        ("AM=D-M", ("AM", "D-M", None)),
        (" AMD = D & A;JNE", ("AMD", "D&A", "JNE")),
        ("AM=D-M ; JEQ", ("AM", "D-M", "JEQ")),
    ],
)
def test_parse_c_instruction(case, expected):
    result = parse_c_instruction(case, 0)
    assert isinstance(result, CInstruction)
    assert (result.dest, result.comp, result.jump) == expected


@pytest.mark.parametrize(
    "case, expected",
    [
        ("(END)", "END"),
        ("(A_B)", "A_B"),
        ("(sys.init)", "sys.init"),
        ("(sys.init$if_true0)", "sys.init$if_true0"),
    ],
)
def test_parse_symbol(case, expected):
    result = parse_symbol(case, 0)
    assert isinstance(result, Symbol)
    assert result.symbol == expected
