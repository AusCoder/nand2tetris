import re


class Token:
    def __init__(self, *, line_num):
        self.line_num = line_num

    @classmethod
    def parse(cls, stream, line_num):
        for regex in cls.regexs:
            m = regex.match(stream)
            if m:
                *args, rest = m.groups()
                return cls(*args, line_num=line_num), rest


class Keyword:
    valid_keywords = [
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
    regexs = [re.compile(rf"^({kw})\s+(.*)") for kw in valid_keywords]

    def __init__(self, value, line_num):
        super().__init__(line_num=line_num)
        self.value = value


class Symbol:
    valid_symbols = [
        "{",
        "}",
        "(",
        ")",
        "[",
        "]",
        ".",
        ",",
        ";",
        "+",
        "-",
        "*",
        "/",
        "&",
        ",",
        "<",
        ">",
        "=",
        "~",
    ]

    def __init__(self, line_num, value):
        super().__init__(line_num)
        self.value = value


class Identifier:
    def __init__(self, name, *, line_num):
        super().__init__(line_num=line_num)
        self.name = name


class IntegerConstant:
    def __init__(self, line_num, value):
        super().__init__(line_num)
        if 0 > value > 32767:
            raise ValueError(f"int constant out of bounds: {value}")
        self.value = value


class StringConstant:
    def __init__(self, line_num, value):
        super().__init__(line_num)
        self.value = value
