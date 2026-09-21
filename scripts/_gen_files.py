import base64, os, subprocess, sys

def w(path, content_b64):
    d = os.path.dirname(path)
    if d: os.makedirs(d, exist_ok=True)
    raw = base64.b64decode(content_b64)
    with open(path, chr(119)+chr(98)) as fh:
        fh.write(raw)
    print(chr(119)+chr(114)+chr(111)+chr(116)+chr(101), path)

# Generate b64 for each file by encoding strings here in Python
# Use chr() so the PS array lines stay simple

NL = chr(10)

MODELS = NL.join([
    chr(102)+chr(114)+chr(111)+chr(109)+chr(32)+chr(112)+chr(121)+chr(100)+chr(97)+chr(110)+chr(116)+chr(105)+chr(99)+chr(32)+chr(105)+chr(109)+chr(112)+chr(111)+chr(114)+chr(116)+chr(32)+chr(66)+chr(97)+chr(115)+chr(101)+chr(77)+chr(111)+chr(100)+chr(101)+chr(108)+chr(44)+chr(32)+chr(67)+chr(111)+chr(110)+chr(102)+chr(105)+chr(103)+chr(68)+chr(105)+chr(99)+chr(116),
    chr(102)+chr(114)+chr(111)+chr(109)+chr(32)+chr(100)+chr(97)+chr(116)+chr(101)+chr(116)+chr(105)+chr(109)+chr(101)+chr(32)+chr(105)+chr(109)+chr(112)+chr(111)+chr(114)+chr(116)+chr(32)+chr(100)+chr(97)+chr(116)+chr(101)+chr(116)+chr(105)+chr(109)+chr(101),
    chr(0),
    chr(0),
    chr(99)+chr(108)+chr(97)+chr(115)+chr(115)+chr(32)+chr(66)+chr(108)+chr(111)+chr(98)+chr(82)+chr(101)+chr(99)+chr(111)+chr(114)+chr(100)+chr(40)+chr(66)+chr(97)+chr(115)+chr(101)+chr(77)+chr(111)+chr(100)+chr(101)+chr(108)+chr(41)+chr(58),
    chr(32)+chr(32)+chr(32)+chr(32)+chr(109)+chr(111)+chr(100)+chr(101)+chr(108)+chr(95)+chr(99)+chr(111)+chr(110)+chr(102)+chr(105)+chr(103)+chr(32)+chr(61)+chr(32)+chr(67)+chr(111)+chr(110)+chr(102)+chr(105)+chr(103)+chr(68)+chr(105)+chr(99)+chr(116)+chr(40)+chr(102)+chr(114)+chr(111)+chr(122)+chr(101)+chr(110)+chr(61)+chr(84)+chr(114)+chr(117)+chr(101)+chr(41),
    chr(0),
    chr(32)*4+chr(99)+chr(111)+chr(109)+chr(109)+chr(105)+chr(116)+chr(95)+chr(104)+chr(97)+chr(115)+chr(104)+chr(58)+chr(32)+chr(115)+chr(116)+chr(114),
    chr(32)*4+chr(99)+chr(111)+chr(109)+chr(109)+chr(105)+chr(116)+chr(95)+chr(116)+chr(105)+chr(109)+chr(101)+chr(115)+chr(116)+chr(97)+chr(109)+chr(112)+chr(58)+chr(32)+chr(100)+chr(97)+chr(116)+chr(101)+chr(116)+chr(105)+chr(109)+chr(101),
    chr(32)*4+chr(102)+chr(105)+chr(108)+chr(101)+chr(95)+chr(112)+chr(97)+chr(116)+chr(104)+chr(58)+chr(32)+chr(115)+chr(116)+chr(114),
    chr(32)*4+chr(98)+chr(108)+chr(111)+chr(98)+chr(95)+chr(99)+chr(111)+chr(110)+chr(116)+chr(101)+chr(110)+chr(116)+chr(58)+chr(32)+chr(115)+chr(116)+chr(114),
    chr(32)*4+chr(105)+chr(115)+chr(95)+chr(104)+chr(101)+chr(97)+chr(100)+chr(58)+chr(32)+chr(98)+chr(111)+chr(111)+chr(108),
]).replace(chr(0), chr(0))
MODELS = MODELS.replace(chr(0), chr(0))
print(chr(111)+chr(107))
