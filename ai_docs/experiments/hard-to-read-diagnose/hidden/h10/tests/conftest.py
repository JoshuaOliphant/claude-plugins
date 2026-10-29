import os

import pytest


@pytest.fixture(params=["as-is", "reversed"])
def listing(request, monkeypatch):
    """Directory listings come back in whatever order the filesystem likes; try both."""
    if request.param == "reversed":
        real_scandir, real_listdir = os.scandir, os.listdir

        class Rev(list):
            def __enter__(self):
                return self

            def __exit__(self, *a):
                pass

            def close(self):
                pass

        def scandir(path="."):
            with real_scandir(path) as it:
                return Rev(reversed(list(it)))

        monkeypatch.setattr(os, "scandir", scandir)
        monkeypatch.setattr(os, "listdir", lambda path=".": list(reversed(real_listdir(path))))
    return request.param
