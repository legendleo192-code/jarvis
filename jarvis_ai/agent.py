from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Callable

from .openrouter import ChatMessage, OpenRouterClient
from .tools import ToolRegistry


SYSTEM_PROMPT = """You are JARVIS, an advanced AI command assistant.

Behavior:
- Understand Hindi, Hinglish, and English. Reply in the user's language/style.
- Be direct, capable, and practical: plan, execute with tools, verify, then answer.
- When a tool can complete the user's request, use it instead of only explaining.
- Never claim a tool result unless it appears in the conversation.
- Ask a short clarification only when the request is unsafe or impossible without missing information.

Tool protocol:
- To use a tool, respond with only strict JSON: {{"tool":"tool_name","args":{{...}}}}
- After a tool result, either call another tool or provide the final user-facing answer.
- Do not wrap tool JSON in markdown.

Available tools:
{tools}
"""


@dataclass
class AgentResult:
    answer: str
    messages: list[ChatMessage] = field(default_factory=list)
    tool_calls: int = 0


class JarvisAgent:
    def __init__(
        self,
        client: OpenRouterClient,
        tools: ToolRegistry,
        approval_callback: Callable[[str, dict], bool] | None = None,
        max_tool_rounds: int = 8,
    ) -> None:
        self.client = client
        self.tools = tools
        self.approval_callback = approval_callback
        self.max_tool_rounds = max_tool_rounds

    def run(self, user_text: str, history: list[ChatMessage] | None = None) -> AgentResult:
        messages = list(history or [])
        if not messages or messages[0].get("role") != "system":
            messages.insert(
                0,
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT.format(tools=self.tools.describe()),
                },
            )

        messages.append({"role": "user", "content": user_text})
        tool_calls = 0

        for _ in range(self.max_tool_rounds + 1):
            assistant_text = self.client.chat(messages)
            messages.append({"role": "assistant", "content": assistant_text})

            tool_call = parse_tool_call(assistant_text)
            if tool_call is None:
                return AgentResult(answer=assistant_text.strip(), messages=messages, tool_calls=tool_calls)

            tool_name, args = tool_call
            if not self.tools.has(tool_name):
                messages.append(
                    {
                        "role": "user",
                        "content": f"Tool result for {tool_name}: ERROR unknown tool. Use one of: {', '.join(self.tools.names())}",
                    }
                )
                continue

            if self.tools.requires_approval(tool_name, args):
                approved = self.approval_callback(tool_name, args) if self.approval_callback else False
                if not approved:
                    messages.append(
                        {
                            "role": "user",
                            "content": f"Tool result for {tool_name}: DENIED by user. Explain what you need or choose a safer option.",
                        }
                    )
                    continue

            result = self.tools.run(tool_name, args)
            tool_calls += 1
            messages.append(
                {
                    "role": "user",
                    "content": f"Tool result for {tool_name}:\n{result}",
                }
            )

        return AgentResult(
            answer="Tool limit hit ho gaya. Main yahin ruk raha hoon taaki loop na chale. Last results check karke command ko thoda specific karke dobara bhejo.",
            messages=messages,
            tool_calls=tool_calls,
        )


def parse_tool_call(text: str) -> tuple[str, dict] | None:
    raw = text.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", raw, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        raw = fenced.group(1).strip()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None

    if not isinstance(parsed, dict):
        return None
    tool = parsed.get("tool")
    args = parsed.get("args", {})
    if not isinstance(tool, str) or not isinstance(args, dict):
        return None
    return tool, args
