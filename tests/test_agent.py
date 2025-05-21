import asyncio
import pytest

from agent import SearchAPIAgent

@pytest.mark.asyncio
async def test_get_tool_required_parameters(monkeypatch):
    agent = SearchAPIAgent()

    async def fake_get_tool_definitions():
        return [
            {
                "name": "foo_tool",
                "inputSchema": {"type": "object", "properties": {"a": {}}, "required": ["a"]}
            },
            {
                "name": "bar_tool",
                "inputSchema": {"type": "object", "properties": {"x": {}, "y": {}}, "required": ["x", "y"]}
            },
        ]

    monkeypatch.setattr(agent, "get_tool_definitions", fake_get_tool_definitions)

    params = await agent.get_tool_required_parameters("bar_tool")
    assert params == ["x", "y"]

