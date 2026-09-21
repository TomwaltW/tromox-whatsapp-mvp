"""Model client factory: mock | openai:<model> | anthropic:<model>."""
from __future__ import annotations

from typing import Any

from .base import Completion, FatalClientError, ModelClient, TransientClientError, Usage
from .mock import DEFAULT_ERROR_RATE, DEFAULT_SEED, MockClient

__all__ = [
    "Completion", "FatalClientError", "ModelClient", "TransientClientError", "Usage",
    "MockClient", "DEFAULT_ERROR_RATE", "DEFAULT_SEED", "build_client",
]


def build_client(spec: str, **options: Any) -> ModelClient:
    """Create a client from a --model value. Unknown options for a client type are ignored."""
    provider, _, model = spec.partition(":")
    provider = provider.strip().lower()
    model = model.strip()

    def pick(*names: str) -> dict[str, Any]:
        return {n: options[n] for n in names if options.get(n) is not None}

    if provider == "mock" and not model:
        kwargs = pick("seed", "error_rate")
        return MockClient(**kwargs)
    if provider == "openai" and model:
        from .openai_compat import OpenAICompatClient

        return OpenAICompatClient(model, **pick("temperature", "max_tokens", "json_mode", "timeout", "transport"))
    if provider == "anthropic" and model:
        from .anthropic_client import AnthropicClient

        return AnthropicClient(model, **pick("max_tokens", "effort", "fallbacks", "timeout", "http_client"))
    raise ValueError(f"unsupported --model {spec!r}; use mock, openai:<model> or anthropic:<model>")
