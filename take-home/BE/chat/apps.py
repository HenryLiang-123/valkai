from django.apps import AppConfig


class ChatConfig(AppConfig):
    name = "chat"

    def ready(self):
        import os

        if os.environ.get("RUN_MAIN") == "true":
            from agent.memory.retrieval import get_embedder

            get_embedder()
