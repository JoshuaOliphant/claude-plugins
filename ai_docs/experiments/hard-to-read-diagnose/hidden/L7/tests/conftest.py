import io
import os
import pathlib
import sys

import pytest

TREE = pathlib.Path(__file__).resolve().parent.parent
if str(TREE) not in sys.path:
    sys.path.insert(0, str(TREE))

_real_scandir = os.scandir
_real_listdir = os.listdir

ORDERS = {
    "default": None,
    "reversed": lambda names: list(reversed(names)),
    "sorted": lambda names: sorted(names),
    "reverse-sorted": lambda names: sorted(names, reverse=True),
}


class _EntryList:
    def __init__(self, entries):
        self._it = iter(entries)

    def __iter__(self):
        return self

    def __next__(self):
        return next(self._it)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def close(self):
        pass


def _install_order(monkeypatch, order):
    if order is None:
        return

    def scandir(path="."):
        with _real_scandir(path) as it:
            entries = list(it)
        by_name = {e.name: e for e in entries}
        return _EntryList([by_name[n] for n in order([e.name for e in entries])])

    def listdir(path="."):
        return order(list(_real_listdir(path)))

    def iterdir(self):
        for name in order(list(_real_listdir(self))):
            yield self / name

    monkeypatch.setattr(os, "scandir", scandir)
    monkeypatch.setattr(os, "listdir", listdir)
    monkeypatch.setattr(pathlib.Path, "iterdir", iterdir)


def _purge():
    for name in list(sys.modules):
        if name == "ledgerkit" or name.startswith("ledgerkit."):
            del sys.modules[name]


@pytest.fixture(params=list(ORDERS), ids=list(ORDERS))
def run_cli(request, monkeypatch):
    """Return a callable running the CLI in a fresh interpreter state with the
    directory listing order given by the fixture parameter."""
    _purge()
    _install_order(monkeypatch, ORDERS[request.param])
    monkeypatch.chdir(TREE)
    for var in list(os.environ):
        if var.startswith("LEDGERKIT_"):
            monkeypatch.delenv(var)

    def run(*argv):
        from ledgerkit.cli import main

        out = io.StringIO()
        code = main(list(argv), out=out)
        return code, out.getvalue()

    yield run
    _purge()
