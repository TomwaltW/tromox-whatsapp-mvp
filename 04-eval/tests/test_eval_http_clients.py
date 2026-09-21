"""Both real clients, exercised only through mock transports - no network, no real keys."""
from __future__ import annotations

import importlib
import json

import httpx
import pytest

from eval.clients import FatalClientError, TransientClientError, build_client
from eval.clients.openai_compat import OpenAICompatClient

SYSTEM, USER = "SYSTEM PROMPT", "<conversation>\nhello\n</conversation>"


# ----------------------------------------------------------------------------- OpenAI-compatible
def _openai_body(text: str = '{"segment": "B2C"}') -> dict:
    return {"model": "served-model", "choices": [{"message": {"role": "assistant", "content": text}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 900, "completion_tokens": 40, "prompt_tokens_details": {"cached_tokens": 600}}}


def test_openai_request_shape_and_usage(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://llm.example.test/v1/")
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(url=str(request.url), auth=request.headers["authorization"], body=json.loads(request.content))
        return httpx.Response(200, json=_openai_body())

    client = OpenAICompatClient("some-model", transport=httpx.MockTransport(handler))
    completion = client.complete(SYSTEM, USER)
    assert seen["url"] == "https://llm.example.test/v1/chat/completions"
    assert seen["auth"] == "Bearer test-openai-key"
    assert seen["body"] == {"model": "some-model", "messages": [
        {"role": "system", "content": SYSTEM}, {"role": "user", "content": USER}]}   # no optional knobs by default
    assert completion.text == '{"segment": "B2C"}' and completion.model == "served-model"
    assert (completion.usage.input_tokens, completion.usage.cache_read_tokens, completion.usage.output_tokens) == (300, 600, 40)
    assert client.name == "openai:some-model"


def test_openai_optional_parameters_and_default_base_url(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(url=str(request.url), body=json.loads(request.content))
        return httpx.Response(200, json=_openai_body())

    client = build_client("openai:m", temperature=0.0, max_tokens=800, json_mode=True, transport=httpx.MockTransport(handler))
    client.complete(SYSTEM, USER)
    assert seen["url"] == "https://api.openai.com/v1/chat/completions"
    assert seen["body"]["temperature"] == 0.0 and seen["body"]["max_tokens"] == 800
    assert seen["body"]["response_format"] == {"type": "json_object"}


def test_openai_requires_key_from_env():
    with pytest.raises(FatalClientError, match="OPENAI_API_KEY"):
        OpenAICompatClient("m")


def test_openai_auth_error_is_fatal_and_not_retried(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(401, json={"error": {"message": "bad key"}})

    client = OpenAICompatClient("m", transport=httpx.MockTransport(handler), sleep=lambda s: None)
    with pytest.raises(FatalClientError, match="401"):
        client.complete(SYSTEM, USER)
    assert len(calls) == 1


def test_openai_retries_then_succeeds_or_gives_up(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    statuses = [429, 503, 200]
    sleeps: list[float] = []

    def flaky(request: httpx.Request) -> httpx.Response:
        status = statuses.pop(0)
        return httpx.Response(status, json=_openai_body() if status == 200 else {"error": "busy"})

    client = OpenAICompatClient("m", transport=httpx.MockTransport(flaky), sleep=sleeps.append)
    assert client.complete(SYSTEM, USER).text and sleeps == [1.0, 2.0]

    attempts = []

    def down(request: httpx.Request) -> httpx.Response:
        attempts.append(1)
        return httpx.Response(500, text="boom")

    client = OpenAICompatClient("m", transport=httpx.MockTransport(down), sleep=lambda s: None)
    with pytest.raises(TransientClientError, match="3 attempts"):
        client.complete(SYSTEM, USER)
    assert len(attempts) == 3


def test_openai_connection_error_is_transient(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "k")

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route", request=request)

    client = OpenAICompatClient("m", transport=httpx.MockTransport(handler), sleep=lambda s: None, max_retries=1)
    with pytest.raises(TransientClientError, match="ConnectError"):
        client.complete(SYSTEM, USER)


# ----------------------------------------------------------------------------- Anthropic (official SDK)
anthropic = pytest.importorskip("anthropic", reason="install `anthropic` to test the Claude client")
# The SDK's HTTP layer (httpx2 on anthropic 1.x, httpx on 0.x); mock transports must come from it.
sdk_http = importlib.import_module(anthropic.DefaultHttpxClient.__mro__[1].__module__.split(".")[0])

from eval.clients.anthropic_client import DEFAULT_MAX_TOKENS, FALLBACK_BETA, AnthropicClient  # noqa: E402


def _message(text: str = '{"segment": "B2B"}', **overrides) -> dict:
    body = {
        "id": "msg_test", "type": "message", "role": "assistant", "model": "claude-opus-5",
        "content": [{"type": "thinking", "thinking": "", "signature": "sig"}, {"type": "text", "text": text}],
        "stop_reason": "end_turn", "stop_sequence": None,
        "usage": {"input_tokens": 50, "output_tokens": 120, "cache_creation_input_tokens": 2000, "cache_read_input_tokens": 0},
    }
    body.update(overrides)
    return body


def _claude(model: str, handler, monkeypatch, **kwargs) -> AnthropicClient:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://claude.example.test")
    http_client = anthropic.DefaultHttpxClient(transport=sdk_http.MockTransport(handler))
    return AnthropicClient(model, http_client=http_client, max_retries=0, **kwargs)


def _capture(seen: dict, response: dict):
    def handler(request):
        seen.update(url=str(request.url), headers=dict(request.headers), body=json.loads(request.content))
        return sdk_http.Response(200, json=response)
    return handler


def test_anthropic_request_shape_and_usage(monkeypatch):
    seen: dict = {}
    client = _claude("claude-haiku-4-5", _capture(seen, _message(model="claude-haiku-4-5")), monkeypatch)
    completion = client.complete(SYSTEM, USER)
    assert seen["url"] == "https://claude.example.test/v1/messages"          # base URL and key come from the env
    assert seen["headers"]["x-api-key"] == "test-anthropic-key" and "anthropic-version" in seen["headers"]
    assert "anthropic-beta" not in seen["headers"]
    body = seen["body"]
    assert body["model"] == "claude-haiku-4-5" and body["max_tokens"] == DEFAULT_MAX_TOKENS
    assert body["system"] == [{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}]
    assert body["messages"] == [{"role": "user", "content": USER}]            # single user turn, no assistant prefill
    for forbidden in ("temperature", "top_p", "top_k", "thinking", "output_config", "fallbacks"):
        assert forbidden not in body
    assert completion.text == '{"segment": "B2B"}'                            # thinking block is not part of the text
    assert completion.model == "claude-haiku-4-5" and completion.stop_reason == "end_turn"
    usage = completion.usage
    assert (usage.input_tokens, usage.output_tokens, usage.cache_write_tokens, usage.cache_read_tokens) == (50, 120, 2000, 0)


def test_anthropic_effort_and_max_tokens_are_opt_in(monkeypatch):
    seen: dict = {}
    client = _claude("claude-sonnet-5", _capture(seen, _message()), monkeypatch, effort="low", max_tokens=4000, fallbacks="off")
    client.complete(SYSTEM, USER)
    assert seen["body"]["output_config"] == {"effort": "low"} and seen["body"]["max_tokens"] == 4000


def test_anthropic_fallbacks_auto_for_recommended_models(monkeypatch):
    seen: dict = {}
    response = _message(usage={"input_tokens": 5, "output_tokens": 5, "iterations": [{"type": "fallback_message"}]},
                        model="claude-opus-4-8")
    client = _claude("claude-opus-5", _capture(seen, response), monkeypatch)
    completion = client.complete(SYSTEM, USER)
    assert "beta=true" in seen["url"] and FALLBACK_BETA in seen["headers"]["anthropic-beta"]
    assert seen["body"]["fallbacks"] == "default"
    assert completion.served_by_fallback and completion.model == "claude-opus-4-8"

    seen.clear()
    _claude("claude-opus-5", _capture(seen, _message()), monkeypatch, fallbacks="off").complete(SYSTEM, USER)
    assert "fallbacks" not in seen["body"] and "anthropic-beta" not in seen["headers"]


def test_anthropic_refusal_is_a_failed_sample_not_a_crash(monkeypatch):
    response = _message(content=[], stop_reason="refusal",
                        stop_details={"type": "refusal", "category": "cyber", "explanation": "declined"})
    completion = _claude("claude-haiku-4-5", _capture({}, response), monkeypatch).complete(SYSTEM, USER)
    assert completion.text == "" and completion.stop_reason == "refusal" and completion.error.startswith("refusal")


def test_anthropic_max_tokens_is_flagged(monkeypatch):
    completion = _claude("claude-haiku-4-5", _capture({}, _message(text='{"segment": "B2', stop_reason="max_tokens")),
                         monkeypatch).complete(SYSTEM, USER)
    assert "max_tokens" in completion.error and completion.text == '{"segment": "B2'


@pytest.mark.parametrize("status, error_type, expected", [
    (401, "authentication_error", FatalClientError),
    (400, "invalid_request_error", FatalClientError),
    (404, "not_found_error", FatalClientError),
    (429, "rate_limit_error", TransientClientError),
    (529, "overloaded_error", TransientClientError),
])
def test_anthropic_error_chain(monkeypatch, status, error_type, expected):
    def handler(request):
        return sdk_http.Response(status, json={"type": "error", "error": {"type": error_type, "message": "nope"}})

    with pytest.raises(expected):
        _claude("claude-haiku-4-5", handler, monkeypatch).complete(SYSTEM, USER)


def test_anthropic_factory_and_validation(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    client = build_client("anthropic:claude-opus-5", effort="low", temperature=0.0)   # temperature is never forwarded
    assert client.name == "anthropic:claude-opus-5" and client.use_fallbacks
    with pytest.raises(ValueError):
        AnthropicClient("claude-opus-5", fallbacks="sometimes")
