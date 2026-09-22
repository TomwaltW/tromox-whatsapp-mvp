"""开发时的快速测试开关：TROMOX_FAST_TESTS=1 跳过带 slow 标记的用例。

慢的是真 Chrome 打印 PDF 与 npx 渲染 Mermaid（单条就要几十秒）。不设这个变量时
什么都不做——条数、行为与从前完全一致，提交前仍应跑全量。
"""
from __future__ import annotations

import os

import pytest

TRUTHY = {"1", "true", "yes"}


def fast_tests_enabled() -> bool:
    return os.environ.get("TROMOX_FAST_TESTS", "").strip().lower() in TRUTHY


def pytest_collection_modifyitems(config, items):
    if not fast_tests_enabled():
        return
    skip = pytest.mark.skip(reason="TROMOX_FAST_TESTS=1")
    for item in items:
        if item.get_closest_marker("slow") is not None:
            item.add_marker(skip)
