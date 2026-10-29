"""Apply the reference fix: the European spreadsheet dialect must not claim
the ``.csv`` extension it inherits from the delimited base class."""

import pathlib
import sys

tree = pathlib.Path(sys.argv[1])
target = tree / "ledgerkit" / "exporters" / "excel_eu.py"
text = target.read_text(encoding="utf-8")
old = '    aliases = ("csv-eu", "excel")\n'
new = '    aliases = ("csv-eu", "excel")\n    extensions = ()\n'
assert old in text, "expected text not found in excel_eu.py"
target.write_text(text.replace(old, new, 1), encoding="utf-8")
print(f"patched {target}")
