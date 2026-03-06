"""Agent loop using Claude Agent SDK with tool-based memory strategies.

The recall_memory tool is exposed to the agent so it can autonomously decide
when to retrieve conversation context. Each memory strategy reads directly
from the DB via a message-fetching callable.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    create_sdk_mcp_server,
    tool,
)

from agent.memory import MEMORY_STRATEGIES
from agent.memory.base import MemoryStrategy

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tool creation
# ---------------------------------------------------------------------------


def create_recall_tool(strategy: MemoryStrategy, fetch_messages: Callable[[], list[dict]]):
    """Create a recall_memory tool backed by the given strategy and DB fetcher.

    For retrieval-based strategies the tool accepts a ``query`` input so
    the agent can specify what to search for.  For simpler strategies
    (buffer, window, summary) no input is needed.
    """
    from agent.memory.retrieval import RetrievalSummaryMemory

    if isinstance(strategy, RetrievalSummaryMemory):
        @tool(
            "recall_memory",
            "Search conversation memory for relevant context. "
            "Provide a query describing what information you need.",
            {"query": {"type": "string", "description": "What to search for in memory"}},
        )
        async def recall_memory_retrieval(args: dict[str, Any]) -> dict[str, Any]:
            query = args.get("query", "")
            logger.info("recall_memory tool invoked (strategy=%s, query=%r)", type(strategy).__name__, query)
            try:
                result = await asyncio.to_thread(strategy.recall, fetch_messages, query)
                logger.info("recall_memory returned %d chars: %s", len(result), result)
            except Exception as e:
                logger.exception(f"recall_memory failed {e}")
                result = "Error retrieving memories."
            return {"content": [{"type": "text", "text": result}]}

        return recall_memory_retrieval
    else:
        @tool(
            "recall_memory",
            "Retrieve the conversation history from memory. "
            "Call this when you need to answer a question that may depend on earlier context.",
            {},
        )
        async def recall_memory(_args: dict[str, Any]) -> dict[str, Any]:
            logger.info("recall_memory tool invoked (strategy=%s)", type(strategy).__name__)
            try:
                result = await asyncio.to_thread(strategy.recall, fetch_messages)
                logger.info("recall_memory returned %d chars: %s", len(result), result)
            except Exception as e:
                logger.exception(f"recall_memory failed {e}")
                result = "Error retrieving memories."
            return {"content": [{"type": "text", "text": result}]}

        return recall_memory


# ---------------------------------------------------------------------------
# Single-turn send (used by the Django views)
# ---------------------------------------------------------------------------


async def send_message(
    strategy: MemoryStrategy,
    fetch_messages: Callable[[], list[dict]],
    user_message: str,
    session_id: str,
    on_event: Callable[[dict[str, Any]], Any] | None = None,
) -> list[dict[str, Any]]:
    """Send a single user message through the agent and return typed events.

    If *on_event* is provided it is called immediately for every event
    (tool_use, chat_message) as it is produced — useful for persisting
    each message to the DB in real time.

    Returns the full list of events for convenience.
    """
    events: list[dict[str, Any]] = []

    async def _collect(event: dict[str, Any]) -> None:
        events.append(event)
        if on_event is not None:
            result = on_event(event)
            if hasattr(result, "__await__"):
                await result

    recall_tool = create_recall_tool(strategy, fetch_messages)

    server = create_sdk_mcp_server(
        name="memory",
        version="1.0.0",
        tools=[recall_tool],
    )

    options = ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        mcp_servers={"memory": server},
        allowed_tools=["mcp__memory__recall_memory"],
        permission_mode="bypassPermissions",
        model="claude-haiku-4-5-20251001",
        max_turns=10,
    )

    logger.info("send_message: starting SDK client for session=%s", session_id)
    async with ClaudeSDKClient(options=options) as client:
        await client.query(user_message, session_id=session_id)
        logger.info("send_message: query sent, awaiting response")

        response_text = ""
        pending_tools: dict[str, dict[str, Any]] = {}
        async for message in client.receive_response():
            logger.info("send_message: received message type=%s", type(message).__name__)
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        response_text = block.text
                    elif isinstance(block, ToolUseBlock):
                        logger.info("Tool use block: session=%s tool=%s input=%s", session_id, block.name, block.input)
                        tc_event = {"type": "tool_use", "content": block.name, "input": block.input, "result": None}
                        pending_tools[block.id] = tc_event
                        await _collect(tc_event)
                    elif isinstance(block, ToolResultBlock):
                        tc_event = pending_tools.get(block.tool_use_id)
                        if tc_event is not None:
                            if isinstance(block.content, str):
                                tc_event["result"] = block.content
                            elif isinstance(block.content, list):
                                texts = [
                                    c["text"] for c in block.content
                                    if isinstance(c, dict) and c.get("type") == "text"
                                ]
                                tc_event["result"] = "\n".join(texts) if texts else None

    await _collect({"type": "chat_message", "content": response_text})
    return events


# ---------------------------------------------------------------------------
# Conversation runner
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You are a helpful assistant with a memory tool. "
    "Use recall_memory to retrieve the conversation history when you need it to answer a question. "
    "Always recall memories before answering questions that might depend on earlier context."
)


@dataclass
class ToolCallResult:
    tool: str
    input: dict[str, Any]
    result: str | None = None


@dataclass
class TurnResult:
    user_message: str
    response: str
    tool_calls: list[ToolCallResult] = field(default_factory=list)


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

    Each user message is sent as a turn. The agent can call recall_memory
    between turns. Returns structured results with tool call logs.

    Note: this runner uses an in-memory message list (not the DB) for the
    fetch_messages callable, suitable for evals and CLI usage.
    """
    strategy_cls = MEMORY_STRATEGIES[strategy_name]
    strategy = strategy_cls()

    # In-memory message store for non-Django contexts (evals, CLI)
    conversation_log: list[dict] = []

    def fetch_messages() -> list[dict]:
        return list(conversation_log)

    recall_tool = create_recall_tool(strategy, fetch_messages)

    server = create_sdk_mcp_server(
        name="memory",
        version="1.0.0",
        tools=[recall_tool],
    )

    options = ClaudeAgentOptions(
        system_prompt=system_prompt,
        mcp_servers={"memory": server},
        allowed_tools=["mcp__memory__recall_memory"],
        permission_mode="bypassPermissions",
        model="claude-haiku-4-5-20251001",
        max_turns=10,
    )

    result = ConversationResult(strategy=strategy_name)

    async with ClaudeSDKClient(options=options) as client:
        for user_msg in messages:
            turn = TurnResult(user_message=user_msg, response="")

            conversation_log.append({
                "role": "user",
                "message_type": "chat_message",
                "content": user_msg,
            })

            await client.query(user_msg)

            # Track pending tool calls by id so we can attach results
            pending_tools: dict[str, ToolCallResult] = {}

            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            turn.response = block.text
                        elif isinstance(block, ToolUseBlock):
                            tc = ToolCallResult(tool=block.name, input=block.input)
                            pending_tools[block.id] = tc
                            turn.tool_calls.append(tc)
                        elif isinstance(block, ToolResultBlock):
                            tc = pending_tools.get(block.tool_use_id)
                            if tc is not None:
                                if isinstance(block.content, str):
                                    tc.result = block.content
                                elif isinstance(block.content, list):
                                    texts = [
                                        c["text"] for c in block.content
                                        if isinstance(c, dict) and c.get("type") == "text"
                                    ]
                                    tc.result = "\n".join(texts) if texts else None

            conversation_log.append({
                "role": "assistant",
                "message_type": "chat_message",
                "content": turn.response,
            })

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
                print(f"  Tool: {tc.tool}({tc.input})")
                if tc.result:
                    print(f"  Result: {tc.result[:200]}")
        print(f"  Response: {turn.response[:200]}")
