"""Apply the reference fix: remove the stray, normally git-ignored
``.env.local`` whose ``RELAYDESK_BATCH=20`` (an environment-layer value)
silently overrides ``delivery.batch_size`` from config/relaydesk.toml."""

import sys
from pathlib import Path


def main(tree: str) -> None:
    stray = Path(tree) / ".env.local"
    assert stray.is_file(), f"{stray} not found"
    text = stray.read_text()
    assert "RELAYDESK_BATCH=20" in text, "unexpected .env.local contents"
    stray.unlink()


if __name__ == "__main__":
    main(sys.argv[1])
