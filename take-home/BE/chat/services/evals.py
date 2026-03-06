"""Service layer for running evals and the harness comparison from the UI."""

import asyncio
import json
import logging
import subprocess
import sys
from pathlib import Path

from agent.sdk_agent import run_conversation

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Harness comparison (adapted from harness/run_comparison.py for Agent SDK)
# ---------------------------------------------------------------------------

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


def _check_recall(response: str, expected: list[str]) -> tuple[bool, list[str]]:
    lower = response.lower()
    found = [kw for kw in expected if kw.lower() in lower]
    return len(found) == len(expected), found


async def _run_harness_strategy(strategy_name: str) -> dict:
    result = await run_conversation(strategy_name, SCRIPTED_TURNS)

    responses = [t.response for t in result.turns]
    tool_calls = []
    for i, t in enumerate(result.turns):
        for tc in t.tool_calls:
            tool_calls.append({"turn": i + 1, "tool": tc["tool"], "input": tc["input"]})

    t7_pass, t7_found = _check_recall(responses[6], RECALL_TURNS[6])
    t8_pass, t8_found = _check_recall(responses[7], RECALL_TURNS[7])

    return {
        "strategy": strategy_name,
        "recall": {
            "turn_7": {"pass": t7_pass, "expected": RECALL_TURNS[6], "found": t7_found},
            "turn_8": {"pass": t8_pass, "expected": RECALL_TURNS[7], "found": t8_found},
        },
        "responses": [
            {"turn": i + 1, "user": SCRIPTED_TURNS[i], "assistant": r}
            for i, r in enumerate(responses)
        ],
        "tool_calls": tool_calls,
    }


def run_harness(strategies: list[str] | None = None) -> dict:
    """Run the harness comparison across strategies. Returns structured results."""
    from agent.memory import MEMORY_STRATEGIES

    if strategies is None:
        strategies = [s for s in MEMORY_STRATEGIES if s != "retrieval"]

    async def _run():
        results = []
        for name in strategies:
            logger.info("Harness: running strategy %s", name)
            r = await _run_harness_strategy(name)
            results.append(r)
        return results

    results = asyncio.run(_run())
    return {"type": "harness", "strategies": strategies, "results": results}


# ---------------------------------------------------------------------------
# Pytest runner
# ---------------------------------------------------------------------------

BE_DIR = Path(__file__).resolve().parent.parent.parent  # take-home/BE


def run_tests(test_path: str = "evals/") -> dict:
    """Run pytest on the given path and return structured results."""
    cmd = [
        sys.executable, "-m", "pytest",
        test_path,
        "--tb=short",
        "-v",
        "--no-header",
        "-q",
    ]
    logger.info("Running tests: %s", " ".join(cmd))

    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(BE_DIR),
        timeout=300,
    )

    lines = proc.stdout.strip().splitlines()
    tests = []
    summary_line = ""

    for line in lines:
        line_stripped = line.strip()
        if "::" in line_stripped and (" PASSED" in line_stripped or " FAILED" in line_stripped or " ERROR" in line_stripped):
            parts = line_stripped.rsplit(" ", 1)
            test_id = parts[0].strip()
            status = parts[1].strip() if len(parts) > 1 else "UNKNOWN"
            tests.append({"test": test_id, "status": status})
        elif "passed" in line_stripped or "failed" in line_stripped or "error" in line_stripped:
            if not line_stripped.startswith("="):
                summary_line = line_stripped

    passed = sum(1 for t in tests if t["status"] == "PASSED")
    failed = sum(1 for t in tests if t["status"] == "FAILED")
    errored = sum(1 for t in tests if t["status"] == "ERROR")

    return {
        "type": "tests",
        "test_path": test_path,
        "exit_code": proc.returncode,
        "passed": passed,
        "failed": failed,
        "errored": errored,
        "tests": tests,
        "summary": summary_line,
        "stdout": proc.stdout,
        "stderr": proc.stderr if proc.returncode != 0 else "",
    }
