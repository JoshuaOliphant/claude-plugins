# ruff: noqa  (one-off experiment script, kept as run)
# ABOUTME: Reads each run's stream-json transcript: tool calls, tokens, cost, skill use, and the commands run before the first edit.
# ABOUTME: Usage: analyze.py [--trace]; env HW. Prints one JSON row per run; --trace also prints pre-edit commands for hand grading.
import glob
import json
import os
import sys

WORK = os.environ.get("HW", "/tmp/hard-diagnose")
SCRATCH = "/tmp/scratch-"


def is_edit(name, inp, run):
    """A mutation of the tree: Edit/Write outside scratch, or a Bash call that rewrites files in place."""
    if name in ("Edit", "Write"):
        return SCRATCH not in inp.get("file_path", "")
    if name == "Bash":
        cmd = inp.get("command", "")
        writes = ("sed -i" in cmd) or (
            "open(" in cmd
            and ("'w'" in cmd or '"w"' in cmd or "write_text" in cmd or ".write(" in cmd)
        )
        return (
            writes
            and ("/tmp/hard-diagnose/runs/" in cmd or "write_text" in cmd or "sed -i" in cmd)
            and SCRATCH not in cmd.split("<<")[0][:200]
            or ("sed -i" in cmd)
        )
    return False


def main() -> None:
    trace = "--trace" in sys.argv
    for path in sorted(glob.glob(f"{WORK}/transcripts/*.jsonl")):
        run = os.path.basename(path)[:-6]
        calls, edit_at, skill, result, pre = 0, None, False, None, []
        for line in open(path):
            try:
                m = json.loads(line)
            except json.JSONDecodeError:
                continue
            if m.get("type") == "assistant":
                for c in m["message"].get("content", []):
                    if c.get("type") != "tool_use":
                        continue
                    calls += 1
                    if c["name"] == "Skill":
                        skill = True
                    if edit_at is None and is_edit(c["name"], c["input"], run):
                        edit_at = calls
                    if edit_at is None:
                        pre.append(
                            (
                                c["name"],
                                c["input"].get("command")
                                or c["input"].get("file_path")
                                or c["input"].get("pattern")
                                or "",
                            )
                        )
            elif m.get("type") == "result":
                result = m
        if not result:
            print(json.dumps({"run": run, "error": "no result"}))
            continue
        u = result["usage"]
        row = {
            "run": run,
            "calls": calls,
            "first_edit_call": edit_at,
            "skill": skill,
            "turns": result.get("num_turns"),
            "secs": round(result.get("duration_ms", 0) / 1000),
            "cost": round(result.get("total_cost_usd", 0), 3),
            "tokens": u.get("input_tokens", 0)
            + u.get("cache_read_input_tokens", 0)
            + u.get("cache_creation_input_tokens", 0)
            + u.get("output_tokens", 0),
        }
        print(json.dumps(row))
        if trace:
            for n, c in pre:
                print(f"    {n}: {c[:400]!r}")


if __name__ == "__main__":
    main()
