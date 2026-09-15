import os

def w(p,c):
    d=os.path.dirname(p)
    if d: os.makedirs(d,exist_ok=True)
    fh=open(p,chr(119),encoding=chr(117)+chr(116)+chr(102)+chr(45)+chr(56))
    fh.write(c)
    fh.close()
    print(chr(119)+chr(114)+chr(111)+chr(116)+chr(101),p)
