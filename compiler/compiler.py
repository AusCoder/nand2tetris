import sys
import shutil
from pathlib import Path
import xml.etree.ElementTree as ET
from xml.dom import minidom

from tokenizer import gen_tokens_for_lines
from parser import Parser
from code_generator import CodeGenerator


OS_LIB = Path("tools/OS")


def print_gen(xs):
    for x in xs:
        print(x)
        yield x


def main():
    input_dir = Path(sys.argv[1])
    if not input_dir.is_dir():
        raise RuntimeError(f"Expected a directory: {input_dir}")

    for src in OS_LIB.glob("*.vm"):
        dst = input_dir.joinpath(src.name)
        if not dst.exists():
            shutil.copy(src, dst)

    for input_path in input_dir.glob("*.jack"):
        output_path = input_path.parent.joinpath(f"{input_path.stem}.vm")
        lines = (line for line in input_path.read_text().split("\n"))
        # lines = print_gen(lines)
        tokens = gen_tokens_for_lines(lines=lines)
        parser = Parser(tokens)
        cls = parser.parse_class()
        code_generator = CodeGenerator()
        code = code_generator.generate(cls)
        output_path.write_text("\n".join(code))


if __name__ == "__main__":
    main()
