#!/bin/bash
ID=$1; mkdir -p /tmp/author/$ID; cd /tmp/author/$ID
[ -s /tmp/author/logs/$ID.done ] && exit 0
timeout 2400 claude -p "$(cat /tmp/author/$ID.prompt)" --model claude-opus-5-5 --disable-slash-commands \
  --output-format stream-json --verbose --allowedTools Bash Read Write Edit Grep Glob > /tmp/author/logs/$ID.jsonl 2>/tmp/author/logs/$ID.err
echo "exit=$?" > /tmp/author/logs/$ID.done
