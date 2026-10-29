import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent


def run(seed):
    env = dict(os.environ, PYTHONHASHSEED=str(seed))
    return subprocess.run(
        [sys.executable, "-m", "board.cli", str(HERE / "entries.json")],
        capture_output=True, text=True, env=env, cwd=ROOT, check=True,
    ).stdout


def test_same_output_for_every_hash_seed():
    outs = {s: run(s) for s in range(8)}
    assert len(set(outs.values())) == 1, outs


def test_scores_still_descending_and_best_kept():
    out = run(0).splitlines()
    scores = [int(l.split()[-1]) for l in out]
    assert scores == sorted(scores, reverse=True)
    assert len(out) == 8 and scores[0] == 90
