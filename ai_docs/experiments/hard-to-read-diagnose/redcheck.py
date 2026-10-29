# ruff: noqa  (one-off experiment script, kept as run)
# ABOUTME: For each run, reports what executed before the first tree edit and whether any pre-edit output shows a failed assertion.
# ABOUTME: Usage: redcheck.py <substring>; env HW. Output is the input for hand labelling (S = symptom observed, R = failing check on record), not the label.
import glob, json, os, re, sys

WORK = os.environ.get("HW", "/tmp/hard-diagnose")
EXEC = re.compile(r"python|pytest|PYTHONHASHSEED|TZ=|time -f")
WRITE = re.compile(
    r"sed -i|write_text|open\(\w+, ?['\"]w|open\([^)]*['\"]w['\"]|cat > (?!/tmp/scratch)|(?<!/tmp/scratch-[\w-]/)tee "
)
FAIL = re.compile(r"AssertionError|FAILED|MISMATCH|assert |Traceback|\bBAD\b|differ|expected", re.I)
pat = sys.argv[1] if len(sys.argv) > 1 else ""
for path in sorted(glob.glob(f"{WORK}/transcripts/*{pat}*.jsonl")):
    run = os.path.basename(path)[:-6]
    pending, ex, asserts, fails, edited = {}, 0, 0, [], False
    for line in open(path):
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
                if n == "Write":  # scratch script
                    asserts += "assert" in i.get("content", "")
                if n == "Bash":
                    if (
                        WRITE.search(cmd)
                        and re.search(r"open\(p|write_text|sed -i|<<'E'.*open\(", cmd, re.S)
                        and "scratch" not in cmd.split("<<")[0]
                    ):
                        edited = True
                        pending[c["id"]] = ("EDIT", cmd)
                        continue
                    if EXEC.search(cmd):
                        ex += 1
                        asserts += bool(re.search(r"\bassert\b", cmd))
                        pending[c["id"]] = ("X", cmd)
        elif m.get("type") == "user":
            for c in m["message"].get("content", []):
                if (
                    isinstance(c, dict)
                    and c.get("type") == "tool_result"
                    and c.get("tool_use_id") in pending
                ):
                    kind, cmd = pending[c["tool_use_id"]]
                    out = c.get("content")
                    out = out if isinstance(out, str) else json.dumps(out)
                    if kind == "X" and FAIL.search(out):
                        fails.append(out[:160].replace("\\n", " "))
    print(f"{run:12s} pre-edit execs={ex} assert-scripts={asserts} fail-outputs={len(fails)}")
