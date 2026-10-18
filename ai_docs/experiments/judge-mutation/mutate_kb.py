#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["typesafe-sdk>=0.7.1", "pyyaml"]
# ///
# ABOUTME: Mutates one claim at a time in compound-retrieve answers that passed every expectation, and compares four judges on it.
# ABOUTME: Issue #113 PoC for knowledge-base claims: Jev per claim, Sonnet per claim, the Sonnet eval checklist, and that checklist plus an open "all claims backed" expectation.
import argparse
import asyncio
import concurrent.futures
import gzip
import hashlib
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
sys.path.insert(0, str(ROOT / "plugins" / "compost" / "scripts"))
sys.path.insert(0, str(ROOT / "ai_docs" / "experiments" / "skill-mutation"))

from typesafe_sdk import Choice, Noul  # noqa: E402

import mutate_skill  # noqa: E402
from jevtools.core import Cache, open_client, session  # noqa: E402

EVALS = ROOT / "plugins" / "compound-knowledge" / "skills" / "compound-retrieve" / "evals"
RESULTS_116 = (
    ROOT / "ai_docs" / "experiments" / "skill-mutation" / "results-116" / "results.jsonl.gz"
)
DATA = HERE / "kb-data"
AUTO = 0.8
CASES = (1, 2, 3)  # cases 4 and 5 answer "nothing found", which holds no KB facts to mutate
PER_CASE = 4
PER_RESPONSE = 3
LLM_OPERATORS = {
    "wrong-fact": "Change exactly one specific fact in the sentence (a number, a name, a file, a cause, a tool) to a different one that sounds just as plausible. Keep everything else, including tone and length.",
    "wrong-conclusion": "Reverse what the sentence implies or recommends so that it is now wrong given the knowledge base, but keep it plausible and keep the same wording as far as you can.",
    "unsupported-addition": "Add one plausible, specific detail to the sentence that the knowledge base never states. Keep the rest of the sentence as it is.",
}

KB_CHOICE = Choice(
    instructions=(
        "`kb` maps each knowledge-base file path to its text. `claim` is one sentence from an answer that "
        "describes what those files contain. How does the knowledge base relate to the claim?"
    ),
    criteria={
        "supports": "Every part of the claim, including any file it names and any number or recommendation, is stated or directly implied by the knowledge base",
        "contradicts": "The knowledge base states something that conflicts with some part of the claim: a different number, file, cause, or recommendation",
        "says_nothing": "Some part of the claim, such as a file it names or a detail it adds, is not in the knowledge base, and nothing in it conflicts",
    },
)
KB_NOUL = Noul(
    instructions="`kb` maps each knowledge-base file path to its text. Is every part of `claim` stated or directly implied by the knowledge base, including any file it names?"
)
QUESTIONS = {"relation": KB_CHOICE, "backed": KB_NOUL}
OPEN_EXPECTATION = "Every file path and factual claim in the response is supported by the knowledge base contents given in the trace"


def kb_files() -> dict[str, str]:
    files = {}
    for path in sorted((EVALS / "fixtures").rglob("*.md")):
        if path.name != "compound-knowledge-registry.md":
            files[str(path.relative_to(EVALS / "fixtures"))] = path.read_text()
    return files


def sentences(response: str) -> list[str]:
    """Checkable units: sentences that name a file, a number or a code identifier and are not about the search itself."""
    units = []
    in_code = False
    for line in response.split("\n"):
        if line.startswith("```"):
            in_code = not in_code
            continue
        if in_code or line.startswith("#") or not line.strip():
            continue
        text = re.sub(r"^\s*(?:[-*]|\d+\.)\s+", "", line).strip()
        for piece in re.split(r"(?<=[.!?])\s+(?=[A-Z*`(\"])", text):
            piece = piece.strip()
            if len(piece) < 40 or re.search(
                r"\bI\b|\b(searched|grep|semantic search|isn't configured|registry)\b", piece
            ):
                continue
            if re.match(
                r"(Confirm|Check|Then|Add|Test|Write|Copy|Sync|Spend|Skip|Run|Use|Call|Load|Start|Make|Keep|Verify)\b",
                piece,
            ):
                continue  # advice, not a claim about what the knowledge base holds
            if re.search(r"`|\d", piece):
                units.append(piece)
    return units


def spread(items: list, count: int) -> list:
    if len(items) <= count:
        return items
    return [items[round(i * (len(items) - 1) / (count - 1))] for i in range(count)]


