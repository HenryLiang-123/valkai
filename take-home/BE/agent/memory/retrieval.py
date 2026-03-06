from __future__ import annotations

from agent.memory.base import MemoryStrategy

SUMMARIZE_EVERY = 4
_EMBEDDER = None


def get_embedder():
    global _EMBEDDER
    if _EMBEDDER is None:
        from sentence_transformers import SentenceTransformer
        _EMBEDDER = SentenceTransformer("all-MiniLM-L6-v2")
    return _EMBEDDER


SUMMARY_PROMPT = (
    "Condense the following conversation chunk into a concise summary that preserves "
    "all important facts, user preferences, names, and decisions. "
    "Write in third person. Be specific — do not lose concrete details.\n\n"
    "{conversation}"
)


def _cosine_similarity(a, b):
    """Cosine similarity between vector *a* and each row of matrix *b*."""
    import numpy as np
    a_norm = a / (np.linalg.norm(a) + 1e-10)
    b_norm = b / (np.linalg.norm(b, axis=1, keepdims=True) + 1e-10)
    return b_norm @ a_norm


class RetrievalSummaryMemory(MemoryStrategy):
    """Chunks the conversation into blocks, summarises each, and retrieves
    the most relevant summaries via embedding similarity.

    On recall the full DB history is chunked, each chunk is summarised,
    and the top-k summaries most similar to the latest user message are
    returned alongside the most recent messages.
    """

    def __init__(
        self,
        model_str: str = "anthropic:claude-haiku-4-5-20251001",
        chunk_size: int = SUMMARIZE_EVERY,
        recent_to_keep: int = 4,
        top_k: int = 3,
    ):
        from langchain.chat_models import init_chat_model
        self._llm = init_chat_model(model_str)
        self._embedder = get_embedder()
        self._chunk_size = chunk_size
        self._recent_to_keep = recent_to_keep
        self._top_k = top_k

    def recall(self, fetch_messages: callable, query: str = "") -> str:
        import numpy as np

        messages = fetch_messages()
        chat_messages = [m for m in messages if m["message_type"] == "chat_message"]
        if not chat_messages:
            return "No conversation history yet."

        # If conversation is short enough, return everything
        if len(chat_messages) <= self._recent_to_keep:
            lines = [f"{m['role']}: {m['content']}" for m in chat_messages]
            return "\n".join(lines)

        older = chat_messages[: -self._recent_to_keep]
        recent = chat_messages[-self._recent_to_keep :]

        # Chunk older messages and summarise each chunk
        chunks = [
            older[i : i + self._chunk_size]
            for i in range(0, len(older), self._chunk_size)
        ]
        summaries = []
        for chunk in chunks:
            text = "\n".join(f"{m['role']}: {m['content']}" for m in chunk)
            prompt = SUMMARY_PROMPT.format(conversation=text)
            result = self._llm.invoke(prompt)
            summaries.append(result.content)

        if not summaries:
            lines = [f"{m['role']}: {m['content']}" for m in recent]
            return "\n".join(lines)

        # Use agent-provided query, fall back to last user message
        search_query = query or next(
            (m["content"] for m in reversed(chat_messages) if m["role"] == "user"),
            "",
        )
        if search_query and len(summaries) > 1:
            query_emb = self._embedder.encode(search_query)
            summary_embs = np.stack([self._embedder.encode(s) for s in summaries])
            scores = _cosine_similarity(query_emb, summary_embs)
            k = min(self._top_k, len(summaries))
            top_indices = np.argsort(scores)[-k:][::-1]
            relevant = [summaries[i] for i in top_indices]
        else:
            relevant = summaries[: self._top_k]

        parts = ["Relevant context from earlier conversation:"]
        parts.extend(f"- {s}" for s in relevant)
        parts.append("")
        parts.extend(f"{m['role']}: {m['content']}" for m in recent)
        return "\n".join(parts)

    def describe(self) -> str:
        return (
            f"Retrieval Summary (chunk size {self._chunk_size}, "
            f"top-{self._top_k} retrieval)"
        )
