import re
from dataclasses import dataclass
from typing import Any, Iterable, List, Tuple


VALID_KEYWORDS = [
    "class",
    "constructor",
    "function",
    "method",
    "field",
    "static",
    "var",
    "int",
    "char",
    "boolean",
    "void",
    "true",
    "false",
    "null",
    "this",
    "let",
    "do",
    "if",
    "else",
    "while",
    "return",
]

SYMBOLDS_NEEDS_ESCAPE = ["(", ")", "[", "]", ".", "-", "+", "*", "|"]
SYMBOLS_REST = ["{", "}", ",", ";", "/", "&", "<", ">", "=", "~"]
VALID_SYMBOLS = SYMBOLDS_NEEDS_ESCAPE + SYMBOLS_REST
VALID_SYMBOLS_ESCAPED = [
    rf"\{symbol}" for symbol in SYMBOLDS_NEEDS_ESCAPE
] + SYMBOLS_REST


class TokenizeError(Exception):
    pass


@dataclass
class Token:
    line_num: int


@dataclass
class Keyword(Token):
    value: str


@dataclass
class Symbol(Token):
    value: str


@dataclass
class Identifier(Token):
    value: str


@dataclass
class IntegerConstant(Token):
    value: str


@dataclass
class StringConstant(Token):
    value: str


def gen_tokens_for_line(
    *, line: str, line_num: int, in_comment: bool
) -> Iterable[Tuple[Token, bool]]:
    while line:
        token, line, in_comment = _parse_token(
            line=line, line_num=line_num, in_comment=in_comment
        )
        yield token, in_comment


def gen_tokens_for_lines(*, lines: Iterable[str]) -> Iterable[Token]:
    in_comment = False
    for line_num, line in enumerate(lines):
        toks = gen_tokens_for_line(line=line, line_num=line_num, in_comment=in_comment)
        for tok, _in_comment in toks:
            in_comment = _in_comment
            if tok:
                yield tok


WHITE_SPACE_REGEX = re.compile(r"^\s*(.*)")
INLINE_COMMENT_REGEX = re.compile(r"^//.*")
MULTILINE_COMMENT_START_REGEX = re.compile(r"^/\*(.*)")
MULTILINE_COMMENT_END_REGEX = re.compile(r"^.*\*/(.*)")

IDENTIFIER_KEYWORD_REGEX = re.compile(r"^([a-zA-Z_][a-zA-Z_\d]*)\s*(.*)")
SYMBOL_REGEXS = [re.compile(rf"^({symbol})\s*(.*)") for symbol in VALID_SYMBOLS_ESCAPED]
INTEGER_CONSTANT_REGEX = re.compile(r"^(\d+)\s*(.*)")
STRING_CONSTANT_REGEX = re.compile(r"^\"([a-zA-Z\d?\s:]*)\"\s*(.*)")

REGEXS_WITH_FACTORY = [
    (
        IDENTIFIER_KEYWORD_REGEX,
        lambda line_num, val: Keyword(line_num, val)
        if val in VALID_KEYWORDS
        else Identifier(line_num, val),
    ),
    *((r, Symbol) for r in SYMBOL_REGEXS),
    (INTEGER_CONSTANT_REGEX, IntegerConstant),
    (STRING_CONSTANT_REGEX, StringConstant),
]


def _parse_token(*, line, line_num, in_comment):
    if in_comment:
        match = MULTILINE_COMMENT_END_REGEX.match(line)
        if match:
            rest, = match.groups()
            return None, rest, False
        else:
            return None, "", True

    line, = WHITE_SPACE_REGEX.match(line).groups()
    if INLINE_COMMENT_REGEX.match(line):
        return None, "", False

    match = MULTILINE_COMMENT_START_REGEX.match(line)
    if match:
        rest, = match.groups()
        return None, rest, True

    for regex, factory in REGEXS_WITH_FACTORY:
        match = regex.match(line)
        if match:
            *args, rest = match.groups()
            return factory(line_num, *args), rest, False
    raise TokenizeError(f"{line_num}: failed to tokenize: {line}")
