import argparse
import sys

from dotenv import load_dotenv

from agent.core import make_agent
from agent.memory import MEMORY_STRATEGIES


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="CLI Chat Agent")
    parser.add_argument(
        "--model",
        default="anthropic:claude-haiku-4-5-20251001",
        help="Model string, e.g. openai:gpt-4o, anthropic:claude-haiku-4-5-20251001, google_genai:gemini-2.5-flash",
    )
    parser.add_argument(
        "--system",
        default=None,
        help="Custom system prompt",
    )
    parser.add_argument(
        "--memory",
        default="buffer",
        choices=MEMORY_STRATEGIES.keys(),
        help="Memory strategy: buffer, window, summary, or retrieval",
    )
    args = parser.parse_args()

    agent = make_agent(args.model, args.system)
    memory = MEMORY_STRATEGIES[args.memory]()

    print(f"Chat started ({memory.describe()}). Type 'quit' to exit.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit"):
            break

        memory.add_user_message(user_input)
        result = agent.invoke({"messages": memory.get_messages()})
        ai_msg = result["messages"][-1]
        print(f"\nAssistant: {ai_msg.content}\n")
        memory.add_assistant_messages(result["messages"])


if __name__ == "__main__":
    main()
