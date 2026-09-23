from __future__ import annotations

import json
import smtplib
import ssl
from datetime import datetime, timezone

import httpx
import pytest

from app.config import Settings
from app.models import BotmakerWebhook
from app.normalize import collect_message_facts, extract_phone, merge_message
from app.notify import (
    EmailNotifier,
    FeishuNotifier,
    GenericWebhookNotifier,
    NotifyError,
    WeComNotifier,
    build_card,
    build_notifiers,
)
from app.notify.feishu import feishu_sign

from webhook_test_helpers import load_fixture

NOW = datetime(2026, 11, 4, 19, 17, 40, tzinfo=timezone.utc)   # one minute after the customer's last message
SECRET_URL = "https://open.feishu.cn/open-apis/bot/v2/hook/SECRET-TOKEN-VALUE"


def _lead():
    lead = None
    for name in ("message_user_first.json", "message_with_variables_b2b.json"):
        payload = BotmakerWebhook.model_validate(load_fixture(name))
        lead = merge_message(lead, extract_phone(payload), collect_message_facts(payload))
    return lead


def _card(**overrides):
    options = dict(customer_id="TRXDEMOCUSTOMER00001", mask=True,
                   chat_url_template="https://go.botmaker.com/#/chats/{customer_id}",
                   display_timezone="Asia/Shanghai", now=NOW)
    options.update(overrides)
    return build_card(_lead(), **options)


def test_card_content_masked_phone_and_window_deadline():
    card = _card()
    fields = dict(card.fields)
    assert card.title == "新线索待接手 | B 端 / distributor | DE" and card.priority == "high"
    assert fields["接管原因"] == "B 端信息已收集完成"
    assert fields["国家"] == "DE（客户自述）" and fields["类型"] == "B 端 / distributor"
    assert fields["公司 / 联系人"] == "Nordrad Mobility GmbH / Jonas Keller / purchasing manager"
    assert fields["意向产品"] == "MC10、UKKO" and fields["数量"] == "about 40 units per year"
    assert fields["来源"] == "instagram（IG-2609）" and fields["优先级"] == "高"
    assert fields["号码"] == "尾号 9011"
    # last customer message 2026-11-04 19:16:40 UTC + 24 h = 2026-11-06 03:16 in Asia/Shanghai
    assert fields["24 小时窗口截止"] == "2026-11-06 03:16（Asia/Shanghai），剩余约 24.0 小时"
    assert card.link_url == "https://go.botmaker.com/#/chats/TRXDEMOCUSTOMER00001"
    assert "个人 WhatsApp" in card.footer and "Nordrad" in card.summary
    assert "4917604069011" not in card.to_markdown() + card.to_text() + json.dumps(card.to_dict())


def test_card_can_show_full_phone_and_reports_a_closed_window():
    card = _card(mask=False, now=datetime(2026, 11, 7, tzinfo=timezone.utc), customer_id=None)
    fields = dict(card.fields)
    assert fields["号码"] == "+4917604069011"
    assert "已关闭，只能发已审核的模板消息" in fields["24 小时窗口截止"]
    assert card.link_url is None


def test_feishu_signature_matches_the_documented_algorithm():
    # independent vector: printf '' | openssl dgst -sha256 -hmac $'1730000000\ntest-secret' -binary | base64
    assert feishu_sign("1730000000", "test-secret") == "s/83FabUZ3qM7iGhNM7nq1UAiWpFgs/DG9mQ19CFs44="


