"""Tests for memory strategies — unit tests (no LLM) and integration tests (real LLM calls)."""

import pytest
from unittest.mock import MagicMock, patch
from dotenv import load_dotenv

from agent.memory.base import MemoryStrategy
from agent.memory.buffer import BufferMemory
from agent.memory.window import WindowMemory
from agent.memory.summary import SummaryMemory
from agent.memory.retrieval import RetrievalSummaryMemory
from agent.memory import MEMORY_STRATEGIES
from agent.core import make_agent

load_dotenv()


# ---------------------------------------------------------------------------
# Unit tests (no LLM calls)
# ---------------------------------------------------------------------------


class TestBufferMemory:
    def test_stores_all_messages(self):
        mem = BufferMemory()
        mem.add_user_message("hello")
        mem.add_user_message("world")
        msgs = mem.get_messages()
        assert len(msgs) == 2
        assert msgs[0]["content"] == "hello"
        assert msgs[1]["content"] == "world"

    def test_assistant_messages_replace_history(self):
        mem = BufferMemory()
        mem.add_user_message("hi")
        full = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hey"}]
        mem.add_assistant_messages(full)
        msgs = mem.get_messages()
        assert len(msgs) == 2
        assert msgs[-1]["content"] == "hey"

    def test_describe(self):
        assert "Buffer" in BufferMemory().describe()


class TestWindowMemory:
    def test_window_bounds_messages(self):
        mem = WindowMemory(window_size=4)
        for i in range(10):
            mem.add_user_message(f"msg {i}")
        msgs = mem.get_messages()
        assert len(msgs) == 4
        assert msgs[0]["content"] == "msg 6"

    def test_small_history_returns_all(self):
        mem = WindowMemory(window_size=6)
        mem.add_user_message("only one")
        assert len(mem.get_messages()) == 1

    def test_describe(self):
        assert "Window" in WindowMemory().describe()


class TestSummaryMemoryUnit:
    def test_compression_triggers_after_n_turns(self):
        """Summary compression should trigger after summarize_every user turns."""
        mock_model = MagicMock()
        mock_model.invoke.return_value = MagicMock(content="A summary.")

        with patch("agent.memory.summary.init_chat_model", return_value=mock_model):
            mem = SummaryMemory(summarize_every=2, recent_to_keep=2)

        mem.add_user_message("turn 1")
        mem.add_assistant_messages([
            {"role": "user", "content": "turn 1"},
            {"role": "assistant", "content": "reply 1"},
        ])
        assert mock_model.invoke.call_count == 0

        mem.add_user_message("turn 2")
        mem.add_assistant_messages([
            {"role": "user", "content": "turn 1"},
            {"role": "assistant", "content": "reply 1"},
            {"role": "user", "content": "turn 2"},
            {"role": "assistant", "content": "reply 2"},
        ])
        assert mock_model.invoke.call_count == 1

    def test_summary_injected_as_system_message(self):
        mock_model = MagicMock()
        mock_model.invoke.return_value = MagicMock(content="Summary text here.")

        with patch("agent.memory.summary.init_chat_model", return_value=mock_model):
            mem = SummaryMemory(summarize_every=1, recent_to_keep=2)

        mem.add_user_message("hello")
        mem.add_assistant_messages([
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ])

        msgs = mem.get_messages()
        assert msgs[0]["role"] == "system"
        assert "Summary" in msgs[0]["content"]


class TestRetrievalSummaryMemoryUnit:
    def test_summaries_accumulate(self):
        """Each compression cycle should add a new summary, not overwrite."""
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = [
            MagicMock(content="Summary 1"),
            MagicMock(content="Summary 2"),
        ]
        mock_embedder = MagicMock()
        mock_embedder.encode.return_value = __import__("numpy").random.rand(384)

        with patch("agent.memory.retrieval.init_chat_model", return_value=mock_llm), \
             patch("agent.memory.retrieval.SentenceTransformer", return_value=mock_embedder):
            mem = RetrievalSummaryMemory(summarize_every=1, recent_to_keep=2)

        # First cycle
        mem.add_user_message("fact 1")
        mem.add_assistant_messages([
            {"role": "user", "content": "fact 1"},
            {"role": "assistant", "content": "ok"},
        ])
        assert len(mem._summaries) == 1

        # Second cycle
        mem.add_user_message("fact 2")
        mem.add_assistant_messages([
            {"role": "user", "content": "fact 1"},
            {"role": "assistant", "content": "ok"},
            {"role": "user", "content": "fact 2"},
            {"role": "assistant", "content": "ok"},
        ])
        assert len(mem._summaries) == 2
        assert "Summary 1" in mem._summaries
        assert "Summary 2" in mem._summaries


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
# Integration tests (real LLM calls)
# ---------------------------------------------------------------------------


@pytest.fixture
def agent():
    return make_agent()


def test_buffer_recalls_facts(agent):
    """Buffer memory should recall facts from early in the conversation."""
    mem = BufferMemory()
    turns = [
        "My name is Henry and I prefer TypeScript.",
        "What's the weather?",
        "Tell me a joke.",
        "What's my name and what language do I prefer?",
    ]
    for turn in turns:
        mem.add_user_message(turn)
        result = agent.invoke({"messages": mem.get_messages()})
        mem.add_assistant_messages(result["messages"])

    last_response = result["messages"][-1].content
    assert "Henry" in last_response
    assert "TypeScript" in last_response


def test_window_loses_old_facts(agent):
    """Window memory with small window should forget early facts."""
    mem = WindowMemory(window_size=4)
    turns = [
        "My name is Bartholomew and I prefer Haskell.",
        "What's the weather?",
        "Tell me a joke.",
        "What's 2+2?",
        "Recommend a book.",
        "What's my name and what language do I prefer?",
    ]
    for turn in turns:
        mem.add_user_message(turn)
        result = agent.invoke({"messages": mem.get_messages()})
        mem.add_assistant_messages(result["messages"])

    last_response = result["messages"][-1].content.lower()
    # Window should have dropped the first message containing name/language
    assert "bartholomew" not in last_response or "haskell" not in last_response
