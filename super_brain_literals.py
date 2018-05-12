"""
Based on the PyPy tutorial by Andrew Brown
example5.py - BF interpreter in RPython, translatable by PyPy, with JIT, and
              with a get_printable_location function and pure function wrapper
              for the dictionary lookup.
"""

import os
import sys

# So that you can still run this module under standard CPython, I add this
# import guard that creates a dummy class instead.
try:
    from rpython.rlib.jit import JitDriver, purefunction
except ImportError:
    class JitDriver(object):
        def __init__(self,**kw): pass
        def jit_merge_point(self,**kw): pass
        def can_enter_jit(self,**kw): pass
    def purefunction(f): return f

def get_location(pc, program, bracket_map):
    return "%s_%s_%s" % (
            program[:pc], program[pc], program[pc+1:]
            )

jitdriver = JitDriver(greens=['pc', 'program', 'bracket_map'], reds=['tape'],
        get_printable_location=get_location)

@purefunction
def get_matching_bracket(bracket_map, pc):
    return bracket_map[pc]

@purefunction
def str_add(a, b):
    return str(a) + str(b)

def mainloop(program, func_map, bracket_map, args=[]):
    pc = 0
    tape = Tape()
    for arg in args:
        tape.set(ord(str(arg)[0]))
        tape.advance()
    for arg in args:
        tape.devance()

    #func_map = {";" : str_add }

    while pc < len(program):
        jitdriver.jit_merge_point(pc=pc, tape=tape, program=program,
                bracket_map=bracket_map)

        code = program[pc]

        if code == ">":
            tape.advance()

        elif code == "<":
            tape.devance()

        elif code == "+":
            tape.inc()

        elif code == "-":
            tape.dec()
        
        elif code == ".":
            # print
            os.write(1, chr(tape.get()))
        
        elif code == ",":
            # read from stdin
            tape.set(ord(os.read(0, 1)[0]))

        elif code == "[" and tape.get() == 0:
            # Skip forward to the matching ]
            pc = get_matching_bracket(bracket_map, pc)
            
        elif code == "]" and tape.get() != 0:
            # Skip back to the matching [
            pc = get_matching_bracket(bracket_map, pc)

        elif code == "^":
            tape.create_str_obj()

        #elif code == ";": # CONCAT
        #    os.write(1, func_map[code]("", "a"))

        pc += 1

class Tape(object):
    def __init__(self):
        self.thetape = [0]
        self.position = 0
        self.objecttape = {}

    def get(self):
        return self.thetape[self.position]
    def set(self, val):
        self.thetape[self.position] = val
    def inc(self):
        self.thetape[self.position] += 1
    def dec(self):
        self.thetape[self.position] -= 1
    def advance(self):
        self.position += 1
        if len(self.thetape) <= self.position:
            self.thetape.append(0)
    def devance(self):
        self.position -= 1

    def create_str_obj(self):
        self.objecttape["STRING"] = [""]

import struct

def parse(program):
    parsed = []
    bracket_map = {}
    leftstack = []

    pc = 0

    import pdb
    pdb.set_trace()

    struct.unpack(">%s" % token_width, 0)
    for char in program:
        if char in ('[', ']', '<', '>', '+', '-', ',', '.'):
            parsed.append(char)

            if char == '[':
                leftstack.append(pc)
            elif char == ']':
                left = leftstack.pop()
                right = pc
                bracket_map[left] = right
                bracket_map[right] = left
            pc += 1
    
    return "".join(parsed), bracket_map

def run(fp, args=[]):
    program_contents = ""
    while True:
        read = os.read(fp, 4096)
        if len(read) == 0:
            break
        program_contents += read
    os.close(fp)
    program, bm = parse(program_contents)
    func_map = {";" : str_add }
    mainloop(program, func_map, bm, args)

def entry_point(argv):
    more_args = False
    try:
        filename = argv[1]
        if len(argv) > 2:
            more_args = True
    except IndexError:
        print "You must supply a filename"
        return 1
    if more_args:
        run(os.open(filename, os.O_RDONLY, 0777), args=argv[2:])
    else:
        run(os.open(filename, os.O_RDONLY, 0777))

    return 0

def target(*args):
    return entry_point, None
    
def jitpolicy(driver):
    from rpython.jit.codewriter.policy import JitPolicy
    return JitPolicy()

if __name__ == "__main__":
    entry_point(sys.argv)
