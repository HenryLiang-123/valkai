# take-home

CLI chat agent built on [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk-python). Memory strategies are exposed as tools (`save_memory` / `recall_memory`) that the agent autonomously decides when to call, rather than transparently managing conversation history behind the scenes.

## Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) package manager
- `ANTHROPIC_API_KEY` environment variable
- Claude Code CLI (`npm install -g @anthropic-ai/claude-code`)

## Quick start

```bash
git clone https://github.com/valkai-tech/take-home.git
cd take-home
uv sync
cp .env.example .env
# Fill in your ANTHROPIC_API_KEY in .env
```

## Usage

```bash
# Default (buffer memory)
uv run chat

# Choose a memory strategy
uv run chat --memory buffer      # Full history (default)
uv run chat --memory window      # Last 6 entries only
uv run chat --memory summary     # LLM-compressed running summary
uv run chat --memory retrieval   # Accumulated summaries + semantic retrieval
```

Type `quit` or `exit` to end the session.

## Memory Strategies

Each strategy is a backend for two tools the agent can call:

- **`save_memory(content)`** — store a fact, preference, or detail
- **`recall_memory(query)`** — retrieve previously stored information

The agent decides when to call these tools based on the conversation. The system prompt instructs it to save noteworthy facts immediately and recall memories before answering questions that might depend on earlier context.

| Strategy | save_memory behavior | recall_memory behavior | Recalls old facts? | Token cost | Extra calls |
|----------|---------------------|----------------------|-------------------|------------|-------------|
| **Buffer** | Append verbatim | Return all entries | Yes | Grows unbounded | None |
| **Window** | Append, keep last k | Return last k entries | No (evicted) | Fixed low | None |
| **Summary** | Append; after N saves, LLM-compress into running summary | Return summary + recent entries | Partially (lossy) | Medium | LLM summarize |
| **Retrieval Summary** | Append + embed; after N saves, LLM-compress + embed summary | Embed query, cosine-search top-k summaries | Yes (if relevant match) | Low-medium | LLM summarize + embedding |

Key difference: **Summary** overwrites its summary each cycle (linear, lossy). **Retrieval Summary** stores multiple summaries and selectively retrieves only the relevant ones per query.

### Trade-offs & When to Use Each

**Buffer** is the right default for short conversations — it's simple, lossless, and requires zero extra infrastructure. But in a product like Valkai where agents interact with users for hours across sessions, token costs scale linearly and you'll eventually hit context limits. It's a baseline, not a production strategy.

**Window** is the cheapest option and works well when only recent context matters (e.g., a quick troubleshooting flow). But it's fundamentally incompatible with learning about users — anything outside the window is permanently gone. For Valkai's goal of building user profiles over time, window memory on its own is insufficient.

**Summary** is a practical middle ground: it preserves the gist of the full conversation within a bounded token budget. The trade-off is lossiness — the LLM summarizer may paraphrase away specific facts (names, preferences, numbers) that matter for personalization. It's a good fit when you need general awareness of history but don't need exact recall of early details.

**Retrieval Summary** is the most sophisticated strategy and the best fit for Valkai's core requirements. By accumulating multiple summaries and retrieving only the relevant ones per query, it can recall old facts without paying the token cost of full history. The key insight: it separates *storage* (all summaries kept) from *retrieval* (only relevant ones injected). This pattern scales to cross-session memory — summaries from prior sessions can be stored and retrieved the same way, enabling the "learn about specific users" goal. The cost is complexity: it requires an embedding model, adds latency from summarization + embedding, and retrieval quality depends on both the summarizer and the embedder.

For a production system at Valkai, the ideal approach would likely combine strategies — retrieval summary for long-term user memory with a buffer or window for the current session's immediate context.

## Running evals

```bash
# Run all evals (makes real LLM + Agent SDK calls)
uv run pytest evals/ -v -s

# Run memory strategy evals only (shows granular tool call output)
uv run pytest evals/test_memory.py -v -s

# Run basic agent evals only
uv run pytest evals/test_agent.py -v -s
```

The `-s` flag prints granular tool call logs: for each turn, you'll see the user message, any `save_memory`/`recall_memory` calls the agent made (with arguments), and the agent's final response.

## Project structure

```
take-home/
├── pyproject.toml          # uv project config, dependencies
├── .env.example            # API key template
├── DESIGN.md               # Architecture & trade-off analysis
├── src/
│   └── agent/
│       ├── sdk_agent.py    # Claude Agent SDK agent loop + memory tools
│       ├── core.py         # Legacy LangChain agent factory (retained for reference)
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
    ├── test_agent.py       # Basic agent evals (Claude Agent SDK)
    └── test_memory.py      # Memory strategy unit + integration tests
```

## Why Claude Agent SDK over LangChain?

### Why we chose Claude Agent SDK

**Production safety & governance** — Claude Agent SDK has built-in permission modes (`acceptEdits`, default review mode) and tool-boundary hooks for observability. Security-first design means fewer accidental side effects. LangChain has no built-in permission model — tool execution is all-or-nothing. You'd need to bolt on custom middleware to gate tool calls, and there's no standard hook system for auditing what the agent did at tool boundaries.

**Minimal abstraction overhead** — Claude Agent SDK loads nothing unless you ask for it. LangChain pulls in a deep dependency tree — a fresh install brings `RunnableSequence`, `ChatPromptTemplate`, `AgentExecutor`, callback managers, and dozens of wrapper classes. Business logic becomes entangled with LangChain primitives, making it hard to extract or migrate later. The API also broke frequently across 0.x releases, creating an upgrade treadmill.

**Native tool orchestration** — MCP support, `@tool` decorator, and `create_sdk_mcp_server` make custom tools first-class citizens. The agent autonomously decides when to call tools. LangChain's tool system requires more ceremony — you define tools, then wire them into an `AgentExecutor` or `RunnableAgent` chain, configure output parsers, and handle the tool-calling loop yourself (or rely on LangGraph for the loop). The framework, not the model, drives the control flow.

**Session management** — `ClaudeSDKClient` maintains conversation context across turns with resume/fork support, ideal for the memory strategy experiments here. LangChain has no native session manager — you manually pass message lists into `.invoke()` each turn and manage history yourself (which is exactly what the old `MemoryStrategy` classes were doing).

**Same foundation as Claude Code** — battle-tested in Anthropic's own production agent; not a research prototype. LangChain's Deep Agents (their closest equivalent) launched more recently and is still establishing its production track record.

### Tradeoffs we accept

**Vendor lock-in** — Claude Agent SDK is optimized for Anthropic's Claude models. LangChain supports 200+ integrations across OpenAI, Google, local models, and niche providers. If multi-model flexibility were a requirement, LangChain would be the stronger choice.

**Smaller ecosystem** — LangChain's Python ecosystem is deeper for RAG pipelines, vector DB adapters, document loaders, and community recipes. For exotic data sources or complex retrieval patterns, LangChain has more off-the-shelf adapters.

**Less mature community** — LangChain has years of Stack Overflow answers, tutorials, and third-party tooling. Claude Agent SDK is newer (launched Sept 2025) with a smaller but growing community.
