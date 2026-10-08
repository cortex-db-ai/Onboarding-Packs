#!/usr/bin/env bash
# On-camera status line for the Codeplane demo terminals.
# Reads the Claude Code status JSON on stdin, prints a large one-line meter:
#   model | $cost | ctx% | in/out tokens
# Settings key (project or user settings.json):
#   "statusLine": {"type": "command", "command": "bash /path/to/scripts/statusline.sh"}
input=$(cat)
py() { /usr/bin/python3 -c "$1" <<<"$input"; }
MODEL=$(py "import json,sys; d=json.load(sys.stdin); print(d.get('model',{}).get('display_name','?'))")
COST=$(py "import json,sys; d=json.load(sys.stdin); c=d.get('cost',{}); print('%.2f' % c.get('total_cost_usd',0))")
CTX=$(py "import json,sys; d=json.load(sys.stdin); print('%d' % round(d.get('context_window',{}).get('used_percentage',0)))")
CW=$(py "import json,sys; d=json.load(sys.stdin); u=d.get('context_window',{}).get('current_usage',{}) or {}; r=u.get('cache_read_input_tokens',0) or 0; i=u.get('input_tokens',0) or 0; o=u.get('output_tokens',0) or 0; print('%dk/%dk/%dk' % (r//1000, i//1000, o//1000))")
printf '\033[2m%s\033[0m \033[1;32m$%s\033[0m \033[1;36mctx %s%%\033[0m \033[2mcache/in/out %s\033[0m' "$MODEL" "$COST" "$CTX" "$CW"