def test_feishu_body_and_signature_are_sent():
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"], seen["body"] = str(request.url), json.loads(request.content)
        return httpx.Response(200, json={"code": 0, "msg": "success"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    FeishuNotifier(SECRET_URL, "test-secret", client=client, clock=lambda: 1730000000.9).send(_card())
    body = seen["body"]
    assert seen["url"] == SECRET_URL and body["msg_type"] == "interactive"
    assert body["timestamp"] == "1730000000" and body["sign"] == "s/83FabUZ3qM7iGhNM7nq1UAiWpFgs/DG9mQ19CFs44="
    assert body["card"]["header"]["template"] == "red"
    assert body["card"]["elements"][1]["actions"][0]["url"].endswith("TRXDEMOCUSTOMER00001")
    assert "尾号 9011" in body["card"]["elements"][0]["text"]["content"]


def test_feishu_without_secret_sends_no_signature():
    body = FeishuNotifier(SECRET_URL).build_body(_card())
    assert "sign" not in body and "timestamp" not in body


@pytest.mark.parametrize("response", [
    httpx.Response(200, json={"code": 19021, "msg": "sign match fail"}),
    httpx.Response(500, text="oops"),
])
def test_feishu_errors_raise_without_leaking_the_url(response):
    client = httpx.Client(transport=httpx.MockTransport(lambda request: response))
    with pytest.raises(NotifyError) as excinfo:
        FeishuNotifier(SECRET_URL, client=client).send(_card())
    assert "SECRET-TOKEN-VALUE" not in str(excinfo.value)


def test_transport_error_is_wrapped_without_the_url():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(NotifyError) as excinfo:
        GenericWebhookNotifier("https://hooks.example.com/SECRET-TOKEN-VALUE", client=client).send(_card())
    assert "SECRET-TOKEN-VALUE" not in str(excinfo.value) and "ConnectError" in str(excinfo.value)


def test_wecom_markdown_errcode_and_truncation():
    sent: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(json.loads(request.content))
        return httpx.Response(200, json={"errcode": 0, "errmsg": "ok"})

    notifier = WeComNotifier("https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=SECRET", client=httpx.Client(transport=httpx.MockTransport(handler)))
    notifier.send(_card())
    assert sent[0]["msgtype"] == "markdown" and "**国家**：DE" in sent[0]["markdown"]["content"]

    long_card = build_card(_lead().model_copy(update={"ai_summary": "长" * 3000}), customer_id=None, mask=True,
                           chat_url_template="", display_timezone="Asia/Shanghai", now=NOW)
    assert len(notifier.build_body(long_card)["markdown"]["content"].encode("utf-8")) <= 4096

    failing = WeComNotifier("https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=SECRET", client=httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"errcode": 93000, "errmsg": "invalid"}))))
    with pytest.raises(NotifyError):
        failing.send(_card())


def test_generic_webhook_posts_text_and_structured_card():
    sent: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(json.loads(request.content))
        return httpx.Response(204)

    GenericWebhookNotifier("https://hooks.example.com/x", client=httpx.Client(transport=httpx.MockTransport(handler))).send(_card())
    assert sent[0]["event"] == "lead_escalated" and sent[0]["card"]["priority"] == "high"
    assert sent[0]["text"].startswith("新线索待接手")


class FakeSMTP:
    instances: list["FakeSMTP"] = []

    def __init__(self, host: str, port: int) -> None:
        self.host, self.port, self.steps, self.messages = host, port, [], []
        self.tls_context: ssl.SSLContext | None = None
        FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc) -> bool:
        self.steps.append("quit")
        return False

    def starttls(self, *, context: ssl.SSLContext | None = None):
        self.steps.append("starttls")
        self.tls_context = context

    def login(self, username, password):
        self.steps.append(f"login:{username}")

    def send_message(self, message):
        self.steps.append("send")
        self.messages.append(message)


def test_email_notifier_uses_starttls_login_and_masks_the_phone():
    FakeSMTP.instances.clear()
    EmailNotifier(host="smtp.example.com", port=587, sender="bot@example.com", recipients=["a@example.com", "b@example.com"],
                  username="bot", password="pw", smtp_factory=FakeSMTP).send(_card())
    smtp = FakeSMTP.instances[0]
    assert smtp.steps == ["starttls", "login:bot", "send", "quit"]
    message = smtp.messages[0]
    assert message["To"] == "a@example.com, b@example.com" and message["Subject"].startswith("新线索待接手")
    assert "尾号 9011" in message.get_content() and "4917604069011" not in message.get_content()


def test_email_failure_is_a_notify_error():
    class Broken(FakeSMTP):
        def send_message(self, message):
            raise OSError("network down")

    with pytest.raises(NotifyError):
        EmailNotifier(host="h", port=587, sender="a@example.com", recipients=["b@example.com"], smtp_factory=Broken).send(_card())


def _verifies(context: ssl.SSLContext | None) -> bool:
    return context is not None and context.verify_mode == ssl.CERT_REQUIRED and context.check_hostname is True


def test_email_starttls_verifies_the_server_certificate():
    FakeSMTP.instances.clear()
    EmailNotifier(host="smtp.example.com", port=587, sender="bot@example.com", recipients=["a@example.com"],
                  username="bot", password="pw", smtp_factory=FakeSMTP).send(_card())
    assert _verifies(FakeSMTP.instances[0].tls_context)


