#!/usr/bin/env python3
"""
CARRIER ZOO — every invisible / near-invisible Unicode channel that can carry a
byte stream through text, plus the encoder + decoder for each.

Goal: find carriers the model perceives-but-ignores, or fails to perceive at all.
Pliny uses VS-on-emoji. There is no reason that is the only one.

Each codec is a byte<->str mapping. `probe.py` uses this to test perception.
"""
import unicodedata

# ---------------------------------------------------------------- codecs
# convention: byte 0-15 -> LOW[i], byte 16-255 -> HIGH[b-16]

class Codec:
    def __init__(self, name, low, high, visible=None, note=""):
        self.name=name; self.low=low; self.high=high
        self.visible=visible; self.note=note
    def enc(self, data: bytes, carrier: str="") -> str:
        out=[carrier] if carrier else []
        for b in data:
            out.append(chr(self.low + b) if b < 16 else chr(self.high + b - 16))
        return "".join(out)
    def dec(self, s: str) -> bytes:
        out=[]
        for ch in s:
            cp=ord(ch)
            if self.low <= cp < self.low+16: out.append(cp-self.low)
            elif self.high <= cp < self.high+240: out.append(cp-self.high+16)
        return bytes(out)

CODECS = {
 # --- the Pliny channel
 "variation_selectors": Codec("variation_selectors", 0xFE00, 0xE0100, note="Pliny's channel"),
 # --- ASCII smuggling: tags block is contiguous with the alpha
 "tags":                Codec("tags", 0xE0000, 0xE0000, note="U+E0000-E007F, full ASCII map"),
 # --- zero-width: only 4-5 usable cps, so base-4/base-5 packing needed (special, below)
 # --- combining marks (thin, subtle, render at ~zero width)
 "combining_grave":     Codec("combining_grave", 0x0300, 0x0340, note="combining diacritics"),
 "combining_ext":       Codec("combining_ext", 0x1AB0, 0x1AB0, note="combining ext block"),
 # --- Mongolian vowel separator + invisible operators
 "mongolian":           Codec("mongolian", 0x180B, 0x180B, note="Mongolian free variation selectors"),
 # --- Hangul filler / braille blank region
 "braille_blank":       Codec("braille_blank", 0x2800, 0x2801, note="braille patterns (visible-ish dots)"),
 # --- emoji skin tone modifiers (5, dark-ish, easily overlooked)
 "skin_tone":           Codec("skin_tone", 0x1F3FB, 0x1F3FB, note="emoji modifiers"),
 # --- keycap / combining enclosing
 "enclosing_keycap":    Codec("enclosing_keycap", 0x20E3, 0x20E3, note="combining enclosing keycap"),
 # --- musical symbols (visible blocks but zero-width in some fonts)
 "musical":             Codec("musical", 0x1D100, 0x1D100, note="musical symbols"),
}

def encode_all(data: bytes) -> dict:
    return {n: c.enc(data, carrier=c.visible or "") for n,c in CODECS.items()}

# ---------------------------------------------------------------- base-N packers
# For channels with few codepoints we pack bits instead of bytes.

ZW_CHARS = ["\u200b","\u200c","\u200d","\u2060","\ufeff"]  # ZWSP ZWNJ ZWJ WJ BOM

def zw_encode(data: bytes, chars=ZW_CHARS) -> str:
    """base-N encoding: each byte -> log_n(256) symbols. n=5 -> 4 symbols/byte."""
    n=len(chars)
    import math
    k=math.ceil(math.log(256,n))
    out=[]
    for b in data:
        x=b
        for _ in range(k):
            out.append(chars[x % n]); x//=n
    return "".join(out)

def zw_decode(s: str, chars=ZW_CHARS) -> bytes:
    n=len(chars); idx={c:i for i,c in enumerate(chars)}
    import math
    k=math.ceil(math.log(256,n))
    vals=[idx[c] for c in s if c in idx]
    out=[]
    for i in range(0,len(vals)-k+1,k):
        x=0
        for j in range(k-1,-1,-1): x=x*n+vals[i+j]
        out.append(x % 256)
    return bytes(out)

# ---------------------------------------------------------------- novel: bidi + homoglyph
BIDI = ["\u202a","\u202b","\u202c","\u202d","\u202e","\u2066","\u2067","\u2068","\u2069"]

def bidi_encode(data: bytes) -> str:
    n=len(BIDI)
    import math
    k=math.ceil(math.log(256,n))
    out=[]
    for b in data:
        x=b
        for _ in range(k): out.append(BIDI[x%n]); x//=n
    return "".join(out)

def bidi_decode(s: str) -> bytes:
    n=len(BIDI); idx={c:i for i,c in enumerate(BIDI)}
    import math
    k=math.ceil(math.log(256,n))
    vals=[idx[c] for c in s if c in idx]
    out=[]
    for i in range(0,len(vals)-k+1,k):
        x=0
        for j in range(k-1,-1,-1): x=x*n+vals[i+j]
        out.append(x%256)
    return bytes(out)

# ---------------------------------------------------------------- INVENTED: cyclic multilayer
# Novel carrier: interleave two independent channels in one string so that a
# decoder extracting either one alone gets noise, but the pair yields the message.
def dual_encode(data: bytes, a="\u200b\u200c", b="\ufe00\ufe01") -> str:
    """even bytes -> channel a (2-sym), odd bytes -> channel b (2-sym)."""
    out=[]
    for i,byte in enumerate(data):
        for j in range(8):
            bit=(byte>>j)&1
            out.append((a if i%2==0 else b)[bit])
    return "".join(out)

def dual_decode(s: str, a="\u200b\u200c", b="\ufe00\ufe01") -> bytes:
    A={c:i for i,c in enumerate(a)}; B={c:i for i,c in enumerate(b)}
    stream=[]
    for ch in s:
        if ch in A: stream.append(("a",A[ch]))
        elif ch in B: stream.append(("b",B[ch]))
    # reconstruct: consecutive 8 bits of the same channel form one byte
    out=[]; buf={}
    for tag,bit in stream:
        buf.setdefault(tag,[]).append(bit)
    ka=buf.get("a",[]); kb=buf.get("b",[])
    def pack(bits):
        r=[]
        for i in range(0,len(bits)-7,8):
            v=0
            for j in range(8): v|=bits[i+j]<<j
            r.append(v)
        return bytes(r)
    A_=pack(ka); B_=pack(kb)
    # re-interleave
    res=bytearray()
    for i in range(max(len(A_),len(B_))):
        if i<len(A_): res.append(A_[i])
        if i<len(B_): res.append(B_[i])
    return bytes(res)

if __name__=="__main__":
    payload=b"CARRIER-ZOO-OK"
    print(f"payload: {payload!r}\n")
    for name,c in CODECS.items():
        try:
            e=c.enc(payload, carrier=c.visible or "")
            got=c.dec(e)
            ok = got==payload
            print(f"  {name:24} {len(e):>4}cp  round-trip={'OK' if ok else 'FAIL'}")
        except Exception as ex:
            print(f"  {name:24} ERR {ex}")
    for nm,(en,de) in {
        "zero_width(base5)":(zw_encode,zw_decode),
        "bidi(base9)":(bidi_encode,bidi_decode),
        "dual_cyclic(NEW)":(dual_encode,dual_decode),
    }.items():
        e=en(payload); got=de(e)
        print(f"  {nm:24} {len(e):>4}cp  round-trip={'OK' if got==payload else 'FAIL:'+repr(got)}")
