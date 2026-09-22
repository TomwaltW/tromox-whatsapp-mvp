"""远程 sink 移出请求路径：mirror_outbox 表、响应后后台镜像、replay 重试、/metrics 计数。

验的是 README 第 1 节"镜像"那一行：远程 sink（飞书多维表格）慢或挂都不许拖累对 Botmaker 的应答。
本地 sink（CSV）照旧在请求路径里同步写。
"""
from __future__ import annotations

import sqlite3
import time

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.metrics import collect
from app.pipeline import Pipeline
from app.replay import replay
from app.store import CsvExportSink, MirrorError, SqliteStore
from app.store.feishu_bitable import FeishuBitableSink

from webhook_test_helpers import HEADERS, NO_WAIT, RecordingNotifier, load_fixture

B2B = "message_with_variables_b2b.json"


class RemoteSink:
    """远程假 sink：可以慢（sleep），也可以抛错。"""

    name = "remote_fake"
    remote = True

    def __init__(self, delay: float = 0.0, fail: bool = False, error: Exception | None = None) -> None:
        self.delay = delay
        self.fail = fail
        self.error = error
        self.calls = 0
        self.leads: list = []

    def upsert_lead(self, lead) -> None:
        self.calls += 1
        if self.delay:
            time.sleep(self.delay)
        if self.fail:
            raise self.error or RuntimeError("remote down")
        self.leads.append(lead)


def outbox(db_path) -> list[tuple]:
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(
            "SELECT lead_id, sink, status, attempts, last_error FROM mirror_outbox ORDER BY id").fetchall()
    finally:
        conn.close()


def make_pipeline(tmp_path, sinks, name: str = "p") -> tuple[Pipeline, object]:
    directory = tmp_path / name
    directory.mkdir(parents=True, exist_ok=True)
    settings = Settings(_env_file=None, botmaker_webhook_token="t", database_path=directory / "l.db",
                        csv_export_path=directory / "l.csv")
    pipeline = Pipeline(settings, SqliteStore(settings.database_path), sinks, [RecordingNotifier()],
                        retry_policy=NO_WAIT)
    return pipeline, settings.database_path


def test_slow_remote_sink_is_not_called_in_the_request_path(tmp_path):
    slow = RemoteSink(delay=1.5)
    pipeline, db = make_pipeline(tmp_path, [slow], "slow")

    started = time.perf_counter()
    result = pipeline.handle(load_fixture(B2B))
    elapsed = time.perf_counter() - started

    assert elapsed < 0.5                       # 应答不等远程
    assert slow.calls == 0                     # 请求路径里一次都没调
    assert result.mirror_queued is True
    assert outbox(db) == [(result.lead_id, "remote_fake", "pending", 0, None)]


def test_mirror_sends_the_pending_row_once_and_marks_it_sent(tmp_path):
    sink = RemoteSink()
    pipeline, db = make_pipeline(tmp_path, [sink], "send")
    result = pipeline.handle(load_fixture(B2B))

    assert pipeline.mirror(result.lead_id) == {"remote_fake": "sent"}
    assert sink.calls == 1 and sink.leads[0].lead_id == result.lead_id
    assert outbox(db) == [(result.lead_id, "remote_fake", "sent", 0, None)]
    # 没有待发行时再跑一次：不重复发，也不报错
    assert pipeline.mirror(result.lead_id) == {} and sink.calls == 1


def test_failing_remote_sink_stays_pending_with_attempts_and_last_error(tmp_path):
    sink = RemoteSink(fail=True, error=MirrorError("remote_fake: 服务端 500"))
    pipeline, db = make_pipeline(tmp_path, [sink], "fail")
    result = pipeline.handle(load_fixture(B2B))

    assert pipeline.mirror(result.lead_id) == {"remote_fake": "failed"}
    assert sink.calls == NO_WAIT.attempts                 # 退避重试用完才算失败
    lead_id, name, status, attempts, last_error = outbox(db)[0]
    assert (lead_id, name, status, attempts) == (result.lead_id, "remote_fake", "pending", 1)
    assert last_error == "remote_fake: 服务端 500"


