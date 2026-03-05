import numpy as np
from langchain.chat_models import init_chat_model
from sentence_transformers import SentenceTransformer

from agent.memory.base import MemoryStrategy

SUMMARIZE_EVERY = 4
SUMMARY_PROMPT = (
    "Condense the following conversation chunk into a concise summary that preserves "
    "all important facts, user preferences, names, and decisions. "
    "Write in third person. Be specific — do not lose concrete details.\n\n"
    "{conversation}"
)


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Cosine similarity between vector *a* and each row of matrix *b*."""
    a_norm = a / (np.linalg.norm(a) + 1e-10)
    b_norm = b / (np.linalg.norm(b, axis=1, keepdims=True) + 1e-10)
    return b_norm @ a_norm


class RetrievalSummaryMemory(MemoryStrategy):
    """Accumulates summaries over time and retrieves the most relevant ones.

    Every *n* user turns the recent conversation chunk is compressed into a
    summary and stored (not overwritten). On each call to ``get_messages()``,
    the latest user message is embedded alongside all stored summaries and only
    the top-k most similar summaries are injected into the context.

    This allows the agent to recall old facts that happen to match the current
    question, without sending the entire history.
    """

    def __init__(
        self,
        model_str: str = "anthropic:claude-haiku-4-5-20251001",
        embed_model: str = "all-MiniLM-L6-v2",
        summarize_every: int = SUMMARIZE_EVERY,
        recent_to_keep: int = 4,
        top_k: int = 3,
    ):
        self._llm = init_chat_model(model_str)
        self._embedder = SentenceTransformer(embed_model)
        self._summarize_every = summarize_every
        self._recent_to_keep = recent_to_keep
        self._top_k = top_k

        self._messages: list[dict] = []
        self._summaries: list[str] = []
        self._summary_embeddings: list[np.ndarray] = []
        self._turns_since_summary = 0

    # --- MemoryStrategy interface ---

    def get_messages(self) -> list[dict]:
        msgs: list[dict] = []
        if self._summaries:
            relevant = self._retrieve_relevant()
            if relevant:
                context = "\n\n".join(f"- {s}" for s in relevant)
                msgs.append({
                    "role": "system",
                    "content": (
                        "Relevant context from earlier conversation:\n" + context
                    ),
                })
        msgs.extend(self._messages[-self._recent_to_keep:])
        return msgs

    def add_user_message(self, content: str) -> None:
        self._messages.append({"role": "user", "content": content})
        self._turns_since_summary += 1

    def add_assistant_messages(self, messages: list) -> None:
        self._messages = list(messages)
        if self._turns_since_summary >= self._summarize_every:
            self._compress()

    def describe(self) -> str:
        return (
            f"Retrieval Summary (compress every {self._summarize_every} turns, "
            f"top-{self._top_k} retrieval)"
        )

    # --- Internal helpers ---

    def _compress(self) -> None:
        """Summarise recent messages and store the summary with its embedding."""
        conversation_text = "\n".join(
            f"{m['role'] if isinstance(m, dict) else m.type}: "
            f"{m['content'] if isinstance(m, dict) else m.content}"
            for m in self._messages
        )
        prompt = SUMMARY_PROMPT.format(conversation=conversation_text)
        result = self._llm.invoke(prompt)
        summary = result.content

        self._summaries.append(summary)
        embedding = self._embedder.encode(summary)
        self._summary_embeddings.append(embedding)
        self._turns_since_summary = 0

    def _retrieve_relevant(self) -> list[str]:
        """Return the top-k summaries most similar to the latest user message."""
        last_user_msg = None
        for m in reversed(self._messages):
            content = m["content"] if isinstance(m, dict) else m.content
            role = m["role"] if isinstance(m, dict) else m.type
            if role in ("user", "human"):
                last_user_msg = content
                break

        if not last_user_msg or not self._summary_embeddings:
            return list(self._summaries[: self._top_k])

        query_embedding = self._embedder.encode(last_user_msg)
        summary_matrix = np.stack(self._summary_embeddings)
        scores = _cosine_similarity(query_embedding, summary_matrix)

        k = min(self._top_k, len(self._summaries))
        top_indices = np.argsort(scores)[-k:][::-1]
        return [self._summaries[i] for i in top_indices]
