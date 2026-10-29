from settings.loader import load


def test_later_files_win_in_any_listing_order(listing):
    cfg = load()
    assert cfg["max_workers"] == 16
    assert cfg["log"] == {"level": "warning", "json": False}
    assert cfg["db"] == {"pool": 20}
