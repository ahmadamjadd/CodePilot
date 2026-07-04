from __future__ import annotations

import httpx
from typing import Any, Dict, Optional

from codepilot_review.llm.base import LLMClient
from codepilot_review.config import settings


class GroqClient(LLMClient):
    """Minimal Groq API client.

    Uses Groq's OpenAI-compatible chat completions endpoint.

    The client is isolated behind the `LLMClient` interface so replacing it
    with another provider later only requires swapping this module.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 30,
    ) -> None:
        self.api_key = api_key or settings.grok_api_key
        self.base_url = (base_url or settings.grok_api_base_url or "https://api.groq.com/openai/v1").rstrip("/")
        self.model = model or settings.grok_model
        self.timeout = timeout
        self._client = httpx.Client(timeout=self.timeout)

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def generate(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("GROQ API key is not set. Set it in .env or pass api_key to GroqClient.")

        model = kwargs.pop("model", self.model)
        if not model:
            raise RuntimeError("A Groq model name is required. Set GROK_MODEL in .env or pass model=...")

        payload: Dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "user", "content": prompt},
            ],
        }

        params = kwargs.pop("params", None)
        if isinstance(params, dict):
            payload.update(params)

        url = f"{self.base_url}/chat/completions"
        resp = self._client.post(url, json=payload, headers=self._headers())
        resp.raise_for_status()
        return resp.json()
