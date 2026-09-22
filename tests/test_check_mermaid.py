"""scripts/check_mermaid.py hands npx a per-checkout npm cache (no Node needed: subprocess.run is faked)."""
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_mermaid.py"

spec = importlib.util.spec_from_file_location("check_mermaid", SCRIPT)
cm = importlib.util.module_from_spec(spec)
sys.modules["check_mermaid"] = cm
spec.loader.exec_module(cm)  # type: ignore[union-attr]


def test_main_passes_private_npm_cache_to_npx(tmp_path, monkeypatch, capsys):
    calls: list[dict] = []

    def fake_run(cmd, **kw):
        calls.append(dict(kw.get("env") or {}))
        Path(cmd[cmd.index("-o") + 1]).write_bytes(b"<svg/>")
        return types.SimpleNamespace(returncode=0, stdout="", stderr="")

    chrome = tmp_path / "chrome"
    chrome.write_text("", encoding="utf-8")
    md = tmp_path / "one.md"
    md.write_text("# 图\n\n```mermaid\ngraph TD; A-->B\n```\n", encoding="utf-8")

    monkeypatch.delenv("TROMOX_NPM_CACHE", raising=False)
    monkeypatch.setattr(cm.subprocess, "run", fake_run)
    monkeypatch.setattr(cm.shutil, "which", lambda *_a, **_k: "/usr/bin/npx")
    monkeypatch.setattr(cm, "CHROME_CANDIDATES", (str(chrome),))
    monkeypatch.setattr(sys, "argv", ["check_mermaid.py", str(md)])

    assert cm.main() == 0
    assert len(calls) == 1
    env = calls[0]
    assert Path(env["npm_config_cache"]).resolve().is_relative_to((ROOT / "scratch").resolve())
    assert env["PUPPETEER_SKIP_DOWNLOAD"] == "1"
    assert "1 block(s), 0 failed" in capsys.readouterr().out
