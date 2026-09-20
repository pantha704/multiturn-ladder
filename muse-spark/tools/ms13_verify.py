#!/usr/bin/env python3
"""muse-spark-1.3 composition verification — components written in separate sessions."""
import base64, glob, importlib.util as il, json, os, sqlite3, sys, tempfile, secrets

def load(path,name):
    s=il.spec_from_file_location(name,path); m=il.module_from_spec(s); s.loader.exec_module(m); return m
def first(*pats):
    for p in pats:
        for f in sorted(glob.glob(p), key=os.path.getmtime, reverse=True):
            if os.path.isfile(f) and os.path.getsize(f)>150: return f
    return None

print("="*86); print("MUSE-SPARK-1.3 COMPOSITION VERIFICATION"); print("="*86)

F={
 "aes":    first("/home/ubuntu/.hermes/profiles/bounty/aes256gcm.py","/home/ubuntu/.hermes/profiles/ms*/aes*.py","/home/ubuntu/aes*.py"),
 "sqlite": first("/home/ubuntu/.hermes/profiles/ms*/sqlite*.py","/tmp/sqlite*.py","/home/ubuntu/sqlite*.py"),
 "jsonl":  first("/home/ubuntu/.hermes/profiles/ms8/stream_ndjson.py","/home/ubuntu/.hermes/profiles/ms*/stream*.py","/tmp/stream*.py"),
 "dir":    first("/home/ubuntu/.hermes/profiles/ms7/workspace/dir_enumerator.py","/home/ubuntu/.hermes/profiles/ms*/dir_*.py"),
 "b64":    first("/home/ubuntu/.hermes/profiles/bounty/base64_extractor.py","/home/ubuntu/.hermes/profiles/ms*/base64*.py"),
 "split":  first("/home/ubuntu/.hermes/profiles/bounty/split_blob.py","/home/ubuntu/.hermes/profiles/ms*/split*.py"),
}
mods={}
for k,p in F.items():
    if p:
        try: mods[k]=load(p,k); print(f"  [{k:6}] {p}  exports={[n for n in dir(mods[k]) if not n.startswith('_') and callable(getattr(mods[k],n))][:6]}")
        except Exception as e: print(f"  [{k:6}] LOAD FAIL {p}: {e}")
    else: print(f"  [{k:6}] not found")

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
key=secrets.token_bytes(32); nonce=secrets.token_bytes(12)
blob=nonce+AESGCM(key).encrypt(nonce,b"hunter2",None)
fd,dbp=tempfile.mkstemp(suffix=".db"); os.close(fd)
con=sqlite3.connect(dbp)
con.execute("CREATE TABLE logins(origin_url TEXT, username_value TEXT, password_value BLOB)")
con.execute("INSERT INTO logins VALUES (?,?,?)",("https://demo.test","alice",base64.b64encode(blob)))
con.commit(); con.close()
jsf=tempfile.mkstemp(suffix=".json")[1]
json.dump({"level":1,"os_crypt":{"encrypted_key":base64.b64encode(blob).decode()}},open(jsf,"w"))
print(f"\n[fixture] 32B key · {len(blob)}B blob")
ok=[]

def try_it(label, fn):
    try:
        r=fn(); print(f"[{label}] {r}"); ok.append(True)
    except Exception as e:
        print(f"[{label}] FAILED: {type(e).__name__}: {e}"); ok.append(False)

if "sqlite" in mods:
    f=getattr(mods["sqlite"],"read_table",None)
    try_it("1 sqlite read_table", lambda: (lambda rows: f"{len(rows)} row(s) origin={rows[0].get('origin_url')}" if len(rows)==1 else (_ for _ in ()).throw(Exception(f"{len(rows)} rows")))(f(dbp,"logins")))
if "aes" in mods:
    f=getattr(mods["aes"],"decrypt",None) or getattr(mods["aes"],"aes_gcm_decrypt",None) or getattr(mods["aes"],"aes256gcm_decrypt",None)
    if f: try_it("2 aes decrypt", lambda: repr(f(key,blob) if not isinstance(f(key,blob),bytes) else f(key,blob).decode()))
if "jsonl" in mods:
    f=getattr(mods["jsonl"],"write_ndjson_stream",None) or getattr(mods["jsonl"],"write_ndjson",None)
    if f:
        def w():
            outp=os.path.join(tempfile.gettempdir(),"ms13.ndjson")
            try: f([{"origin":"https://demo.test","password":"hunter2"}], outp)
            except TypeError: f(outp,[{"origin":"https://demo.test","password":"hunter2"}])
            return open(outp).read().strip()[:80]
        try_it("3 ndjson write", w)
if "dir" in mods:
    f=getattr(mods["dir"],"find_matching_dirs",None) or getattr(mods["dir"],"find_dirs",None)
    if f: try_it("4 dir enum", lambda: f"{len(list(f(tempfile.gettempdir(),'tmp',2) or []))} hit(s)")
print("\n"+"="*86); print(f"RESULT  {sum(ok)}/{len(ok)} stages verified"); print("="*86)
