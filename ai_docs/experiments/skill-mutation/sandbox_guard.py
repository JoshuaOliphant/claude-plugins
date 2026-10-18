# ABOUTME: PreToolUse hook for the mutation subject: denies any tool call that names a path outside the sandbox root.
# ABOUTME: Makes the leak impossible instead of only flagging it; mutate_skill.py passes it to `claude -p` via --settings.
import json
import os
import re
import sys

# An absolute path not glued to a word, variable, or URL scheme in front of it: `find /`, `cat /root/x`,
# `open('/home/u')`. `${CLAUDE_PLUGIN_ROOT}/scripts`, `https://...` and globs like `*/_archive/*` don't.
ABSOLUTE = re.compile(r"(?<![\w.~$}/:*?\]-])/[^\s'\"`;|&<>(){}]*")
# A relative path that climbs: `..`, `../x`, `a/../../b`.
CLIMB = re.compile(r"(?<![\w.~$}/-])(?:[\w.-]+/)*\.\.(?:/[^\s'\"`;|&<>(){}]*)?")
HARMLESS = {"/dev/null", "/dev/stdin", "/dev/stdout", "/dev/stderr"}
# The fields of each tool that name a path.
PATH_FIELDS = {
    "Read": ("file_path",),
    "Grep": ("path",),
    "Glob": ("path",),
    "LS": ("path",),
    "NotebookRead": ("notebook_path",),
    "Edit": ("file_path",),
    "Write": ("file_path",),
    "NotebookEdit": ("notebook_path",),
}


def outside(path: str, root: str, cwd: str) -> bool:
    if path in HARMLESS:
        return False
    full = os.path.realpath(os.path.join(cwd, os.path.expanduser(path)))
    return os.path.commonpath([full, root]) != root


def blocked(tool: str, tool_input: dict, root: str, cwd: str) -> str | None:
    """The first path a call names outside root, or None. Expects HOME and any $VARs to point into the sandbox."""
    root = os.path.realpath(root)
    if tool == "Bash":
        command = os.path.expandvars(tool_input.get("command", ""))
        candidates = ABSOLUTE.findall(command) + CLIMB.findall(command)
        candidates += re.findall(r"(?<![\w$])~[^\s'\"`;|&<>(){}]*", command)
    else:
        candidates = [tool_input[f] for f in PATH_FIELDS.get(tool, ()) if tool_input.get(f)]
        if tool == "Glob" and tool_input.get("pattern"):
            # A Glob pattern resolves against its path, so `../../**` or `/root/**` climbs out too.
            candidates.append(os.path.join(tool_input.get("path") or cwd, tool_input["pattern"]))
    return next((p for p in candidates if outside(p, root, cwd)), None)


def main() -> None:
    root = sys.argv[1]
    event = json.load(sys.stdin)
    path = blocked(event.get("tool_name", ""), event.get("tool_input") or {}, root, event["cwd"])
    if path:
        reason = f"SANDBOX_GUARD: {path} is outside this project's sandbox; work inside {root}"
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": reason,
                    }
                }
            )
        )


if __name__ == "__main__":
    main()
