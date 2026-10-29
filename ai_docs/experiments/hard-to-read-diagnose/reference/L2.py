"""Apply the reference fix: give the growth calculations their own decimal
context instead of reconfiguring the thread's shared one at import time."""

import sys
from pathlib import Path

tree = Path(sys.argv[1])
target = tree / "ledgerly" / "analytics" / "trends.py"
text = target.read_text()
old = "    ctx = decimal.getcontext()\n    ctx.prec = GROWTH_PRECISION\n"
new = "    ctx = decimal.Context()\n    ctx.prec = GROWTH_PRECISION\n"
assert text.count(old) == 1, "expected text not found in trends.py"
target.write_text(text.replace(old, new))
print(f"patched {target}")
