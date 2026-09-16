#!/usr/bin/env python3
"""Raw probe: is muse-spark-1.3-contributor itself broken, or is it our request shape?"""
import json, urllib.request, urllib.error

AUTH="/home/ubuntu/.hermes/profiles/msx/auth.json"
d=json.load(open(AUTH))
pool=d.get("credential_pool",{}).get("opencode-go",[])
import os
key=os.environ.get("OPENCODE_GO_API_KEY")
if pool and not key:
    e=pool[0] if isinstance(pool,list) else pool
    if isinstance(e,dict):
        key=e.get("api_key") or e.get("key") or e.get("access_token")
    elif isinstance(e,str): key=e
print("key found:", bool(key), "entries:", len(pool) if isinstance(pool,list) else 1)

URL="https://opencode.ai/zen/go/v1/chat/completions"

def probe(model, body_extra=None, label=""):
    body={"model":model,"messages":[{"role":"user","content":"say OK"}],"max_tokens":16}
    if body_extra: body.update(body_extra)
    req=urllib.request.Request(URL, data=json.dumps(body).encode(),
        headers={"Authorization":"Bearer "+key,"Content-Type":"application/json",
                 "User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36",
                 "Accept":"application/json","Accept-Language":"en-US,en;q=0.9",
                 "Origin":"https://opencode.ai","Referer":"https://opencode.ai/",
                 "x-opencode-session":"sess-"+os.urandom(8).hex(),
                 "x-opencode-client":"hermes"})
    try:
        r=urllib.request.urlopen(req,timeout=90)
        print(f"  {label or model:42} HTTP {r.status}  {r.read()[:120].decode()}")
    except urllib.error.HTTPError as e:
        print(f"  {label or model:42} HTTP {e.code}  {e.read()[:200].decode()}")
    except Exception as e:
        print(f"  {label or model:42} ERR {type(e).__name__}: {e}")

print("\n--- WITH x-opencode-session ---")
probe("deepseek-v4.1-flash")
probe("muse-spark-1.2-contributor")
probe("muse-spark-1.3-contributor")

print("\n--- 1.3 with variant request shapes ---")
probe("muse-spark-1.3-contributor", {"stream":False}, "1.3 stream=False")
probe("muse-spark-1.3-contributor", {"max_tokens":512}, "1.3 max_tokens=512")
probe("muse-spark-1.3-contributor", {"temperature":0.7}, "1.3 temperature=0.7")
probe("muse-spark-1.3-contributor", {"reasoning_effort":"high"}, "1.3 reasoning_effort=high")
probe("muse-spark-1.3-contributor", {"messages":[{"role":"user","content":"hi"}]}, "1.3 minimal msg")
