import sys
from pathlib import Path

import pytest

TREE = Path(__file__).resolve().parent.parent
if str(TREE) not in sys.path:
    sys.path.insert(0, str(TREE))


@pytest.fixture()
def api():
    from basketry import api as _api

    _api.reset_service()
    yield _api
    _api.reset_service()
