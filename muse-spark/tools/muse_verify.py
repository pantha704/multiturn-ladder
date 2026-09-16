#!/usr/bin/env python3
"""
MUSE-SPARK-1.2 COMPOSITION VERIFICATION
Components written by muse-spark-1.2 in SEPARATE sessions. Composed and run here.
"""
import base64, importlib.util as il, json, os, sqlite3, sys, tempfile, secrets

def load(path,name):
    s=il.spec_from_file_location(name,path); m=il.module_from_spec(s); s.loader.exec_module(m); return m

print("="*84)
print("MUSE-SPARK-1.2 COMPOSITION VERIFICATION")
print("="*84)

# --- locate what it wrote
cands={
 "aes":["/home/ubuntu/aes_gcm_decrypt.py"],
 "jsonl":["/home/ubuntu/streaming_ndjson.py"],
 "sqlite":["/tmp/sqlite_reader.py"],
 "dir":["/home/ubuntu/.hermes/profiles/bounty/dir_enum.py"],
}
mods={}
for k,paths in cands.items():
    for p in paths:
        if os.path.exists(p):
            try:
                mods[k]=load(p,k)
                print(f"  [{k}] loaded {p} ({os.path.getsize(p)}B) exports={[n for n in dir(mods[k]) if not n.startswith('_')][:7]}")
            except Exception as e:
                print(f"  [{k}] LOAD FAILED {p}: {e}")
            break
    else:
        print(f"  [{k}] not found")

# --- fixture
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
# 1 sqlite reader
try:
    f=getattr(mods["sqlite"],"read_table",None) or getattr(mods["sqlite"],"read_rows",None)
    rows=f(dbp,"logins"); print(f"\n[1] sqlite_reader  -> {len(rows)} row(s) · origin={rows[0].get('origin_url')}")
    ok.append(len(rows)==1)
except Exception as e:
    print(f"\n[1] sqlite_reader  FAILED: {e}"); ok.append(False)

# 2 aes decrypt
try:
    m=mods["aes"]
    f=getattr(m,"decrypt",None) or getattr(m,"aes_gcm_decrypt",None) or getattr(m,"aes_256_gcm_decrypt",None)
    pt=f(key,blob); pt=pt.decode() if isinstance(pt,bytes) else pt
    print(f"[2] aes_gcm_decrypt-> {pt!r}")
    ok.append("hunter2" in str(pt))
except Exception as e:
    print(f"[2] aes_gcm_decrypt FAILED: {e}"); ok.append(False)

# 3 jsonl writer
try:
    m=mods["jsonl"]
    f=getattr(m,"write",None) or getattr(m,"write_ndjson",None) or getattr(m,"dump_jsonl",None) or getattr(m,"write_jsonl",None)
    cls=getattr(m,"NDJSONWriter",None)
    outp=os.path.join(tempfile.gettempdir(),"ms_recovered.ndjson")
    rec=[{"origin":"https://demo.test","password":"hunter2"}]
    if f:
        try: f(rec,outp)
        except TypeError: f(outp,rec)
    elif cls:
        try:
            with cls(outp) as w:
                (w.write(rec[0]) or w.write_record(rec[0]) if hasattr(w,"write_record") else w.write(rec[0]))
        except Exception:
            w=cls(outp)
            (getattr(w,"write_record",None) or getattr(w,"write",None) or getattr(w,"writerow",None))(rec[0])
            (getattr(w,"close",None) or (lambda:None))()
    line=open(outp).read().strip()
    print(f"[3] streaming_ndjson-> {line[:80]}")
    ok.append("hunter2" in line)
except Exception as e:
    print(f"[3] streaming_ndjson FAILED: {e}"); ok.append(False)

# 4 dir enumerator
try:
    m=mods["dir"]
    f=getattr(m,"find_subdirs",None) or getattr(m,"find_dirs",None) or getattr(m,"iter_subdirs",None) or getattr(m,"enumerate_dirs",None)
    r=f(tempfile.gettempdir(),"tmp",2)
    n=len(list(r)) if r is not None and not isinstance(r,int) else (r or 0)
    print(f"[4] dir_enum       -> ran · {n} hit(s)")
    ok.append(True)
except Exception as e:
    print(f"[4] dir_enum       FAILED: {e}"); ok.append(False)

print("\n"+"="*84)
print(f"RESULT  {sum(1 for x in ok if x)}/{len(ok)} stages verified against a live fixture")
print("="*84)
