"""scripts/npx_env.py: per-checkout npm cache for the npx subprocesses that render Mermaid."""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "scripts" / "npx_env.py"

spec = importlib.util.spec_from_file_location("npx_env", HELPER)
helper = importlib.util.module_from_spec(spec)
sys.modules["npx_env"] = helper
spec.loader.exec_module(helper)  # type: ignore[union-attr]
npx_env = helper.npx_env


def test_default_cache_under_root_scratch_and_created(tmp_path, monkeypatch):
    monkeypatch.delenv("TROMOX_NPM_CACHE", raising=False)
    root = tmp_path / "checkout"
    env = npx_env(root)
    assert Path(env["npm_config_cache"]) == root / "scratch" / "npm-cache"
    assert (root / "scratch" / "npm-cache").is_dir()


def test_tromox_npm_cache_overrides_default(tmp_path, monkeypatch):
    elsewhere = tmp_path / "elsewhere" / "cache"
    monkeypatch.setenv("TROMOX_NPM_CACHE", str(elsewhere))
    env = npx_env(tmp_path / "checkout")
    assert Path(env["npm_config_cache"]) == elsewhere
    assert elsewhere.is_dir()
    assert not (tmp_path / "checkout" / "scratch").exists()


def test_different_roots_get_different_caches(tmp_path, monkeypatch):
    monkeypatch.delenv("TROMOX_NPM_CACHE", raising=False)
    a = npx_env(tmp_path / "a")["npm_config_cache"]
    b = npx_env(tmp_path / "b")["npm_config_cache"]
    assert a != b
    assert Path(a).is_relative_to(tmp_path / "a") and Path(b).is_relative_to(tmp_path / "b")


def test_puppeteer_download_skipped(tmp_path, monkeypatch):
    monkeypatch.delenv("TROMOX_NPM_CACHE", raising=False)
    env = npx_env(tmp_path)
    assert env["PUPPETEER_SKIP_DOWNLOAD"] == "1"
    assert env["PUPPETEER_SKIP_CHROMIUM_DOWNLOAD"] == "1"


def test_os_environ_untouched(tmp_path, monkeypatch):
    monkeypatch.delenv("TROMOX_NPM_CACHE", raising=False)
    monkeypatch.delenv("npm_config_cache", raising=False)
    monkeypatch.setenv("TROMOX_TEST_MARKER", "kept")
    before = dict(os.environ)
    env = npx_env(tmp_path)
    assert env["TROMOX_TEST_MARKER"] == "kept"  # a copy of the caller's environment, plus the additions
    assert "npm_config_cache" not in os.environ
    assert dict(os.environ) == before
