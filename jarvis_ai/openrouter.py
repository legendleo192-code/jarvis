from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import TypedDict


class ChatMessage(TypedDict):
    role: str
    content: str


class OpenRouterError(RuntimeError):
    pass


class OpenRouterClient:
    def __init__(
        self,
        api_key: str,
        model: str = "openrouter/auto",
        base_url: str = "https://openrouter.ai/api/v1",
        app_name: str = "jarvis-ai-assistant",
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.app_name = app_name

    def chat(self, messages: list[ChatMessage], temperature: float = 0.2) -> str:
        body = json.dumps(
            {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/legendleo192-code/jarvis",
                "X-Title": self.app_name,
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise OpenRouterError(f"OpenRouter HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise OpenRouterError(f"OpenRouter request failed: {exc.reason}") from exc

        try:
            return payload["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as exc:
            raise OpenRouterError(f"Unexpected OpenRouter response: {payload}") from exc
