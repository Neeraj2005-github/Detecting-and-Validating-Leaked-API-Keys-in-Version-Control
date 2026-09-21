import base64, os, sys

MODELS_PY = b64e = None

def b64e(s):
    return base64.b64encode(s.encode(chr(117)+chr(116)+chr(102)+chr(45)+chr(56))).decode()

lines = []

# ── src/shd/__init__.py
lines.append(fw(chr(39)+chr(115)+chr(114)+chr(99)+chr(47)+chr(115)+chr(104)+chr(100)+chr(47)+chr(95)+chr(95)+chr(105)+chr(110)+chr(105)+chr(116)+chr(95)+chr(95)+chr(46)+chr(112)+chr(121)+chr(39), chr(39)+chr(39)))

with open(os.path.join(os.path.dirname(__file__), chr(95)+chr(103)+chr(101)+chr(110)+chr(95)+chr(102)+chr(105)+chr(108)+chr(101)+chr(115)+chr(46)+chr(112)+chr(121)), chr(97), encoding=chr(117)+chr(116)+chr(102)+chr(45)+chr(56)) as f:
    for line in lines:
        f.write(line + chr(10))
