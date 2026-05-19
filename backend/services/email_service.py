"""Transactional email delivery providers for auth flows."""

from __future__ import annotations

import json
import logging
import os
import smtplib
import ssl
from dataclasses import dataclass
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Mapping
from urllib import error as urllib_error
from urllib import request as urllib_request
from urllib.parse import urlencode, urlparse, parse_qsl, urlunparse

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency is present in normal runtime
    load_dotenv = None


logger = logging.getLogger(__name__)
SELF_DELIVERY_DEBUG_LOG = Path(__file__).resolve().parents[2] / "logs" / "email_self_delivery.log"


class EmailDeliveryError(RuntimeError):
    """Raised when transactional email delivery fails."""


@dataclass(frozen=True)
class EmailDeliveryResult:
    """Outcome of an email send attempt."""

    delivery_mode: str
    delivered_externally: bool


def _normalize_smtp_password(host: str, password: str) -> str:
    if host.strip().lower() == "smtp.gmail.com":
        return password.replace(" ", "")
    return password


def _is_self_delivery(settings: "EmailSettings", recipient_email: str) -> bool:
    recipient = recipient_email.strip().lower()
    sender_candidates = {
        settings.smtp_from_email.strip().lower(),
        settings.smtp_username.strip().lower(),
    }
    sender_candidates.discard("")
    return recipient in sender_candidates


def _mirror_self_delivery(settings: "EmailSettings", recipient_email: str, subject: str, text_body: str) -> None:
    environment = os.getenv("ENVIRONMENT", "development").strip().lower()
    if environment == "production" or not _is_self_delivery(settings, recipient_email):
        return

    SELF_DELIVERY_DEBUG_LOG.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat()
    with SELF_DELIVERY_DEBUG_LOG.open("a", encoding="utf-8") as handle:
        handle.write(f"[{timestamp}] To={recipient_email} Subject={subject}\n")
        handle.write(
            "Self-delivery mirror: sender and recipient are the same mailbox, so your mail provider may show this message under Sent or All Mail instead of Inbox.\n\n"
        )
        handle.write(text_body)
        handle.write("\n" + ("-" * 80) + "\n")

    logger.info("[Email:self-delivery-debug] To=%s Subject=%s Mirror=%s", recipient_email, subject, SELF_DELIVERY_DEBUG_LOG)


def _env_flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class EmailSettings:
    delivery_mode: str
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    smtp_from_email: str
    smtp_from_name: str
    smtp_use_starttls: bool
    smtp_use_ssl: bool
    resend_api_key: str
    resend_api_base_url: str
    frontend_base_url: str

    @classmethod
    def from_env(cls) -> "EmailSettings":
        if load_dotenv is not None:
            load_dotenv()

        environment = os.getenv("ENVIRONMENT", "development").strip().lower()
        default_mode = "smtp" if environment == "production" else "console"
        smtp_host = os.getenv("SMTP_HOST", "").strip()
        smtp_password = _normalize_smtp_password(smtp_host, os.getenv("SMTP_PASSWORD", ""))
        return cls(
            delivery_mode=os.getenv("EMAIL_DELIVERY_MODE", default_mode).strip().lower(),
            smtp_host=smtp_host,
            smtp_port=int(os.getenv("SMTP_PORT", "587") or "587"),
            smtp_username=os.getenv("SMTP_USERNAME", "").strip(),
            smtp_password=smtp_password,
            smtp_from_email=os.getenv("SMTP_FROM_EMAIL", "").strip(),
            smtp_from_name=os.getenv("SMTP_FROM_NAME", "InsightPro").strip() or "InsightPro",
            smtp_use_starttls=_env_flag("SMTP_USE_STARTTLS", True),
            smtp_use_ssl=_env_flag("SMTP_USE_SSL", False),
            resend_api_key=os.getenv("RESEND_API_KEY", "").strip(),
            resend_api_base_url=(os.getenv("RESEND_API_BASE_URL", "https://api.resend.com").strip() or "https://api.resend.com").rstrip("/"),
            frontend_base_url=(os.getenv("FRONTEND_BASE_URL", "http://127.0.0.1:3000").strip() or "http://127.0.0.1:3000").rstrip("/"),
        )


def build_frontend_url(query_params: Mapping[str, str]) -> str:
    settings = EmailSettings.from_env()
    parsed = urlparse(settings.frontend_base_url)
    existing_params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    existing_params.update({key: value for key, value in query_params.items() if value is not None})
    return urlunparse(parsed._replace(query=urlencode(existing_params)))


