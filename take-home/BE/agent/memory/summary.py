from __future__ import annotations

from langchain.chat_models import init_chat_model

from agent.memory.base import MemoryStrategy

SUMMARIZE_EVERY = 4  # summarize after this many new user messages
SUMMARY_PROMPT = (
    "Condense the following conversation into a concise summary that preserves "
    "all important facts, user preferences, names, and decisions. "
    "Write in third person. Be specific — do not lose concrete details.\n\n"
    "{conversation}"
)


class SummaryMemory(MemoryStrategy):
    """Periodically summarises older messages to save tokens.

    On recall, if the conversation is long enough, older messages are compressed
    into a summary (via LLM) and prepended before the most recent messages.

    Trade-off: reduces token usage substantially, but the summary is lossy —
    specific details may be paraphrased or dropped.
    """

    def __init__(
        self,
        model_str: str = "anthropic:claude-haiku-4-5-20251001",
        summarize_every: int = SUMMARIZE_EVERY,
        recent_to_keep: int = 4,
    ):
        self._model = init_chat_model(model_str)
        self._summarize_every = summarize_every
        self._recent_to_keep = recent_to_keep

    def recall(self, fetch_messages: callable, query: str = "") -> str:
        messages = fetch_messages()
        chat_messages = [m for m in messages if m["message_type"] == "chat_message"]
        if not chat_messages:
            return "No conversation history yet."

        # If conversation is short enough, return everything
        if len(chat_messages) <= self._recent_to_keep:
            lines = [f"{m['role']}: {m['content']}" for m in chat_messages]
            return "\n".join(lines)

        # Summarize older messages, keep recent ones verbatim
        older = chat_messages[: -self._recent_to_keep]
        recent = chat_messages[-self._recent_to_keep :]

        conversation_text = "\n".join(
            f"{m['role']}: {m['content']}" for m in older
        )
        prompt = SUMMARY_PROMPT.format(conversation=conversation_text)
        result = self._model.invoke(prompt)
        summary = result.content

        parts = [f"Summary of earlier conversation:\n{summary}", ""]
        parts.extend(f"{m['role']}: {m['content']}" for m in recent)
        return "\n".join(parts)

    def describe(self) -> str:
        return f"Summary (compress older, keep last {self._recent_to_keep} msgs)"
