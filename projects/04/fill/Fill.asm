// This file is part of www.nand2tetris.org
// and the book "The Elements of Computing Systems"
// by Nisan and Schocken, MIT Press.
// File name: projects/04/Fill.asm

// Runs an infinite loop that listens to the keyboard input.
// When a key is pressed (any key), the program blackens the screen,
// i.e. writes "black" in every pixel;
// the screen should remain fully black as long as the key is pressed.
// When no key is pressed, the program clears the screen, i.e. writes
// "white" in every pixel;
// the screen should remain fully clear as long as no key is pressed.

// READ:
// address = SCREEN
// x = kbd
// if x == 0:
//     colour = 0
// else:
//     colour = 1
// goto DRAW

// DRAW:
// if address = KBD:
//     goto READ
// RAM[address] = colour
// address += 1
// goto DRAW

    @prev_key  // previous seen key
    M=0

(READ_LOOP)
    @SCREEN  // address = SCREEN
    D=A
    @address
    M=D

    @KBD  // read keyboard
    D=M

    @key_read  // if key_read == prev_key: goto READ_LOOP
    M=D
    @prev_key
    D=D-M
    @READ_LOOP
    D; JEQ

    // At this point, the a key was pressed
    @key_read
    D=M
    @prev_key  // update previous seen key
    M=D

    @COLOUR_0  // if x == 0: colour = 0
    D; JEQ

    @colour
    M=-1
    @FILL_LOOP  // draw(colour)
    0; JMP

(COLOUR_0)
    @colour
    M=0
    @FILL_LOOP  // draw(colour)
    0; JMP

(FILL_LOOP)
    @address  // if address = KBD, Goto END
    D=M
    @KBD
    D=A-D
    @READ_LOOP
    D; JEQ

    @colour  // RAM[address] = colour
    D=M
    @address
    A=M
    M=D

    @address // address += 1
    M=M + 1

    @FILL_LOOP
    0; JMP  // GoTo FILL_LOOP
