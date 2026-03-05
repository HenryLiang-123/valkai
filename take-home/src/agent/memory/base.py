from abc import ABC, abstractmethod


class MemoryStrategy(ABC):
    """Base interface for conversation memory strategies."""

    @abstractmethod
    def get_messages(self) -> list[dict]:
        """Return the message list to send to the agent."""

    @abstractmethod
    def add_user_message(self, content: str) -> None:
        """Record a new user message."""

    @abstractmethod
    def add_assistant_messages(self, messages: list) -> None:
        """Record the assistant's response messages (may include tool calls)."""

    @abstractmethod
    def describe(self) -> str:
        """Return a human-readable description of this strategy."""
