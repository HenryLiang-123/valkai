import asyncio
import json

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from dotenv import load_dotenv

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    TextBlock,
    ToolUseBlock,
    create_sdk_mcp_server,
    tool,
)
from agent.memory import MEMORY_STRATEGIES
from agent.sdk_agent import SYSTEM_PROMPT, _StrategyAdapter

from .models import ChatMessage, ChatSession

load_dotenv()

# In-memory backend store keyed by session UUID (memory strategies are stateful
# Python objects that can't be serialised to DB, so we keep them in process).
_backends: dict[str, _StrategyAdapter] = {}


def _get_backend(session: ChatSession) -> _StrategyAdapter:
    key = str(session.id)
    if key not in _backends:
        strategy_cls = MEMORY_STRATEGIES[session.strategy]
        _backends[key] = _StrategyAdapter(strategy_cls())
    return _backends[key]


# ---------------------------------------------------------------------------
# GET /api/strategies — list available memory strategies
# ---------------------------------------------------------------------------

@require_GET
def strategies(request):
    data = [
        {"key": "buffer", "name": "Buffer", "description": "Keeps the full conversation history."},
        {"key": "window", "name": "Window", "description": "Retains only the most recent messages."},
        {"key": "summary", "name": "Summary", "description": "Compresses older messages into a summary."},
        {"key": "retrieval", "name": "Retrieval", "description": "Embeds and retrieves relevant memories."},
    ]
    return JsonResponse(data, safe=False)


# ---------------------------------------------------------------------------
# POST /api/sessions — create a new chat session
# ---------------------------------------------------------------------------

@csrf_exempt
@require_POST
def create_session(request):
    body = json.loads(request.body)
    strategy = body.get("strategy", "")

    if strategy not in MEMORY_STRATEGIES:
        return JsonResponse({"error": f"Invalid strategy: {strategy}"}, status=400)

    session = ChatSession.objects.create(strategy=strategy)
    return JsonResponse({
        "id": str(session.id),
        "strategy": session.strategy,
        "created_at": session.created_at.isoformat(),
    }, status=201)


# ---------------------------------------------------------------------------
# GET /api/sessions/<id>/messages — load persisted messages for a session
# ---------------------------------------------------------------------------

@require_GET
def session_messages(request, session_id):
    session = get_object_or_404(ChatSession, id=session_id)
    messages = session.messages.all().values(
        "id", "role", "message_type", "content", "created_at"
    )
    return JsonResponse({
        "session_id": str(session.id),
        "strategy": session.strategy,
        "messages": list(messages),
    })


# ---------------------------------------------------------------------------
# POST /api/sessions/<id>/send — send a message and get agent response
# ---------------------------------------------------------------------------

async def _send_message(session: ChatSession, user_message: str) -> list[dict]:
    """Send a message through the agent and return typed events."""
    backend = _get_backend(session)
    events = []
    sdk_session_id = str(session.id)

    @tool(
        "save_memory",
        "Save an important fact, preference, or detail from the conversation to memory. "
        "Call this whenever the user shares personal information, preferences, or key facts.",
        {"content": str},
    )
    async def save_memory(args: dict) -> dict:
        result = backend.save(args["content"])
        events.append({
            "type": "saved_memory",
            "content": args["content"],
        })
        return {"content": [{"type": "text", "text": result}]}

    @tool(
        "recall_memory",
        "Retrieve previously stored information from memory. "
        "Call this when you need to answer a question that may depend on earlier context.",
        {"query": str},
    )
    async def recall_memory(args: dict) -> dict:
        result = backend.recall(args["query"])
        return {"content": [{"type": "text", "text": result}]}

    server = create_sdk_mcp_server(
        name="memory",
        version="1.0.0",
        tools=[save_memory, recall_memory],
    )

    options = ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        mcp_servers={"memory": server},
        allowed_tools=["mcp__memory__save_memory", "mcp__memory__recall_memory"],
        permission_mode="bypassPermissions",
        model="claude-haiku-4-5-20251001",
        max_turns=10,
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query(user_message, session_id=sdk_session_id)

        response_text = ""
        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        response_text = block.text
                    elif isinstance(block, ToolUseBlock):
                        if block.name == "mcp__memory__save_memory":
                            content = block.input.get("content", "")
                            if content and not any(
                                e["type"] == "saved_memory" and e["content"] == content
                                for e in events
                            ):
                                events.append({
                                    "type": "saved_memory",
                                    "content": content,
                                })

    events.append({
        "type": "chat_message",
        "content": response_text,
    })

    return events


@csrf_exempt
@require_POST
def send(request, session_id):
    body = json.loads(request.body)
    user_message = body.get("message", "").strip()

    if not user_message:
        return JsonResponse({"error": "message is required"}, status=400)

    session = get_object_or_404(ChatSession, id=session_id)

    ChatMessage.objects.create(
        session=session,
        role="user",
        message_type="chat_message",
        content=user_message,
    )

    events = asyncio.run(_send_message(session, user_message))

    for event in events:
        ChatMessage.objects.create(
            session=session,
            role="assistant",
            message_type=event["type"],
            content=event["content"],
        )

    return JsonResponse({
        "session_id": str(session.id),
        "events": events,
    })
