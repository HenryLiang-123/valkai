import uuid

from django.db import models

STRATEGY_CHOICES = [
    ("buffer", "Buffer"),
    ("window", "Window"),
    ("summary", "Summary"),
    ("retrieval", "Retrieval"),
]

MESSAGE_TYPE_CHOICES = [
    ("chat_message", "Chat Message"),
    ("tool_use", "Tool Use"),
]


class ChatSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    strategy = models.CharField(max_length=20, choices=STRATEGY_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.strategy} — {self.id}"


class ChatMessage(models.Model):
    session = models.ForeignKey(
        ChatSession, on_delete=models.CASCADE, related_name="messages"
    )
    role = models.CharField(max_length=20)  # "user", "assistant"
    message_type = models.CharField(
        max_length=20, choices=MESSAGE_TYPE_CHOICES, default="chat_message"
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"[{self.role}] {self.content[:50]}"


EVAL_TYPE_CHOICES = [
    ("harness", "Harness"),
    ("agent_sdk", "Agent SDK"),
    ("tests", "Tests"),
]


class EvalRun(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    eval_type = models.CharField(max_length=20, choices=EVAL_TYPE_CHOICES)
    result = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.eval_type} — {self.created_at}"
