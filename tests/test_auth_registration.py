import sqlite3
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).parent.parent))

import backend.auth as auth_module
import backend.routes.auth_routes as auth_routes
from backend.database.connection import get_db
from backend.database.models import Base, Branch, Company, EmailVerificationOTP, PasswordResetToken, User
from backend.services.email_service import EmailDeliveryResult
from src.tenant_paths import tenant_scope_dir


@pytest.fixture
def registration_client(tmp_path, monkeypatch):
    auth_db_path = tmp_path / "auth.db"
    legacy_db_path = tmp_path / "legacy.db"
    tenant_data_root = tmp_path / "tenant-data"
    sent_verification_messages: list[dict[str, str]] = []
    sent_reset_messages: list[dict[str, str]] = []

    engine = create_engine(
        f"sqlite:///{auth_db_path}",
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    app = FastAPI()
    app.include_router(auth_routes.router)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr(auth_routes, "LEGACY_DATASETS_DB", legacy_db_path)
    monkeypatch.setattr(auth_module, "LEGACY_DATASETS_DB", legacy_db_path)
    monkeypatch.setattr(auth_routes, "DB_DIR", tenant_data_root)
    monkeypatch.setattr(auth_routes, "_generate_otp_code", lambda: "123456")
    monkeypatch.setattr(auth_routes, "_generate_password_reset_token", lambda: "reset-token-123")
    monkeypatch.setattr(
        auth_routes,
        "_send_verification_email",
        lambda user, company_name, otp_code: (
            sent_verification_messages.append(
                {"email": user.email, "company_name": company_name, "otp_code": otp_code}
            )
            or EmailDeliveryResult(delivery_mode="smtp", delivered_externally=True)
        ),
    )
    monkeypatch.setattr(
        auth_routes,
        "_send_password_reset_email",
        lambda user, raw_token: (
            sent_reset_messages.append(
                {"email": user.email, "token": raw_token}
            )
            or EmailDeliveryResult(delivery_mode="smtp", delivered_externally=True)
        ),
    )

    with TestClient(app) as client:
        yield client, TestingSessionLocal, legacy_db_path, tenant_data_root, sent_verification_messages, sent_reset_messages

    engine.dispose()


def _register_pending_admin(client: TestClient) -> dict:
    payload = {
        "company_name": "Northwind Labs",
        "branch_name": "Headquarters",
        "full_name": "Amina Rahal",
        "email": "AMINA@northwind.example",
        "password": "StrongPass123",
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201
    return payload


def test_register_returns_verification_challenge_and_keeps_user_inactive(registration_client):
    client, session_local, legacy_db_path, tenant_data_root, sent_verification_messages, _ = registration_client

    payload = {
        "company_name": "Northwind Labs",
        "branch_name": "Headquarters",
        "full_name": "Amina Rahal",
        "email": "AMINA@northwind.example",
        "password": "StrongPass123",
    }

    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201

    body = response.json()
    assert body["verification_required"] is True
    assert body["email_sent"] is True
    assert body["email"] == payload["email"].lower()
    assert body["expires_in"] > 0
    assert body["resend_available_in"] == auth_routes.EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS

    assert sent_verification_messages == [
        {
            "email": payload["email"].lower(),
            "company_name": payload["company_name"],
            "otp_code": "123456",
        }
    ]

    with session_local() as db:
        company = db.query(Company).one()
        branch = db.query(Branch).one()
        user = db.query(User).one()
        otp_record = db.query(EmailVerificationOTP).one()
        branch_id = branch.id
        user_id = user.id

        assert company.name == payload["company_name"]
        assert branch.company_id == company.id
        assert branch.manager_id == user.id
        assert user.company_id == company.id
        assert user.branch_id == branch.id
        assert user.email == payload["email"].lower()
        assert user.role.value == "company_admin"
        assert user.is_active is False
        assert user.is_email_verified is False
        assert otp_record.user_id == user.id
        assert otp_record.used is False
        assert otp_record.attempt_count == 0
        assert otp_record.max_attempts == auth_routes.EMAIL_VERIFICATION_MAX_ATTEMPTS

    conn = sqlite3.connect(legacy_db_path)
    conn.row_factory = sqlite3.Row
    try:
        legacy_branch = conn.execute("SELECT * FROM branches").fetchone()
        legacy_user = conn.execute("SELECT * FROM users").fetchone()
    finally:
        conn.close()

    assert legacy_branch is not None
    assert legacy_user is not None
    assert int(legacy_branch["id"]) == branch_id
    assert legacy_branch["company_id"] == payload["company_name"]
    assert legacy_branch["name"] == payload["branch_name"]
    assert str(legacy_branch["manager_id"]) == str(user_id)
    assert int(legacy_user["id"]) == user_id
    assert legacy_user["company_id"] == payload["company_name"]
    assert int(legacy_user["branch_id"]) == branch_id
    assert legacy_user["role"] == "company_admin"
    assert int(legacy_user["is_active"]) == 0
    assert int(legacy_user["email_verified"]) == 0

    assert tenant_scope_dir(tenant_data_root, payload["company_name"], None).exists()
    assert tenant_scope_dir(tenant_data_root, payload["company_name"], branch_id).exists()


def test_unverified_user_cannot_login_until_otp_verified(registration_client):
    client, _, _, _, _, _ = registration_client

    payload = {
        "company_name": "Northwind Labs",
        "branch_name": "Headquarters",
        "full_name": "Amina Rahal",
        "email": "AMINA@northwind.example",
        "password": "StrongPass123",
    }
    register_response = client.post("/api/auth/register", json=payload)
    assert register_response.status_code == 201

    login_response = client.post(
        "/api/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    assert login_response.status_code == 403
    assert login_response.json()["detail"] == "Email address is not verified. Please verify your email to continue."


def test_register_console_mode_does_not_claim_external_email_delivery(registration_client, monkeypatch):
    client, session_local, _, _, _, _ = registration_client

    monkeypatch.setattr(
        auth_routes,
        "_send_verification_email",
        lambda user, company_name, otp_code: EmailDeliveryResult(
            delivery_mode="console",
            delivered_externally=False,
        ),
    )

    payload = {
        "company_name": "Console Labs",
        "branch_name": "HQ",
        "full_name": "Mina Rahal",
        "email": "mina@console.example",
        "password": "StrongPass123",
    }

    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201

    body = response.json()
    assert body["verification_required"] is True
    assert body["email_sent"] is False
    assert "console mode" in body["message"].lower()
    assert body["expires_in"] > 0
    assert body["resend_available_in"] == auth_routes.EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS

    with session_local() as db:
        otp_record = db.query(EmailVerificationOTP).one()
        assert otp_record.used is False

    verify_response = client.post(
        "/api/auth/verify-email",
        json={"email": payload["email"], "otp": "123456"},
    )
    assert verify_response.status_code == 200
    verify_body = verify_response.json()
    assert verify_body["access_token"]
    assert verify_body["user"]["role"] == "company_admin"
    assert verify_body["user"]["is_email_verified"] is True

    token_check = client.get(
        "/api/auth/verify",
        headers={"Authorization": f"Bearer {verify_body['access_token']}"},
    )
    assert token_check.status_code == 200


def test_register_rejects_duplicate_email_case_insensitive(registration_client):
    client, session_local, _, _, _, _ = registration_client

    first_payload = {
        "company_name": "Blue Orbit",
        "branch_name": "Main Office",
        "full_name": "Karim Benali",
        "email": "karim@blueorbit.example",
        "password": "StrongPass123",
    }
    second_payload = {
        "company_name": "Blue Orbit Two",
        "branch_name": "Main Office",
        "full_name": "Karim Benali",
        "email": "KARIM@blueorbit.example",
        "password": "StrongPass123",
    }

    first_response = client.post("/api/auth/register", json=first_payload)
    assert first_response.status_code == 201

    second_response = client.post("/api/auth/register", json=second_payload)
    assert second_response.status_code == 400
    assert second_response.json()["detail"] == "Email already registered"

    with session_local() as db:
        assert db.query(Company).count() == 1
        assert db.query(Branch).count() == 1
        assert db.query(User).count() == 1
        assert db.query(EmailVerificationOTP).count() == 1


def test_forgot_password_resets_hash_and_invalidates_token(registration_client):
    client, session_local, legacy_db_path, _, _, sent_reset_messages = registration_client

    payload = {
        "company_name": "Atlas Retail",
        "branch_name": "Downtown",
        "full_name": "Sami Khellaf",
        "email": "sami@atlas.example",
        "password": "OldPassword123",
    }
    register_response = client.post("/api/auth/register", json=payload)
    assert register_response.status_code == 201
    verify_response = client.post(
        "/api/auth/verify-email",
        json={"email": payload["email"], "otp": "123456"},
    )
    assert verify_response.status_code == 200

    forgot_response = client.post(
        "/api/auth/forgot-password",
        json={"email": payload["email"]},
    )
    assert forgot_response.status_code == 200
    assert forgot_response.json()["message"] == auth_routes.GENERIC_PASSWORD_RESET_MESSAGE
    assert sent_reset_messages == [{"email": payload["email"], "token": "reset-token-123"}]

    validate_response = client.get("/api/auth/reset-password/validate", params={"token": "reset-token-123"})
    assert validate_response.status_code == 200
    assert validate_response.json()["valid"] is True

    reset_response = client.post(
        "/api/auth/reset-password",
        json={"token": "reset-token-123", "password": "NewPassword123"},
    )
    assert reset_response.status_code == 200
    assert reset_response.json()["message"] == "Password updated successfully. You can sign in now."

    old_login = client.post(
        "/api/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    assert old_login.status_code == 401

    new_login = client.post(
        "/api/auth/login",
        json={"email": payload["email"], "password": "NewPassword123"},
    )
    assert new_login.status_code == 200

    with session_local() as db:
        user = db.query(User).one()
        token_record = db.query(PasswordResetToken).one()
        assert auth_module.verify_password("NewPassword123", user.hashed_password) is True
        assert token_record.used is True
        assert token_record.used_at is not None

    conn = sqlite3.connect(legacy_db_path)
    conn.row_factory = sqlite3.Row
    try:
        legacy_user = conn.execute("SELECT hashed_password FROM users WHERE lower(email) = ?", (payload["email"],)).fetchone()
    finally:
        conn.close()

    assert legacy_user is not None
    assert auth_module.verify_password("NewPassword123", legacy_user["hashed_password"]) is True


def test_forgot_password_can_recover_unverified_registration(registration_client):
    client, session_local, legacy_db_path, _, _, sent_reset_messages = registration_client

    payload = {
        "company_name": "Pending Retail",
        "branch_name": "Central",
        "full_name": "Nadia Rahal",
        "email": "nadia@pending.example",
        "password": "InitialPass123",
    }
    register_response = client.post("/api/auth/register", json=payload)
    assert register_response.status_code == 201

    forgot_response = client.post(
        "/api/auth/forgot-password",
        json={"email": payload["email"]},
    )
    assert forgot_response.status_code == 200
    assert forgot_response.json()["message"] == auth_routes.GENERIC_PASSWORD_RESET_MESSAGE
    assert sent_reset_messages == [{"email": payload["email"], "token": "reset-token-123"}]

    validate_response = client.get("/api/auth/reset-password/validate", params={"token": "reset-token-123"})
    assert validate_response.status_code == 200
    assert validate_response.json()["valid"] is True

    reset_response = client.post(
        "/api/auth/reset-password",
        json={"token": "reset-token-123", "password": "RecoveredPass123"},
    )
    assert reset_response.status_code == 200
    assert reset_response.json()["message"] == "Password updated successfully. You can sign in now."

    login_response = client.post(
        "/api/auth/login",
        json={"email": payload["email"], "password": "RecoveredPass123"},
    )
    assert login_response.status_code == 200

    with session_local() as db:
        user = db.query(User).filter(User.email == payload["email"]).one()
        token_record = db.query(PasswordResetToken).one()
        assert user.is_active is True
        assert user.is_email_verified is True
        assert user.email_verified_at is not None
        assert auth_module.verify_password("RecoveredPass123", user.hashed_password) is True
        assert token_record.used is True
        assert token_record.used_at is not None

    conn = sqlite3.connect(legacy_db_path)
    conn.row_factory = sqlite3.Row
    try:
        legacy_user = conn.execute(
            "SELECT hashed_password, is_active, email_verified FROM users WHERE lower(email) = ?",
            (payload["email"],),
        ).fetchone()
    finally:
        conn.close()

    assert legacy_user is not None
    assert auth_module.verify_password("RecoveredPass123", legacy_user["hashed_password"]) is True
    assert legacy_user["is_active"] == 1
    assert legacy_user["email_verified"] == 1