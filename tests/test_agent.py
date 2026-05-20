import unittest

from jarvis_ai.agent import JarvisAgent, parse_tool_call
from jarvis_ai.tools import ToolRegistry


class FakeClient:
    def __init__(self):
        self.calls = 0

    def chat(self, messages):
        self.calls += 1
        if self.calls == 1:
            return '{"tool":"now","args":{}}'
        return "Time check ho gaya."


class ParseToolCallTest(unittest.TestCase):
    def test_parses_raw_json_tool_call(self):
        self.assertEqual(
            parse_tool_call('{"tool":"now","args":{}}'),
            ("now", {}),
        )

    def test_parses_fenced_json_tool_call(self):
        self.assertEqual(
            parse_tool_call('```json\n{"tool":"read_file","args":{"path":"README.md"}}\n```'),
            ("read_file", {"path": "README.md"}),
        )

    def test_ignores_normal_text(self):
        self.assertIsNone(parse_tool_call("Kaam ho gaya."))

    def test_agent_runs_tool_loop(self):
        tools = ToolRegistry(workspace=".", auto_approve=True)
        result = JarvisAgent(client=FakeClient(), tools=tools).run("time batao")
        self.assertEqual(result.answer, "Time check ho gaya.")
        self.assertEqual(result.tool_calls, 1)


if __name__ == "__main__":
    unittest.main()
