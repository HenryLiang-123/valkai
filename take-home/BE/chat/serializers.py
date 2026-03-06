from __future__ import annotations

from dataclasses import dataclass


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

    def to_dict(self) -> dict:
        return {"type": self.type, "role": self.role, "tool_name": self.tool_name}


def serialize_message(role: str, message_type: str, content: str) -> dict:
    if message_type == "tool_use":
        return ToolUseMessageSchema(type="tool_use", role=role, tool_name=content).to_dict()
    return ChatMessageSchema(type="chat_message", role=role, text=content).to_dict()
