import sys
import shutil
from pathlib import Path
import xml.etree.ElementTree as ET
from xml.dom import minidom

from tokenizer import gen_tokens_for_lines
from parser import Parser
from code_generator import CodeGenerator


OS_LIB = Path("tools/OS")
EXTRA_OS_LIBS = [
    Path("projects/12/Memory.vm"),
    Path("projects/12/Array.vm"),
    Path("projects/12/Math.vm"),
    Path("projects/12/Keyboard.vm"),
    # Path("projects/12/Screen.vm"),
]


def print_gen(xs):
    for x in xs:
        print(x)
        yield x


def main():
    inpt = Path(sys.argv[1])
    if inpt.is_dir():
        input_paths = inpt.glob("*.jack")

        for src in OS_LIB.glob("*.vm"):
            dst = inpt.joinpath(src.name)
            shutil.copy(src, dst)

        for src in EXTRA_OS_LIBS:
            dst = inpt.joinpath(src.name)
            shutil.copy(src, dst)
    else:
        input_paths = [inpt]

    for input_path in input_paths:
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
