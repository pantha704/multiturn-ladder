#!/usr/bin/env python3
"""
FRV2 codec — full builder, matching the structure found in elder-plinius/FRV1T.

Container (observed, byte-exact from his 🫐.txt):
    [0x0F] [F][R][V][2] [gzip stream]
      ^      ^___________^  ^
      |      magic "FRV2"   gzip (1f 8b 08 ...) — its 0x1f follows the magic directly
      |
      version/mode byte = 0x0F  (== byte value of U+FE0F, which is why the
      emoji-presentation selector right after the glyph IS the first payload byte)

Transport (variation selectors):
    byte 0-15   -> U+FE00 + byte
    byte 16-255 -> U+E0100 + (byte - 16)
    prefixed with a visible carrier glyph (his is 🫐)

Both directions verified against his real file.
"""
import gzip, sys

MAGIC = b"\x0fFRV2"
CARRIER = "🫐"

def encode_bytes(b: bytes, carrier: str = CARRIER) -> str:
    out = [carrier]
    for x in b:
        out.append(chr(0xFE00 + x) if x < 16 else chr(0xE0100 + (x - 16)))
    return "".join(out)

def decode_bytes(s: str) -> bytes:
    out = []
    for ch in s:
        cp = ord(ch)
        if 0xFE00 <= cp <= 0xFE0F: out.append(cp - 0xFE00)
        elif 0xE0100 <= cp <= 0xE01EF: out.append((cp - 0xE0100) + 16)
    return bytes(out)

def build(payload: bytes, carrier: str = CARRIER) -> str:
    """payload -> the invisible string (carrier + VS)."""
    body = MAGIC + gzip.compress(payload, compresslevel=9, mtime=0)
    return encode_bytes(body, carrier)

def parse(s: str) -> bytes:
    """invisible string -> original payload."""
    b = decode_bytes(s)
    if not b.startswith(MAGIC):
        raise ValueError(f"bad magic: {b[:5]!r}")
    return gzip.decompress(b[len(MAGIC):])

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "verify":
        raw = open("/tmp/frv1t/berries.txt", encoding="utf-8", errors="replace").read()
        b = decode_bytes(raw)
        print(f"his file   : {len(raw)} codepoints -> {len(b)} bytes")
        print(f"magic      : {b[:5]!r}  ({'OK' if b.startswith(MAGIC) else 'MISMATCH'})")
        pl = parse(raw)
        print(f"payload    : {len(pl)} bytes")
        print(f"head       : {pl[:40]!r}")
        # re-build it and compare
        mine = build(pl)
        print(f"\nre-encoded : {len(mine)} codepoints (his: {len(raw)})")
        print(f"round-trip : {'IDENTICAL' if decode_bytes(mine) == b else 'DIFFERS (gzip re-compression)'}")
        print(f"re-parse   : {len(parse(mine))} bytes, {'OK' if parse(mine)==pl else 'MISMATCH'}")
    elif len(sys.argv) > 2 and sys.argv[1] == "build":
        data = open(sys.argv[2], "rb").read()
        s = build(data)
        open(sys.argv[3], "w", encoding="utf-8").write(s)
        print(f"built {len(s)} codepoints -> {sys.argv[3]}")
    elif len(sys.argv) > 2 and sys.argv[1] == "parse":
        s = open(sys.argv[2], encoding="utf-8", errors="replace").read()
        open(sys.argv[3], "wb").write(parse(s))
        print(f"parsed -> {sys.argv[3]}")
    else:
        print(__doc__)
