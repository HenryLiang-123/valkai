import asyncio
import logging

from agent.sdk_agent import send_message

from chat.models import ChatMessage, ChatSession
from chat.serializers import serialize_message
from chat.services.db import db_retry
from chat.services.session import get_session, get_memory_strategy, get_fetch_messages

logger = logging.getLogger(__name__)


def save_message(session: ChatSession, role: str, message_type: str, content: str) -> ChatMessage:
    msg = db_retry(
        ChatMessage.objects.create,
        session=session,
        role=role,
        message_type=message_type,
        content=content,
    )
    logger.info("Message saved to DB: session=%s role=%s type=%s", session.id, role, message_type)
    return msg


def handle_send_message(session_id, user_message: str) -> dict:
    session = get_session(session_id)
    strategy = get_memory_strategy(session)
    fetch_messages = get_fetch_messages(session)

    logger.info("Message received: session=%s message=%r", session_id, user_message)

    save_message(session, "user", "chat_message", user_message)

    async def _persist(event):
        await asyncio.to_thread(save_message, session, "assistant", event["type"], event["content"])

    events = asyncio.run(send_message(strategy, fetch_messages, user_message, str(session.id), on_event=_persist))

    logger.info("Response sent: session=%s events=%d", session_id, len(events))

    serialized = [serialize_message("assistant", e["type"], e["content"]) for e in events]
    return {
        "session_id": str(session.id),
        "events": serialized,
    }
