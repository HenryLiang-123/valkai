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

    After every *n* user turns the full history is compressed into a summary
    that is prepended as a system message. The most recent messages are kept
    verbatim so the agent still has immediate context.

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
        self._messages: list[dict] = []
        self._summary: str | None = None
        self._turns_since_summary = 0

    def get_messages(self) -> list[dict]:
        msgs: list[dict] = []
        if self._summary:
            msgs.append({
                "role": "system",
                "content": f"Summary of earlier conversation:\n{self._summary}",
            })
        msgs.extend(self._messages[-self._recent_to_keep :])
        return msgs

    def add_user_message(self, content: str) -> None:
        self._messages.append({"role": "user", "content": content})
        self._turns_since_summary += 1

    def add_assistant_messages(self, messages: list) -> None:
        self._messages = list(messages)
        if self._turns_since_summary >= self._summarize_every:
            self._compress()

    def _compress(self) -> None:
        """Use the LLM to summarise the conversation so far."""
        conversation_text = "\n".join(
            f"{m['role'] if isinstance(m, dict) else m.type}: "
            f"{m['content'] if isinstance(m, dict) else m.content}"
            for m in self._messages
        )
        prompt = SUMMARY_PROMPT.format(conversation=conversation_text)
        result = self._model.invoke(prompt)
        self._summary = result.content
        self._turns_since_summary = 0

    def describe(self) -> str:
        return f"Summary (compress every {self._summarize_every} turns, keep last {self._recent_to_keep} msgs)"
