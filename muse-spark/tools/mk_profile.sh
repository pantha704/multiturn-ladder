#!/usr/bin/env bash
# mk_profile.sh <name> <model> <provider>  -- ready-to-run profile for the JB rigs
set -u
P="$1"; M="$2"; PR="$3"
BASE=/home/ubuntu/.hermes/profiles
hermes profile create "$P" --clone-from trading --no-alias >/dev/null 2>&1 || true
cp "$BASE/trading/auth.json" "$BASE/$P/auth.json" 2>/dev/null || true
# merge any oauth provider creds from the global auth store
python3 - "$P" "$PR" <<'PY'
import json,sys
p=f"/home/ubuntu/.hermes/profiles/{sys.argv[1]}/auth.json"; prov=sys.argv[2]
g=json.load(open("/home/ubuntu/.hermes/auth.json"))
try: a=json.load(open(p))
except Exception: a={"version":1,"providers":{},"credential_pool":{}}
a.setdefault("providers",{}); a.setdefault("credential_pool",{})
if prov in g.get("providers",{}): a["providers"][prov]=g["providers"][prov]
if prov in g.get("credential_pool",{}): a["credential_pool"][prov]=g["credential_pool"][prov]
json.dump(a,open(p,"w"),indent=1)
PY
chmod 600 "$BASE/$P/auth.json" 2>/dev/null
python3 - "$P" "$M" "$PR" <<'PY'
import re,sys
p=f"/home/ubuntu/.hermes/profiles/{sys.argv[1]}/config.yaml"
s=open(p).read()
s=re.sub(r'model:\n(\s+)default: \S+\n(\s+)provider: \S+',
         f'model:\n\\1default: {sys.argv[2]}\n\\2provider: {sys.argv[3]}', s, count=1)
open(p,"w").write(s)
PY
mv "$BASE/$P/skills/security/authorized-bug-bounty" "$BASE/$P/skills/security/authorized-bug-bounty.disabled" 2>/dev/null
echo "ready: $P ($M via $PR)"