def _send_via_resend(
    *,
    settings: EmailSettings,
    recipient_email: str,
    subject: str,
    html_body: str,
    text_body: str,
) -> EmailDeliveryResult:
    if not settings.resend_api_key:
        raise EmailDeliveryError("Resend delivery is not configured. Set RESEND_API_KEY.")

    if not settings.smtp_from_email:
        raise EmailDeliveryError("Resend delivery requires SMTP_FROM_EMAIL for the sender address.")

    payload = {
        "from": f"{settings.smtp_from_name} <{settings.smtp_from_email}>",
        "to": [recipient_email],
        "subject": subject,
        "html": html_body,
        "text": text_body,
    }
    request = urllib_request.Request(
        f"{settings.resend_api_base_url}/emails",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.resend_api_key}",
            "Content-Type": "application/json",
            "User-Agent": "InsightPro/1.0",
        },
        method="POST",
    )

    try:
        with urllib_request.urlopen(request, timeout=30) as response:
            response_body = response.read().decode("utf-8") if response else ""
        response_payload = json.loads(response_body) if response_body else {}
    except urllib_error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        try:
            error_payload = json.loads(error_body) if error_body else {}
        except json.JSONDecodeError:
            error_payload = {}
        detail = error_payload.get("message") or error_payload.get("name") or error_body or exc.reason
        raise EmailDeliveryError(f"Resend API request failed ({exc.code}): {detail}") from exc
    except urllib_error.URLError as exc:
        reason = getattr(exc, "reason", exc)
        raise EmailDeliveryError(f"Failed to send email via Resend: {reason}") from exc
    except OSError as exc:
        raise EmailDeliveryError(f"Failed to send email via Resend: {exc}") from exc

    logger.info(
        "[Email:resend] To=%s Subject=%s Id=%s",
        recipient_email,
        subject,
        response_payload.get("id", "unknown"),
    )
    _mirror_self_delivery(settings, recipient_email, subject, text_body)
    return EmailDeliveryResult(delivery_mode=settings.delivery_mode, delivered_externally=True)


def send_transactional_email(*, recipient_email: str, subject: str, html_body: str, text_body: str) -> EmailDeliveryResult:
    settings = EmailSettings.from_env()

    if settings.delivery_mode == "console":
        logger.info("[Email:console] To=%s Subject=%s", recipient_email, subject)
        logger.info("[Email:console] Body:\n%s", text_body)
        _mirror_self_delivery(settings, recipient_email, subject, text_body)
        return EmailDeliveryResult(delivery_mode=settings.delivery_mode, delivered_externally=False)

    if settings.delivery_mode == "resend":
        return _send_via_resend(
            settings=settings,
            recipient_email=recipient_email,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
        )

    if settings.delivery_mode != "smtp":
        raise EmailDeliveryError(f"Unsupported email delivery mode: {settings.delivery_mode}")

    if not settings.smtp_host or not settings.smtp_from_email:
        raise EmailDeliveryError("SMTP email delivery is not configured. Set SMTP_HOST and SMTP_FROM_EMAIL.")

    if settings.smtp_username and not settings.smtp_password:
        raise EmailDeliveryError("SMTP_PASSWORD is required when SMTP_USERNAME is set.")

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
    message["To"] = recipient_email
    message.set_content(text_body)
    message.add_alternative(html_body, subtype="html")

    try:
        if settings.smtp_use_ssl:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=30, context=context) as server:
                if settings.smtp_username:
                    server.login(settings.smtp_username, settings.smtp_password)
                server.send_message(message)
            logger.info("[Email:smtp] To=%s Subject=%s", recipient_email, subject)
            _mirror_self_delivery(settings, recipient_email, subject, text_body)
            return EmailDeliveryResult(delivery_mode=settings.delivery_mode, delivered_externally=True)

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as server:
            server.ehlo()
            if settings.smtp_use_starttls:
                context = ssl.create_default_context()
                server.starttls(context=context)
                server.ehlo()
            if settings.smtp_username:
                server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(message)
        logger.info("[Email:smtp] To=%s Subject=%s", recipient_email, subject)
        _mirror_self_delivery(settings, recipient_email, subject, text_body)
        return EmailDeliveryResult(delivery_mode=settings.delivery_mode, delivered_externally=True)
    except OSError as exc:
        raise EmailDeliveryError(f"Failed to send email: {exc}") from exc