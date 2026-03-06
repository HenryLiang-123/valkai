"""Basic agent evals using Claude Agent SDK."""

import pytest
from dotenv import load_dotenv

from agent.sdk_agent import run_conversation

load_dotenv()


@pytest.mark.asyncio
async def test_agent_responds():
    """Agent should return a non-empty response to a simple question."""
    result = await run_conversation("buffer", ["What is 2 + 2?"])
    assert len(result.turns) == 1
    assert result.turns[0].response
    assert "4" in result.turns[0].response


@pytest.mark.asyncio
async def test_agent_multi_turn():
    """Agent should handle multi-turn conversation with memory tools."""
    result = await run_conversation(
        "buffer",
        ["My name is Alice.", "What is my name?"],
    )
    assert len(result.turns) == 2
    assert "Alice" in result.turns[-1].response
