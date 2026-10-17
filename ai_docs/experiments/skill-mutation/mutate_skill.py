# ABOUTME: Deletion-mutation testing for a SKILL.md against its evals: drop one chunk at a time, rerun the evals, see what dies.
# ABOUTME: A surviving mutant is either an eval gap or an instruction that changes nothing. Throwaway PoC, not shipped.
import argparse
import concurrent.futures
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

WRAPPER = (
    "The user has invoked the `{name}` skill. Follow its instructions below for this request.\n\n"
    "<skill>\n{body}\n</skill>"
)

JUDGE = """You grade one run of an AI assistant against expectations. Judge only from the evidence below.
Process expectations (what it searched, read, or checked) are judged from the TOOL TRACE; content
expectations from the FINAL RESPONSE. Be strict: a vague gesture at a fact is not mentioning it.

USER REQUEST:
{prompt}

TOOL TRACE:
{trace}

FINAL RESPONSE:
{response}

EXPECTATIONS:
{expectations}

Reply with only a JSON array of {n} booleans, one per expectation, in order."""


def split_skill(text: str) -> tuple[str, str]:
    match = re.match(r"^---\n.*?\n---\n", text, re.DOTALL)
    return (match.group(0), text[match.end() :]) if match else ("", text)


def chunks(body: str) -> list[tuple[int, int]]:
    """Line ranges [start, end) that can each be deleted: paragraphs, single list items, whole code blocks. Headings stay."""
    lines = body.split("\n")
    spans, i = [], 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.startswith("#"):
            i += 1
        elif line.startswith("```"):
            j = i + 1
            while j < len(lines) and not lines[j].startswith("```"):
                j += 1
            spans.append((i, j + 1))
            i = j + 1
        elif re.match(r"^\s*(-|\d+\.) ", line):
            j = i + 1
            while (
                j < len(lines)
                and lines[j].startswith("  ")
                and not re.match(r"^\s*(-|\d+\.) ", lines[j])
            ):
                j += 1
            spans.append((i, j))
            i = j
        else:
            j = i + 1
            while (
                j < len(lines) and lines[j].strip() and not lines[j].startswith(("#", "```", "- "))
            ):
                j += 1
            spans.append((i, j))
            i = j
    return spans


def run(cmd: list[str], cwd: Path, timeout: int) -> str:
    return subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, check=False
    ).stdout


def subject(prompt: str, system: str, model: str, sandbox: Path) -> dict:
    out = run(
        [
            "claude",
            "-p",
            prompt,
            "--append-system-prompt",
            system,
            "--model",
            model,
            "--setting-sources",
            "",
            "--strict-mcp-config",
            "--no-session-persistence",
            "--allowedTools",
            "Read",
            "Grep",
            "Glob",
            "Bash",
            "--disallowedTools",
            "Skill",
            "Agent",
            "Task",
            "WebFetch",
            "WebSearch",
            "--output-format",
            "stream-json",
            "--verbose",
        ],
        sandbox,
        600,
    )
    trace, response = [], ""
    for line in out.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "assistant":
            for block in event["message"].get("content", []):
                if block.get("type") == "tool_use":
                    trace.append(f"{block['name']}({json.dumps(block['input'])[:300]})")
        elif event.get("type") == "result":
            response = event.get("result", "")
    return {"trace": trace, "response": response}


def judge(case: dict, transcript: dict, model: str, sandbox: Path) -> list[bool] | None:
    expectations = case["expectations"]
    prompt = JUDGE.format(
        prompt=case["prompt"],
        trace="\n".join(transcript["trace"]) or "(no tool calls)",
        response=transcript["response"] or "(empty)",
        n=len(expectations),
        expectations="\n".join(f"{i + 1}. {e}" for i, e in enumerate(expectations)),
    )
    for _ in range(2):
        out = run(
            [
                "claude",
                "-p",
                prompt,
                "--model",
                model,
                "--setting-sources",
                "",
                "--strict-mcp-config",
                "--no-session-persistence",
                "--tools",
                "",
                "--output-format",
                "json",
            ],
            sandbox,
            300,
        )
        try:
            verdict = json.loads(
                re.search(r"\[.*\]", json.loads(out)["result"], re.DOTALL).group(0)
            )
            if len(verdict) == len(expectations):
                return [bool(v) for v in verdict]
        except (json.JSONDecodeError, AttributeError, KeyError):
            pass
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skill", type=Path, required=True)
    parser.add_argument("--evals", type=Path, required=True)
    parser.add_argument(
        "--kb", type=Path, required=True, help="copied to <sandbox>/knowledge/solutions"
    )
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--model", default="haiku")
    parser.add_argument("--judge-model", default="sonnet")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--baseline-only", action="store_true")
    args = parser.parse_args()

    front, body = split_skill(args.skill.read_text())
    name = re.search(r"^name:\s*(\S+)", front, re.MULTILINE).group(1)
    lines = body.split("\n")
    spans = chunks(body)
    variants = {"baseline": body}
    if not args.baseline_only:
        for start, end in spans:
            variants[f"del-L{start + 1}-{end}"] = "\n".join(lines[:start] + lines[end:])
    cases = json.loads(args.evals.read_text())["evals"]

    sandbox = Path(tempfile.mkdtemp(prefix="mutation-sandbox-"))
    shutil.copytree(args.kb, sandbox / "knowledge" / "solutions")
    args.out.mkdir(parents=True, exist_ok=True)
    results_path = args.out / "results.jsonl"
    done = set()
    if results_path.exists():
        done = {
            (r["variant"], r["case"], r["trial"])
            for r in map(json.loads, results_path.read_text().splitlines())
        }
    (args.out / "chunks.json").write_text(
        json.dumps({f"del-L{s + 1}-{e}": "\n".join(lines[s:e]) for s, e in spans}, indent=1)
    )

    def job(variant: str, case: dict, trial: int) -> dict:
        system = WRAPPER.format(name=name, body=variants[variant])
        transcript = subject(case["prompt"], system, args.model, sandbox)
        return {
            "variant": variant,
            "case": case["id"],
            "trial": trial,
            "body_sha": hashlib.sha1(variants[variant].encode()).hexdigest()[:8],
            "verdict": judge(case, transcript, args.judge_model, sandbox),
            **transcript,
        }

    todo = [
        (v, c, t)
        for v in variants
        for c in cases
        for t in range(args.trials)
        if (v, c["id"], t) not in done
    ]
    print(
        f"{len(variants)} variants x {len(cases)} cases x {args.trials} trials; {len(todo)} runs to do"
    )
    with (
        concurrent.futures.ThreadPoolExecutor(args.workers) as pool,
        results_path.open("a") as sink,
    ):
        for n, future in enumerate(
            concurrent.futures.as_completed(pool.submit(job, *t) for t in todo), 1
        ):
            row = future.result()
            sink.write(json.dumps(row) + "\n")
            sink.flush()
            print(
                f"[{n}/{len(todo)}] {row['variant']} case {row['case']} t{row['trial']}: {row['verdict']}",
                flush=True,
            )


if __name__ == "__main__":
    main()
