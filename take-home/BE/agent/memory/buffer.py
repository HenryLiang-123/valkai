from agent.memory.base import MemoryStrategy


class BufferMemory(MemoryStrategy):
    """Full conversation history — every message is kept and sent to the agent.

    This is the simplest strategy and serves as the baseline. It provides
    perfect recall but grows without bound, eventually hitting token limits.
    """

    def __init__(self):
        self._messages: list[dict] = []

    def get_messages(self) -> list[dict]:
        return list(self._messages)

    def add_user_message(self, content: str) -> None:
        self._messages.append({"role": "user", "content": content})

    def add_assistant_messages(self, messages: list) -> None:
        self._messages = list(messages)

    def describe(self) -> str:
        return "Buffer (full history)"
