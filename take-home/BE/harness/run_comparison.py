"""Run the same 8-turn conversation through all memory strategies and compare recall."""

import json
import logging
import sys
from dotenv import load_dotenv

from agent.core import make_agent
from agent.memory import MEMORY_STRATEGIES

logger = logging.getLogger(__name__)

SCRIPTED_TURNS = [
    "My name is Henry and I'm a backend engineer.",
    "I prefer TypeScript over Python for APIs.",
    "What's the weather like today?",
    "Tell me a joke.",
    "Can you recommend a book?",
    "What's 2 + 2?",
    "What's my name and what language do I prefer?",
    "What do I do for work?",
]

RECALL_TURNS = {6: ["Henry", "TypeScript"], 7: ["backend engineer"]}


def run_strategy(name: str, agent, memory) -> dict:
    """Run all scripted turns and return results."""
    conversation_log: list[dict] = []

    def fetch_messages() -> list[dict]:
        return list(conversation_log)

    logger.info("[LangChain harness] Starting strategy=%s (%s)", name, memory.describe())

    responses: list[str] = []
    for i, turn in enumerate(SCRIPTED_TURNS):
        conversation_log.append({"role": "user", "message_type": "chat_message", "content": turn})

        # Build messages: inject recall context as a system message + the user turn
        context = memory.recall(fetch_messages)
        logger.info("[LangChain harness] strategy=%s turn=%d user=%r", name, i + 1, turn)
        logger.info("[LangChain harness] strategy=%s turn=%d recall_context=%r", name, i + 1, context[:300] if context else "")
        messages = []
        if context and context != "No conversation history yet.":
            messages.append(("system", f"Conversation context:\n{context}"))
        messages.append(("human", turn))

        result = agent.invoke({"messages": messages})
        ai_msg = result["messages"][-1]
        content = ai_msg.content if hasattr(ai_msg, "content") else str(ai_msg)
        logger.info("[LangChain harness] strategy=%s turn=%d response=%r", name, i + 1, content[:300])
        responses.append(content)

        conversation_log.append({"role": "assistant", "message_type": "chat_message", "content": content})

    logger.info("[LangChain harness] Finished strategy=%s", name)
    return {"name": name, "description": memory.describe(), "responses": responses}


def check_recall(response: str, expected_keywords: list[str]) -> tuple[bool, list[str]]:
    """Check if response contains expected keywords (case-insensitive)."""
    lower = response.lower()
    found = [kw for kw in expected_keywords if kw.lower() in lower]
    return len(found) == len(expected_keywords), found


def run_comparison(strategies_to_run: list[str] | None = None, skip_retrieval: bool = False) -> list[dict]:
    """Run the harness comparison and return structured results.

    Each result dict has keys: name, description, responses,
    and added recall info: recall_turn_7, recall_turn_8.
    """
    load_dotenv()

    model_str = "anthropic:claude-haiku-4-5-20251001"
    agent = make_agent(model_str)

    if strategies_to_run is None:
        strategies_to_run = list(MEMORY_STRATEGIES.keys())
    if skip_retrieval:
        strategies_to_run = [s for s in strategies_to_run if s != "retrieval"]

    results = []
    for name in strategies_to_run:
        strategy_cls = MEMORY_STRATEGIES[name]
        memory = strategy_cls()
        result = run_strategy(name, agent, memory)

        t7_pass, t7_found = check_recall(result["responses"][6], RECALL_TURNS[6])
        t8_pass, t8_found = check_recall(result["responses"][7], RECALL_TURNS[7])
        result["recall_turn_7"] = {"passed": t7_pass, "expected": RECALL_TURNS[6], "found": t7_found}
        result["recall_turn_8"] = {"passed": t8_pass, "expected": RECALL_TURNS[7], "found": t8_found}

        results.append(result)

    return results


def main():
    skip_retrieval = "--skip-retrieval" in sys.argv
    results = run_comparison(skip_retrieval=skip_retrieval)

    if "--json" in sys.argv:
        out = []
        for r in results:
            out.append({
                "strategy": r["name"],
                "description": r["description"],
                "recall": {
                    "turn_7": r["recall_turn_7"],
                    "turn_8": r["recall_turn_8"],
                },
                "responses": [
                    {"turn": i + 1, "user": SCRIPTED_TURNS[i], "assistant": resp}
                    for i, resp in enumerate(r["responses"])
                ],
            })
        print(json.dumps({"type": "harness", "results": out}))
        return

    # --- Print comparison ---
    print("=" * 70)
    print("RECALL COMPARISON")
    print("=" * 70)

    header = f"{'Strategy':<30} {'Turn 7 (name+lang)':<20} {'Turn 8 (job)':<20}"
    print(header)
    print("-" * 70)

    for r in results:
        t7 = r["recall_turn_7"]
        t8 = r["recall_turn_8"]
        t7_status = "PASS" if t7["passed"] else f"FAIL (found: {t7['found']})"
        t8_status = "PASS" if t8["passed"] else f"FAIL (found: {t8['found']})"
        print(f"{r['description']:<30} {t7_status:<20} {t8_status:<20}")

    print()
    print("=" * 70)
    print("RECALL RESPONSES (Turns 7 & 8)")
    print("=" * 70)

    for r in results:
        print(f"\n--- {r['description']} ---")
        print(f"  Turn 7: {r['responses'][6][:200]}")
        print(f"  Turn 8: {r['responses'][7][:200]}")


if __name__ == "__main__":
    main()
