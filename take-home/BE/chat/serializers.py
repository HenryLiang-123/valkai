from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from chat.models import EvalRun


# ---------------------------------------------------------------------------
# Chat message schemas
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ChatMessageSchema:
    type: str  # "chat_message"
    role: str
    text: str

    def to_dict(self) -> dict:
        return {"type": self.type, "role": self.role, "text": self.text}


@dataclass(frozen=True)
class ToolUseMessageSchema:
    type: str  # "tool_use"
    role: str
    tool_name: str
    input: dict | None = None
    result: str | None = None

    def to_dict(self) -> dict:
        d: dict = {"type": self.type, "role": self.role, "tool_name": self.tool_name}
        if self.input is not None:
            d["input"] = self.input
        if self.result is not None:
            d["result"] = self.result
        return d


def serialize_message(role: str, message_type: str, content: str, **extra) -> dict:
    if message_type == "tool_use":
        return ToolUseMessageSchema(
            type="tool_use",
            role=role,
            tool_name=content,
            input=extra.get("input"),
            result=extra.get("result"),
        ).to_dict()
    return ChatMessageSchema(type="chat_message", role=role, text=content).to_dict()


# ---------------------------------------------------------------------------
# Eval run schemas
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EvalRunSummarySchema:
    id: str
    eval_type: str
    created_at: str

    def to_dict(self) -> dict:
        return {"id": self.id, "eval_type": self.eval_type, "created_at": self.created_at}


@dataclass(frozen=True)
class EvalRunDetailSchema:
    run_id: str
    eval_type: str
    created_at: str
    result: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {**self.result, "run_id": self.run_id, "created_at": self.created_at}


def serialize_eval_run_summary(run: EvalRun) -> dict:
    return EvalRunSummarySchema(
        id=str(run.id),
        eval_type=run.eval_type,
        created_at=run.created_at.isoformat(),
    ).to_dict()


def serialize_eval_run_detail(run: EvalRun) -> dict:
    return EvalRunDetailSchema(
        run_id=str(run.id),
        eval_type=run.eval_type,
        created_at=run.created_at.isoformat(),
        result=run.result,
    ).to_dict()
