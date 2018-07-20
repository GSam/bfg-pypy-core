import sys
import struct
import uuid

file1 = sys.argv[1]
file2 = sys.argv[2]

f1 = open(file1, 'rb')
f2 = open(file2, 'wb')

token_width = 'Q'

for b in f1.read():
    # Ignore brainfuck comments and other metadata
    if b not in ('[', ']', '<', '>', '+', '-', ',', '.'):
        continue
    print b, 1
    data = struct.pack(">%s" % token_width, 0)
    f2.write(data)
    data = struct.pack(">%s" % token_width, ord(b))
    print repr(data)
    f2.write(data)

id_uuid = uuid.uuid4().bytes
id_uuid = uuid.UUID(int=uuid.uuid4().int | (1 << 127)).bytes
f2.write(id_uuid)

f2.close()
f1.close()
