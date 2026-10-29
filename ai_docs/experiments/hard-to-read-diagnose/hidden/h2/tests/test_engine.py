from report.config import ReportConfig
from report.engine import summarize


def test_west_net():
    assert summarize(ReportConfig("west"))["net"] == 185.68


def test_eur():
    assert summarize(ReportConfig("east", currency="EUR"))["net"] == 82.8


def test_whole_units():
    # Dashboard tiles show whole dollars.
    assert summarize(ReportConfig("west", rounding=0, title="West tile"))["net"] == 186.0
