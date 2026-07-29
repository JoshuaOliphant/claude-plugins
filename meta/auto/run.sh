#!/usr/bin/env bash
# ABOUTME: Immutable evaluation runner for meta-agent search candidates (tier 1).
# ABOUTME: Gates a candidate's genome, then scores each mutated SKILL.md — emits METRIC lines.
#
# Usage: meta/auto/run.sh <candidate-dir>
#
# A candidate dir contains genome/ mirroring plugin-relative paths, e.g.
#   meta/archive/candidate-001/genome/plugins/mochi-creator/skills/mochi-creator/SKILL.md
# Only mutated files are present. The meta-agent must NEVER edit this script,
# evals/*.json, or the judge prompt in evals/run_trigger_eval.py.
set -euo pipefail
cd "$(dirname "$0")/../.."

CANDIDATE_DIR="${1:?usage: meta/auto/run.sh <candidate-dir>}"

# Gate 1: candidate structure — a genome with at least one SKILL.md.
mapfile -t SKILL_FILES < <(find "$CANDIDATE_DIR/genome" -name SKILL.md 2>/dev/null | sort)
if [[ ${#SKILL_FILES[@]} -eq 0 ]]; then
    echo "GATE FAIL: no SKILL.md under $CANDIDATE_DIR/genome" >&2
    exit 1
fi

# Gate 2 + fitness: frontmatter must parse and score against the skill's eval
# fixture (run_trigger_eval.py exits non-zero on unparseable frontmatter or an
# unmapped skill, so a malformed genome fails fast before judge spend).
for skill_md in "${SKILL_FILES[@]}"; do
    eval_name="$(basename "$(dirname "$skill_md")")"
    python3 evals/run_trigger_eval.py --skill "$eval_name" --description-file "$skill_md"
done
