# Design Document: Implementing and Comparing Memory Types

## Goal

Build a conversational agent that supports multiple swappable memory strategies, then demonstrate and compare how each affects context recall. Directly addresses Valkai's need for agents that "learn about specific users and learn patterns across users."

---

## Memory Strategies to Implement

### 1. Buffer Memory (Baseline)
- **What it does:** Stores and replays the entire conversation history on every turn.
- **How:** Pass the full `messages` list to `agent.invoke()` — this is what the starter code already does.
- **Strengths:** Perfect recall. Zero information loss.
- **Weaknesses:** Token usage grows linearly. Will hit context limits on long conversations.
- **Effort:** Wrap existing behavior in the `MemoryStrategy` interface. ~20 lines.

### 2. Window Memory (Sliding Window)
- **What it does:** Only keeps the last *k* messages (default: 6). Older messages are dropped.
- **How:** Slice `messages[-k:]` before passing to the agent.
- **Strengths:** Bounded token usage. Simple, predictable.
- **Weaknesses:** Total amnesia for anything outside the window. Fails recall tests for early-conversation facts.
- **Effort:** ~25 lines.

### 3. Summary Memory (LLM-Compressed)
- **What it does:** After every *n* user turns, calls the LLM to compress the full history into a summary paragraph. Prepends the summary as a system message and keeps only the most recent messages verbatim.
- **How:** Maintain a `_summary` string. Every *n* turns, format the conversation and call `model.invoke(SUMMARIZE_PROMPT)`. Inject the summary as `{"role": "system", "content": "Summary of earlier conversation: ..."}` before the recent messages.
- **Strengths:** Retains the gist of the full conversation within bounded tokens.
- **Weaknesses:** Lossy — specific details (names, numbers) may be paraphrased away. Adds latency and cost from the summarization call.
- **Effort:** ~60 lines. Requires an LLM call for compression.

### 4. Retrieval Summary Memory (Accumulated Summaries + Semantic Retrieval)
- **What it does:** Every *n* turns, LLM-compresses the recent conversation chunk into a summary and **appends** it to a list of stored summaries (not overwritten like Summary Memory). On each new user message, embeds the query and all stored summaries, ranks by cosine similarity, and injects only the top-k most relevant summaries into context.
- **How:** Uses `sentence-transformers` (`all-MiniLM-L6-v2`) for embedding and `numpy` for cosine similarity. All in-memory, no external vector DB.
- **Strengths:** Can recall old facts if they appear in a stored summary that matches the current question. Token usage stays bounded. Scales better than buffer for long conversations.
- **Weaknesses:** Retrieval quality depends on embedding model and summary quality. Adds latency from summarization + embedding. More complex to implement.
- **Effort:** ~110 lines. Requires LLM call for summarization + sentence-transformers for embedding.

---

## Architecture

### Module Structure
```
src/agent/
    memory/
        __init__.py      # Registry: {"buffer": BufferMemory, "window": WindowMemory, ...}
        base.py          # Abstract MemoryStrategy with get_messages(), add_user_message(), add_assistant_messages()
        buffer.py
        window.py
        summary.py
        retrieval.py
    core.py              # Updated: make_agent() unchanged, memory is handled at the CLI/harness layer
    cli.py               # Updated: add --memory flag, wire memory strategy into the REPL loop
harness/
    run_comparison.py    # Scripted conversation, runs all 4 strategies, prints side-by-side results
evals/
    test_agent.py        # Existing tests (unchanged)
    test_memory.py       # New: memory-specific eval tests
```

### MemoryStrategy Interface
```python
class MemoryStrategy(ABC):
    def get_messages(self) -> list[dict]          # Messages to send to the agent
    def add_user_message(self, content: str)      # Record user input
    def add_assistant_messages(self, messages)     # Record agent response (full message list)
    def describe(self) -> str                     # Human-readable name
```

### Integration Point
Memory lives *outside* the agent. The CLI loop becomes:
```python
memory = MEMORY_STRATEGIES[args.memory]()
while True:
    user_input = input("You: ")
    memory.add_user_message(user_input)
    result = agent.invoke({"messages": memory.get_messages()})
    memory.add_assistant_messages(result["messages"])
    print(result["messages"][-1].content)
```

This keeps `make_agent()` unchanged and memory fully swappable.

---

## Comparison Harness

### Scripted Conversation (8 turns)
| Turn | Message | Tests |
|------|---------|-------|
| 1 | "My name is Henry and I'm a backend engineer." | Fact introduction |
| 2 | "I prefer TypeScript over Python for APIs." | Preference statement |
| 3 | "What's the weather like today?" | Unrelated filler |
| 4 | "Tell me a joke." | More filler to push window |
| 5 | "Can you recommend a book?" | More filler |
| 6 | "What's 2 + 2?" | More filler |
| 7 | "What's my name and what language do I prefer?" | **Recall test** |
| 8 | "What do I do for work?" | **Recall test** |

### Expected Results
| Strategy | Turn 7 Recall | Turn 8 Recall | Token Usage |
|----------|--------------|--------------|-------------|
| Buffer | Full recall | Full recall | High (grows) |
| Window (k=6) | Fails (turns 1-2 dropped) | Fails | Bounded low |
| Summary | Likely recalls gist | Likely partial | Medium |
| Retrieval Summary | Yes (if relevant match) | Yes (if relevant match) | Low-medium + embedding cost |

### Harness Output
The script runs all 4 strategies against the same conversation, then prints:
1. Each strategy's responses to the recall turns (7 and 8)
2. A summary table showing pass/fail for each recall question
3. Approximate token counts per strategy

---

## Implementation Steps

1. **Create `memory/base.py`** — abstract interface (done)
2. **Create `memory/buffer.py`** — wrap existing behavior
3. **Create `memory/window.py`** — add slicing logic
4. **Create `memory/summary.py`** — add LLM summarization call
5. **Create `memory/retrieval.py`** — add LLM summarization + sentence-transformers embedding + cosine retrieval
6. **Create `memory/__init__.py`** — strategy registry
7. **Update `cli.py`** — add `--memory` arg, wire into REPL
8. **Create `harness/run_comparison.py`** — scripted conversation + comparison output
9. **Create `evals/test_memory.py`** — automated recall tests per strategy
10. **Write `README.md`** — setup instructions, usage, trade-off summary

---

## Key Design Decisions

- **Memory is external to the agent.** The agent itself is stateless — memory strategies control what messages it sees. This makes strategies trivially swappable.
- **Summary and Retrieval Summary use a cheap model for side-calls.** Haiku for summarization keeps costs low while the main conversation can use any model.
- **The harness is deterministic.** Same conversation, same order, all strategies. Makes comparison fair and reproducible.