def pick_originals() -> list[dict]:
    rows = [json.loads(line) for line in gzip.open(RESULTS_116, "rt")]
    good = [
        r
        for r in rows
        if r["variant"] != "ctrl-no-skill" and all(r["verdict"]) and int(r["case"]) in CASES
    ]
    cases = {c["id"]: c for c in json.loads((EVALS / "evals.json").read_text())["evals"]}
    originals = []
    for case in CASES:
        mine = sorted(
            (r for r in good if int(r["case"]) == case),
            key=lambda r: (r["variant"], int(r["trial"])),
        )
        for row in spread(mine, PER_CASE):
            row["response"] = re.sub(
                r"/tmp/mutation-sandbox-\w+/(?:project/|home/)", "", row["response"]
            )
            units = sentences(row["response"])
            targets = spread(units, PER_RESPONSE)
            originals.append(
                {
                    "id": f"c{case}-{row['variant']}-{row['trial']}",
                    "case": cases[case],
                    "trace": row["trace"],
                    "response": row["response"],
                    "sentences": units,
                    "targets": targets,
                }
            )
    return originals


def bump(number: str) -> str:
    return number[:-1] + str((int(number[-1]) + 1) % 10)


def path_swap(sentence: str, kb: dict[str, str]) -> str | None:
    """Change the date in a cited file name, so it points at a file that does not exist."""
    match = re.search(r"(\d{8})\.md", sentence)
    return (
        sentence.replace(match.group(0), "20260301.md")
        if match and match.group(1) != "20260301"
        else None
    )


def fabricated_source(sentence: str, kb: dict[str, str]) -> str | None:
    """Swap a cited file for a plausible name that is not in the knowledge base."""
    match = re.search(r"([\w-]+)-(\d{8})\.md", sentence)
    return (
        sentence.replace(match.group(0), f"agent-isolation-playbook-{match.group(2)}.md")
        if match
        else None
    )


def number_swap(sentence: str, kb: dict[str, str]) -> str | None:
    text = " ".join(kb.values())
    for match in re.finditer(r"(?<![\w.-])\d{1,3}(?![\w.-])", sentence):
        if match.group(0) in text and bump(match.group(0)) != match.group(0):
            return sentence[: match.start()] + bump(match.group(0)) + sentence[match.end() :]
    return None


CODE_OPERATORS = {
    "path-swap": path_swap,
    "fabricated-source": fabricated_source,
    "number-swap": number_swap,
}


def claude(prompt: str, model: str = "sonnet") -> str:
    done = subprocess.run(
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
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
        cwd="/tmp",
    )
    return json.loads(done.stdout)["result"]


def cached(store: dict, key: str, make):
    if key not in store:
        store[key] = make()
    return store[key]


def llm_mutant(sentence: str, operator: str, kb: dict[str, str]) -> str | None:
    prompt = (
        "You write one defective version of a sentence for testing a fact checker.\n\n"
        f"KNOWLEDGE BASE:\n{json.dumps(kb)[:20000]}\n\nSENTENCE:\n{sentence}\n\nTASK: {LLM_OPERATORS[operator]}\n"
        'Reply with only JSON: {"mutant": "<the rewritten sentence>"}. Do not explain.'
    )
    try:
        mutant = json.loads(re.search(r"\{.*\}", claude(prompt), re.DOTALL).group(0))["mutant"]
    except (AttributeError, KeyError, TypeError, json.JSONDecodeError, subprocess.SubprocessError):
        return None
    return mutant if isinstance(mutant, str) and mutant.strip() != sentence.strip() else None


def build_items(originals: list[dict], kb: dict[str, str], store: dict) -> list[dict]:
    items = []
    for original in originals:
        for sentence in original["targets"]:
            for name, make in CODE_OPERATORS.items():
                if (mutant := make(sentence, kb)) and mutant != sentence:
                    items.append(
                        {
                            "original": original["id"],
                            "operator": name,
                            "claim": sentence,
                            "mutant": mutant,
                        }
                    )
            for name in LLM_OPERATORS:
                key = hashlib.sha256(f"{name}|{sentence}".encode()).hexdigest()
                mutant = cached(store, key, lambda: llm_mutant(sentence, name, kb))
                if mutant:
                    items.append(
                        {
                            "original": original["id"],
                            "operator": name,
                            "claim": sentence,
                            "mutant": mutant,
                        }
                    )
    return items


def unknown_files(claim: str, kb: dict[str, str]) -> bool:
    """The deterministic stage: the claim names a .md file whose name is in no knowledge-base path."""
    known = {Path(p).name for p in kb}
    return any(name not in known for name in re.findall(r"[\w-]+\.md", claim))


