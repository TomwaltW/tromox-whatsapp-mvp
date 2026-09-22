"""Inbound request checks: shared secret (primary) and optional IP allowlist (defence in depth).

Botmaker sends the token configured on the webhook in the `auth-bm-token` header
(SOURCES S-B5). Its egress IP list is public (SOURCES S-B11) and can go into ALLOWED_IPS.

Behind a reverse proxy the peer address is the proxy, so uvicorn runs with `--proxy-headers`
and only trusts X-Forwarded-For from the senders listed in `FORWARDED_ALLOW_IPS` (IP, CIDR or
`*`); a header from anyone else is ignored and `request.client.host` stays the real peer, so
the allowlist cannot be bypassed by forging the header.

`deploy/docker-compose.yml` sets it to `*` by default, which is safe only because port 8000 is
bound to 127.0.0.1 and the sole entry point is Caddy on the same compose network (its container
address changes on every rebuild, so pinning it is pointless). Exposing 8000 to the internet
means narrowing it -- via `TROMOX_FORWARDED_ALLOW_IPS` -- to the proxy's fixed IP, or emptying
it so no forwarded header is believed.
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