def test_a_non_mirror_exception_is_recorded_by_type_only(tmp_path):
    """非 sink 自己的异常只记类型名，异常文本可能带 URL 或密钥。"""
    sink = RemoteSink(fail=True, error=RuntimeError("https://open.feishu.cn/secret-token"))
    pipeline, db = make_pipeline(tmp_path, [sink], "opaque")
    result = pipeline.handle(load_fixture(B2B))
    pipeline.mirror(result.lead_id)

    assert outbox(db)[0][4] == "RuntimeError"


def test_replay_retries_the_mirror_until_it_succeeds(tmp_path):
    sink = RemoteSink(fail=True)
    pipeline, db = make_pipeline(tmp_path, [sink], "replay")
    result = pipeline.handle(load_fixture(B2B))
    pipeline.mirror(result.lead_id)
    assert outbox(db)[0][2] == "pending"

    sink.fail = False
    counts = replay(pipeline)

    assert counts["mirrors"] == 1
    assert outbox(db) == [(result.lead_id, "remote_fake", "sent", 1, None)]
    assert replay(pipeline)["mirrors"] == 0      # 发完就不再重试


def test_two_callbacks_for_one_lead_keep_a_single_outbox_row(tmp_path):
    sink = RemoteSink()
    pipeline, db = make_pipeline(tmp_path, [sink], "dedup")
    first = pipeline.handle(load_fixture(B2B))
    second_payload = load_fixture("message_user_first.json")
    second = pipeline.handle(second_payload)
    assert first.lead_id == second.lead_id       # 同一个号码

    rows = outbox(db)
    assert len(rows) == 1 and rows[0][2] == "pending"
    pipeline.mirror(first.lead_id)
    assert sink.calls == 1                       # 两条回调只发一次，发的是当下的最新状态
    assert outbox(db)[0][2] == "sent"

    # 发完之后同一号码再来一条新回调：同一行重新变回 pending，不会长出第二行
    third = load_fixture("message_user_first.json")
    third["messages"][0]["_id_"] = "TRXDEMOMSG-third"
    pipeline.handle(third)
    rows = outbox(db)
    assert len(rows) == 1 and rows[0][2] == "pending"


def test_a_row_whose_sink_disappeared_is_marked_failed(tmp_path):
    sink = RemoteSink()
    pipeline, db = make_pipeline(tmp_path, [sink], "gone")
    result = pipeline.handle(load_fixture(B2B))
    pipeline.sinks = []                          # STORAGE_BACKENDS 改了，行还在

    assert pipeline.mirror(result.lead_id) == {"remote_fake": "failed"}
    assert outbox(db)[0][3] == 1 and "not configured" in outbox(db)[0][4]


def test_mirror_never_raises_even_when_the_store_is_broken(tmp_path):
    pipeline, _ = make_pipeline(tmp_path, [RemoteSink()], "crash")

    def boom(*args, **kwargs):
        raise sqlite3.OperationalError("database is locked")

    pipeline.store.pending_mirrors = boom        # type: ignore[method-assign]
    assert pipeline.mirror("L-whatever") == {}   # 后台任务不许把 worker 带崩


def test_local_csv_sink_still_writes_inside_the_request_path(tmp_path):
    pipeline, db = make_pipeline(tmp_path, [], "csv")
    csv_path = tmp_path / "csv" / "export.csv"
    pipeline.sinks = [CsvExportSink(pipeline.store, csv_path, min_interval_s=0)]

    result = pipeline.handle(load_fixture(B2B))

    assert csv_path.exists() and result.mirror_queued is False
    assert outbox(db) == []                      # 本地 sink 不进 outbox


def test_webhook_answers_before_the_remote_sink_runs_and_mirrors_afterwards(tmp_path):
    settings = Settings(_env_file=None, botmaker_webhook_token="test-token", database_path=tmp_path / "l.db",
                        csv_export_path=tmp_path / "l.csv")
    sink = RemoteSink(delay=0.3)
    client = TestClient(create_app(settings, notifiers=[RecordingNotifier()], sinks=[sink], retry_policy=NO_WAIT))

    response = client.post("/webhooks/botmaker", json=load_fixture(B2B), headers=HEADERS)

    assert response.status_code == 200 and response.json()["status"] == "lead_upserted"
    assert sink.calls == 1                       # TestClient 在返回前跑完后台任务，调用发生在响应之后
    assert outbox(settings.database_path)[0][2] == "sent"


