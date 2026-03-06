import logging

from django.shortcuts import get_object_or_404

from agent.memory import MEMORY_STRATEGIES
from agent.memory.base import MemoryStrategy

from chat.models import ChatSession
from chat.serializers import serialize_message
from chat.services.db import db_retry

logger = logging.getLogger(__name__)


def get_memory_strategy(session: ChatSession) -> MemoryStrategy:
    strategy_cls = MEMORY_STRATEGIES[session.strategy]
    return strategy_cls()


def get_fetch_messages(session: ChatSession):
    """Return a callable that fetches all messages for this session from the DB."""

    def fetch() -> list[dict]:
        rows = db_retry(
            lambda: list(session.messages.all().values(
                "role", "message_type", "content"
            ))
        )
        return rows

    return fetch


def get_session(session_id) -> ChatSession:
    return db_retry(get_object_or_404, ChatSession, id=session_id)


def list_strategies() -> list[dict]:
    return [
        {"key": "buffer", "name": "Buffer", "description": "Keeps the full conversation history."},
        {"key": "window", "name": "Window", "description": "Retains only the most recent messages."},
        {"key": "summary", "name": "Summary", "description": "Compresses older messages into a summary."},
        {"key": "retrieval", "name": "Retrieval", "description": "Embeds and retrieves relevant memories."},
    ]


def handle_list_sessions() -> list[dict]:
    sessions = db_retry(
        lambda: list(ChatSession.objects.order_by("-created_at").values(
            "id", "strategy", "created_at"
        ))
    )
    return [
        {
            "id": str(s["id"]),
            "strategy": s["strategy"],
            "created_at": s["created_at"].isoformat(),
        }
        for s in sessions
    ]


def handle_create_session(strategy: str) -> dict | None:
    if strategy not in MEMORY_STRATEGIES:
        return None
    session = db_retry(ChatSession.objects.create, strategy=strategy)
    logger.info("Session created: id=%s strategy=%s", session.id, strategy)
    return {
        "id": str(session.id),
        "strategy": session.strategy,
        "created_at": session.created_at.isoformat(),
    }


def handle_session_messages(session_id) -> dict:
    session = get_session(session_id)
    rows = db_retry(
        lambda: list(session.messages.all().values(
            "role", "message_type", "content"
        ))
    )
    messages = [
        serialize_message(row["role"], row["message_type"], row["content"])
        for row in rows
    ]
    return {
        "session_id": str(session.id),
        "strategy": session.strategy,
        "messages": messages,
    }
