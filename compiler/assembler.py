import re
import sys
import argparse
from typing import Dict, Iterable, Any
from dataclasses import dataclass
from pathlib import Path


class ParseError(RuntimeError):
    pass


@dataclass
class AInstructionNumeric:
    address: int
    src_line_num: int


@dataclass
class AInstructionSymbolic:
    symbol: str
    src_line_num: int


@dataclass
class CInstruction:
    dest: str
    comp: str
    jump: str
    src_line_num: int


@dataclass
class Symbol:
    symbol: str
    src_line_num: int


@dataclass
class NoneLine:
    src_line_num: int


class RamSymbolTable:
    def __init__(self):
        self._table = dict(SCREEN=16384, KBD=24576, SP=0, LCL=1, ARG=2, THIS=3, THAT=4)
        for x in range(16):
            self._table[f"R{x}"] = x
        self._cur_mem_addr = 16

    def location(self, symbol: str) -> int:
        if symbol not in self._table:
            self._table[symbol] = self._cur_mem_addr
            self._cur_mem_addr += 1
        return self._table[symbol]


def create_machine_code_tables():
    comp_table = {
        "0": "0101010",
        "1": "0111111",
        "-1": "0111010",
        "D": "0001100",
        "A": "0110000",
        "M": "1110000",
        "!D": "0001101",
        "!A": "0110001",
        "!M": "1110001",
        "-D": "0001111",
        "-A": "0110011",
        "-M": "0110011",
        "D+1": "0011111",
        "A+1": "0110111",
        "M+1": "1110111",
        "D-1": "0001110",
        "A-1": "0110010",
        "M-1": "1110010",
        "D+A": "0000010",
        "D+M": "1000010",
        "D-A": "0010011",
        "D-M": "1010011",
        "A-D": "0000111",
        "M-D": "1000111",
        "D&A": "0000000",
        "D&M": "1000000",
        "D|A": "0010101",
        "D|M": "1010101",
    }
    dest_table = {
        None: "000",
        "M": "001",
        "D": "010",
        "MD": "011",
        "A": "100",
        "AM": "101",
        "AD": "110",
        "AMD": "111",
    }
    jump_table = {
        None: "000",
        "JGT": "001",
        "JEQ": "010",
        "JGE": "011",
        "JLT": "100",
        "JNE": "101",
        "JLE": "110",
        "JMP": "111",
    }
    return comp_table, dest_table, jump_table


def parse_a_instruction_numeric(line: str, line_num: int):
    pat = r"^\s*@(\d+)\s*(//.*)?$"
    result_fn = lambda match: AInstructionNumeric(int(match.group(1)), line_num)
    return _parse(pat, result_fn, line, line_num)


def parse_a_instruction_symbolic(line: str, line_num: int):
    pat = r"^\s*@([a-zA-Z][a-zA-Z\d_\.:$]*)\s*(//.*)?$"
    result_fn = lambda match: AInstructionSymbolic(match.group(1), line_num)
    return _parse(pat, result_fn, line, line_num)


def parse_c_instruction(line: str, line_num: int):
    # destination
    dest, line = _parse(
        r"^\s*(([AMD]{1,3})\s*=)?(.*)$",
        lambda m: (m.group(2), m.group(3)),
        line,
        line_num,
    )

    # computation
    pat = r"^\s*([1AMD]?)\s*([+\-!&|]?)\s*([01AMD])(.*)$"
    *groups, line = _parse(pat, lambda m: m.groups(), line, line_num)
    comp = "".join(groups)

    # destination
    pat = r"^\s*(;\s*(JGT|JEQ|JGE|JLT|JNE|JLE|JMP))?\s*(//.*)?$"
    jmp = _parse(pat, lambda m: m.group(2), line, line_num)

    return CInstruction(dest, comp, jmp, line_num)


def parse_symbol(line: str, line_num: int):
    name = _parse(
        r"^\s*\(([a-zA-Z][a-zA-Z\d_\.$]*)\)\s*(//.*)?$",
        lambda m: m.group(1),
        line,
        line_num,
    )
    return Symbol(name, line_num)


