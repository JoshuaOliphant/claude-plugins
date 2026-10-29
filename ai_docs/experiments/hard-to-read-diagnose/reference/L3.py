"""Apply the reference fix: publish a lazily built service only once.

Usage: python reference_fix.py <tree_dir>
"""

import sys
from pathlib import Path

OLD = """        instance = factory(self)
        with self._lock:
            self._instances[name] = instance
        return instance
"""

NEW = """        instance = factory(self)
        with self._lock:
            return self._instances.setdefault(name, instance)
"""


def main() -> None:
    target = Path(sys.argv[1]) / "stockflow" / "container.py"
    text = target.read_text(encoding="utf-8")
    assert OLD in text, "expected code not found in container.py"
    target.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
    print(f"patched {target}")


if __name__ == "__main__":
    main()
