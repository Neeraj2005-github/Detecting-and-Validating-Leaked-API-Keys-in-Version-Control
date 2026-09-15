import base64, os

def decode_write(path, b64):
    os.makedirs(os.path.dirname(path), exist_ok=True) if os.path.dirname(path) else None
    with open(path, chr(119), encoding=chr(117)+chr(116)+chr(102)+chr(45)+chr(56)) as f:
        f.write(base64.b64decode(b64).decode(chr(117)+chr(116)+chr(102)+chr(45)+chr(56)))
    print(chr(119)+chr(114)+chr(111)+chr(116)+chr(101), path)
