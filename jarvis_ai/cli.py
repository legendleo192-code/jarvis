from __future__ import annotations

import argparse
import os
import sys

from .agent import JarvisAgent
from .openrouter import OpenRouterClient
from .tools import ToolRegistry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="OpenRouter-powered JARVIS assistant")
    parser.add_argument("--model", default=os.getenv("OPENROUTER_MODEL", "openrouter/auto"))
    parser.add_argument("--once", help="Run a single command and exit")
    parser.add_argument("--auto-approve", action="store_true", default=os.getenv("JARVIS_AUTO_APPROVE") == "1")
    parser.add_argument("--workspace", default=os.getenv("JARVIS_WORKSPACE", os.getcwd()))
    parser.add_argument("--memory-file", default=os.getenv("JARVIS_MEMORY_FILE"))
    args = parser.parse_args(argv)

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("OPENROUTER_API_KEY missing hai. Pehle export OPENROUTER_API_KEY='...' set karo.", file=sys.stderr)
        return 2

    tools = ToolRegistry(workspace=args.workspace, memory_file=args.memory_file, auto_approve=args.auto_approve)
    client = OpenRouterClient(api_key=api_key, model=args.model)
    agent = JarvisAgent(client=client, tools=tools, approval_callback=_approval(args.auto_approve))

    if args.once:
        result = agent.run(args.once)
        print(result.answer)
        return 0

    print(f"JARVIS online. Brain: {args.model}. Workspace: {tools.workspace}")
    print("Type 'exit' to quit.")
    history = None
    while True:
        try:
            user_text = input("You> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nJARVIS offline.")
            return 0
        if user_text.lower() in {"exit", "quit", "bye"}:
            print("JARVIS offline.")
            return 0
        if not user_text:
            continue
        result = agent.run(user_text, history=history)
        history = result.messages
        print(f"JARVIS> {result.answer}")


def _approval(auto_approve: bool):
    def approve(tool_name: str, args: dict) -> bool:
        if auto_approve:
            return True
        print(f"\nJARVIS wants to run tool: {tool_name}")
        print(args)
        answer = input("Approve? [y/N] ").strip().lower()
        return answer in {"y", "yes", "haan", "ha"}

    return approve
