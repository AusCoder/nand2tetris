import re
import sys
import argparse
import itertools
import logging
from collections import deque
from enum import Enum
from pathlib import Path
from typing import Optional, Tuple, List, Iterable


logger = logging.getLogger(__name__)


class CommandType(Enum):
    NONE = 0
    ARITHMETIC = 1
    PUSH = 2
    POP = 3
    LABEL = 4
    GOTO = 5
    IFGOTO = 6
    FUNCTION = 7
    CALL = 8
    RETURN = 9


class ParseError(Exception):
    pass


class InvalidArgumentError(Exception):
    pass


class Parser:
    # End of line with comments regex
    _re_eol = r"\s*(//.*)?\n$"
    # Empty or commented line
    _re_none_line = rf"^{_re_eol}"
    # Arithmetic commands regex
    _re_arithmetic = rf"\s*(add|sub|neg|eq|gt|lt|and|or|not){_re_eol}"
    # Push and pop command regexes
    _re_memory_segment = r"(local|argument|this|that|constant|static|pointer|temp)"
    _re_argument = r"(\d+)"
    _re_push = rf"\s*push\s+{_re_memory_segment}\s+{_re_argument}{_re_eol}"
    _re_pop = rf"\s*pop\s+{_re_memory_segment}\s+{_re_argument}{_re_eol}"
    # Symbol name regex
    _re_symbol = r"([a-zA-Z][a-zA-Z\d_\.:$]*)"
    # Label regex
    _re_label = rf"\s*label\s+{_re_symbol}{_re_eol}"
    # Goto regex
    _re_goto = rf"\s*goto\s+{_re_symbol}{_re_eol}"
    # If-goto regex
    _re_if_goto = rf"\s*if-goto\s+{_re_symbol}{_re_eol}"
    # Function regex
    _re_function = rf"\s*function\s+{_re_symbol}\s+(\d+){_re_eol}"
    # Call regex
    _re_call = rf"\s*call\s+{_re_symbol}\s+(\d+){_re_eol}"
    # Return regex
    _re_return = rf"\s*return{_re_eol}"

    _regexs = [
        (re.compile(r), c)
        for r, c in [
            (_re_arithmetic, CommandType.ARITHMETIC),
            (_re_push, CommandType.PUSH),
            (_re_pop, CommandType.POP),
            (_re_label, CommandType.LABEL),
            (_re_goto, CommandType.GOTO),
            (_re_if_goto, CommandType.IFGOTO),
            (_re_function, CommandType.FUNCTION),
            (_re_call, CommandType.CALL),
            (_re_return, CommandType.RETURN),
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
                _, = m.groups()
                self._current_arguments = (None, None)
                return command_type
            elif command_type == CommandType.ARITHMETIC:
                argument, _ = m.groups()
                self._current_arguments = (argument, None)
                return command_type
            elif command_type in [CommandType.PUSH, CommandType.POP]:
                memory_segment, argument, _ = m.groups()
                self._current_arguments = (memory_segment, int(argument))
                return command_type
            elif command_type in [
                CommandType.LABEL,
                CommandType.GOTO,
                CommandType.IFGOTO,
            ]:
                label, _ = m.groups()
                self._current_arguments = (label, None)
                return command_type
            elif command_type in [CommandType.FUNCTION, CommandType.CALL]:
                label, num_args_or_locals, _ = m.groups()
                self._current_arguments = (label, int(num_args_or_locals))
                return command_type
            elif command_type == CommandType.RETURN:
                _, = m.groups()
                self._current_arguments = (None, None)
                return command_type
            else:
                raise RuntimeError(f"Unexpected command type: {command_type}")
        raise ParseError(f"Line {self._current_line_num}:'{self._current_line}'")

    def arguments(self) -> Tuple[Optional[str], Optional[int]]:
        return self._current_arguments


class CodeGenerator:
    def __init__(self, verbose: bool = True) -> None:
        self.static_prefix = None
        self._uniq_int = 0
        self._current_fn_name = "Sys.init"
        self._verbose = verbose

    def generate_init(self) -> str:
        lines = ["// bootstrap"] if self._verbose else []
        lines.extend(["@256", "D=A", "@SP", "M=D"])
        return "\n".join(lines) + "\n" + self.generate_call("Sys.init", 0)

    def generate_arithmetic(self, argument: str) -> str:
        lines = [f"// {argument}"] if self._verbose else []
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
                f"@{argument}.true{self._uniq_int}",
                jump_line,
                "@SP  // RAM[*SP - 1]=false (ie 0)",
                "A=M-1",
                "M=0",
                f"@{argument}.end{self._uniq_int}",
                "0; JMP",
                f"({argument}.true{self._uniq_int})",
                "@SP  // RAM[*SP - 1]=true (ie -1)",
                "A=M-1",
                "M=-1",
                f"({argument}.end{self._uniq_int})",
            ]
        )
        self._uniq_int += 1
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

    def generate_push(self, memory_segment: str, argument: int) -> str:
        if self.static_prefix is None:
            raise RuntimeError("static_prefix not set")

        lines = [f"// push {memory_segment} {argument}"] if self._verbose else []
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
            lines.extend(self._push_constant(argument))
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

    def _push_constant(self, argument: int) -> List[str]:
        if argument in [0, 1]:
            lines = [f"D={argument}  // D={argument}"]
        else:
            lines = [f"@{argument}  // D={argument}", "D=A"]
        lines.extend(self._push_d_sp_inc())
        return lines

    def generate_pop(self, memory_segment: str, argument: int) -> str:
        if self.static_prefix is None:
            raise RuntimeError("static_prefix not set")

        lines = [f"// pop {memory_segment} {argument}"] if self._verbose else []
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

    def _sp_dec_pop_d(self) -> List[str]:
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

    def generate_label(self, symbol: str) -> str:
        label = f"{self._current_fn_name}${symbol}"
        lines = [f"// label {label}", f"({label})"] if self._verbose else []
        return "\n".join(lines)

    def generate_goto(self, symbol: str) -> str:
        label = f"{self._current_fn_name}${symbol}"
        lines = [f"// goto {label}", f"@{label}", "0; JMP"] if self._verbose else []
        return "\n".join(lines)

    def generate_if_goto(self, symbol: str) -> str:
        label = f"{self._current_fn_name}${symbol}"
        lines = [f"// if-goto {label}"] if self._verbose else []
        lines.extend(self._sp_dec_pop_d())
        lines.extend([f"@{label}", "D; JNE"])
        return "\n".join(lines)

    def generate_function(self, name: str, num_locals: int) -> str:
        self._current_fn_name = name
        lines = [f"// function {name} {num_locals}"] if self._verbose else []
        lines.extend([f"({name})", "D=0"])
        for _ in range(num_locals):
            lines.extend(self._push_d_sp_inc())
        return "\n".join(lines)

    def generate_return(self) -> str:
        lines = ["// return"] if self._verbose else []
        lines.extend(
            [
                "@LCL  // R13 = LCL = FRAME",
                "D=M",
                "@R13",
                "M=D",
                "@5  // R14 = *(LCL - 5) = return address",
                "A=D-A",
                "D=M",
                "@R14",
                "M=D",
                "@SP  // *ARG = return value",
                "A=M-1",
                "D=M",
                "@ARG",
                "A=M",
                "M=D",
                "@ARG  // SP = ARG + 1",
                "D=M",
                "@SP",
                "M=D+1",
                "@R13  // THAT = *(FRAME - 1)",
                "D=M",
                "A=D-1",
                "D=M",
                "@THAT",
                "M=D",
                "@R13  // THIS = *(FRAME - 2)",
                "D=M",
                "@2",
                "A=D-A",
                "D=M",
                "@THIS",
                "M=D",
                "@R13  // ARG = *(FRAME - 3)",
                "D=M",
                "@3",
                "A=D-A",
                "D=M",
                "@ARG",
                "M=D",
                "@R13  // LCL = *(FRAME - 4)",
                "D=M",
                "@4",
                "A=D-A",
                "D=M",
                "@LCL",
                "M=D",
                "@R14  // goto return address",
                "A=M",
                "0; JMP",
            ]
        )
        return "\n".join(lines)

    def generate_call(self, name: str, num_arguments: int) -> str:
        lines = [f"// call {name} {num_arguments}"] if self._verbose else []
        return_label = f"RETURN_{self._uniq_int}"
        self._uniq_int += 1
        # push return address
        lines.extend([f"@{return_label}", "D=A"])
        lines.extend(self._push_d_sp_inc())
        # push local, argument, this, that onto stack
        for segment in ["LCL", "ARG", "THIS", "THAT"]:
            lines.extend([f"@{segment}", "D=M"])
            lines.extend(self._push_d_sp_inc())
        # set ARG = SP - num_arguments - 5
        lines.extend(
            [
                f"@{num_arguments} // ARG=SP - num_arguments - 5",
                "D=A",
                "@5",
                "D=D+A",
                "@SP",
                "D=M-D",
                "@ARG",
                "M=D",
            ]
        )
        # set LCL = SP
        lines.extend(["@SP  // LCL = SP", "D=M", "@LCL", "M=D"])
        # goto f
        lines.extend([f"@{name}  // goto {name}", "0; JMP"])
        # return address label
        lines.extend([f"({return_label})  // return address"])
        return "\n".join(lines)


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

    if input_filepath.is_dir():
        needs_bootstrap = True
        input_filepaths = input_filepath.glob("*.vm")
    else:
        needs_bootstrap = False
        input_filepaths = [input_filepath]

    logger.info(f"Input: {input_filepath}")
    logger.info(f"Output: {output_filepath}")

    code_gen = CodeGenerator()
    with open(output_filepath, "w") as out_fh:
        if needs_bootstrap:
            out_fh.write(code_gen.generate_init())
            out_fh.write("\n")
        for input_filepath in input_filepaths:
            code_gen.static_prefix = input_filepath.stem
            with open(input_filepath) as fh:
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
                    elif command_type == CommandType.LABEL:
                        label, _ = p.arguments()
                        code = code_gen.generate_label(label)
                    elif command_type == CommandType.GOTO:
                        label, _ = p.arguments()
                        code = code_gen.generate_goto(label)
                    elif command_type == CommandType.IFGOTO:
                        label, _ = p.arguments()
                        code = code_gen.generate_if_goto(label)
                    elif command_type == CommandType.FUNCTION:
                        name, num_locals = p.arguments()
                        code = code_gen.generate_function(name, num_locals)
                    elif command_type == CommandType.CALL:
                        name, num_args = p.arguments()
                        code = code_gen.generate_call(name, num_args)
                    elif command_type == CommandType.RETURN:
                        code = code_gen.generate_return()
                    else:
                        raise RuntimeError(f"Unexpected command type: {command_type}")
                    out_fh.write(code)
                    out_fh.write("\n")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("vm_translator")
    main(parse_args())
