import sys
from pathlib import Path

from tokenizer import gen_tokens_for_lines
from parser import Parser


def print_gen(xs):
    for x in xs:
        print(x)
        yield x


def main():
    input_path = Path(sys.argv[1])
    lines = (line for line in input_path.read_text().split("\n"))
    # lines = print_gen(lines)
    tokens = gen_tokens_for_lines(lines=lines)
    parser = Parser(tokens)
    print(parser.parse_class())
    # for token in tokens:
    #     print(token)


if __name__ == "__main__":
    main()
