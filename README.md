# Valkai Take-Home: Memory-Augmented Chatbot

Full-stack chat agent with swappable memory strategies, built on [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk-python). Memory is exposed as a `recall_memory` tool that the agent autonomously decides when to call, rather than transparently managing conversation history behind the scenes. Instead of running via CLI, the user can try out different memory saving methods via a natural-feeling chatbot.

I'm interested in human-AI interaction, so beyond implementing the memory strategies themselves, I wanted to explore how the dynamic between a human and an AI changes when the AI has memory tools at its disposal. The user can observe and interact with that behavior in real time.

## Architecture

- **Backend** — Django API that manages chat sessions and routes messages through the Claude Agent SDK agent. The agent is given `save_memory` and `recall_memory` as tools, backed by swappable memory strategies (buffer, window, summary, retrieval).
- **Frontend** — React/TypeScript (Vite) chat UI with session management sidebar, strategy selection, tool-use visibility, and an evals dashboard for running memory strategy comparisons.
- **Evals** — pytest-based harness and Agent SDK harness for evaluating memory strategy quality across conversations.

## Prerequisites

- Python 3.13+
- Node.js 22+ (managed via [mise](https://mise.jit.io/) if you use the setup script)
- [uv](https://docs.astral.sh/uv/) package manager
- `ANTHROPIC_API_KEY` environment variable (set in `take-home/BE/.env`)

## Quick start

The fastest way to get everything running:

```bash
cd take-home
./setup.sh          # installs mise, uv, node, all deps, runs DB migrations

mise run dev         # starts both BE and FE in parallel
```

This starts:
- **Backend** at http://localhost:8000
- **Frontend** at http://localhost:5173

## API endpoints

All endpoints are under `/api/`:

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/strategies` | List available memory strategies |
| GET | `/api/sessions/list` | List all chat sessions |
| POST | `/api/sessions` | Create a new session (`{"strategy": "buffer"}`) |
| GET | `/api/sessions/<id>/messages` | Get messages for a session |
| POST | `/api/sessions/<id>/send` | Send a message (`{"message": "..."}`) |
| POST | `/api/evals/run` | Run evals (`{"type": "harness"\|"agent_sdk"\|"tests"}`) |

## Running evals

Evals can be run from the frontend evals dashboard or via the command line:

```bash
cd take-home/BE

# Run all evals (makes real LLM + Agent SDK calls)
uv run pytest evals/ -v -s

# Run memory strategy evals only
uv run pytest evals/test_memory.py -v -s

# Run basic agent evals only
uv run pytest evals/test_agent.py -v -s
```

The `-s` flag prints granular tool call logs: for each turn you'll see the user message, any `recall_memory` calls the agent made (with arguments), and the agent's final response.

## Memory strategies

Each strategy backs a `recall_memory` tool the agent can call to retrieve conversation context. The agent decides when to use it based on the system prompt.

| Strategy | recall_memory behavior | Recalls old facts? | Token cost |
|----------|----------------------|-------------------|------------|
| **Buffer** | Return all messages | Yes | Grows unbounded |
| **Window** | Return last k messages | No (evicted) | Fixed low |
| **Summary** | Return LLM-compressed summary + recent messages | Partially (lossy) | Medium |
| **Retrieval** | Embed query, cosine-search stored summaries | Yes (if relevant match) | Low-medium |

Key difference: **Summary** overwrites its summary each cycle (linear, lossy). **Retrieval** stores multiple summaries and selectively retrieves only the relevant ones per query.

### Trade-offs

**Buffer** is the right default for short conversations — simple, lossless, zero extra infrastructure. But token costs scale linearly and will eventually hit context limits.

**Window** is cheapest and works when only recent context matters. Anything outside the window is permanently gone.

**Summary** preserves the gist of the full conversation within a bounded token budget. The trade-off is lossiness — the summarizer may paraphrase away specific facts.

**Retrieval** is the most sophisticated: it separates *storage* (all summaries kept) from *retrieval* (only relevant ones injected per query). This scales to cross-session memory. The cost is complexity: requires an embedding model and adds latency.

For a production system, the ideal approach would likely combine strategies — retrieval for long-term user memory with a buffer or window for the current session's immediate context.

## Project structure

```
take-home/
├── setup.sh                    # one-command setup script
├── mise.toml                   # task runner config (mise run dev)
├── BE/
│   ├── pyproject.toml          # uv project config, dependencies
│   ├── manage.py               # Django management
│   ├── chatproject/            # Django project settings & URL config
│   ├── chat/                   # Django app: models, views, services
│   │   ├── models.py           # ChatSession, ChatMessage
│   │   ├── views.py            # API endpoints
│   │   ├── serializers.py      # Response serialization
│   │   ├── services/           # Business logic (session, message, evals)
│   │   └── urls.py             # Route definitions
│   ├── agent/
│   │   ├── sdk_agent.py        # Claude Agent SDK agent loop + recall_memory tool
│   │   ├── cli.py              # Interactive chat REPL with --memory flag
│   │   ├── core.py             # Legacy LangChain agent factory (retained for reference)
│   │   └── memory/
│   │       ├── base.py         # Abstract MemoryStrategy interface
│   │       ├── buffer.py       # Full history (baseline)
│   │       ├── window.py       # Sliding window (last k messages)
│   │       ├── summary.py      # LLM-compressed running summary
│   │       └── retrieval.py    # Accumulated summaries + semantic retrieval
│   ├── evals/                  # Pytest-based eval suites
│   │   ├── test_agent.py       # Basic agent evals (Claude Agent SDK)
│   │   ├── test_memory.py      # Memory strategy unit + integration tests
│   │   └── test_integration.py # Integration tests
│   ├── harness/
│   │   └── run_comparison.py   # Scripted conversation, side-by-side comparison
│   └── DESIGN.md               # Architecture & trade-off analysis
├── FE/
│   ├── src/
│   │   ├── App.tsx             # Root component (sidebar + chat/evals)
│   │   ├── api.ts              # API client (sessions, messages, evals)
│   │   └── components/
│   │       ├── Chat.tsx        # Chat interface
│   │       ├── Sidebar.tsx     # Session list + new session creation
│   │       └── Evals.tsx       # Eval runner dashboard
│   ├── package.json
│   └── vite.config.ts
```

## Why Claude Agent SDK over LangChain?

**Production safety & governance** — built-in permission modes and tool-boundary hooks. LangChain has no built-in permission model.

**Minimal abstraction overhead** — loads nothing unless you ask for it. LangChain pulls a deep dependency tree and entangles business logic with framework primitives.

**Native tool orchestration** — MCP support, `@tool` decorator, and `create_sdk_mcp_server` make custom tools first-class. The agent autonomously decides when to call tools.

**Session management** — `ClaudeSDKClient` maintains conversation context across turns with resume/fork support.

### Tradeoffs we accept

- **Vendor lock-in** — optimized for Claude models only. LangChain supports 200+ integrations.
- **Smaller ecosystem** — LangChain has more off-the-shelf adapters for RAG, vector DBs, and document loaders.
- **Less mature community** — Claude Agent SDK is newer with a smaller community.
