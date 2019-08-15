import re
import sys
import argparse
import itertools
import logging
from enum import Enum
from pathlib import Path
from typing import Optional, Tuple, List, Iterable


logger = logging.getLogger(__name__)


class CommandType(Enum):
    NONE = 0
    ARITHMETIC = 1
    PUSH = 2
    POP = 3


class ParseError(Exception):
    pass


class InvalidArgumentError(Exception):
    pass


class Parser:
    # End of line with comments regex
    _re_eol = r"\s*(//.*)?\n$"
    # Arithmetic commands regex
    _re_arithmetic = rf"\s*(add|sub|neg|eq|gt|lt|and|or|not){_re_eol}"
    # Push and pop command regexes
    _re_memory_segment = r"(local|argument|this|that|constant|static|pointer|temp)"
    _re_argument = r"(\d+)"
    _re_push = rf"\s*push\s+{_re_memory_segment}\s+{_re_argument}{_re_eol}"
    _re_pop = rf"\s*pop\s+{_re_memory_segment}\s+{_re_argument}{_re_eol}"
    # Empty or commented line
    _re_none_line = rf"^{_re_eol}"

    _regexs = [
        (re.compile(r), c)
        for r, c in [
            (_re_arithmetic, CommandType.ARITHMETIC),
            (_re_push, CommandType.PUSH),
            (_re_pop, CommandType.POP),
            (_re_none_line, CommandType.NONE),
        ]
    ]

    def __init__(self, line_gen: Iterable[str]) -> None:
        self._line_gen = line_gen

        self._current_line = None
        self._current_line_num = -1
        self._current_arguments = None

    def has_next_command(self) -> bool:
        try:
            self._current_line = next(self._line_gen)
            self._current_line_num += 1
            return True
        except StopIteration:
            return False

    def advance(self) -> CommandType:
        for regex, command_type in self._regexs:
            m = regex.match(self._current_line)
            if not m:
                continue
            if command_type == CommandType.NONE:
                return command_type
            elif command_type == CommandType.ARITHMETIC:
                argument, _ = m.groups()
                self._current_arguments = (argument, None)
                return command_type
            elif command_type == CommandType.PUSH or command_type == CommandType.POP:
                memory_segment, argument, _ = m.groups()
                self._current_arguments = (memory_segment, int(argument))
                return command_type
            else:
                raise RuntimeError(f"Unexpected command type: {command_type}")
        raise ParseError(f"Line {self._current_line_num}:'{self._current_line}'")

    def arguments(self) -> Tuple[str, Optional[int]]:
        return self._current_arguments


