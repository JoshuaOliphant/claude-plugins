# ABOUTME: Tests the Jev tool registry: registering a tool by name and rejecting input without required keys.
# ABOUTME: Every family module relies on these two behaviors.
import pytest
from jevtools import registry


def test_tool_registers_its_gather_and_judge(monkeypatch):
    monkeypatch.setattr(registry, "TOOLS", {})

    @registry.tool("probe", "A probe.", gather=dict)
    async def probe(jev, gathered):
        return gathered

    assert registry.TOOLS["probe"] == registry.Tool("probe", "A probe.", dict, probe)


def test_require_names_every_missing_key():
    registry.require({"a": 1}, "a")
    with pytest.raises(registry.BadInput, match="input is missing b, c"):
        registry.require({"a": 1}, "a", "b", "c")
