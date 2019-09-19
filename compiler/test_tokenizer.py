import pytest

from tokenizer import (
    VALID_KEYWORDS,
    VALID_SYMBOLS,
    Keyword,
    Symbol,
    Identifier,
    IntegerConstant,
    StringConstant,
    gen_tokens_for_line,
    gen_tokens_for_lines,
)


@pytest.mark.parametrize(
    "line, expected",
    [(f"{kw}\n", [Keyword(value=kw, line_num=0)]) for kw in VALID_KEYWORDS]
    + [(f"{s}\n", [Symbol(value=s, line_num=0)]) for s in VALID_SYMBOLS]
    + [
        ("abc\n", [Identifier(value="abc", line_num=0)]),
        ("23\n", [IntegerConstant(value="23", line_num=0)]),
        ('"abc"\n', [StringConstant(value="abc", line_num=0)]),
        ('""\n', [StringConstant(value="", line_num=0)]),
        ("Main\n", [Identifier(value="Main", line_num=0)]),
        ("Main {\n", [Identifier(value="Main", line_num=0), Symbol(value="{", line_num=0)]),
        ("   function", [Keyword(value="function", line_num=0)]),
        ("// abc\n", []),
        ("  // abc", []),
        ("  /* abc */", []),
        ("  /* abc */ 1", [IntegerConstant(value="1", line_num=0)]),
    ],
)
def test_gen_tokens_for_line(line, expected):
    toks = gen_tokens_for_line(line=line, line_num=0, in_comment=False)
    assert list(t for t, _ in toks if t) == expected


EXAMPLE1 = """function main {
}
""".split("\n")
EXPECTED1 = [
    Keyword(value="function", line_num=0),
    Identifier(value="main", line_num=0),
    Symbol(value="{", line_num=0),
    Symbol(value="}", line_num=1),
]

EXAMPLE2 = """
/* abc def
kjdfs
*/
"abc" 1
}
""".split("\n")
EXPECTED2 = [
    StringConstant(value="abc", line_num=4),
    IntegerConstant(value="1", line_num=4),
    Symbol(value="}", line_num=5),
]

@pytest.mark.parametrize(
    "lines, expected",
    [
        (EXAMPLE1, EXPECTED1),
        (EXAMPLE2, EXPECTED2),
    ],
)
def test_gen_tokens_for_lines(lines, expected):
    toks = gen_tokens_for_lines(lines=lines)
    assert list(toks) == expected