def test_email_implicit_tls_on_465_verifies_the_server_certificate(monkeypatch):
    opened: list[dict] = []

    class RecordingSSL(FakeSMTP):
        def __init__(self, host, port, **kwargs):
            super().__init__(host, port)
            opened.append(kwargs)

    monkeypatch.setattr(smtplib, "SMTP_SSL", RecordingSSL)
    FakeSMTP.instances.clear()
    EmailNotifier(host="smtp.example.com", port=465, sender="bot@example.com", recipients=["a@example.com"],
                  username="bot", password="pw").send(_card())   # default factory
    assert opened[0]["timeout"] == 15 and _verifies(opened[0]["context"])
    assert FakeSMTP.instances[0].steps == ["login:bot", "send", "quit"]   # no STARTTLS on an implicit-TLS port


def test_email_certificate_failure_is_a_notify_error_without_the_password():
    class Intercepted(FakeSMTP):
        def starttls(self, *, context=None):
            raise ssl.SSLCertVerificationError(1, "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: "
                                                  "self-signed certificate (_ssl.c:1006)")

    with pytest.raises(NotifyError) as excinfo:
        EmailNotifier(host="smtp.example.com", port=587, sender="a@example.com", recipients=["b@example.com"],
                      username="bot", password="SMTP-PASSWORD-VALUE", smtp_factory=Intercepted).send(_card())
    assert str(excinfo.value) == "email: SSLCertVerificationError"


# ------------------------------------------------------------------ 非 2xx 一律算发送失败（3xx 也是）
_REDIRECT_TARGETS = [
    ("generic", lambda client: GenericWebhookNotifier("https://hooks.example.com/SECRET-TOKEN-VALUE", client=client)),
    ("feishu", lambda client: FeishuNotifier(SECRET_URL, client=client)),
    ("wecom", lambda client: WeComNotifier("https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=SECRET-TOKEN-VALUE",
                                           client=client)),
]


@pytest.mark.parametrize("status", [301, 302])
@pytest.mark.parametrize(("channel", "make"), _REDIRECT_TARGETS, ids=[c for c, _ in _REDIRECT_TARGETS])
def test_a_redirect_is_a_failed_delivery_not_a_sent_card(channel, make, status):
    client = httpx.Client(transport=httpx.MockTransport(
        lambda request: httpx.Response(status, headers={"location": "https://elsewhere.example.com/"})))
    with pytest.raises(NotifyError) as excinfo:
        make(client).send(_card())
    assert str(excinfo.value) == f"{channel}: HTTP {status}"
    assert "SECRET-TOKEN-VALUE" not in str(excinfo.value) and "elsewhere" not in str(excinfo.value)


# ------------------------------------------------------------------ send_text（周报摘要等纯文字消息）
TEXT_TITLE = "调优期周报 2026-11-09 至 2026-11-16"
TEXT_BODY = "线索 5 条（B 端占比 40.0%）\n转人工率 80.0%\n通知 sent 4 / partial 0 / failed 0"


def _recorder(response: httpx.Response):
    sent: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(json.loads(request.content))
        return response

    return sent, httpx.Client(transport=httpx.MockTransport(handler))


def test_feishu_send_text_posts_rich_text_with_signature():
    sent, client = _recorder(httpx.Response(200, json={"code": 0, "msg": "success"}))
    FeishuNotifier(SECRET_URL, "test-secret", client=client, clock=lambda: 1730000000.9).send_text(TEXT_TITLE, TEXT_BODY)
    body = sent[0]
    assert body["msg_type"] == "post"
    post = body["content"]["post"]["zh_cn"]
    assert post["title"] == TEXT_TITLE and len(post["content"]) == 3
    assert [block[0]["text"] for block in post["content"]] == TEXT_BODY.split("\n")
    assert body["timestamp"] == "1730000000" and body["sign"] == "s/83FabUZ3qM7iGhNM7nq1UAiWpFgs/DG9mQ19CFs44="


def test_feishu_send_text_error_does_not_leak_the_url():
    _, client = _recorder(httpx.Response(200, json={"code": 19021, "msg": "sign match fail"}))
    with pytest.raises(NotifyError) as excinfo:
        FeishuNotifier(SECRET_URL, client=client).send_text(TEXT_TITLE, TEXT_BODY)
    assert "SECRET-TOKEN-VALUE" not in str(excinfo.value)


