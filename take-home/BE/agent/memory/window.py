from __future__ import annotations

from agent.memory.base import MemoryStrategy

DEFAULT_WINDOW_SIZE = 6  # number of messages (user + assistant) to keep


class WindowMemory(MemoryStrategy):
    """Sliding-window memory — only the last *k* messages are returned.

    Older messages are not included. This bounds token usage but means
    the agent loses access to anything said earlier in the conversation.
    """

    def __init__(self, window_size: int = DEFAULT_WINDOW_SIZE):
        self._window_size = window_size

    def recall(self, fetch_messages: callable, query: str = "") -> str:
        messages = fetch_messages()
        if not messages:
            return "No conversation history yet."
        chat_messages = [m for m in messages if m["message_type"] == "chat_message"]
        window = chat_messages[-self._window_size :]
        lines = [f"{m['role']}: {m['content']}" for m in window]
        return "\n".join(lines) if lines else "No conversation history yet."

    def describe(self) -> str:
        return f"Window (last {self._window_size} messages)"
