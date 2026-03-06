# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
uv sync

# Run the chat agent (default: buffer memory)
uv run chat

# Choose a memory strategy
uv run chat --memory buffer
uv run chat --memory window
uv run chat --memory summary
uv run chat --memory retrieval

# Run evals (makes real LLM + Agent SDK calls)
uv run pytest evals/ -v -s

# Run a single eval file
uv run pytest evals/test_agent.py -v -s
```

## Architecture

CLI chat agent built on [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk-python). Memory strategies are exposed as tools (`save_memory` / `recall_memory`) that the agent autonomously calls.

**Key files:**
```
src/agent/
    sdk_agent.py  # Claude Agent SDK agent loop + memory tool backends
    cli.py        # Interactive REPL with --memory flag
    core.py       # Legacy LangChain agent factory (retained for reference)
    memory/       # Original MemoryStrategy classes (used by unit tests)
evals/
    test_agent.py   # Basic agent evals (Claude Agent SDK)
    test_memory.py  # Memory strategy unit + integration tests
```

**Environment:** `ANTHROPIC_API_KEY` loaded from `.env` via `python-dotenv`.

**Package manager:** `uv` — use `uv run` to execute scripts, `uv sync` to install deps, `uv add` to add packages.
