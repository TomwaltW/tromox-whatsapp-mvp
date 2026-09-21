"""OpenAI-compatible chat-completions client (any provider exposing /chat/completions).

Configuration comes from the environment only:
    OPENAI_BASE_URL  default https://api.openai.com/v1
    OPENAI_API_KEY   required
Claude models must NOT be called through this client - use `anthropic:<model>`.
"""
from __future__ import annotations

import os
import time
from typing import Any, Callable

import httpx

from .base import Completion, FatalClientError, TransientClientError, Usage

DEFAULT_BASE_URL = "https://api.openai.com/v1"
_RETRYABLE_STATUS = {408, 409, 429, 500, 502, 503, 504}


class OpenAICompatClient:
    def __init__(
        self,
        model: str,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_mode: bool = False,
        timeout: float = 120.0,
        max_retries: int = 2,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise FatalClientError("OPENAI_API_KEY is not set")
        self.model = model
        self.name = f"openai:{model}"
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.json_mode = json_mode
        self.max_retries = max_retries
        self._sleep = sleep
        base_url = (os.environ.get("OPENAI_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self._http = httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            timeout=timeout,
            transport=transport,
        )

    def _payload(self, system_prompt: str, user_message: str) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        }
        # Optional knobs are only sent when asked for: several providers and reasoning models
        # reject `temperature`, `max_tokens` or `response_format`.
        if self.temperature is not None:
            payload["temperature"] = self.temperature
        if self.max_tokens is not None:
            payload["max_tokens"] = self.max_tokens
        if self.json_mode:
            payload["response_format"] = {"type": "json_object"}
        return payload

    def complete(self, system_prompt: str, user_message: str, *, sample: object | None = None) -> Completion:
        payload = self._payload(system_prompt, user_message)
        started = time.perf_counter()
        last_problem = "no attempt made"
        for attempt in range(self.max_retries + 1):
            try:
                response = self._http.post("/chat/completions", json=payload)
            except httpx.HTTPError as exc:  # connection errors, timeouts
                last_problem = f"{type(exc).__name__}: {exc}"
            else:
                if response.status_code == 200:
                    return self._completion(response.json(), time.perf_counter() - started)
                detail = response.text[:300]
                if response.status_code not in _RETRYABLE_STATUS:
                    raise FatalClientError(f"HTTP {response.status_code} from {self.name}: {detail}")
                last_problem = f"HTTP {response.status_code}: {detail}"
            if attempt < self.max_retries:
                self._sleep(min(2.0 ** attempt, 30.0))
        raise TransientClientError(f"{self.name} failed after {self.max_retries + 1} attempts: {last_problem}")

    def _completion(self, body: dict[str, Any], latency_s: float) -> Completion:
        choices = body.get("choices") or []
        if not choices:
            return Completion(text="", model=str(body.get("model") or self.model), latency_s=latency_s,
                              error="empty choices")
        choice = choices[0]
        text = (choice.get("message") or {}).get("content") or ""
        usage_raw = body.get("usage") or {}
        cached = int(((usage_raw.get("prompt_tokens_details") or {}).get("cached_tokens")) or 0)
        prompt_tokens = int(usage_raw.get("prompt_tokens") or 0)
        usage = Usage(input_tokens=max(0, prompt_tokens - cached),
                      output_tokens=int(usage_raw.get("completion_tokens") or 0),
                      cache_read_tokens=cached)
        finish = choice.get("finish_reason")
        error = "content_filter" if finish == "content_filter" else None
        return Completion(text=text, usage=usage, model=str(body.get("model") or self.model),
                          stop_reason=finish, latency_s=latency_s, error=error)

    def close(self) -> None:
        self._http.close()
