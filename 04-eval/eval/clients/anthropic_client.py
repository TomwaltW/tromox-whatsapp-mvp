"""Claude client built on the official `anthropic` SDK (Messages API).

Credentials and endpoint are resolved by the SDK from the environment - nothing is read
or hard-coded here: ANTHROPIC_API_KEY (or ANTHROPIC_AUTH_TOKEN, or an `ant auth login`
profile) and ANTHROPIC_BASE_URL.

Request-shape notes (current Claude models):
* no `temperature` / `top_p` / `top_k` - the newest models reject sampling parameters;
* `thinking` is left to the model default; tune cost/depth with `effort` instead
  (`output_config.effort`; not accepted by every model, so it is only sent when asked for);
* no assistant prefill - JSON-only output is enforced by the prompt;
* the classification prompt is identical for every sample, so it is sent as a cached
  system block and only the enquiry varies;
* `stop_reason` is checked before the content is read; a refusal is a failed sample.
"""
from __future__ import annotations

import time
from typing import Any

from .base import Completion, FatalClientError, TransientClientError, Usage

DEFAULT_MAX_TOKENS = 16000
FALLBACK_BETA = "server-side-fallback-2026-07-01"
# Models for which Anthropic recommends opting into server-side refusal fallbacks.
_FALLBACK_AUTO_MODELS = frozenset({"claude-opus-5", "claude-fable-5-1", "claude-mythos-5-1"})


class AnthropicClient:
    def __init__(
        self,
        model: str,
        *,
        max_tokens: int | None = None,
        effort: str | None = None,
        fallbacks: str = "auto",
        max_retries: int = 2,
        timeout: float | None = None,
        http_client: Any | None = None,
    ) -> None:
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - depends on the environment
            raise FatalClientError(
                "the `anthropic` package is required for anthropic:<model>; install the eval extra: "
                '`uv pip install -e ".[eval]"`'
            ) from exc
        if fallbacks not in ("auto", "on", "off"):
            raise ValueError("fallbacks must be auto, on or off")
        self._sdk = anthropic
        self.model = model
        self.name = f"anthropic:{model}"
        self.max_tokens = max_tokens or DEFAULT_MAX_TOKENS
        self.effort = effort
        self.use_fallbacks = fallbacks == "on" or (fallbacks == "auto" and model in _FALLBACK_AUTO_MODELS)
        options: dict[str, Any] = {"max_retries": max_retries}
        if timeout is not None:
            options["timeout"] = timeout
        if http_client is not None:
            options["http_client"] = http_client
        try:
            self._client = anthropic.Anthropic(**options)
        except anthropic.AnthropicError as exc:
            raise FatalClientError(
                f"could not create the Anthropic client ({exc}); set ANTHROPIC_API_KEY or run `ant auth login`"
            ) from exc

    def _request(self, system_prompt: str, user_message: str) -> dict[str, Any]:
        request: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": [{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}],
            "messages": [{"role": "user", "content": user_message}],
        }
        if self.effort:
            request["output_config"] = {"effort": self.effort}
        return request

    def complete(self, system_prompt: str, user_message: str, *, sample: object | None = None) -> Completion:
        sdk = self._sdk
        request = self._request(system_prompt, user_message)
        started = time.perf_counter()
        try:
            if self.use_fallbacks:
                response = self._client.beta.messages.create(betas=[FALLBACK_BETA], fallbacks="default", **request)
            else:
                response = self._client.messages.create(**request)
        except (sdk.BadRequestError, sdk.AuthenticationError, sdk.PermissionDeniedError, sdk.NotFoundError) as exc:
            raise FatalClientError(f"{type(exc).__name__} from {self.name}: {exc.message}") from exc
        except sdk.RateLimitError as exc:
            raise TransientClientError(f"rate limited by {self.name}: {exc.message}") from exc
        except sdk.APIStatusError as exc:
            if exc.status_code >= 500:
                raise TransientClientError(f"server error {exc.status_code} from {self.name}") from exc
            raise FatalClientError(f"HTTP {exc.status_code} from {self.name}: {exc.message}") from exc
        except sdk.APIConnectionError as exc:  # includes APITimeoutError
            raise TransientClientError(f"connection problem with {self.name}: {exc}") from exc
        latency = time.perf_counter() - started

        raw_usage = response.usage
        usage = Usage(
            input_tokens=int(getattr(raw_usage, "input_tokens", 0) or 0),
            output_tokens=int(getattr(raw_usage, "output_tokens", 0) or 0),
            cache_write_tokens=int(getattr(raw_usage, "cache_creation_input_tokens", 0) or 0),
            cache_read_tokens=int(getattr(raw_usage, "cache_read_input_tokens", 0) or 0),
        )
        iterations = getattr(raw_usage, "iterations", None) or []
        served_by_fallback = any(getattr(entry, "type", None) == "fallback_message" for entry in iterations)
        served_model = str(getattr(response, "model", "") or self.model)

        # Always look at stop_reason before reading content.
        if response.stop_reason == "refusal":
            details = getattr(response, "stop_details", None)
            category = getattr(details, "category", None) or "unspecified"
            return Completion(text="", usage=usage, model=served_model, stop_reason="refusal",
                              latency_s=latency, error=f"refusal: {category}",
                              served_by_fallback=served_by_fallback)
        text = "".join(block.text for block in response.content if block.type == "text")
        error = "max_tokens reached - output may be truncated" if response.stop_reason == "max_tokens" else None
        return Completion(text=text, usage=usage, model=served_model, stop_reason=response.stop_reason,
                          latency_s=latency, error=error, served_by_fallback=served_by_fallback)

    def close(self) -> None:
        self._client.close()