async def jev_judge(claims: list[str], kb: dict[str, str], out: Path) -> dict[str, dict]:
    answers = {}
    async with session(open_client, Cache(out / "jev-cache.json")) as jev:

        async def one(claim: str) -> None:
            got = await jev.ask("judge-mutation-kb", {"claim": claim, "kb": kb}, QUESTIONS)
            answers[claim] = {
                "relation": got.choice("relation"),
                "confidence": round(got.confidence("relation"), 3),
                "noul": round(got.noul("backed"), 3),
            }

        await asyncio.gather(*(one(c) for c in claims))
        print(f"jev input tokens {jev.input_tokens}, cached asks {jev.cached}", file=sys.stderr)
    return answers


SONNET_CLAIM = """You check one sentence from an answer against a knowledge base. Judge only from the knowledge base below.

KNOWLEDGE BASE (path: text):
{kb}

SENTENCE:
{claim}

Does the knowledge base back every part of the sentence, including any file it names? Reply with only JSON:
{{"relation": "supports" | "contradicts" | "says_nothing"}}
supports: every part is stated or directly implied. contradicts: some part conflicts with the knowledge base. says_nothing: some part, or a named file, is not in it and nothing conflicts."""


def sonnet_claim(claim: str, kb: dict[str, str]) -> str | None:
    try:
        text = claude(SONNET_CLAIM.format(kb=json.dumps(kb), claim=claim))
        relation = json.loads(re.search(r"\{.*\}", text, re.DOTALL).group(0))["relation"]
    except (AttributeError, KeyError, TypeError, json.JSONDecodeError, subprocess.SubprocessError):
        return None
    return relation if relation in ("supports", "contradicts", "says_nothing") else None


def checklist(
    original: dict, response: str, kb: dict[str, str], open_check: bool
) -> list[bool] | None:
    case = {
        "prompt": original["case"]["prompt"],
        "expectations": list(original["case"]["expectations"]),
    }
    trace = list(original["trace"])
    if open_check:
        case["expectations"].append(OPEN_EXPECTATION)
        trace += ["KNOWLEDGE BASE CONTENTS (path: text):", json.dumps(kb)]
    try:
        return mutate_skill.judge(case, {"trace": trace, "response": response}, "sonnet")
    except mutate_skill.Infra:
        return None


def resp_key(variant: str, response: str, rep: int | None = None) -> str:
    """Keyed by content, so a changed answer never reads another answer's verdict. rep numbers repeat judgments of an unchanged answer."""
    return f"resp|{variant}|{hashlib.sha256(response.encode()).hexdigest()[:16]}|{rep}"


def flips(base: list[bool] | None, other: list[bool] | None) -> bool | None:
    if base is None or other is None:
        return None
    return any(b and not o for b, o in zip(base, other, strict=True))


def jev_flag(answer: dict) -> str:
    """caught: not supported with confidence at the gate; routed: below it; kept: supported with confidence."""
    if answer["relation"] != "supports":
        return "caught" if answer["confidence"] >= AUTO else "routed"
    return "kept" if answer["confidence"] >= AUTO else "routed"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    DATA.mkdir(exist_ok=True)
    kb = kb_files()
    originals = pick_originals()
    by_id = {o["id"]: o for o in originals}
    mutant_store = (
        json.loads((DATA / "llm-mutants.json").read_text())
        if (DATA / "llm-mutants.json").exists()
        else {}
    )
    items = build_items(originals, kb, mutant_store)
    (DATA / "llm-mutants.json").write_text(json.dumps(mutant_store, indent=1))
    print(f"{len(originals)} originals, {len(items)} mutants", file=sys.stderr)

    claims = sorted({c for o in originals for c in o["sentences"]} | {i["mutant"] for i in items})
    jev = asyncio.run(jev_judge(claims, kb, DATA))

    judged_path = DATA / "sonnet-cache.json"
    store = json.loads(judged_path.read_text()) if judged_path.exists() else {}
    jobs = {}
    for claim in claims:
        jobs[f"claim|{claim}"] = lambda c=claim: sonnet_claim(c, kb)
    for o in originals:
        for variant, open_check in (("closed", False), ("open", True)):
            for rep in (0, 1):
                jobs[resp_key(variant, o["response"], rep)] = lambda o=o, oc=open_check: checklist(
                    o, o["response"], kb, oc
                )
    for n, item in enumerate(items):
        o = by_id[item["original"]]
        item["response"] = o["response"].replace(item["claim"], item["mutant"], 1)
        item["n"] = n
        for variant, open_check in (("closed", False), ("open", True)):
            jobs[resp_key(variant, item["response"])] = lambda o=o, it=item, oc=open_check: (
                checklist(o, it["response"], kb, oc)
            )
    todo = [k for k in jobs if k not in store or store[k] is None]
    print(f"{len(todo)} sonnet calls", file=sys.stderr)
    with concurrent.futures.ThreadPoolExecutor(args.workers) as pool:
        for key, value in zip(todo, pool.map(lambda k: jobs[k](), todo), strict=True):
            store[key] = value
    store = {key: value for key, value in store.items() if key in jobs}
    judged_path.write_text(json.dumps(store))

    rows = []
    for item in items:
        o = by_id[item["original"]]
        row = {k: item[k] for k in ("original", "operator", "claim", "mutant")}
        row["det"] = unknown_files(item["mutant"], kb) and not unknown_files(item["claim"], kb)
        row["jev"] = jev[item["mutant"]]
        row["sonnet_claim"] = store[f"claim|{item['mutant']}"]
        for variant in ("closed", "open"):
            base = store[resp_key(variant, o["response"], 0)]
            row[f"{variant}_flag"] = flips(base, store[resp_key(variant, item["response"])])
        rows.append(row)
    controls = []
    for o in originals:
        row = {"original": o["id"], "claims": []}
        for claim in o["sentences"]:
            row["claims"].append(
                {
                    "det": unknown_files(claim, kb),
                    "jev": jev[claim],
                    "sonnet_claim": store[f"claim|{claim}"],
                }
            )
        for variant in ("closed", "open"):
            row[f"{variant}_flag"] = flips(
                store[resp_key(variant, o["response"], 0)],
                store[resp_key(variant, o["response"], 1)],
            )
        controls.append(row)
    (DATA / "results.json").write_text(
        json.dumps({"mutants": rows, "originals": controls}, indent=1)
    )
    text = report(rows, controls)
    (DATA / "analysis.txt").write_text(text + "\n")
    print(text)


