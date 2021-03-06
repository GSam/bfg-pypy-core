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

from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.translator.tool.cbuild import ExternalCompilationInfo

eci = ExternalCompilationInfo(libraries=['testlib'],
                              library_dirs=[os.path.abspath('.')],#/testlib.so')],
                              includes=[os.path.abspath('./stdlib.h')])

external_function = rffi.llexternal('myprint', [], lltype.Void,
                                    compilation_info=eci)

# Note to self: UUID4 has some fixed bits
# struct.unpack('>qq', uuid.UUID(int=uuid.UUID(bytes=os.urandom(16)).int | (1 << 127)).bytes)
INTEGER = (-6855051840143784798, -7880198636693933229)
STRING = (-5744892467500213749, 739713154171887357)
DOUBLE = (-5419088552942547567, 806613043255133199)

TYPE_BFG_OBJECT = rffi.CStruct('bfg_object',
                               # ('GUID_high', rffi.ULONGLONG), # unneeded?
                               # ('GUID_low', rffi.ULONGLONG), # unneeded?
                               ('metadata', rffi.ULONGLONG),
                               ('data', rffi.VOIDP))

TYPE_BFG_OBJECT_PTR = lltype.Ptr(TYPE_BFG_OBJECT)
TYPE_BFG_OBJECT_ARRAY = rffi.CArray(TYPE_BFG_OBJECT)

TYPE_BFG_TYPE_SPACE = rffi.CStruct('bfg_type_space',
                                   ('GUID_high', rffi.ULONGLONG),
                                   ('GUID_low', rffi.ULONGLONG),
                                   ('index', rffi.UINT),
                                   ('length', rffi.UINT),
                                   ('alloc_length', rffi.UINT),
                                   ('objects', TYPE_BFG_OBJECT_PTR))

TYPE_BFG_TYPE_SPACE_PTR = lltype.Ptr(TYPE_BFG_TYPE_SPACE)
TYPE_BFG_TAPE_ARRAY = rffi.CArray(TYPE_BFG_TYPE_SPACE_PTR)

aa = lltype.malloc(TYPE_BFG_TAPE_ARRAY, 1, flavor='raw')
aa[0] = lltype.malloc(TYPE_BFG_TYPE_SPACE, flavor='raw')

test = rffi.make(TYPE_BFG_TYPE_SPACE,
                 c_GUID_high=rffi.cast(rffi.ULONG, INTEGER[0]),#1),
                 c_GUID_low=rffi.cast(rffi.ULONG, 1),
                 c_length=rffi.cast(rffi.UINT, 2),
                 c_index=rffi.cast(rffi.UINT, 0),
                 c_alloc_length=rffi.cast(rffi.UINT, 2))

# test.c_objects = lltype.nullptr(TYPE_BFG_OBJECT_PTR.TO)
test_object = rffi.make(TYPE_BFG_OBJECT,
                        c_metadata=rffi.cast(rffi.ULONGLONG, 0),
                        c_data=lltype.nullptr(rffi.VOIDP.TO))
#test.c_objects = test_object

testb = lltype.malloc(TYPE_BFG_OBJECT_ARRAY, 2, flavor='raw')
testb[0].c_metadata = rffi.cast(rffi.ULONGLONG, 20)
testb[1].c_metadata = rffi.cast(rffi.ULONGLONG, 43)
test.c_objects = rffi.cast(TYPE_BFG_OBJECT_PTR, testb)

external_function2 = rffi.llexternal('bfg_execute', [rffi.ULONGLONG,
                                                     rffi.ULONGLONG,
                                                     TYPE_BFG_TYPE_SPACE_PTR,
                                                     rffi.UINT], lltype.Bool,
                                     compilation_info=eci)

tape_array_length = 1

def mainloop(program, bracket_map, args=[], types=[INTEGER, STRING, DOUBLE]):
    pc = 0
    tape = Tape(types)
    for arg in args:
        tape.set(ord(str(arg)[0]))
        tape.advance()
    for arg in args:
        tape.devance()

    #func_map = {";" : str_add }

    while pc < len(program):
        jitdriver.jit_merge_point(pc=pc, tape=tape, program=program,
                bracket_map=bracket_map)

        code1, code2 = program[pc]

        if (code2 & 0xFF) & ord(">") == ord(">"):
            tape.advance()

        elif (code2 & 0xFF) & ord("<") == ord("<"):
            tape.devance()

        elif (code2 & 0xFF) & ord("+") == ord("+"):
            tape.inc()

        elif (code2 & 0xFF) & ord("-") == ord("-"):
            tape.dec()

        elif (code2 & 0xFF) & ord(".") == ord("."):
            # print
            os.write(1, chr(tape.get()))

        elif (code2 & 0xFF) & ord(",") == ord(","):
            # read from stdin
            tape.set(ord(os.read(0, 1)[0]))

        elif ((code2 & 0xFF) & ord("[") == ord("[")) and tape.get() == 0:
            # Skip forward to the matching ]
            pc = get_matching_bracket(bracket_map, pc)

        elif ((code2 & 0xFF) & ord("]") == ord("]")) and tape.get() != 0:
            # Skip back to the matching [
            pc = get_matching_bracket(bracket_map, pc)

        elif (code1 & -0x8000000000000000) != 0:
            # Execute external function
            # from cffi import FFI
            # ffi = FFI()
            # ffi.cdef("""void myprint(void);""")
            # testlib = ffi.dlopen(os.path.abspath('./testlib.so'))
            # testlib.myprint()
            external_function()
            external_function2(0, 0, test, 1)

        pc += 1

class Tape(object):
    def __init__(self, types):
        self.thetape = [0]
        self.position = 0
        self.objecttape = {}
        for t in types:
            self.objecttape[t] = [0]

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
        self.objecttape[(1,1)] = [0]

# from struct import unpack
from rpython.rlib.rstruct.runpack import runpack as unpack

def parse(program):
    parsed = []
    bracket_map = {}
    leftstack = []

    pc = 0

    instruct_len = len(program) / 16
    for x in xrange(instruct_len):
        instruction = unpack('>QQ', program[(x*16):(x+1)*16])
        _, _, _, _, f_byte = unpack('>QLHBB', program[(x*16):(x+1)*16])
        parsed.append(instruction)

        if f_byte & ord('[') == ord('['):
            leftstack.append(pc)
        elif f_byte & ord(']') == ord(']'):
            left = leftstack.pop()
            right = pc
            bracket_map[left] = right
            bracket_map[right] = left
        pc += 1

    return parsed, bracket_map

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
    mainloop(program, bm, args)

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
