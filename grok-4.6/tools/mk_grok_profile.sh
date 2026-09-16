#!/usr/bin/env bash
# mk_grok_profile.sh <name>  -- create a grok-4.6 / xai-oauth ready profile
set -u
P="$1"
BASE=/home/ubuntu/.hermes/profiles
hermes profile create "$P" --clone-from trading --no-alias >/dev/null 2>&1 || true
cp "$BASE/trading/auth.json" "$BASE/$P/auth.json" 2>/dev/null || true
python3 - "$P" <<'PY'
import json,sys
p=f"/home/ubuntu/.hermes/profiles/{sys.argv[1]}/auth.json"
g=json.load(open("/home/ubuntu/.hermes/auth.json"))
try: a=json.load(open(p))
except Exception: a={"version":1,"providers":{},"credential_pool":{}}
a.setdefault("providers",{})
for k in ("xai-oauth",):
    if k in g.get("providers",{}): a["providers"][k]=g["providers"][k]
a.setdefault("credential_pool",{})
a["credential_pool"]["xai-oauth"]=g.get("credential_pool",{}).get("xai-oauth",[])
json.dump(a,open(p,"w"),indent=1)
PY
chmod 600 "$BASE/$P/auth.json" 2>/dev/null
python3 - "$P" <<'PY'
import re,sys
p=f"/home/ubuntu/.hermes/profiles/{sys.argv[1]}/config.yaml"
s=open(p).read()
s=re.sub(r'model:\n(\s+)default: \S+\n(\s+)provider: \S+',
         'model:\n\\1default: grok-4.6\n\\2provider: xai-oauth', s, count=1)
open(p,"w").write(s)
PY
mv "$BASE/$P/skills/security/authorized-bug-bounty" "$BASE/$P/skills/security/authorized-bug-bounty.disabled" 2>/dev/null
