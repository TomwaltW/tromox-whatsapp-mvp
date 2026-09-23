from __future__ import annotations

import csv
import io
import json
import subprocess
import sys
from pathlib import Path

import pytest

from eval.run import EXIT_CLIENT, EXIT_DATA, EXIT_OK, EXIT_THRESHOLD, main

ROOT = Path(__file__).resolve().parents[1]
BASE_ARGS = ["--input", "synthetic-samples.csv", "--prompt", "prompts/classify-v1.md", "--model", "mock"]


@pytest.fixture(autouse=True)
def _in_eval_dir(monkeypatch):
    monkeypatch.chdir(ROOT)


def test_end_to_end_report(tmp_path, capsys):
    out = tmp_path / "report.md"
    assert main([*BASE_ARGS, "--out", str(out)]) == EXIT_OK           # thresholds fail, exit code stays 0
    stdout = capsys.readouterr().out
    assert "RESULT: FAIL" in stdout and "offline_min_samples" in stdout and "B2B recall" in stdout
    report = out.read_text(encoding="utf-8")
    for heading in ("## 2. 验收阈值对照", "## 3. B 端漏判清单", "## 4. 客户类型混淆矩阵", "## 6. 分语种分布",
                    "## 8. 成本与时延", "## 9. 解析失败与调用失败"):
        assert heading in report
    assert report.index("## 3. B 端漏判清单") < report.index("## 4. 客户类型混淆矩阵")   # misses come first
    assert "合成数据只用于跑通流程" in report and "`classify-v1`" in report
    assert "未设置单价" in report


def test_fail_under_and_custom_thresholds(tmp_path, capsys):
    out = tmp_path / "report.md"
    assert main([*BASE_ARGS, "--out", str(out), "--fail-under"]) == EXIT_THRESHOLD
    relaxed = tmp_path / "thresholds.json"
    relaxed.write_text(json.dumps({"b2b_recall_min": 0.5, "escalation_rate_max": 0.9}), encoding="utf-8")
    capsys.readouterr()
    assert main([*BASE_ARGS, "--out", str(out), "--fail-under", "--thresholds", str(relaxed)]) == EXIT_OK
    assert "RESULT: PASS (2 checks)" in capsys.readouterr().out


def test_report_is_deterministic_and_the_committed_one_is_fresh(tmp_path):
    first, second = tmp_path / "a.md", tmp_path / "b.md"
    assert main([*BASE_ARGS, "--out", str(first)]) == EXIT_OK
    assert main([*BASE_ARGS, "--out", str(second)]) == EXIT_OK
    assert first.read_bytes() == second.read_bytes()
    committed = ROOT / "reports" / "synthetic-mock-report.md"
    assert committed.read_bytes() == first.read_bytes(), "re-run the command in 04-eval/README.md to refresh the report"


def test_cost_limit_and_predictions(tmp_path, monkeypatch):
    monkeypatch.setenv("EVAL_PRICE_INPUT_PER_1M", "1")
    monkeypatch.setenv("EVAL_PRICE_OUTPUT_PER_1M", "5")
    out, predictions = tmp_path / "r.md", tmp_path / "p.jsonl"
    assert main([*BASE_ARGS, "--out", str(out), "--limit", "10", "--predictions-out", str(predictions)]) == EXIT_OK
    report = out.read_text(encoding="utf-8")
    assert "| 样本数 | 10（" in report and "USD（单价：输入 1、输出 5" in report
    lines = [json.loads(line) for line in predictions.read_text(encoding="utf-8").splitlines()]
    assert len(lines) == 10 and lines[0]["sample_id"] == "SYN-001" and "prediction_after_routing" in lines[0]


def test_error_exit_codes(tmp_path, capsys):
    bad = tmp_path / "bad.csv"
    bad.write_text("sample_id,text\n1,hello\n", encoding="utf-8")
    assert main(["--input", str(bad), "--prompt", "prompts/classify-v1.md", "--model", "mock", "--out", str(tmp_path / "r.md")]) == EXIT_DATA
    assert main([*BASE_ARGS[:-1], "bogus-model", "--out", str(tmp_path / "r.md")]) == EXIT_CLIENT
    assert main([*BASE_ARGS[:-1], "openai:some-model", "--out", str(tmp_path / "r.md")]) == EXIT_CLIENT   # no key in env
    assert "OPENAI_API_KEY" in capsys.readouterr().err


def _example_only_csv(tmp_path) -> tuple[Path, int]:
    """试用样例包那样的 CSV：每行 data_origin=example，其余字段沿用合成集。"""
    with (ROOT / "synthetic-samples.csv").open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        fieldnames = list(reader.fieldnames or [])
        rows = [{**row, "data_origin": "example"} for row in reader]
    path = tmp_path / "example-only.csv"
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path, len(rows)


def test_include_examples_evaluates_example_rows(tmp_path, capsys):
    csv_path, count = _example_only_csv(tmp_path)
    out = tmp_path / "example-report.md"
    args = ["--input", str(csv_path), "--prompt", "prompts/classify-v1.md", "--model", "mock", "--out", str(out)]
    assert main([*args, "--include-examples"]) == EXIT_OK
    captured = capsys.readouterr()
    assert f"evaluating {count} samples" in captured.err     # 样例行计入待评测样本
    assert out.exists() and "RESULT:" in captured.out


def test_example_rows_are_skipped_without_the_flag(tmp_path, capsys):
    csv_path, _ = _example_only_csv(tmp_path)
    out = tmp_path / "skipped-report.md"
    assert main(["--input", str(csv_path), "--prompt", "prompts/classify-v1.md", "--model", "mock",
                 "--out", str(out)]) == EXIT_DATA
    assert "example" in capsys.readouterr().err and not out.exists()


def test_module_entry_point(tmp_path):
    out = tmp_path / "cli.md"
    result = subprocess.run([sys.executable, "-m", "eval.run", *BASE_ARGS, "--out", str(out)],
                            cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert out.exists() and "RESULT:" in result.stdout


def test_non_utf8_input_is_a_data_error_not_a_threshold_failure(tmp_path, capsys):
    with (ROOT / "synthetic-samples.csv").open(encoding="utf-8", newline="") as fh:
        rows = list(csv.reader(fh))[:3]
    text_col = rows[0].index("conversation_text")
    for row in rows[1:]:
        row[text_col] = "你好，我们想做经销商，请问价格"
    buf = io.StringIO()
    csv.writer(buf).writerows(rows)
    gbk = tmp_path / "gbk.csv"
    gbk.write_bytes(buf.getvalue().encode("gbk", errors="replace"))
    out = tmp_path / "r.md"
    assert main(["--input", str(gbk), "--prompt", "prompts/classify-v1.md", "--model", "mock", "--out", str(out),
                 "--fail-under"]) == EXIT_DATA                        # 2, not the threshold exit code 1
    err = capsys.readouterr().err
    assert "不是 UTF-8 编码" in err and "CSV UTF-8" in err and not out.exists()