def test_metrics_counts_pending_and_failed_mirrors(tmp_path):
    settings = Settings(_env_file=None, botmaker_webhook_token="test-token", database_path=tmp_path / "l.db",
                        csv_export_path=tmp_path / "l.csv")
    client = TestClient(create_app(settings, notifiers=[RecordingNotifier()], sinks=[RemoteSink(fail=True)],
                                   retry_policy=NO_WAIT))

    body = client.get("/metrics", headers=HEADERS).json()
    assert body["mirror_outbox_pending"] == 0 and body["mirror_outbox_failed_24h"] == 0

    client.post("/webhooks/botmaker", json=load_fixture(B2B), headers=HEADERS)
    body = client.get("/metrics", headers=HEADERS).json()

    assert body["mirror_outbox_pending"] == 1    # 后台镜像试过一次、失败、还挂着
    assert body["mirror_outbox_failed_24h"] == 1


def test_delete_lead_removes_the_outbox_rows_of_that_lead(tmp_path):
    pipeline, db = make_pipeline(tmp_path, [RemoteSink(fail=True)], "forget")
    result = pipeline.handle(load_fixture(B2B))
    pipeline.mirror(result.lead_id)
    lead = pipeline.store.get_lead(result.lead_id)
    assert lead is not None

    digits = "".join(ch for ch in (lead.phone or "") if ch.isdigit()) or None
    preview = pipeline.store.lead_footprint(result.lead_id, digits, None)
    counts = pipeline.store.delete_lead(result.lead_id, digits, None)

    assert preview["mirror_outbox"] == 1 and counts == preview
    assert outbox(db) == []


def test_feishu_bitable_is_remote_and_the_csv_export_is_not():
    assert FeishuBitableSink.remote is True
    assert CsvExportSink.remote is False


# --------------------------------------------------------------- 收尾：重试预算、条件更新、卡住的行
def _payload(company: str, message_id: str) -> dict:
    """同一个号码的又一条回调，公司名可变（用来看发出去的是不是最新状态）。"""
    payload = load_fixture(B2B)
    payload["variables"]["company"] = company
    payload["messages"][0]["_id_"] = message_id
    return payload


def test_re_enqueue_resets_the_retry_budget(tmp_path):
    """线索又变了 = 一份新的活，重试预算重新给满：attempts 归零、last_error 清空。

    不重置的话，同一 (线索, sink) 失败累计满 10 次之后 `pending_mirrors` 再也不取它，
    这行就永远 pending、永不重试。"""
    sink = RemoteSink(fail=True, error=MirrorError("remote_fake: 服务端 500"))
    pipeline, db = make_pipeline(tmp_path, [sink], "budget")
    first = pipeline.handle(_payload("Alpha GmbH", "TRXMSG-B1"))
    pipeline.mirror(first.lead_id)
    assert outbox(db)[0][3] == 1 and outbox(db)[0][4] is not None

    pipeline.handle(_payload("Beta GmbH", "TRXMSG-B2"))

    _, _, status, attempts, last_error = outbox(db)[0]
    assert (status, attempts, last_error) == ("pending", 0, None)


def test_finish_mirror_only_completes_the_version_it_sent(tmp_path):
    """条件更新：拿过期的 updated_at 去标 sent 不生效，行仍 pending、attempts 不变。"""
    pipeline, db = make_pipeline(tmp_path, [RemoteSink()], "version")
    result = pipeline.handle(_payload("Alpha GmbH", "TRXMSG-V1"))
    row = pipeline.store.pending_mirrors(result.lead_id)[0]

    pipeline.handle(_payload("Beta GmbH", "TRXMSG-V2"))        # 发送期间来了新回调，版本变了

    assert pipeline.store.finish_mirror(row.id, True, None, seen_updated_at=row.updated_at) is False
    assert outbox(db)[0][2] == "pending" and outbox(db)[0][3] == 0
    fresh = pipeline.store.pending_mirrors(result.lead_id)[0]   # 拿当下的版本就能标完
    assert pipeline.store.finish_mirror(fresh.id, True, None, seen_updated_at=fresh.updated_at) is True
    assert outbox(db)[0][2] == "sent"


