"""Tests for memory strategies — unit tests (no LLM) and integration tests (Claude Agent SDK)."""

import pytest
from unittest.mock import MagicMock, patch
from dotenv import load_dotenv

from agent.memory.base import MemoryStrategy
from agent.memory.buffer import BufferMemory
from agent.memory.window import WindowMemory
from agent.memory.summary import SummaryMemory
from agent.memory.retrieval import RetrievalSummaryMemory
from agent.memory import MEMORY_STRATEGIES
from agent.sdk_agent import run_conversation, print_tool_calls

load_dotenv()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_messages(*pairs):
    """Build a list of message dicts from (role, content) pairs."""
    return [
        {"role": role, "message_type": "chat_message", "content": content}
        for role, content in pairs
    ]


# ---------------------------------------------------------------------------
# Unit tests (no LLM calls)
# ---------------------------------------------------------------------------


class TestBufferMemory:
    def test_recalls_all_messages(self):
        mem = BufferMemory()
        messages = _make_messages(
            ("user", "hello"),
            ("assistant", "hi"),
            ("user", "world"),
        )
        result = mem.recall(lambda: messages)
        assert "hello" in result
        assert "hi" in result
        assert "world" in result

    def test_empty_history(self):
        mem = BufferMemory()
        result = mem.recall(lambda: [])
        assert "No conversation" in result

    def test_describe(self):
        assert "Buffer" in BufferMemory().describe()


class TestWindowMemory:
    def test_window_bounds_messages(self):
        mem = WindowMemory(window_size=2)
        messages = _make_messages(
            ("user", "msg 0"),
            ("assistant", "reply 0"),
            ("user", "msg 1"),
            ("assistant", "reply 1"),
            ("user", "msg 2"),
            ("assistant", "reply 2"),
        )
        result = mem.recall(lambda: messages)
        assert "msg 2" in result
        assert "reply 2" in result
        assert "msg 0" not in result

    def test_small_history_returns_all(self):
        mem = WindowMemory(window_size=6)
        messages = _make_messages(("user", "only one"))
        result = mem.recall(lambda: messages)
        assert "only one" in result

    def test_describe(self):
        assert "Window" in WindowMemory().describe()


class TestSummaryMemoryUnit:
    def test_short_conversation_returns_all(self):
        mock_model = MagicMock()
        with patch("agent.memory.summary.init_chat_model", return_value=mock_model):
            mem = SummaryMemory(recent_to_keep=4)

        messages = _make_messages(
            ("user", "hello"),
            ("assistant", "hi"),
        )
        result = mem.recall(lambda: messages)
        assert "hello" in result
        assert mock_model.invoke.call_count == 0

    def test_long_conversation_triggers_summary(self):
        mock_model = MagicMock()
        mock_model.invoke.return_value = MagicMock(content="Summary text here.")
        with patch("agent.memory.summary.init_chat_model", return_value=mock_model):
            mem = SummaryMemory(recent_to_keep=2)

        messages = _make_messages(
            ("user", "turn 1"),
            ("assistant", "reply 1"),
            ("user", "turn 2"),
            ("assistant", "reply 2"),
            ("user", "turn 3"),
            ("assistant", "reply 3"),
        )
        result = mem.recall(lambda: messages)
        assert "Summary" in result
        assert "turn 3" in result
        assert mock_model.invoke.call_count == 1


class TestRetrievalSummaryMemoryUnit:
    def test_short_conversation_returns_all(self):
        mock_llm = MagicMock()
        mock_embedder = MagicMock()

        with patch(
            "agent.memory.retrieval.init_chat_model", return_value=mock_llm
        ), patch(
            "agent.memory.retrieval.SentenceTransformer", return_value=mock_embedder
        ):
            mem = RetrievalSummaryMemory(recent_to_keep=4)

        messages = _make_messages(("user", "hello"), ("assistant", "hi"))
        result = mem.recall(lambda: messages)
        assert "hello" in result
        assert mock_llm.invoke.call_count == 0

    def test_long_conversation_chunks_and_retrieves(self):
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = [
            MagicMock(content="Summary of chunk 1"),
        ]
        mock_embedder = MagicMock()
        mock_embedder.encode.return_value = __import__("numpy").random.rand(384)

        with patch(
            "agent.memory.retrieval.init_chat_model", return_value=mock_llm
        ), patch(
            "agent.memory.retrieval.SentenceTransformer", return_value=mock_embedder
        ):
            mem = RetrievalSummaryMemory(chunk_size=4, recent_to_keep=2)

        messages = _make_messages(
            ("user", "fact 1"),
            ("assistant", "ok 1"),
            ("user", "fact 2"),
            ("assistant", "ok 2"),
            ("user", "fact 3"),
            ("assistant", "ok 3"),
        )
        result = mem.recall(lambda: messages)
        assert "Summary of chunk 1" in result
        assert "fact 3" in result


class TestRegistry:
    def test_all_strategies_registered(self):
        assert "buffer" in MEMORY_STRATEGIES
        assert "window" in MEMORY_STRATEGIES
        assert "summary" in MEMORY_STRATEGIES
        assert "retrieval" in MEMORY_STRATEGIES

    def test_all_implement_interface(self):
        for cls in MEMORY_STRATEGIES.values():
            assert issubclass(cls, MemoryStrategy)


# ---------------------------------------------------------------------------
# Integration tests (Claude Agent SDK — real LLM calls + tool use)
# ---------------------------------------------------------------------------

SCRIPTED_TURNS = [
    "My name is Henry and I prefer TypeScript.",
    "What's the weather?",
    "Tell me a joke.",
    "What's my name and what language do I prefer?",
]

SCRIPTED_TURNS_WINDOW = [
    "My name is Bartholomew and I prefer Haskell.",
    "What's the weather?",
    "Tell me a joke.",
    "What's 2+2?",
    "Recommend a book.",
    "What's my name and what language do I prefer?",
]


@pytest.mark.asyncio
async def test_buffer_agent_recalls():
    """Buffer strategy: the agent should recall facts from conversation history."""
    result = await run_conversation("buffer", SCRIPTED_TURNS)
    print_tool_calls(result)

    last_response = result.turns[-1].response
    assert "Henry" in last_response
    assert "TypeScript" in last_response


@pytest.mark.asyncio
async def test_window_agent_forgets():
    """Window strategy: with a small window, the agent should lose early facts."""
    result = await run_conversation("window", SCRIPTED_TURNS_WINDOW)
    print_tool_calls(result)

    last_response = result.turns[-1].response.lower()
    # Window only keeps last 6 entries — early facts get evicted
    assert "bartholomew" not in last_response or "haskell" not in last_response
