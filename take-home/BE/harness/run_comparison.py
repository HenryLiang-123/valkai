"""Run the same 8-turn conversation through all memory strategies and compare recall."""

import sys
from dotenv import load_dotenv

from agent.core import make_agent
from agent.memory import MEMORY_STRATEGIES

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
    responses: list[str] = []
    for turn in SCRIPTED_TURNS:
        memory.add_user_message(turn)
        result = agent.invoke({"messages": memory.get_messages()})
        ai_msg = result["messages"][-1]
        content = ai_msg.content if hasattr(ai_msg, "content") else str(ai_msg)
        responses.append(content)
        memory.add_assistant_messages(result["messages"])
    return {"name": name, "description": memory.describe(), "responses": responses}


def check_recall(response: str, expected_keywords: list[str]) -> tuple[bool, list[str]]:
    """Check if response contains expected keywords (case-insensitive)."""
    lower = response.lower()
    found = [kw for kw in expected_keywords if kw.lower() in lower]
    return len(found) == len(expected_keywords), found


def main():
    load_dotenv()

    model_str = "anthropic:claude-haiku-4-5-20251001"
    agent = make_agent(model_str)

    # Skip retrieval by default if sentence-transformers is slow to load
    strategies_to_run = list(MEMORY_STRATEGIES.keys())
    if "--skip-retrieval" in sys.argv:
        strategies_to_run = [s for s in strategies_to_run if s != "retrieval"]

    results = []
    for name in strategies_to_run:
        strategy_cls = MEMORY_STRATEGIES[name]
        memory = strategy_cls()
        print(f"Running: {memory.describe()} ...")
        result = run_strategy(name, agent, memory)
        results.append(result)
        print(f"  Done.\n")

    # --- Print comparison ---
    print("=" * 70)
    print("RECALL COMPARISON")
    print("=" * 70)

    header = f"{'Strategy':<30} {'Turn 7 (name+lang)':<20} {'Turn 8 (job)':<20}"
    print(header)
    print("-" * 70)

    for r in results:
        t7_pass, t7_found = check_recall(r["responses"][6], RECALL_TURNS[6])
        t8_pass, t8_found = check_recall(r["responses"][7], RECALL_TURNS[7])

        t7_status = "PASS" if t7_pass else f"FAIL (found: {t7_found})"
        t8_status = "PASS" if t8_pass else f"FAIL (found: {t8_found})"

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
