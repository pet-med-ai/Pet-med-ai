"""Deterministic fictional attachment bytes; no external files or real patients."""
import base64
import json
from pathlib import Path
import struct
import zlib

def png():
    def chunk(kind, data):
        return struct.pack(">I",len(data))+kind+data+struct.pack(">I",zlib.crc32(kind+data)&0xffffffff)
    return b"\x89PNG\r\n\x1a\n"+chunk(b"IHDR",struct.pack(">IIBBBBB",2,2,8,2,0,0,0))+chunk(b"IDAT",zlib.compress(b"\x00"+bytes([80,130,100])*2+b"\x00"+bytes([80,130,100])*2))+chunk(b"IEND",b"")

def pdf():
    stream=b"BT /F1 12 Tf 20 70 Td (CW-B6 SYNTHETIC ONLY - no patient data) Tj ET"
    objects=[b"<< /Type /Catalog /Pages 2 0 R >>",b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 400 100] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",b"<< /Length "+str(len(stream)).encode()+b" >>\nstream\n"+stream+b"\nendstream"]
    out=b"%PDF-1.4\n"; offsets=[0]
    for n,obj in enumerate(objects,1):
        offsets.append(len(out));out+=str(n).encode()+b" 0 obj\n"+obj+b"\nendobj\n"
    start=len(out);out+=b"xref\n0 6\n0000000000 65535 f \n"
    out+=b"".join((f"{n:010d} 00000 n \n").encode() for n in offsets[1:])
    return out+b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n"+str(start).encode()+b"\n%%EOF\n"

def jpeg():
    return base64.b64decode("/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAACAAIDASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwDPooorE8s//9k=")

def samples():
    return [("synthetic.pdf","application/pdf",pdf()),("synthetic.png","image/png",png()),("synthetic.jpg","image/jpeg",jpeg())]

if __name__ == "__main__":
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument("directory",type=Path);args=parser.parse_args()
    args.directory.mkdir(parents=True,exist_ok=True)
    for name,mime,data in samples():(args.directory/name).write_bytes(data)
    print(json.dumps({"synthetic_only":True,"files":[name for name,_,_ in samples()]}))
