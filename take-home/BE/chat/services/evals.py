"""Service layer for running evals and the harness comparison from the UI."""

import asyncio
import logging
import re
import subprocess
import sys
from pathlib import Path

from harness.run_comparison import run_comparison, SCRIPTED_TURNS, RECALL_TURNS, check_recall
from agent.sdk_agent import run_conversation
from agent.memory import MEMORY_STRATEGIES

logger = logging.getLogger(__name__)

BE_DIR = Path(__file__).resolve().parent.parent.parent  # take-home/BE

# ---------------------------------------------------------------------------
# Harness comparison — delegates to harness/run_comparison.py
# ---------------------------------------------------------------------------


def run_harness(strategies: list[str] | None = None) -> dict:
    """Run the harness comparison across strategies. Returns structured results."""
    raw = run_comparison(strategies_to_run=strategies, skip_retrieval=False)

    results = []
    for r in raw:
        results.append({
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

    return {"type": "harness", "results": results}


# ---------------------------------------------------------------------------
# Pytest runner
# ---------------------------------------------------------------------------


def run_tests(test_path: str = "evals/") -> dict:
    """Run pytest on the given path and return structured results."""
    cmd = [
        sys.executable, "-m", "pytest",
        test_path,
        "--tb=short",
        "-v",
        "--no-header",
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
        m = re.match(r'^(.+::.*?)\s+(PASSED|FAILED|ERROR)\s*', line_stripped)
        if m:
            tests.append({"test": m.group(1).strip(), "status": m.group(2)})
        elif line_stripped.startswith("=") and ("passed" in line_stripped or "failed" in line_stripped or "error" in line_stripped):
            summary_line = line_stripped.strip("= ")

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


# ---------------------------------------------------------------------------
# Agent SDK comparison — same scripted turns but via the SDK agent with tools
# ---------------------------------------------------------------------------


def run_agent_sdk_harness(strategies: list[str] | None = None) -> dict:
    """Run the scripted conversation through the Agent SDK agent with memory tools.

    Returns structured results with tool call info and recall checks.
    """
    if strategies is None:
        strategies = list(MEMORY_STRATEGIES.keys())

    async def _run_all():
        results = []
        for name in strategies:
            logger.info("[SDK harness] Starting strategy=%s", name)
            conv = await run_conversation(name, SCRIPTED_TURNS)
            # Extract responses and tool calls per turn
            turns = []
            for i, turn in enumerate(conv.turns):
                logger.info("[SDK harness] strategy=%s turn=%d user=%r", name, i + 1, turn.user_message)
                if turn.tool_calls:
                    logger.info("[SDK harness] strategy=%s turn=%d tool_calls=%s", name, i + 1, turn.tool_calls)
                logger.info("[SDK harness] strategy=%s turn=%d response=%r", name, i + 1, turn.response[:300])
                turns.append({
                    "turn": i + 1,
                    "user": turn.user_message,
                    "assistant": turn.response,
                    "tool_calls": turn.tool_calls,
                })

            # Check recall on turns 7 and 8 (indices 6 and 7)
            t7_pass, t7_found = check_recall(conv.turns[6].response, RECALL_TURNS[6])
            t8_pass, t8_found = check_recall(conv.turns[7].response, RECALL_TURNS[7])
            logger.info(
                "[SDK harness] strategy=%s recall: turn_7=%s turn_8=%s",
                name,
                "PASS" if t7_pass else f"FAIL (found: {t7_found})",
                "PASS" if t8_pass else f"FAIL (found: {t8_found})",
            )

            results.append({
                "strategy": name,
                "recall": {
                    "turn_7": {"passed": t7_pass, "expected": RECALL_TURNS[6], "found": t7_found},
                    "turn_8": {"passed": t8_pass, "expected": RECALL_TURNS[7], "found": t8_found},
                },
                "turns": turns,
            })
            logger.info("[SDK harness] Finished strategy=%s", name)
        return results

    loop = asyncio.new_event_loop()
    try:
        results = loop.run_until_complete(_run_all())
    finally:
        loop.close()

    return {"type": "agent_sdk", "results": results}
