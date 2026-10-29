"""Apply the reference fix: deep_merge must not hand out nested objects from its inputs."""

import sys
from pathlib import Path


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert text.count(old) == 1, f"expected exactly one occurrence in {path}: {old!r}"
    path.write_text(text.replace(old, new), encoding="utf-8")


def main(tree: str) -> None:
    target = Path(tree) / "basketry" / "utils" / "mapping.py"
    replace_once(
        target,
        "from __future__ import annotations\n\nfrom collections.abc",
        "from __future__ import annotations\n\nimport copy\nfrom collections.abc",
    )
    replace_once(
        target,
        """    result = dict(base)
    for key, value in override.items():
        current = result.get(key)
        if isinstance(value, Mapping) and isinstance(current, Mapping):
            result[key] = deep_merge(current, value)
        else:
            result[key] = value
    return result""",
        """    result = copy.deepcopy(dict(base))
    for key, value in override.items():
        current = result.get(key)
        if isinstance(value, Mapping) and isinstance(current, Mapping):
            result[key] = deep_merge(current, value)
        else:
            result[key] = copy.deepcopy(value)
    return result""",
    )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python reference_fix.py <tree_dir>")
    main(sys.argv[1])
