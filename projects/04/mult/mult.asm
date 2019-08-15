// This file is part of www.nand2tetris.org
// and the book "The Elements of Computing Systems"
// by Nisan and Schocken, MIT Press.
// File name: projects/04/Mult.asm

// Multiplies R0 and R1 and stores the result in R2.
// (R0, R1, R2 refer to RAM[0], RAM[1], and RAM[2], respectively.)

// Approach is going to be repreated addition

// int a, b;
// int acc = 0;
// if (b < 0) {
//     a *= -1;
//     b *= -1;
// }
// while (b > 0) {
//     acc += a;
//     b -= 1;
// }
// return acc;

    @acc  // acc = 0
    M=0
    @R0  // copy a to new register to preserve original registers
    D=M
    @a
    M=D
    @R1  // copy b to new register
    D=M
    @b
    M=D

    @b  // if b >= 0 GoTo loop
    D=M
    @LOOP
    D; JGE

    @a  // a *= -1
    M=-M
    @b  // b *= -1
    M=-M

(LOOP)
    @b  // while (b > 0)
    D=M
    @RESULT
    D; JEQ

    @a  // D = a
    D=M
    @acc
    M=D + M  // sum += a
    @b
    M=M - 1  // b -=1

    @LOOP
    0; JMP  // GoTo LOOP

(RESULT)
    @acc  // write result to R3
    D=M
    @R2
    M=D

(END)
    @END
    0; JMP // End loop
