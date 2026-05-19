import io
import json
from urllib.error import HTTPError

import pytest

from backend.services import email_service


class _FakeResponse:
    def __init__(self, body: dict[str, str]):
        self._body = json.dumps(body).encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


@pytest.fixture
def resend_env(monkeypatch):
    monkeypatch.setenv("EMAIL_DELIVERY_MODE", "resend")
    monkeypatch.setenv("RESEND_API_KEY", "re_test_123")
    monkeypatch.setenv("RESEND_API_BASE_URL", "https://api.resend.com")
    monkeypatch.setenv("SMTP_FROM_EMAIL", "no-reply@example.com")
    monkeypatch.setenv("SMTP_FROM_NAME", "InsightPro")


def test_send_transactional_email_resend_success(resend_env, monkeypatch):
    captured: dict[str, object] = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        captured["authorization"] = request.get_header("Authorization")
        captured["content_type"] = request.get_header("Content-type")
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return _FakeResponse({"id": "email_123"})

    monkeypatch.setattr(email_service.urllib_request, "urlopen", fake_urlopen)

    result = email_service.send_transactional_email(
        recipient_email="user@example.com",
        subject="Welcome",
        html_body="<p>Hello</p>",
        text_body="Hello",
    )

    assert result.delivery_mode == "resend"
    assert result.delivered_externally is True
    assert captured["url"] == "https://api.resend.com/emails"
    assert captured["timeout"] == 30
    assert captured["authorization"] == "Bearer re_test_123"
    assert captured["content_type"] == "application/json"
    assert captured["payload"] == {
        "from": "InsightPro <no-reply@example.com>",
        "to": ["user@example.com"],
        "subject": "Welcome",
        "html": "<p>Hello</p>",
        "text": "Hello",
    }


def test_send_transactional_email_resend_http_error_raises_delivery_error(resend_env, monkeypatch):
    def fake_urlopen(request, timeout):
        raise HTTPError(
            request.full_url,
            403,
            "Forbidden",
            hdrs=None,
            fp=io.BytesIO(b'{"message":"Invalid API key"}'),
        )

    monkeypatch.setattr(email_service.urllib_request, "urlopen", fake_urlopen)

    with pytest.raises(email_service.EmailDeliveryError, match="Invalid API key"):
        email_service.send_transactional_email(
            recipient_email="user@example.com",
            subject="Welcome",
            html_body="<p>Hello</p>",
            text_body="Hello",
        )