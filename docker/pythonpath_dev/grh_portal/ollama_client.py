"""Local Ollama chat client. No API key, no cloud endpoint."""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)


class OllamaError(RuntimeError):
    """The local model did not return a completion."""


class OllamaClient:
    def __init__(self, base_url: str, model: str, timeout: float) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def complete(self, system: str, user: str) -> str:
        payload = {
            "model": self.model,
            "stream": False,
            "format": "json",
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "options": {"temperature": 0, "num_predict": 400},
        }
        request = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as ex:
            logger.warning("Ollama request failed: %s", type(ex).__name__)
            raise OllamaError("L'assistant est momentanément indisponible.") from ex
        content = ((body.get("message") or {}).get("content") or "").strip()
        if not content:
            raise OllamaError("L'assistant est momentanément indisponible.")
        return content


def ollama_reachable(base_url: str, timeout: float = 2) -> bool:
    request = urllib.request.Request(f"{base_url.rstrip('/')}/api/tags", method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout):
            return True
    except (urllib.error.URLError, TimeoutError):
        return False
