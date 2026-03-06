# Valkai Take-Home: Memory-Augmented Chatbot

I'm interested in human-AI interaction, so beyond implementing the memory strategies themselves, I wanted to explore how the dynamic between a human and an AI changes when the AI has memory tools at its disposal. To that end, I built a chatbot using the Claude Agent SDK where the agent autonomously decides when to save and recall memories, and the user can observe and interact with that behavior in real time.

## Architecture

- **Backend** — Django + Claude Agent SDK. The agent is given `save_memory` and `recall_memory` as tools, backed by swappable memory strategies (buffer, window, summary, retrieval).
- **Frontend** — React/TypeScript chat UI that shows sessions, strategy selection, and tool-use visibility so you can see when the agent invokes its memory tools.
- **Evals** — pytest-based harness and Agent SDK harness for evaluating memory strategy quality across conversations.

## Memory Strategies

| Strategy | Description |
|----------|-------------|
| Buffer | Stores the full conversation history verbatim |
| Window | Keeps only the last *k* messages |
| Summary | Maintains a running summary of the conversation |
| Retrieval | Embeds messages and retrieves the most relevant via similarity search |

## Getting Started

```bash
# Setup (installs BE + FE dependencies)
./setup.sh

# Backend
cd BE
uv sync
uv run python manage.py runserver

# Frontend
cd FE
npm install
npm run dev
```

Requires `ANTHROPIC_API_KEY` in `BE/.env`.

## Running Evals

```bash
cd BE
uv run pytest evals/ -v -s
```

Or trigger evals from the UI, which persists results to the database.
