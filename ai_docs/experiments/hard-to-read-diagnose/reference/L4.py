"""Apply the reference fix: python reference_fix.py <tree_dir>"""

import sys
from pathlib import Path

OLD = "    return int(time.mktime(moment.timetuple()))\n"
NEW = "    return int(moment.timestamp())\n"


def main(tree: str) -> None:
    path = Path(tree) / "tillbook" / "utils" / "timeconv.py"
    text = path.read_text(encoding="utf-8")
    assert text.count(OLD) == 1, "expected buggy to_epoch body not found"
    path.write_text(text.replace(OLD, NEW), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1])
