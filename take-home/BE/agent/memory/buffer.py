from __future__ import annotations

from agent.memory.base import MemoryStrategy


class BufferMemory(MemoryStrategy):
    """Full conversation history — every message is returned from the DB.

    This is the simplest strategy and serves as the baseline. It provides
    perfect recall but grows without bound, eventually hitting token limits.
    """

    def recall(self, fetch_messages: callable, query: str = "") -> str:
        messages = fetch_messages()
        if not messages:
            return "No conversation history yet."
        lines = []
        for m in messages:
            if m["message_type"] == "chat_message":
                lines.append(f"{m['role']}: {m['content']}")
        return "\n".join(lines) if lines else "No conversation history yet."

    def describe(self) -> str:
        return "Buffer (full history)"
