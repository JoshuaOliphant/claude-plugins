# ruff: noqa  (one-off experiment script, kept as run)
# ABOUTME: Prints each pre-edit executing command and the head of its output for one run, for hand labelling.
# ABOUTME: Usage: preedit.py <run>...; env HW.
import json, os, re, sys

WORK = os.environ.get("HW", "/tmp/hard-diagnose")
EXEC = re.compile(r"python|pytest|PYTHONHASHSEED|TZ=")
for run in sys.argv[1:]:
    print("=====", run)
    pending, edited = {}, False
    for line in open(f"{WORK}/transcripts/{run}.jsonl"):
        try:
            m = json.loads(line)
        except Exception:
            continue
        if edited:
            break
        if m.get("type") == "assistant":
            for c in m["message"].get("content", []):
                if c.get("type") != "tool_use":
                    continue
                n, i = c["name"], c["input"]
                cmd = i.get("command", "")
                if n in ("Edit", "Write") and "/tmp/scratch" not in i.get("file_path", ""):
                    edited = True
                    continue
                if (
                    n == "Bash"
                    and re.search(r"open\(p|write_text|sed -i", cmd)
                    and "scratch" not in cmd.split("<<")[0]
                ):
                    edited = True
                    print("  EDIT:", cmd[:100].replace("\n", "\\n"))
                    continue
                if n == "Bash" and EXEC.search(cmd):
                    pending[c["id"]] = cmd
        elif m.get("type") == "user":
            for c in m["message"].get("content", []):
                if (
                    isinstance(c, dict)
                    and c.get("type") == "tool_result"
                    and c.get("tool_use_id") in pending
                ):
                    out = c.get("content")
                    out = out if isinstance(out, str) else json.dumps(out)
                    print("  CMD:", pending[c["tool_use_id"]][:420].replace("\n", "\\n"))
                    print("  OUT:", out[:380].replace("\n", "\\n"))
