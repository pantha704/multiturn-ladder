#!/usr/bin/env python3
"""Find the request shape that makes muse-spark answer. 1.2 works via hermes => a shape works."""
import json, os, urllib.request, urllib.error

key=os.environ["OPENCODE_GO_API_KEY"]
URL="https://opencode.ai/zen/go/v1/chat/completions"
H={"Authorization":"Bearer "+key,"Content-Type":"application/json",
   "User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36",
   "Accept":"application/json","Origin":"https://opencode.ai","Referer":"https://opencode.ai/",
   "x-opencode-session":"sess-"+os.urandom(8).hex(),"x-opencode-client":"hermes"}

def probe(model, extra, label):
    body={"model":model,"messages":[{"role":"user","content":"say OK"}],"max_tokens":32}
    body.update(extra)
    req=urllib.request.Request(URL,data=json.dumps(body).encode(),headers=H)
    try:
        r=urllib.request.urlopen(req,timeout=90); t=r.read()[:110].decode()
        print(f"  {label:38} HTTP {r.status}  {t}")
        return True
    except urllib.error.HTTPError as e:
        print(f"  {label:38} HTTP {e.code}  {e.read()[:110].decode()}")
    except Exception as e:
        print(f"  {label:38} ERR {type(e).__name__}")
    return False

M="muse-spark-1.2-contributor"
print(f"--- {M} : hunting the working shape ---")
probe(M, {}, "bare")
probe(M, {"reasoning_effort":75}, "reasoning_effort=int 75")
probe(M, {"reasoning_effort":"high"}, "reasoning_effort='high'")
probe(M, {"reasoning":{"effort":"high"}}, "reasoning={effort:high}")
probe(M, {"reasoning":{"effort":75}}, "reasoning={effort:75}")
probe(M, {"stream":True}, "stream=True")
probe(M, {"max_tokens":4096}, "max_tokens=4096")
probe(M, {"temperature":1.0,"top_p":1.0}, "temp-1 top_p-1")
probe(M, {"messages":[{"role":"user","content":"say OK"}],"max_completion_tokens":32}, "max_completion_tokens")

print(f"\n--- muse-spark-1.3 same sweep ---")
N="muse-spark-1.3-contributor"
probe(N, {}, "bare")
probe(N, {"reasoning_effort":75}, "reasoning_effort=int 75")
probe(N, {"stream":True}, "stream=True")

print("\n--- other opencode contributors, same shape ---")
for m in ["muse-spark-1.2-contributor","omen-alpha","union-alpha","hy4-preview","gpt-5.6-luna"]:
    probe(m, {}, f"{m} bare")
