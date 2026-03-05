# take-home

Barebones CLI chat agent built on [LangChain Deep Agents](https://github.com/langchain-ai/deepagents). Supports OpenAI, Anthropic, and Google models out of the box. Includes 4 swappable memory strategies and a comparison harness to demonstrate recall trade-offs.

## Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) package manager
- At least one LLM provider API key

## Quick start

```bash
git clone https://github.com/valkai-tech/take-home.git
cd take-home
uv sync
cp .env.example .env
# Fill in your API key(s) in .env
```

## Usage

```bash
# Default model (Anthropic Claude Haiku — cheapest)
uv run chat

# Choose a memory strategy
uv run chat --memory buffer      # Full history (default)
uv run chat --memory window      # Last 6 messages only
uv run chat --memory summary     # LLM-compressed running summary
uv run chat --memory retrieval   # Accumulated summaries + semantic retrieval

# OpenAI
uv run chat --model openai:gpt-4o

# Google
uv run chat --model google_genai:gemini-2.5-flash

# Custom system prompt
uv run chat --system "You are a helpful coding assistant."
```

Type `quit` or `exit` to end the session.

## Memory Strategies

| Strategy | How it works | Recalls old facts? | Token cost | Extra calls |
|----------|-------------|-------------------|------------|-------------|
| **Buffer** | Stores full history | Yes | Grows unbounded | None |
| **Window** | Keeps last 6 messages | No (dropped) | Fixed low | None |
| **Summary** | LLM-compresses history into one running summary every 4 turns | Partially (lossy) | Medium | LLM summarize |
| **Retrieval Summary** | Accumulates summaries + embeds them; retrieves top-k by cosine similarity per query | Yes (if relevant match) | Low-medium | LLM summarize + embedding |

Key difference: **Summary** overwrites its summary each cycle (linear, lossy). **Retrieval Summary** stores multiple summaries and selectively retrieves only the relevant ones per question.

### Trade-offs & When to Use Each

**Buffer** is the right default for short conversations — it's simple, lossless, and requires zero extra infrastructure. But in a product like Valkai where agents interact with users for hours across sessions, token costs scale linearly and you'll eventually hit context limits. It's a baseline, not a production strategy.

**Window** is the cheapest option and works well when only recent context matters (e.g., a quick troubleshooting flow). But it's fundamentally incompatible with learning about users — anything outside the window is permanently gone. For Valkai's goal of building user profiles over time, window memory on its own is insufficient.

**Summary** is a practical middle ground: it preserves the gist of the full conversation within a bounded token budget. The trade-off is lossiness — the LLM summarizer may paraphrase away specific facts (names, preferences, numbers) that matter for personalization. It's a good fit when you need general awareness of history but don't need exact recall of early details.

**Retrieval Summary** is the most sophisticated strategy and the best fit for Valkai's core requirements. By accumulating multiple summaries and retrieving only the relevant ones per query, it can recall old facts without paying the token cost of full history. The key insight: it separates *storage* (all summaries kept) from *retrieval* (only relevant ones injected). This pattern scales to cross-session memory — summaries from prior sessions can be stored and retrieved the same way, enabling the "learn about specific users" goal. The cost is complexity: it requires an embedding model, adds latency from summarization + embedding, and retrieval quality depends on both the summarizer and the embedder.

For a production system at Valkai, the ideal approach would likely combine strategies — retrieval summary for long-term user memory with a buffer or window for the current session's immediate context.

## Comparison Harness

Run the same 8-turn scripted conversation through all 4 strategies and compare recall:

```bash
uv run python -m harness.run_comparison

# Skip retrieval strategy (faster, no embedding model download)
uv run python -m harness.run_comparison --skip-retrieval
```

The harness shares facts in turns 1-2, sends filler in turns 3-6, then tests recall in turns 7-8.

## Running evals

```bash
uv run pytest evals/ -v
```

Evals include both unit tests (mocked, no API calls) and integration tests (real LLM calls).

## Supported providers

| Provider  | Model string example                          | Required env var       |
|-----------|-----------------------------------------------|------------------------|
| Anthropic | `anthropic:claude-haiku-4-5-20251001` (default) | `ANTHROPIC_API_KEY`    |
| OpenAI    | `openai:gpt-4o`                               | `OPENAI_API_KEY`       |
| Google    | `google_genai:gemini-2.5-flash`               | `GOOGLE_API_KEY`       |

Any model supported by LangChain's [`init_chat_model`](https://docs.langchain.com/oss/python/langchain/models) works — just pass the `provider:model` string.

## Project structure

```
take-home/
├── pyproject.toml          # uv project config, dependencies
├── .env.example            # API key template
├── DESIGN.md               # Architecture & trade-off analysis
├── src/
│   └── agent/
│       ├── core.py         # Agent factory (create_deep_agent wrapper)
│       ├── cli.py          # Interactive chat REPL with --memory flag
│       └── memory/
│           ├── base.py     # Abstract MemoryStrategy interface
│           ├── buffer.py   # Full history (baseline)
│           ├── window.py   # Sliding window (last k messages)
│           ├── summary.py  # LLM-compressed running summary
│           └── retrieval.py # Accumulated summaries + semantic retrieval
├── harness/
│   └── run_comparison.py   # Scripted conversation, side-by-side comparison
└── evals/
    ├── test_agent.py       # Barebones agent evals
    └── test_memory.py      # Memory strategy unit + integration tests
```