def pct(hits: int, n: int) -> str:
    return f"{hits}/{n}"


def report(rows: list[dict], controls: list[dict]) -> str:
    by_op = defaultdict(list)
    for r in rows:
        by_op[r["operator"]].append(r)
    lines = [
        "Mutated sentences per operator. det = names a .md file that is in no KB path (no model). jev c/r/m = Jev strict-style Choice",
        f"caught/routed/missed (gate {AUTO}). jev+det counts det as caught. sonnet = per-sentence Sonnet verdict not 'supports'.",
        "closed = Sonnet eval checklist on the whole mutated answer (any expectation that held on the original now fails); open = same plus",
        "the open 'every claim is supported by the KB' expectation. hybrid = jev+det caught or closed flagged. Blank flags (judge error) are skipped.",
        "",
        f"{'operator':<22}{'n':>3} {'det':>4} {'jev c/r/m':>10} {'jev+det':>8} {'sonnet':>7} {'closed':>7} {'open':>6} {'hybrid':>7}",
    ]

    def row_of(label: str, group: list[dict]) -> str:
        n = len(group)
        o = defaultdict(int)
        for r in group:
            o[jev_flag(r["jev"])] += 1
        both = sum(r["det"] or jev_flag(r["jev"]) == "caught" for r in group)
        son = sum(r["sonnet_claim"] not in (None, "supports") for r in group)
        closed = [r["closed_flag"] for r in group if r["closed_flag"] is not None]
        opened = [r["open_flag"] for r in group if r["open_flag"] is not None]
        hybrid = sum(
            bool(r["det"] or jev_flag(r["jev"]) == "caught" or r["closed_flag"]) for r in group
        )
        return (
            f"{label:<22}{n:>3} {sum(r['det'] for r in group):>4} {o['caught']}/{o['routed']}/{o['kept']:<5} {pct(both, n):>8} {pct(son, n):>7} "
            f"{pct(sum(closed), len(closed)):>7} {pct(sum(opened), len(opened)):>6} {pct(hybrid, n):>7}"
        )

    for op, group in by_op.items():
        lines.append(row_of(op, group))
    lines.append(row_of("all mutants", rows))
    claims = [c for o in controls for c in o["claims"]]
    o = defaultdict(int)
    for c in claims:
        o[jev_flag(c["jev"])] += 1
    lines += [
        "",
        f"Originals (true sentences from answers that passed every expectation): {len(claims)} sentences in {len(controls)} answers.",
        f"  jev: {o['caught']} caught (false flags), {o['routed']} routed, {o['kept']} kept; det false flags {sum(c['det'] for c in claims)};"
        f" sonnet claim false flags {sum(c['sonnet_claim'] not in (None, 'supports') for c in claims)}",
        f"  checklist re-judged on the same answer: closed flips {sum(bool(c['closed_flag']) for c in controls)}/{len(controls)}, open flips {sum(bool(c['open_flag']) for c in controls)}/{len(controls)} (judge noise)",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    main()
