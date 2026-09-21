"""Client interface shared by the mock and the two real model clients."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:  # pragma: no cover
    from ..data import Sample


class FatalClientError(RuntimeError):
    """Configuration / auth / bad-request problem: abort the whole run."""


class TransientClientError(RuntimeError):
    """One request failed after retries: record the sample as failed and carry on."""


@dataclass(frozen=True)
class Usage:
    input_tokens: int = 0        # uncached input tokens
    output_tokens: int = 0
    cache_write_tokens: int = 0  # Anthropic cache_creation_input_tokens
    cache_read_tokens: int = 0   # Anthropic cache_read_input_tokens / OpenAI cached_tokens


@dataclass(frozen=True)
class Completion:
    text: str
    usage: Usage = field(default_factory=Usage)
    model: str = ""                  # model that actually served the request
    stop_reason: str | None = None
    latency_s: float = 0.0
    error: str | None = None         # e.g. "refusal: cyber" - the sample counts as a failure
    served_by_fallback: bool = False


@runtime_checkable
class ModelClient(Protocol):
    name: str  # e.g. "mock", "openai:gpt-x", "anthropic:claude-opus-5"

    def complete(self, system_prompt: str, user_message: str, *, sample: "Sample | None" = None) -> Completion:
        """Return the raw model text. `sample` is only used by the mock client."""
        ...
