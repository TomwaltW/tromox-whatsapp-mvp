"""Inbound request checks: shared secret (primary) and optional IP allowlist (defence in depth).

Botmaker sends the token configured on the webhook in the `auth-bm-token` header
(SOURCES S-B5). Its egress IP list is public (SOURCES S-B11) and can go into ALLOWED_IPS.

Behind a reverse proxy, run uvicorn with proxy headers trusted only from the proxy
(`FORWARDED_ALLOW_IPS=<proxy ip>`), so that `request.client.host` is the real caller and
cannot be spoofed through X-Forwarded-For.
"""
from __future__ import annotations

import hmac
import ipaddress

TOKEN_HEADER = "auth-bm-token"


def verify_token(provided: str | None, expected: str) -> bool:
    """Constant-time comparison; an unset expected token never matches."""
    if not expected:
        return False
    return hmac.compare_digest((provided or "").encode("utf-8"), expected.encode("utf-8"))


def ip_allowed(client_ip: str | None, allowed: list[str]) -> bool:
    """True when no allowlist is configured, or the caller is inside one of the entries."""
    if not allowed:
        return True
    if not client_ip:
        return False
    try:
        address = ipaddress.ip_address(client_ip)
    except ValueError:
        return False
    for entry in allowed:
        try:
            if address in ipaddress.ip_network(entry, strict=False):
                return True
        except ValueError:
            continue
    return False
