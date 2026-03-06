import logging

from django.shortcuts import get_object_or_404

from agent.memory import MEMORY_STRATEGIES
from agent.sdk_agent import _StrategyAdapter

from chat.models import ChatSession
from chat.services.db import db_retry

logger = logging.getLogger(__name__)

# In-memory backend store keyed by session UUID (memory strategies are stateful
# Python objects that can't be serialised to DB, so we keep them in process).
_backends: dict[str, _StrategyAdapter] = {}


def get_memory_backend(session: ChatSession) -> _StrategyAdapter:
    key = str(session.id)
    if key not in _backends:
        strategy_cls = MEMORY_STRATEGIES[session.strategy]
        _backends[key] = _StrategyAdapter(strategy_cls())
    return _backends[key]


def get_session(session_id) -> ChatSession:
    return db_retry(get_object_or_404, ChatSession, id=session_id)


def list_strategies() -> list[dict]:
    return [
        {"key": "buffer", "name": "Buffer", "description": "Keeps the full conversation history."},
        {"key": "window", "name": "Window", "description": "Retains only the most recent messages."},
        {"key": "summary", "name": "Summary", "description": "Compresses older messages into a summary."},
        {"key": "retrieval", "name": "Retrieval", "description": "Embeds and retrieves relevant memories."},
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
    messages = db_retry(
        lambda: list(session.messages.all().values(
            "id", "role", "message_type", "content", "created_at"
        ))
    )
    return {
        "session_id": str(session.id),
        "strategy": session.strategy,
        "messages": messages,
    }
