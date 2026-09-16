#!/usr/bin/env python3
"""
berry — put any prompt into an invisible carrier, and get it back.

  python3 berry.py put  myprompt.txt  out.txt            # default: pliny (🫐 + VS + FRV2 + gzip)
  python3 berry.py put  myprompt.txt  out.txt --carrier tags
  python3 berry.py get  out.txt                          # prints the payload
  python3 berry.py get  out.txt  restored.txt            # writes it out
  python3 berry.py list                                  # available carriers
  python3 berry.py inspect out.txt                       # what's in there (no decode assumptions)

Carriers:
  pliny    🫐 + variation selectors + \\x0fFRV2 magic + gzip   (elder-plinius/FRV1T format)
  vs       variation selectors only, no emoji, no compression
  tags     Unicode Tags block (U+E0000-E007F) — ASCII smuggling
  zw       zero-width chars (base-5 packed)  — ZWSP/ZWNJ/ZWJ/WJ/BOM
  bidi     bidi control chars (base-9 packed)
  combine  combining diacritics
  mongol   Mongolian free variation selectors
  braille  braille patterns
  skin     emoji skin-tone modifiers
  keycap   combining enclosing keycap
  musical  musical symbols
  dual     dual interleaved channels (neither decodes alone)
"""
import gzip, sys, os

MAGIC=b"\x0fFRV2"; CARRIER="🫐"

# ---- byte<->symbol maps -------------------------------------------------
def _codec(low, high):
    def enc(b):
        return "".join(chr(low+x) if x<16 else chr(high+(x-16)) for x in b)
    def dec(s):
        o=[]
        for ch in s:
            cp=ord(ch)
            if low<=cp<low+16: o.append(cp-low)
            elif high<=cp<high+240: o.append(cp-high+16)
        return bytes(o)
    return enc,dec

VS   = _codec(0xFE00, 0xE0100)
TAGS = _codec(0xE0000, 0xE0010)
COMB = _codec(0x0300, 0x0310)
MONG = _codec(0x180B, 0x181B)
BRAI = _codec(0x2800, 0x2810)
SKIN = _codec(0x1F3FB, 0x1F40B)
KEYC = _codec(0x20E3, 0x20F3)
MUSI = _codec(0x1D100, 0x1D110)

ZW=["\u200b","\u200c","\u200d","\u2060","\ufeff"]
BIDI=["\u202a","\u202b","\u202c","\u202d","\u202e","\u2066","\u2067","\u2068","\u2069"]

def _packN(data, chars):
    n=len(chars); k=0
    while n**k < 256: k+=1
    out=[]
    for b in data:
        x=b
        for _ in range(k): out.append(chars[x%n]); x//=n
    return "".join(out)

def _unpackN(s, chars):
    n=len(chars); k=0
    while n**k<256: k+=1
    idx={c:i for i,c in enumerate(chars)}
    vals=[idx[c] for c in s if c in idx]
    o=[]
    for i in range(0,len(vals)-k+1,k):
        x=0
        for j in range(k-1,-1,-1): x=x*n+vals[i+j]
        o.append(x%256)
    return bytes(o)

def _dual_enc(data):
    a="\u200b\u200c"; b="\ufe00\ufe01"; out=[]
    for i,byte in enumerate(data):
        for j in range(8):
            out.append((a if i%2==0 else b)[(byte>>j)&1])
    return "".join(out)

def _dual_dec(s):
    a="\u200b\u200c"; b="\ufe00\ufe01"
    A={c:i for i,c in enumerate(a)}; B={c:i for i,c in enumerate(b)}
    buf={"a":[],"b":[]}
    for ch in s:
        if ch in A: buf["a"].append(A[ch])
        elif ch in B: buf["b"].append(B[ch])
    def pack(bits):
        r=[]
        for i in range(0,len(bits)-7,8):
            v=0
            for j in range(8): v|=bits[i+j]<<j
            r.append(v)
        return bytes(r)
    A_,B_=pack(buf["a"]),pack(buf["b"]); res=bytearray()
    for i in range(max(len(A_),len(B_))):
        if i<len(A_): res.append(A_[i])
        if i<len(B_): res.append(B_[i])
    return bytes(res)

