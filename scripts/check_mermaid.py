#!/usr/bin/env python3
"""Render every ```mermaid block in the repo (or in the given files) with mermaid-cli.

Needs Node (npx) and a local Chrome; no Chromium download. A block that fails to parse
makes the script exit 1 and prints file:line of the block.

    python scripts/check_mermaid.py                 # whole repo
    python scripts/check_mermaid.py 07-project/timeline.md
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # scripts/ is not on sys.path when tests load this by path
from npx_env import npx_env  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CHROME_CANDIDATES = (
    os.environ.get("PUPPETEER_EXECUTABLE_PATH", ""),
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
)
BLOCK_RE = re.compile(r"^```mermaid[ \t]*\n(.*?)^```", re.DOTALL | re.MULTILINE)
SKIP_DIRS = {".git", ".venv", "node_modules", "__pycache__", ".worktrees", "review", ".claude", "dist"}


def find_blocks(path: Path) -> list[tuple[int, str]]:
    text = path.read_text(encoding="utf-8")
    return [(text.count("\n", 0, m.start()) + 1, m.group(1)) for m in BLOCK_RE.finditer(text)]


def main() -> int:
    targets = [Path(a).resolve() for a in sys.argv[1:]] or [
        p for p in ROOT.rglob("*.md") if not (set(p.relative_to(ROOT).parts) & SKIP_DIRS)
    ]
    chrome = next((c for c in CHROME_CANDIDATES if c and Path(c).exists()), None)
    if not shutil.which("npx") or not chrome:
        print("SKIP: npx or Chrome not found; cannot render Mermaid locally")
        return 2
    env = npx_env(ROOT)  # private npm cache per checkout, see scripts/npx_env.py
    total = failed = 0
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        config = tmpdir / "puppeteer.json"
        config.write_text(json.dumps({"executablePath": chrome, "args": ["--no-sandbox"]}), encoding="utf-8")
        for path in sorted(targets):
            for index, (line, body) in enumerate(find_blocks(path)):
                total += 1
                src = tmpdir / f"block_{total}.mmd"
                src.write_text(body, encoding="utf-8")
                proc = subprocess.run(
                    ["npx", "-y", "@mermaid-js/mermaid-cli@11", "-q", "-p", str(config),
                     "-i", str(src), "-o", str(tmpdir / f"block_{total}.svg")],
                    capture_output=True, text=True, env=env, timeout=300,
                )
                rel = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
                if proc.returncode != 0:
                    failed += 1
                    detail = (proc.stderr or proc.stdout).strip().splitlines()
                    print(f"FAIL {rel}:{line} (block {index + 1})")
                    for row in detail[:12]:
                        print(f"     {row}")
                else:
                    print(f"ok   {rel}:{line}")
    print(f"{total} block(s), {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
