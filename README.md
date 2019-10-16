## Nand to tetris

This is code for the Nand to Tetris course. The original course page can be found [here](https://www.nand2tetris.org/). You need to download the course materials to get the various emulation programs required to run the hdl, binary, assembly and vm programs.

### Compiler

The assembler, vm translator and compiler are written in python. Python `3.7+` is required. They can be run using:
```bash
python compiler/assembler.py path/to/File.asm
python compiler/vm_translator.py path/to/Directory
python compiler/compiler.py path/to/Directory
```

The compiler does not output an xml AST as proposed in the course. Instead an AST is created using python dataclasses.
