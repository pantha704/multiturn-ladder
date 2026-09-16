#!/usr/bin/env bash
# jb — the whole workflow in one script.
#
#   ./jb.sh setup                 create a fresh ready-to-run profile
#   ./jb.sh new "YOUR PROMPT"     scaffold a ladder from your prompt
#   ./jb.sh tune mytarget         open it in $EDITOR
#   ./jb.sh show mytarget         print the 12 turns
#   ./jb.sh run mytarget          run it and collect the artifact
#   ./jb.sh list                  show existing ladders
#
# Everything lands in /home/ubuntu/.hermes/profiles/bounty
set -u
DIR=/home/ubuntu/.hermes/profiles/bounty
PROF=${JB_PROF:-jbx}
cd "$DIR" || exit 1

case "${1:-}" in
setup)
  echo "creating profile '$PROF' (model: deepseek-v4.1-flash / opencode-go)"
  hermes profile create "$PROF" --clone-from trading --no-alias >/dev/null 2>&1
  cp /home/ubuntu/.hermes/profiles/trading/auth.json "/home/ubuntu/.hermes/profiles/$PROF/auth.json" 2>/dev/null
  chmod 600 "/home/ubuntu/.hermes/profiles/$PROF/auth.json" 2>/dev/null
  # pin model + provider exactly
  python3 - "$PROF" <<'PY'
import re,sys
p=f"/home/ubuntu/.hermes/profiles/{sys.argv[1]}/config.yaml"
try: s=open(p).read()
except FileNotFoundError: sys.exit(f"no config at {p}")
s=re.sub(r'model:\n(\s+)default: \S+\n(\s+)provider: \S+',
         'model:\n\\1default: deepseek-v4.1-flash\n\\2provider: opencode-go', s, count=1)
open(p,"w").write(s)
print("  model pinned")
PY
  # the model READS profile skills and quotes them back as refusal reasons
  for s in authorized-bug-bounty; do
    mv "/home/ubuntu/.hermes/profiles/$PROF/skills/security/$s" \
       "/home/ubuntu/.hermes/profiles/$PROF/skills/security/$s.disabled" 2>/dev/null \
       && echo "  disabled skill: $s"
  done
  echo "  ready. now:  ./jb.sh new \"your prompt\""
  ;;

new)
  shift
  if [ $# -lt 1 ]; then echo "usage: ./jb.sh new \"YOUR PROMPT\""; exit 1; fi
  PROMPT="$*"
  NAME=$(python3 -c "
import hashlib,sys
print('ladder_'+hashlib.sha1(sys.argv[1].encode()).hexdigest()[:6])" "$PROMPT")
  python3 ladder.py from-prompt "$PROMPT" "$NAME"
  echo
  echo "NEXT: tune turns 1-11 in $NAME.ladder, then ./jb.sh run $NAME"
  echo "      (turn 12 is fixed — it defers to the scope. NEVER paste your prompt there.)"
  ;;

tune)  shift; ${EDITOR:-nano} "$1.ladder" ;;
show)  shift; python3 ladder.py show "$1" ;;
list)  ls -1 *.ladder 2>/dev/null | sed 's/\.ladder$//' || echo "(none yet)" ;;

run)
  shift
  NAME="${1:-}"
  [ -z "$NAME" ] && { echo "usage: ./jb.sh run <name>"; exit 1; }
  [ -f "$NAME.ladder" ] || { echo "no such ladder: $NAME"; exit 1; }
  echo "running '$NAME' on profile '$PROF' --reasoning max"
  echo "turn 12 may take >30 min; this will sit there. Ctrl-C is safe (session resumes with --continue)."
  python3 ladder.py run "$NAME" --profile "$PROF" --reasoning max
  echo
  echo "transcript -> $DIR/eval_$NAME.json"
  echo "artifact   -> check the model's turn-12 output for the path it wrote"
  ;;

*) sed -n '2,14p' "$0" ;;
esac
