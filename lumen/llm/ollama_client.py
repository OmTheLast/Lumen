"""Small Ollama chat client."""

from __future__ import annotations

from typing import Any

import requests


class OllamaError(RuntimeError):
    """Raised when the local Ollama service is unavailable or returns an error."""


class OllamaClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        *,
        json_mode: bool = False,
        timeout: int = 120,
    ) -> str:
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
        }
        if json_mode:
            payload["format"] = "json"

        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=timeout,
            )
            response.raise_for_status()
        except requests.exceptions.ConnectionError as exc:
            raise OllamaError("Ollama is not running. Start it with `ollama serve`.") from exc
        except requests.exceptions.Timeout as exc:
            raise OllamaError("Ollama request timed out.") from exc
        except requests.RequestException as exc:
            raise OllamaError(f"Ollama request failed: {exc}") from exc

        data = response.json()
        message = data.get("message") or {}
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise OllamaError("Ollama returned an empty response.")
        return content.strip()

