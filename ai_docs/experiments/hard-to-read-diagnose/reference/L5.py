"""Apply the reference fix: python reference_fix.py <tree_dir>

The shipped database carries an AFTER UPDATE trigger on stock_levels that,
besides stamping updated_at, clamps `reserved` to the new on_hand. That
destroys backorder reservations whenever stock is received, shipped,
counted or transferred. The fix adds a schema migration (run automatically
on every open) that recreates the trigger without the clamp.
"""

import sys
from pathlib import Path

tree = Path(sys.argv[1])
path = tree / "stockroom" / "db" / "migrations.py"
text = path.read_text(encoding="utf-8")

old_list = '''    (9, "availability view", _m9_availability_view),
]
'''
new_list = '''    (9, "availability view", _m9_availability_view),
    (10, "stock_levels touch trigger keeps reservations", _m10_stock_touch_trigger),
]
'''
old_anchor = '''MIGRATIONS: list[Migration] = ['''
new_func = '''def _m10_stock_touch_trigger(conn: sqlite3.Connection) -> None:
    # Reservations may legitimately exceed on_hand (backorders); the trigger
    # must only stamp updated_at.
    conn.execute("DROP TRIGGER IF EXISTS trg_stock_levels_touch")
    conn.execute(
        """
        CREATE TRIGGER trg_stock_levels_touch
        AFTER UPDATE OF on_hand ON stock_levels
        WHEN NEW.on_hand <> OLD.on_hand
        BEGIN
            UPDATE stock_levels
               SET updated_at = strftime('%Y-%m-%dT%H:%M:%S', 'now')
             WHERE sku = NEW.sku AND warehouse = NEW.warehouse;
        END
        """
    )


MIGRATIONS: list[Migration] = ['''

assert text.count(old_list) == 1, "migration list not found"
assert text.count(old_anchor) == 1, "MIGRATIONS anchor not found"
text = text.replace(old_list, new_list).replace(old_anchor, new_func)
path.write_text(text, encoding="utf-8")
print(f"patched {path}")