def test_the_row_version_is_strictly_increasing(tmp_path):
    """updated_at 当版本号用：同一毫秒内连着入队也必须严格递增，否则条件更新分不出新旧。"""
    pipeline, _ = make_pipeline(tmp_path, [RemoteSink()], "monotonic")
    result = pipeline.handle(_payload("Alpha GmbH", "TRXMSG-M1"))

    seen = []
    for _ in range(5):
        pipeline.store.enqueue_mirror(result.lead_id, "remote_fake")
        seen.append(pipeline.store.pending_mirrors(result.lead_id)[0].updated_at)

    assert seen == sorted(seen) and len(set(seen)) == len(seen)


def test_a_callback_during_the_send_is_not_lost(tmp_path):
    """发送期间同一线索来了新回调：第一遍被超过，第二遍把最新状态发出去。"""

    class ReentrantSink(RemoteSink):
        def __init__(self) -> None:
            super().__init__()
            self.companies: list = []
            self.hook = None

        def upsert_lead(self, lead) -> None:
            self.companies.append(lead.company)
            if self.hook is not None:
                hook, self.hook = self.hook, None
                hook()
            super().upsert_lead(lead)

    sink = ReentrantSink()
    pipeline, db = make_pipeline(tmp_path, [sink], "race")
    result = pipeline.handle(_payload("Old GmbH", "TRXMSG-R1"))
    sink.hook = lambda: pipeline.handle(_payload("New GmbH", "TRXMSG-R2"))

    assert pipeline.mirror(result.lead_id) == {"remote_fake": "sent"}
    assert sink.companies == ["Old GmbH", "New GmbH"]          # 第二遍发的是最新状态
    assert outbox(db)[0][2] == "sent"


def test_a_second_supersede_leaves_the_row_for_the_next_run(tmp_path):
    """连着两次被超过就收手：最多两遍，行留着 pending 交给下次回调 / replay。"""

    class AlwaysReentrantSink(RemoteSink):
        def __init__(self) -> None:
            super().__init__()
            self.pipeline = None
            self.n = 0

        def upsert_lead(self, lead) -> None:
            self.n += 1
            self.pipeline.handle(_payload(f"Company {self.n}", f"TRXMSG-S{self.n}"))
            super().upsert_lead(lead)

    sink = AlwaysReentrantSink()
    pipeline, db = make_pipeline(tmp_path, [sink], "twice")
    sink.pipeline = pipeline
    result = pipeline.handle(_payload("Start GmbH", "TRXMSG-S0"))

    assert pipeline.mirror(result.lead_id) == {"remote_fake": "superseded"}
    assert sink.n == 2                                          # 不无限重试
    assert outbox(db)[0][2] == "pending"


def test_exhausted_rows_are_skipped_visible_and_resettable(tmp_path):
    """卡满 10 次：pending_mirrors 不再取、/metrics 看得到、--reset-mirrors 之后能重发。"""
    sink = RemoteSink(fail=True, error=MirrorError("remote_fake: 服务端 500"))
    pipeline, db = make_pipeline(tmp_path, [sink], "stuck")
    result = pipeline.handle(_payload("Alpha GmbH", "TRXMSG-E1"))
    conn = sqlite3.connect(db)
    conn.execute("UPDATE mirror_outbox SET attempts = 10")
    conn.commit()
    conn.close()

    assert pipeline.store.pending_mirrors() == []               # 不再自动重试
    assert pipeline.store.exhausted_mirrors() == 1
    assert collect(db)["mirror_outbox_exhausted"] == 1

    sink.fail = False
    counts = replay(pipeline, reset_mirrors=True)

    assert counts["mirrors_reset"] == 1 and counts["mirrors"] == 1
    assert outbox(db)[0][2] == "sent"
    assert collect(db)["mirror_outbox_exhausted"] == 0
    assert pipeline.store.get_lead(result.lead_id) is not None


def test_replay_without_the_flag_leaves_exhausted_rows_alone(tmp_path):
    """默认不重置：卡住的行原样留着，等人看过 last_error 再说。"""
    pipeline, db = make_pipeline(tmp_path, [RemoteSink(fail=True)], "no-reset")
    pipeline.handle(_payload("Alpha GmbH", "TRXMSG-N1"))
    conn = sqlite3.connect(db)
    conn.execute("UPDATE mirror_outbox SET attempts = 10")
    conn.commit()
    conn.close()

    counts = replay(pipeline)

    assert counts["mirrors_reset"] == 0 and counts["mirrors"] == 0
    assert outbox(db)[0][2] == "pending" and outbox(db)[0][3] == 10
