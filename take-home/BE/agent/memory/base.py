from __future__ import annotations

from abc import ABC, abstractmethod


class MemoryStrategy(ABC):
    """Base interface for DB-aware conversation memory strategies.

    Each strategy reads from the DB (via a message-fetching callable) and
    returns the context that should be injected into the agent's recall.
    """

    @abstractmethod
    def recall(self, fetch_messages: callable, query: str = "") -> str:
        """Return conversation context for the agent.

        *fetch_messages* is a callable that returns a list of dicts with
        keys ``role``, ``message_type``, and ``content``, ordered by time,
        representing the full conversation history from the DB.

        *query* is an optional search string provided by the agent to
        focus retrieval (used by embedding-based strategies).
        """

    @abstractmethod
    def describe(self) -> str:
        """Return a human-readable description of this strategy."""
