from __future__ import annotations

import json
import shlex
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable


ToolHandler = Callable[[dict], str]


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    handler: ToolHandler
    needs_approval: bool = False


class ToolRegistry:
    def __init__(self, workspace: str, memory_file: str | None = None, auto_approve: bool = False) -> None:
        self.workspace = Path(workspace).expanduser().resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)
        default_memory = Path.home() / ".jarvis" / "memory.json"
        self.memory_file = Path(memory_file).expanduser().resolve() if memory_file else default_memory
        self.auto_approve = auto_approve
        self._tools = {
            "shell": Tool(
                name="shell",
                description="Run a shell command inside the workspace. Args: {command: string, timeout_seconds?: number}",
                handler=self._shell,
                needs_approval=True,
            ),
            "list_files": Tool(
                name="list_files",
                description="List files under a workspace-relative path. Args: {path?: string}",
                handler=self._list_files,
            ),
            "read_file": Tool(
                name="read_file",
                description="Read a UTF-8 text file from the workspace. Args: {path: string, max_chars?: number}",
                handler=self._read_file,
            ),
            "write_file": Tool(
                name="write_file",
                description="Write a UTF-8 text file under the workspace. Args: {path: string, content: string}",
                handler=self._write_file,
                needs_approval=True,
            ),
            "remember": Tool(
                name="remember",
                description="Store a memory fact for future sessions. Args: {key: string, value: string}",
                handler=self._remember,
            ),
            "recall_memory": Tool(
                name="recall_memory",
                description="Read all stored memory facts. Args: {}",
                handler=self._recall_memory,
            ),
            "now": Tool(
                name="now",
                description="Get current local date and time. Args: {}",
                handler=self._now,
            ),
        }

    def describe(self) -> str:
        return "\n".join(f"- {tool.name}: {tool.description}" for tool in self._tools.values())

    def names(self) -> list[str]:
        return sorted(self._tools)

    def has(self, name: str) -> bool:
        return name in self._tools

    def requires_approval(self, name: str, args: dict) -> bool:
        if self.auto_approve:
            return False
        return self._tools[name].needs_approval or _looks_dangerous(name, args)

    def run(self, name: str, args: dict) -> str:
        try:
            return self._tools[name].handler(args)
        except Exception as exc:  # noqa: BLE001 - tool errors are returned to the model
            return f"ERROR: {exc}"

    def _resolve(self, raw_path: str | None = None) -> Path:
        candidate = self.workspace if not raw_path else (self.workspace / raw_path).resolve()
        if self.workspace != candidate and self.workspace not in candidate.parents:
            raise ValueError("Path workspace ke bahar hai")
        return candidate

    def _shell(self, args: dict) -> str:
        command = _required_string(args, "command")
        timeout = float(args.get("timeout_seconds", 60))
        completed = subprocess.run(
            command,
            cwd=self.workspace,
            shell=True,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        output = ""
        if completed.stdout:
            output += completed.stdout
        if completed.stderr:
            output += "\nSTDERR:\n" + completed.stderr
        output += f"\nEXIT_CODE: {completed.returncode}"
        return _truncate(output.strip(), 12000)

    def _list_files(self, args: dict) -> str:
        root = self._resolve(args.get("path") or ".")
        if not root.exists():
            return "Path not found"
        if root.is_file():
            return str(root.relative_to(self.workspace))

        lines: list[str] = []
        for path in sorted(root.rglob("*")):
            if len(lines) >= 300:
                lines.append("... truncated ...")
                break
            rel = path.relative_to(self.workspace)
            if any(part in {".git", "node_modules", "__pycache__"} for part in rel.parts):
                continue
            suffix = "/" if path.is_dir() else ""
            lines.append(f"{rel}{suffix}")
        return "\n".join(lines) if lines else "No files"

    def _read_file(self, args: dict) -> str:
        path = self._resolve(_required_string(args, "path"))
        max_chars = int(args.get("max_chars", 20000))
        if not path.is_file():
            return "Not a file"
        return _truncate(path.read_text(encoding="utf-8"), max_chars)

    def _write_file(self, args: dict) -> str:
        path = self._resolve(_required_string(args, "path"))
        content = _required_string(args, "content")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return f"Wrote {path.relative_to(self.workspace)} ({len(content)} chars)"

    def _remember(self, args: dict) -> str:
        key = _required_string(args, "key")
        value = _required_string(args, "value")
        data = self._load_memory()
        data[key] = value
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)
        self.memory_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return f"Remembered {key}"

    def _recall_memory(self, args: dict) -> str:
        data = self._load_memory()
        return json.dumps(data, indent=2, ensure_ascii=False) if data else "No memory stored yet"

    def _now(self, args: dict) -> str:
        return datetime.now().astimezone().isoformat(timespec="seconds")

    def _load_memory(self) -> dict[str, str]:
        if not self.memory_file.exists():
            return {}
        payload = json.loads(self.memory_file.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return {}
        return {str(key): str(value) for key, value in payload.items()}


def _required_string(args: dict, key: str) -> str:
    value = args.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Missing required string arg: {key}")
    return value


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n... truncated ..."


def _looks_dangerous(name: str, args: dict) -> bool:
    if name != "shell":
        return False
    command = str(args.get("command", ""))
    try:
        tokens = shlex.split(command)
    except ValueError:
        return True
    dangerous_tokens = {"rm", "sudo", "mkfs", "dd", "shutdown", "reboot", "chmod", "chown"}
    return any(Path(token).name in dangerous_tokens for token in tokens)
