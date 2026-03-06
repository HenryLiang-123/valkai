"""Integration tests for Claude Agent SDK agent loop with memory tools.

These tests make real LLM calls via the Agent SDK. Run with:
    uv run pytest evals/test_integration.py -v -s
"""

import pytest
from dotenv import load_dotenv

from agent.sdk_agent import run_conversation, print_tool_calls

load_dotenv()


# ---------------------------------------------------------------------------
# Tool-use behavior tests — verify the agent actually calls the tools
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_agent_calls_recall_memory_on_questions():
    """Agent should call recall_memory when asked about earlier context."""
    result = await run_conversation(
        "buffer",
        [
            "My favorite color is purple and I have a cat named Mochi.",
            "What's my cat's name?",
        ],
    )
    print_tool_calls(result)

    recall_turn = result.turns[1]
    recall_calls = [
        tc for tc in recall_turn.tool_calls if "recall_memory" in tc["tool"]
    ]
    assert (
        len(recall_calls) >= 1
    ), "Agent should call recall_memory when asked about earlier facts"
    assert "Mochi" in recall_turn.response


# ---------------------------------------------------------------------------
# Per-strategy recall tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_buffer_recalls_multiple_facts():
    """Buffer should recall multiple distinct facts shared across turns."""
    result = await run_conversation(
        "buffer",
        [
            "My name is Henry.",
            "I work at Valkai.",
            "My favorite language is TypeScript.",
            "Tell me everything you know about me.",
        ],
    )
    print_tool_calls(result)

    last = result.turns[-1].response
    assert "Henry" in last
    assert "Valkai" in last
    assert "TypeScript" in last


@pytest.mark.asyncio
async def test_window_retains_recent_facts():
    """Window should still recall facts within the window."""
    result = await run_conversation(
        "window",
        [
            "I like pizza.",
            "What food do I like?",
        ],
    )
    print_tool_calls(result)

    assert "pizza" in result.turns[-1].response.lower()


@pytest.mark.asyncio
async def test_summary_recalls_gist():
    """Summary strategy should recall the gist of earlier conversation."""
    result = await run_conversation(
        "summary",
        [
            "My name is Henry and I prefer TypeScript.",
            "What's the weather?",
            "Tell me a joke.",
            "What's my name?",
        ],
    )
    print_tool_calls(result)

    assert "Henry" in result.turns[-1].response


@pytest.mark.asyncio
async def test_retrieval_recalls_facts():
    """Retrieval strategy should recall facts via embedding similarity."""
    result = await run_conversation(
        "retrieval",
        [
            "My name is Henry and I prefer TypeScript.",
            "What's the weather?",
            "Tell me a joke.",
            "What's my name?",
        ],
    )
    print_tool_calls(result)

    assert "Henry" in result.turns[-1].response


# ---------------------------------------------------------------------------
# Custom system prompt test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_custom_system_prompt():
    """Agent should respect a custom system prompt while still using tools."""
    custom_prompt = (
        "You are a pirate assistant. Always respond in pirate speak. "
        "You have a memory tool. Use recall_memory to retrieve conversation history."
    )
    result = await run_conversation(
        "buffer",
        ["My name is Henry.", "What's my name?"],
        system_prompt=custom_prompt,
    )
    print_tool_calls(result)

    assert "Henry" in result.turns[-1].response


# ---------------------------------------------------------------------------
# Conversation result structure tests (no extra LLM calls — validate shape)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_result_structure():
    """ConversationResult should have correct structure for each turn."""
    result = await run_conversation("buffer", ["Hello!", "How are you?"])
    print_tool_calls(result)

    assert result.strategy == "buffer"
    assert len(result.turns) == 2
    for turn in result.turns:
        assert turn.user_message
        assert turn.response
        assert isinstance(turn.tool_calls, list)