class CodeGenerator:
    def __init__(self, static_prefix: str) -> None:
        self.static_prefix = static_prefix
        self._jmp_count = 0

    def generate_arithmetic(self, argument: str) -> str:
        lines = [f"// {argument}"]
        if argument in ["add", "sub", "and", "or"]:
            lines = self._generate_binary_op(lines, argument)
        elif argument in ["eq", "gt", "lt"]:
            lines = self._generate_comparison(lines, argument)
        elif argument in ["neg", "not"]:
            lines = self._generate_unary_op(lines, argument)
        else:
            RuntimeError(f"Unexpected argument: {argument}")
        return "\n".join(lines)

    def _generate_binary_op(self, lines: List[str], argument: str) -> List[str]:
        if argument == "add":
            op = "M=M+D"
        elif argument == "sub":
            op = "M=M-D"
        elif argument == "and":
            op = "M=D&M"
        elif argument == "or":
            op = "M=D|M"
        else:
            RuntimeError(f"Unexpected argument: {argument}")
        lines.extend(self._sp_dec_pop_d())
        lines.extend(["@SP", "A=M-1", op])
        return lines

    def _generate_unary_op(self, lines: List[str], argument: str) -> List[str]:
        if argument == "neg":
            op = "M=-M"
        elif argument == "not":
            op = "M=!M"
        else:
            RuntimeError(f"Unexpected argument: {argument}")
        lines.extend(["@SP", "A=M-1", op])
        return lines

    def _generate_comparison(self, lines: List[str], argument: str) -> List[str]:
        if argument == "eq":
            jump_line = "D; JEQ"
        elif argument == "gt":
            jump_line = "D; JGT"
        elif argument == "lt":
            jump_line = "D; JLT"
        else:
            RuntimeError(f"Unexpected argument: {argument}")
        lines.extend(self._sp_dec_pop_d())
        lines.extend(
            [
                "@SP  // D=RAM[*SP - 1] - D",
                "A=M-1",
                "D=M-D",
                f"@eq.true{self._jmp_count}",
                jump_line,
                "@SP  // RAM[*SP - 1]=false (ie 0)",
                "A=M-1",
                "M=0",
                f"@eq.end{self._jmp_count}",
                "0; JMP",
                f"(eq.true{self._jmp_count})  // RAM[*SP - 1]=true (ie -1)",
                "@SP",
                "A=M-1",
                "M=-1",
                f"(eq.end{self._jmp_count})",
            ]
        )
        self._jmp_count += 1
        return lines

    def generate_push(self, memory_segment: str, argument: int) -> str:
        lines = [f"// push {memory_segment} {argument}"]
        if memory_segment in ["local", "argument", "this", "that"]:
            translated_segment = self._translate_memory_segment(memory_segment)
            lines.extend(
                [
                    f"@{argument}  // D=RAM[*{translated_segment} + {argument}]",
                    "D=A",
                    f"@{translated_segment}",
                    "A=D+M",
                    "D=M",
                ]
            )
            lines.extend(self._push_d_sp_inc())
        elif memory_segment == "static":
            lines.extend([f"@{self.static_prefix}.{argument}", "D=M"])
            lines.extend(self._push_d_sp_inc())
        elif memory_segment == "constant":
            lines.extend([f"@{argument}  // D={argument}", "D=A"])
            lines.extend(self._push_d_sp_inc())
        elif memory_segment == "pointer":
            if 0 > argument > 1:
                raise InvalidArgumentError(f"pointer argument: {argument}")
            register_num = argument + 3
            lines.extend([f"@R{register_num}  // D=R{register_num}", "D=M"])
            lines.extend(self._push_d_sp_inc())
        elif memory_segment == "temp":
            if 0 > argument > 7:
                raise InvalidArgumentError(f"temp argument: {argument}")
            register_num = argument + 5
            lines.extend([f"@R{register_num}  // D=R{register_num}", "D=M"])
            lines.extend(self._push_d_sp_inc())
        else:
            raise RuntimeError(f"Unexpected memory segment: {memory_segment}")
        return "\n".join(lines)

    def _push_d_sp_inc(self):
        """Sets RAM[*SP]=D and SP++"""
        return ["@SP  // RAM[*SP]=D", "A=M", "M=D", "@SP  // SP++", "M=M+1"]

    def generate_pop(self, memory_segment: str, argument: int) -> str:
        lines = [f"// pop {memory_segment} {argument}"]
        if memory_segment in ["local", "argument", "this", "that"]:
            translated_segment = self._translate_memory_segment(memory_segment)
            lines.extend(
                [
                    f"@{argument}  // R13=*{translated_segment} + {argument}",
                    "D=A",
                    f"@{translated_segment}",
                    "D=D+M",
                    "@R13",
                    "M=D",
                ]
            )
            lines.extend(self._sp_dec_pop_d())
            lines.extend(["@R13  // RAM[*R13]=D", "A=M", "M=D"])
        elif memory_segment == "static":
            lines.extend(self._sp_dec_pop_d())
            lines.extend([f"@{self.static_prefix}.{argument}", "M=D"])
        elif memory_segment == "pointer":
            if 0 > argument > 1:
                raise InvalidArgumentError(f"pointer argument: {argument}")
            register_num = argument + 3
            lines.extend(self._sp_dec_pop_d())
            lines.extend([f"@R{register_num}  // R{register_num}=D", "M=D"])
        elif memory_segment == "temp":
            if 0 > argument > 7:
                raise InvalidArgumentError(f"temp argument: {argument}")
            register_num = argument + 5
            lines.extend(self._sp_dec_pop_d())
            lines.extend([f"@R{register_num}  // R{register_num}=D", "M=D"])
        elif memory_segment == "constant":
            raise InvalidArgumentError("cannot have argument 'pop constant'")
        else:
            raise RuntimeError(f"Unexpected memory segment: {memory_segment}")
        return "\n".join(lines)

    def _sp_dec_pop_d(self):
        """SP-- and D=RAM[*SP]"""
        return ["@SP  // SP-- and D=RAM[*SP]", "AM=M-1", "D=M"]

    def _translate_memory_segment(self, memory_segment: str) -> str:
        if memory_segment == "local":
            return "LCL"
        elif memory_segment == "argument":
            return "ARG"
        elif memory_segment == "this":
            return "THIS"
        elif memory_segment == "that":
            return "THAT"
        else:
            raise RuntimeError(f"Unexpected memory segment: {memory_segment}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str)
    parser.add_argument("-o", "--output", help="output path", type=str)
    return parser.parse_args()


def main(args: argparse.Namespace) -> None:
    input_filepath = Path(args.input)
    if args.output is not None:
        output_filepath = Path(args.output)
    elif input_filepath.is_dir():
        output_filepath = input_filepath.joinpath(f"{input_filepath.stem}.asm")
    else:
        output_filepath = input_filepath.parent.joinpath(f"{input_filepath.stem}.asm")

    logger.info(f"Input: {input_filepath}")
    logger.info(f"Output: {output_filepath}")

    code_gen = CodeGenerator(input_filepath.stem)
    with open(input_filepath) as fh:
        with open(output_filepath, "w") as out_fh:
            p = Parser(fh)
            while p.has_next_command():
                command_type = p.advance()
                if command_type == CommandType.NONE:
                    continue
                elif command_type == CommandType.ARITHMETIC:
                    arg, _ = p.arguments()
                    code = code_gen.generate_arithmetic(arg)
                elif command_type == CommandType.PUSH:
                    code = code_gen.generate_push(*p.arguments())
                elif command_type == CommandType.POP:
                    code = code_gen.generate_pop(*p.arguments())
                else:
                    raise RuntimeError(f"Unexpected command type: {command_type}")
                out_fh.write(code)
                out_fh.write("\n")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("vm_translator")
    main(parse_args())
