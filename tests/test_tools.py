import tempfile
import unittest
from pathlib import Path

from jarvis_ai.tools import ToolRegistry


class ToolRegistryTest(unittest.TestCase):
    def test_read_write_and_list_stay_inside_workspace(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tools = ToolRegistry(workspace=temp_dir, auto_approve=True)
            self.assertIn("Wrote note.txt", tools.run("write_file", {"path": "note.txt", "content": "hello"}))
            self.assertEqual(tools.run("read_file", {"path": "note.txt"}), "hello")
            self.assertIn("note.txt", tools.run("list_files", {}))

    def test_blocks_paths_outside_workspace(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tools = ToolRegistry(workspace=temp_dir, auto_approve=True)
            result = tools.run("read_file", {"path": "../secret.txt"})
            self.assertIn("workspace", result)

    def test_memory_persists(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            memory = Path(temp_dir) / "memory.json"
            tools = ToolRegistry(workspace=temp_dir, memory_file=str(memory), auto_approve=True)
            tools.run("remember", {"key": "name", "value": "Legend"})
            self.assertIn("Legend", tools.run("recall_memory", {}))


if __name__ == "__main__":
    unittest.main()
