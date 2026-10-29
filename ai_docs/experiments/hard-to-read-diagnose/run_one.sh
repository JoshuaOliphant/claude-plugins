#!/bin/bash
# usage: run_one.sh <run>   e.g. skill-h3-1
# Runs one headless Sonnet 5.5 agent on a built run directory; skips runs that already have a transcript.
set -u
HW=${HW:-/tmp/hard-diagnose}
RUN=$1
OUT=$HW/transcripts/$RUN.jsonl
mkdir -p $HW/transcripts
[ -s "$OUT" ] && grep -q '"type":"result"' "$OUT" && exit 0
FLAGS=()
case $RUN in base-*) FLAGS=(--disable-slash-commands);; esac
cd $HW/runs/$RUN
START=$(date +%s)
timeout 900 claude -p "$(cat $HW/briefs/$RUN.md)" --model claude-sonnet-5-5 \
  --session-id "$(python3 -c 'import uuid;print(uuid.uuid4())')" \
  --output-format stream-json --verbose --allowedTools Bash Read Edit Write Grep Glob Skill "${FLAGS[@]}" \
  > "$OUT.tmp" 2> $HW/transcripts/$RUN.err
mv "$OUT.tmp" "$OUT"
echo "$RUN exit=$? secs=$(( $(date +%s)-START ))" >> $HW/transcripts/done.log
