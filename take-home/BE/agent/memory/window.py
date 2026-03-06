from agent.memory.base import MemoryStrategy

DEFAULT_WINDOW_SIZE = 6  # number of messages (user + assistant) to keep


class WindowMemory(MemoryStrategy):
    """Sliding-window memory — only the last *k* messages are retained.

    Older messages are silently dropped. This bounds token usage but means
    the agent loses access to anything said earlier in the conversation.
    """

    def __init__(self, window_size: int = DEFAULT_WINDOW_SIZE):
        self._window_size = window_size
        self._messages: list[dict] = []

    def get_messages(self) -> list[dict]:
        return self._messages[-self._window_size :]

    def add_user_message(self, content: str) -> None:
        self._messages.append({"role": "user", "content": content})

    def add_assistant_messages(self, messages: list) -> None:
        self._messages = list(messages)

    def describe(self) -> str:
        return f"Window (last {self._window_size} messages)"
