"""Environment for the npx subprocesses that render Mermaid (check_mermaid.py, export_client_docs.py).

npx unpacks mermaid-cli into ``_npx/<hash>/`` under the npm cache. With one machine-wide cache, two
checkouts rendering at the same time trample each other's lock files (npm reports ECOMPROMISED).
So every checkout gets its own cache under ``<root>/scratch/npm-cache`` (gitignored); set
``TROMOX_NPM_CACHE`` to put it somewhere else. Standard library only.
"""
from __future__ import annotations

import os
from pathlib import Path


def npx_env(root: Path) -> dict[str, str]:
    """Environment variables for an npx child process.

    A copy of ``os.environ`` plus ``PUPPETEER_SKIP_DOWNLOAD=1``, ``PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=1``
    and ``npm_config_cache=<cache dir>``. The cache dir is ``TROMOX_NPM_CACHE`` when that variable is
    non-empty, otherwise ``<root>/scratch/npm-cache``; it is created if missing (parents included).
    ``os.environ`` itself is never modified.
    """
    override = os.environ.get("TROMOX_NPM_CACHE", "")
    cache = Path(override) if override else Path(root) / "scratch" / "npm-cache"
    cache.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env["PUPPETEER_SKIP_DOWNLOAD"] = "1"
    env["PUPPETEER_SKIP_CHROMIUM_DOWNLOAD"] = "1"
    env["npm_config_cache"] = str(cache)
    return env
