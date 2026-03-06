"""Agent loop using Claude Agent SDK with tool-based memory strategies.

Each memory strategy is exposed as a pair of tools (save_memory / recall_memory)
that the agent autonomously decides when to call, rather than transparently
managing conversation history behind the scenes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    create_sdk_mcp_server,
    tool,
)

from agent.memory import MEMORY_STRATEGIES
from agent.memory.base import MemoryStrategy

# ---------------------------------------------------------------------------
# Adapter — wraps existing MemoryStrategy classes for the save/recall tool API
# ---------------------------------------------------------------------------

ACK = "Acknowledged."


class _StrategyAdapter:
    """Thin adapter that translates save/recall tool calls into the existing
    MemoryStrategy message-list interface.

    save(content)  -> feeds content as a user message + a synthetic assistant ack,
                      which may trigger the strategy's internal compression.
    recall(query)  -> feeds the query as a user message, reads back whatever the
                      strategy injects (summaries, windowed history, etc.), then
                      removes the temporary query message.
    """

    def __init__(self, strategy: MemoryStrategy):
        self._strategy = strategy

    def save(self, content: str) -> str:
        self._strategy.add_user_message(content)
        # Simulate an assistant acknowledgement so the strategy's turn counter
        # advances and compression triggers at the right cadence.
        msgs = self._strategy.get_messages()
        msgs.append({"role": "assistant", "content": ACK})
        self._strategy.add_assistant_messages(msgs)
        return f"Saved to memory."

    def recall(self, query: str) -> str:
        # Temporarily inject the query so retrieval-based strategies can embed it
        self._strategy.add_user_message(query)
        msgs = self._strategy.get_messages()
        # Remove the temporary query message we just added
        if hasattr(self._strategy, "_messages") and self._strategy._messages:
            self._strategy._messages.pop()
        # Pull out the strategy's injected context (system messages, recent history)
        parts = []
        for m in msgs:
            role = m["role"] if isinstance(m, dict) else getattr(m, "type", "")
            content = m["content"] if isinstance(m, dict) else getattr(m, "content", "")
            if role == "system":
                parts.append(content)
            elif role == "user" and content != query:
                parts.append(f"- {content}")
        return "\n\n".join(parts) if parts else "No memories stored yet."


def _make_backend(strategy_name: str) -> _StrategyAdapter:
    strategy_cls = MEMORY_STRATEGIES[strategy_name]
    return _StrategyAdapter(strategy_cls())


# ---------------------------------------------------------------------------
# Tool creation
# ---------------------------------------------------------------------------


def create_memory_tools(strategy_name: str):
    """Create save_memory and recall_memory tools backed by the given strategy."""
    backend = _make_backend(strategy_name)

    @tool(
        "save_memory",
        "Save an important fact, preference, or detail from the conversation to memory. "
        "Call this whenever the user shares personal information, preferences, or key facts.",
        {"content": str},
    )
    async def save_memory(args: dict[str, Any]) -> dict[str, Any]:
        result = backend.save(args["content"])
        return {"content": [{"type": "text", "text": result}]}

    @tool(
        "recall_memory",
        "Retrieve previously stored information from memory. "
        "Call this when you need to answer a question that may depend on earlier context.",
        {"query": str},
    )
    async def recall_memory(args: dict[str, Any]) -> dict[str, Any]:
        result = backend.recall(args["query"])
        return {"content": [{"type": "text", "text": result}]}

    return save_memory, recall_memory, backend


# ---------------------------------------------------------------------------
# Conversation runner
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You are a helpful assistant with memory tools. "
    "Use save_memory to store important facts, preferences, or details the user shares. "
    "Use recall_memory to retrieve previously stored information when you need it to answer a question. "
    "Always save noteworthy facts immediately when the user shares them. "
    "Always recall memories before answering questions that might depend on earlier context."
)


@dataclass
class TurnResult:
    user_message: str
    response: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ConversationResult:
    strategy: str
    turns: list[TurnResult] = field(default_factory=list)


async def run_conversation(
    strategy_name: str,
    messages: list[str],
    system_prompt: str = SYSTEM_PROMPT,
) -> ConversationResult:
    """Run a multi-turn conversation using the Claude Agent SDK with memory tools.

    Each user message is sent as a turn. The agent can call save_memory / recall_memory
    tools between turns. Returns structured results with tool call logs.
    """
    save_tool, recall_tool, _backend = create_memory_tools(strategy_name)

    server = create_sdk_mcp_server(
        name="memory",
        version="1.0.0",
        tools=[save_tool, recall_tool],
    )

    options = ClaudeAgentOptions(
        system_prompt=system_prompt,
        mcp_servers={"memory": server},
        allowed_tools=["mcp__memory__save_memory", "mcp__memory__recall_memory"],
        permission_mode="bypassPermissions",
        model="claude-haiku-4-5-20251001",
        max_turns=10,
    )

    result = ConversationResult(strategy=strategy_name)

    async with ClaudeSDKClient(options=options) as client:
        for user_msg in messages:
            turn = TurnResult(user_message=user_msg, response="")

            await client.query(user_msg)

            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            turn.response = block.text
                        elif isinstance(block, ToolUseBlock):
                            turn.tool_calls.append(
                                {
                                    "tool": block.name,
                                    "input": block.input,
                                }
                            )

            result.turns.append(turn)

    return result


def print_tool_calls(result: ConversationResult) -> None:
    """Print granular tool call log for a conversation."""
    print(f"\n{'='*60}")
    print(f"Strategy: {result.strategy}")
    print(f"{'='*60}")

    for i, turn in enumerate(result.turns):
        print(f"\n--- Turn {i + 1} ---")
        print(f"  User: {turn.user_message}")
        if turn.tool_calls:
            for tc in turn.tool_calls:
                print(f"  Tool: {tc['tool']}({tc['input']})")
        print(f"  Response: {turn.response[:200]}")
