"""Apply the reference fix: FeedClient.open_cursor must start a new cursor
instead of handing back a partially consumed one."""

import sys
from pathlib import Path

OLD = """        key = (feed, since)
        cursor = self._open.get(key)
        if cursor is None or cursor.closed:
            self._evict()
            cursor = PageCursor(self.transport, feed, since)
            self._open[key] = cursor
            log.debug("opened %r", cursor)
        else:
            self._open.move_to_end(key)
        return cursor
"""

NEW = """        key = (feed, since)
        previous = self._open.pop(key, None)
        if previous is not None:
            previous.close()
        self._evict()
        cursor = PageCursor(self.transport, feed, since)
        self._open[key] = cursor
        log.debug("opened %r", cursor)
        return cursor
"""


def main(tree: str) -> None:
    path = Path(tree) / "ledgerflow" / "feeds" / "client.py"
    text = path.read_text()
    assert OLD in text, "expected original open_cursor body not found"
    path.write_text(text.replace(OLD, NEW, 1))


if __name__ == "__main__":
    main(sys.argv[1])
