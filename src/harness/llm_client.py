from __future__ import annotations

import json
import os
from ipaddress import ip_address
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlparse
from urllib import request


class LLMClient(Protocol):
    backend_name: str

    def complete(self, *, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
        ...


@dataclass
class LLMSettings:
    backend: str = "heuristic"
    model: str = "gpt-4.1-mini"
    api_key: str | None = None
    base_url: str = "https://api.openai.com/v1"
    timeout_seconds: int = 60

    @classmethod
    def from_env(cls) -> "LLMSettings":
        return cls(
            backend=os.getenv("HARNESS_LLM_BACKEND", "heuristic").strip().lower(),
            model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            timeout_seconds=int(os.getenv("HARNESS_LLM_TIMEOUT_SECONDS", "60")),
        )


class HeuristicLLMClient:
    backend_name = "heuristic"

    def complete(self, *, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
        del system_prompt, temperature
        return user_prompt


class OpenAICompatibleLLMClient:
    backend_name = "openai"

    def __init__(self, settings: LLMSettings):
        if not settings.api_key and not _is_local_base_url(settings.base_url):
            raise ValueError(
                "OPENAI_API_KEY is required for non-local OPENAI_BASE_URL when HARNESS_LLM_BACKEND=openai."
            )
        self._settings = settings

    def complete(self, *, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
        payload = {
            "model": self._settings.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
        }
        url = self._settings.base_url.rstrip("/") + "/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self._settings.api_key:
            headers["Authorization"] = f"Bearer {self._settings.api_key}"

        req = request.Request(
            url=url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with request.urlopen(req, timeout=self._settings.timeout_seconds) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]


def create_llm_client(settings: LLMSettings | None = None) -> LLMClient:
    settings = settings or LLMSettings.from_env()
    if settings.backend == "openai":
        return OpenAICompatibleLLMClient(settings=settings)
    return HeuristicLLMClient()


def _is_local_base_url(base_url: str) -> bool:
    parsed = urlparse(base_url)
    hostname = (parsed.hostname or "").strip().lower()
    if not hostname:
        return False
    if hostname in {"localhost", "0.0.0.0", "::1"}:
        return True
    try:
        addr = ip_address(hostname)
    except ValueError:
        return False
    return addr.is_loopback or addr.is_private