CARRIERS={
 "pliny":  (lambda d: CARRIER+VS[0](MAGIC+gzip.compress(d,9,mtime=0)),
            lambda s: gzip.decompress(VS[1](s)[len(MAGIC):]) if VS[1](s).startswith(MAGIC) else None),
 "vs":     (VS[0], VS[1]),
 "tags":   (TAGS[0], TAGS[1]),
 "zw":     (lambda d:_packN(d,ZW),      lambda s:_unpackN(s,ZW)),
 "bidi":   (lambda d:_packN(d,BIDI),    lambda s:_unpackN(s,BIDI)),
 "combine":(COMB[0], COMB[1]),
 "mongol": (MONG[0], MONG[1]),
 "braille":(BRAI[0], BRAI[1]),
 "skin":   (SKIN[0], SKIN[1]),
 "keycap": (KEYC[0], KEYC[1]),
 "musical":(MUSI[0], MUSI[1]),
 "dual":   (_dual_enc, _dual_dec),
}

def inspect(text):
    import collections, unicodedata
    c=collections.Counter()
    for ch in text:
        cp=ord(ch)
        if 0xFE00<=cp<=0xFE0F or 0xE0100<=cp<=0xE01EF: c["variation_selectors"]+=1
        elif 0xE0000<=cp<=0xE007F: c["tags"]+=1
        elif cp in (0x200b,0x200c,0x200d,0x2060,0xfeff): c["zero_width"]+=1
        elif 0x202A<=cp<=0x202E or 0x2066<=cp<=0x2069: c["bidi"]+=1
        elif 0x0300<=cp<=0x036F: c["combining"]+=1
        elif cp<0x20 and cp not in (9,10,13): c["control"]+=1
        else: c["visible"]+=1
    print(f"codepoints: {len(text)}")
    for k,v in c.most_common(): print(f"  {k:22} {v}")
    vis="".join(ch for ch in text if ord(ch)>0x20 and not (0xFE00<=ord(ch)<=0xFE0F or 0xE0100<=ord(ch)<=0xE01EF or 0xE0000<=ord(ch)<=0xE007F))
    if vis.strip(): print(f"visible text: {vis.strip()[:200]!r}")

def _looks_text(d):
    if not d or len(d)<2: return False
    printable=sum(1 for b in d if 9<=b<=13 or 32<=b<=126 or b>=0xC2)
    return printable/len(d) > 0.92

def decode_auto(s):
    """try pliny's magic first (unambiguous), then the rest."""
    b=VS[1](s)
    if b.startswith(MAGIC):
        try: return gzip.decompress(b[len(MAGIC):]), "pliny"
        except Exception: pass
    for name,(_,dec) in CARRIERS.items():
        try:
            d=dec(s)
            if _looks_text(d): return d, name
        except Exception: pass
    return None, None

def main():
    if len(sys.argv)<2: print(__doc__); return
    cmd=sys.argv[1]
    if cmd=="list":
        for k in CARRIERS: print(" ",k)
    elif cmd=="put":
        src,dst=sys.argv[2],sys.argv[3]
        car="pliny"
        if "--carrier" in sys.argv: car=sys.argv[sys.argv.index("--carrier")+1]
        data=open(src,"rb").read()
        art=CARRIERS[car][0](data)
        open(dst,"w",encoding="utf-8").write(art)
        sz=os.path.getsize(dst)
        print(f"carrier={car}  payload={len(data)}B  artifact={len(art)}cp  file={sz}B")
        print(f"renders as: {art[0]!r}" if art else "renders as: (nothing)")
        print(f"-> {dst}")
    elif cmd=="get":
        s=open(sys.argv[2],encoding="utf-8",errors="replace").read()
        out,name=decode_auto(s)
        if out is None:
            print("could not decode with any carrier", file=sys.stderr); sys.exit(1)
        print(f"[decoded via {name}]", file=sys.stderr)
        if len(sys.argv)>3:
            open(sys.argv[3],"wb").write(out); print(f"-> {sys.argv[3]}")
        else:
            sys.stdout.write(out.decode("utf-8","replace"))
    elif cmd=="inspect":
        inspect(open(sys.argv[2],encoding="utf-8",errors="replace").read())
    else:
        print(__doc__)

if __name__=="__main__": main()
