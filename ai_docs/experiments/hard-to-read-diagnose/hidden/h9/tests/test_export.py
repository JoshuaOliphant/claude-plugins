from exporter.pipeline import export_csv


def ids(result):
    return [int(l.split(",")[0]) for l in result["csv"].strip().splitlines()[1:]]


def test_plain_export_has_all_rows():
    assert ids(export_csv()) == list(range(1, 121))


def test_preview_export_has_all_rows_too():
    res = export_csv(preview=True)
    assert ids(res) == list(range(1, 121))
    assert res["preview"] == ["1: ITEM-1", "2: ITEM-2", "3: ITEM-3"]
