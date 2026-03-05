from agent.memory.base import MemoryStrategy
from agent.memory.buffer import BufferMemory
from agent.memory.window import WindowMemory
from agent.memory.summary import SummaryMemory
from agent.memory.retrieval import RetrievalSummaryMemory

MEMORY_STRATEGIES = {
    "buffer": BufferMemory,
    "window": WindowMemory,
    "summary": SummaryMemory,
    "retrieval": RetrievalSummaryMemory,
}

__all__ = [
    "MemoryStrategy",
    "BufferMemory",
    "WindowMemory",
    "SummaryMemory",
    "RetrievalSummaryMemory",
    "MEMORY_STRATEGIES",
]