def test_wecom_send_text_is_markdown_with_the_title_as_heading():
    sent, client = _recorder(httpx.Response(200, json={"errcode": 0, "errmsg": "ok"}))
    WeComNotifier("https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=SECRET", client=client).send_text(TEXT_TITLE, TEXT_BODY)
    assert sent[0]["msgtype"] == "markdown"
    assert sent[0]["markdown"]["content"] == f"# {TEXT_TITLE}\n{TEXT_BODY}"

    _, failing = _recorder(httpx.Response(200, json={"errcode": 93000, "errmsg": "invalid"}))
    with pytest.raises(NotifyError) as excinfo:
        WeComNotifier("https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=SECRET", client=failing).send_text(TEXT_TITLE, TEXT_BODY)
    assert "SECRET" not in str(excinfo.value)


def test_generic_send_text_posts_a_typed_text_payload():
    sent, client = _recorder(httpx.Response(200, json={"ok": True}))
    GenericWebhookNotifier("https://hooks.example.com/SECRET-TOKEN-VALUE", client=client).send_text(TEXT_TITLE, TEXT_BODY)
    assert sent[0] == {"type": "text", "title": TEXT_TITLE, "text": TEXT_BODY}


def test_generic_send_text_non_2xx_raises_without_the_url():
    _, client = _recorder(httpx.Response(500, json={"error": "boom"}))
    with pytest.raises(NotifyError) as excinfo:
        GenericWebhookNotifier("https://hooks.example.com/SECRET-TOKEN-VALUE", client=client).send_text(TEXT_TITLE, TEXT_BODY)
    assert "SECRET-TOKEN-VALUE" not in str(excinfo.value) and "500" in str(excinfo.value)


def test_email_send_text_uses_the_title_as_subject_and_plain_text_body():
    FakeSMTP.instances.clear()
    EmailNotifier(host="smtp.example.com", port=587, sender="bot@example.com", recipients=["a@example.com"],
                  username="bot", password="pw", smtp_factory=FakeSMTP).send_text(TEXT_TITLE, TEXT_BODY)
    smtp = FakeSMTP.instances[0]
    assert smtp.steps == ["starttls", "login:bot", "send", "quit"]
    message = smtp.messages[0]
    assert message["Subject"] == TEXT_TITLE and message["To"] == "a@example.com"
    assert message.get_content().rstrip("\n") == TEXT_BODY


def test_email_send_text_failure_is_a_notify_error():
    class Broken(FakeSMTP):
        def send_message(self, message):
            raise OSError("network down")

    with pytest.raises(NotifyError) as excinfo:
        EmailNotifier(host="h", port=587, sender="a@example.com", recipients=["b@example.com"],
                      smtp_factory=Broken).send_text(TEXT_TITLE, TEXT_BODY)
    assert "email: OSError" == str(excinfo.value)


def test_build_notifiers_validates_configuration():
    base = dict(_env_file=None, botmaker_webhook_token="t")
    assert build_notifiers(Settings(**base)) == []
    names = [n.name for n in build_notifiers(Settings(
        **base, notifiers="feishu, wecom,generic,email", feishu_webhook_url="https://f.example/x",
        wecom_webhook_url="https://w.example/x", generic_webhook_url="https://g.example/x",
        smtp_host="smtp.example.com", email_from="a@example.com", email_to="b@example.com"))]
    assert names == ["feishu", "wecom", "generic", "email"]
    with pytest.raises(ValueError, match="FEISHU_WEBHOOK_URL"):
        build_notifiers(Settings(**base, notifiers="feishu"))
    with pytest.raises(ValueError, match="unknown notifier"):
        build_notifiers(Settings(**base, notifiers="pager"))


@pytest.mark.parametrize(("field", "env_name", "url"), [
    ("feishu_webhook_url", "FEISHU_WEBHOOK_URL", "http://open.feishu.cn/open-apis/bot/v2/hook/SECRET-TOKEN-VALUE"),
    ("wecom_webhook_url", "WECOM_WEBHOOK_URL", "http://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=SECRET-TOKEN-VALUE"),
])
def test_build_notifiers_requires_https_for_the_bot_urls(field, env_name, url):
    channel = field.split("_")[0]
    with pytest.raises(ValueError, match=f"{env_name} must start with https://") as excinfo:
        build_notifiers(Settings(_env_file=None, notifiers=channel, **{field: url}))
    assert "SECRET-TOKEN-VALUE" not in str(excinfo.value)   # the URL is the secret: never echoed


def test_build_notifiers_leaves_the_generic_webhook_scheme_alone():
    notifiers = build_notifiers(Settings(_env_file=None, notifiers="generic", generic_webhook_url="http://10.0.0.5/hook"))
    assert [n.name for n in notifiers] == ["generic"]
