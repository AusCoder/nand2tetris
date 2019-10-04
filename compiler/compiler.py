import sys
from pathlib import Path
import xml.etree.ElementTree as ET
from xml.dom import minidom

from tokenizer import gen_tokens_for_lines
from parser import Parser
from code_generator import CodeGenerator


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
    cls = parser.parse_class()
    code_generator = CodeGenerator()
    code = code_generator.generate(cls)
    Path("test.vm").write_text("\n".join(code))
    # print(code_generator._symbol_tables._tables[0]._table)
    # print(cls)
    # xmlstr = minidom.parseString(ET.tostring(cls.to_xml())).toprettyxml(indent="  ")
    # with open("test.xml", "w") as fh:
    #     fh.write(xmlstr)


if __name__ == "__main__":
    main()
