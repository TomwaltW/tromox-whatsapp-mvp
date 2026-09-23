"""Shared HTTP helper for webhook-style notifiers. Error messages never include the URL.

Only a 2xx counts as delivered. httpx does not follow redirects, and a 3xx has no JSON body:
treating it as success would read `{}`, pass the Feishu `code` / WeCom `errcode` checks and
record the card as sent while it went nowhere.
"""
from __future__ import annotations

from typing import Any

import httpx

from .base import NotifyError

DEFAULT_TIMEOUT = httpx.Timeout(10.0, connect=5.0)


def post_json(url: str, body: dict[str, Any], *, channel: str, client: httpx.Client | None = None) -> dict[str, Any]:
    owns_client = client is None
    http = client or httpx.Client(timeout=DEFAULT_TIMEOUT)
    try:
        response = http.post(url, json=body)
    except httpx.HTTPError as exc:
        raise NotifyError(f"{channel}: transport error {type(exc).__name__}") from None
    finally:
        if owns_client:
            http.close()
    if not response.is_success:
        raise NotifyError(f"{channel}: HTTP {response.status_code}")
    try:
        data = response.json()
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}