def parse_null_line(line: str, line_num: int):
    _parse(r"^\s*(//.*)?$", lambda m: None, line, line_num)
    return NoneLine(line_num)


def parse_statement(line: str, line_num: int):
    return _parse_one_of(
        [
            parse_a_instruction_numeric,
            parse_a_instruction_symbolic,
            parse_c_instruction,
            parse_symbol,
            parse_null_line,
        ],
        line,
        line_num,
    )


def _parse_one_of(line_parsers, line: str, line_num: int):
    for line_parser in line_parsers:
        try:
            return line_parser(line, line_num)
        except ParseError:
            pass
    raise ParseError(line_num, line)


def _parse(pat, result_fn, line: str, line_num: int):
    match = re.match(pat, line)
    if match:
        return result_fn(match)
    raise ParseError(line_num, pat, line)


def gen_lines(filepath: Path):
    for line_num, line in enumerate(filepath.read_text().split("\n")):
        yield line_num, line


def gen_instructions(lines: Iterable[Any]):
    for line_num, line in lines:
        statement = parse_statement(line, line_num)
        if isinstance(statement, NoneLine):
            continue
        yield statement


def fill_rom_symbol_table(rom_symbol_table: Dict[str, int], instructions: Iterable[Any]):
    """ First pass of the assembler that fills the rom symbol table
        with locations of symbols.
    """
    instruction_number = 0
    for instruction in instructions:
        if isinstance(instruction, Symbol):
            rom_symbol_table[instruction.symbol] = instruction_number
        else:
            instruction_number += 1


def gen_translated_symbols(
    rom_symbol_table: Dict[str, int],
    ram_symbol_table: RamSymbolTable,
    instructions: Iterable[Any],
):
    """ Translates symbols to numeric memory addresses """
    for instruction in instructions:
        if isinstance(instruction, AInstructionSymbolic):
            if instruction.symbol in rom_symbol_table:
                instr_num = rom_symbol_table[instruction.symbol]
            else:
                instr_num = ram_symbol_table.location(instruction.symbol)
            yield AInstructionNumeric(instr_num, instruction.src_line_num)
        elif isinstance(instruction, Symbol):
            continue
        else:
            yield instruction


def gen_machine_code(
    comp_table: Dict[str, str],
    dest_table: Dict[str, str],
    jump_table: Dict[str, str],
    instructions: Iterable[Any],
):
    """ Converts instructions to machine code """
    for instruction in instructions:
        if isinstance(instruction, AInstructionNumeric):
            yield f"0{instruction.address:015b}"
        elif isinstance(instruction, CInstruction):
            try:
                comp = comp_table[instruction.comp]
                dest = dest_table[instruction.dest]
                jump = jump_table[instruction.jump]
            except KeyError:
                raise ParseError(instruction)
            yield f"111{comp}{dest}{jump}"
        else:
            raise RuntimeError(f"Unexpected instruction: {instruction}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str)
    parser.add_argument("-o", "--output", help="output path", type=str)
    return parser.parse_args()


def main(args: argparse.Namespace):
    input_filepath = Path(args.input)
    if args.output is None:
        output_filepath = input_filepath.parent.joinpath(f"{input_filepath.stem}.hack")
    else:
        output_filepath = Path(args.output)

    # Initialize symbol tables and translation tables
    rom_symbol_table = dict()
    ram_symbol_table = RamSymbolTable()
    comp_table, dest_table, jump_table = create_machine_code_tables()

    # First pass, record symbol locations
    lines = gen_lines(input_filepath)
    instructions = gen_instructions(lines)
    fill_rom_symbol_table(rom_symbol_table, instructions)

    # Second pass
    lines = gen_lines(input_filepath)
    instructions = gen_instructions(lines)
    instructions = gen_translated_symbols(
        rom_symbol_table, ram_symbol_table, instructions
    )
    machine_code = gen_machine_code(
        comp_table, dest_table, jump_table, instructions
    )

    # Write machine code to output file
    output_filepath.write_text("\n".join(l for l in machine_code))


if __name__ == "__main__":
    main(parse_args())
