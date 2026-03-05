# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
uv sync

# Run the chat agent (default: Anthropic Claude Haiku)
uv run chat

# Run with a specific model
uv run chat --model openai:gpt-4o
uv run chat --model google_genai:gemini-2.5-flash
uv run chat --model anthropic:claude-haiku-4-5-20251001

# Run with a custom system prompt
uv run chat --system "You are a helpful coding assistant."

# Run evals (makes real LLM API calls)
uv run pytest evals/ -v

# Run a single eval file
uv run pytest evals/test_agent.py -v
```

## Architecture

This is a barebones CLI chat agent built on [LangChain Deep Agents](https://github.com/langchain-ai/deepagents). The entry point is `agent.cli:main`.

**Intended structure** (to be implemented):
```
src/agent/
    core.py     # Agent factory — wraps create_deep_agent from deepagents
    cli.py      # Interactive REPL — reads user input, streams agent responses, handles quit/exit
evals/
    test_agent.py  # pytest evals making real LLM calls
```

**Model string format:** `provider:model-name` (e.g. `anthropic:claude-haiku-4-5-20251001`). Parsed by LangChain's `init_chat_model`. Supported providers: `anthropic`, `openai`, `google_genai`.

**Environment:** API keys loaded from `.env` via `python-dotenv`. Copy `.env.example` to `.env` and fill in the relevant key(s).

**Package manager:** `uv` — use `uv run` to execute scripts, `uv sync` to install deps, `uv add` to add packages.
