"""Authentication API routes."""

import logging
import os
import re
import secrets
import shutil
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy import func, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database.connection import DB_DIR, get_db
from backend.database.models import Branch, Company, EmailVerificationOTP, PasswordResetToken, User, UserRole
from backend.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    LEGACY_DATASETS_DB,
    authenticate_user,
    build_access_token_payload,
    canonicalize_email,
    create_access_token,
    find_user_by_email,
    get_current_user,
    get_password_hash,
    hash_one_time_token,
    normalize_role,
    verify_password,
)
from backend.services.email_service import EmailDeliveryError, EmailDeliveryResult, build_frontend_url, send_transactional_email
from backend.services.email_templates import render_email_verification_email, render_password_reset_email
from src.tenant_paths import ensure_tenant_directories, tenant_scope_dir

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

logger = logging.getLogger(__name__)

EMAIL_VERIFICATION_OTP_MINUTES = int(os.getenv("EMAIL_VERIFICATION_OTP_MINUTES", "10"))
EMAIL_VERIFICATION_MAX_ATTEMPTS = int(os.getenv("EMAIL_VERIFICATION_MAX_ATTEMPTS", "5"))
EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS = int(os.getenv("EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS", "60"))
EMAIL_VERIFICATION_MAX_SENDS_PER_HOUR = int(os.getenv("EMAIL_VERIFICATION_MAX_SENDS_PER_HOUR", "5"))
PASSWORD_RESET_TOKEN_MINUTES = int(os.getenv("PASSWORD_RESET_TOKEN_MINUTES", "30"))
PASSWORD_RESET_REQUEST_COOLDOWN_SECONDS = int(os.getenv("PASSWORD_RESET_REQUEST_COOLDOWN_SECONDS", "60"))
PASSWORD_RESET_MAX_REQUESTS_PER_HOUR = int(os.getenv("PASSWORD_RESET_MAX_REQUESTS_PER_HOUR", "5"))
GENERIC_PASSWORD_RESET_MESSAGE = "If an account with that email exists, password reset instructions have been sent."


def _safe_company_name(user: User, db: Session) -> Optional[str]:
    """Return a company name without failing login if the relationship is missing."""
    try:
        if getattr(user, "company", None) is not None:
            name = getattr(user.company, "name", None)
            if name:
                return str(name)
    except Exception:
        pass

    try:
        company = db.query(Company).filter(Company.id == user.company_id).first()
        if company and company.name:
            return str(company.name)
    except Exception:
        pass

    return None


def _to_user_response(user: User, db: Session) -> "UserResponse":
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=normalize_role(user.role).value,
        company_id=user.company_id,
        branch_id=user.branch_id,
        company_name=_safe_company_name(user, db),
        is_active=user.is_active,
        is_email_verified=user.is_email_verified,
        created_at=user.created_at.isoformat(),
        last_login=user.last_login.isoformat() if user.last_login else None,
    )


def _to_token_response(user: User, db: Session) -> "TokenResponse":
    access_token = create_access_token(
        data=build_access_token_payload(user, db),
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=_to_user_response(user, db),
    )


def _slugify_company_name(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug or "company"


def _unique_company_slug(db: Session, company_name: str) -> str:
    base_slug = _slugify_company_name(company_name)
    slug = base_slug
    suffix = 2
    while db.query(Company).filter(Company.slug == slug).first() is not None:
        slug = f"{base_slug}-{suffix}"
        suffix += 1
    return slug


def _open_legacy_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(LEGACY_DATASETS_DB)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_legacy_registration_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS branches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id TEXT NOT NULL,
            name TEXT NOT NULL,
            city TEXT NOT NULL,
            phone TEXT,
            manager_id TEXT,
            created_at TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            full_name TEXT,
            role TEXT NOT NULL DEFAULT 'employee',
            branch_id INTEGER,
            company_id TEXT,
            created_at TEXT NOT NULL,
            hashed_password TEXT,
            phone TEXT,
            is_active INTEGER NOT NULL DEFAULT 1,
            email_verified INTEGER NOT NULL DEFAULT 1
        )
        """
    )

    branch_cols = [row[1] for row in conn.execute("PRAGMA table_info(branches)").fetchall()]
    if "phone" not in branch_cols:
        conn.execute("ALTER TABLE branches ADD COLUMN phone TEXT")
    if "is_active" not in branch_cols:
        conn.execute("ALTER TABLE branches ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1")

    user_cols = [row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()]
    if "hashed_password" not in user_cols:
        conn.execute("ALTER TABLE users ADD COLUMN hashed_password TEXT")
    if "phone" not in user_cols:
        conn.execute("ALTER TABLE users ADD COLUMN phone TEXT")
    if "is_active" not in user_cols:
        conn.execute("ALTER TABLE users ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1")
    if "email_verified" not in user_cols:
        conn.execute("ALTER TABLE users ADD COLUMN email_verified INTEGER NOT NULL DEFAULT 1")


def _legacy_email_exists(conn: sqlite3.Connection, email: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM users WHERE lower(email) = ? LIMIT 1",
        (canonicalize_email(email),),
    ).fetchone()
    return row is not None


def _next_shared_id(db: Session, conn: sqlite3.Connection, model, legacy_table: str) -> int:
    auth_max = db.query(func.max(model.id)).scalar() or 0
    legacy_max_row = conn.execute(f"SELECT COALESCE(MAX(id), 0) FROM {legacy_table}").fetchone()
    legacy_max = int(legacy_max_row[0] or 0)
    return max(int(auth_max or 0), legacy_max) + 1


def _sync_postgres_pk_sequence_if_needed(db: Session, table_name: str) -> None:
    bind = db.get_bind()
    if bind is None or bind.dialect.name != "postgresql":
        return
    db.execute(
        text(
            f"SELECT setval(pg_get_serial_sequence('{table_name}', 'id'), GREATEST(COALESCE((SELECT MAX(id) FROM {table_name}), 0), 1), true)"
        )
    )


def _insert_legacy_registration(
    conn: sqlite3.Connection,
    *,
    user_id: int,
    branch_id: int,
    company_name: str,
    branch_name: str,
    full_name: str,
    email: str,
    hashed_password: str,
    created_at: str,
    is_active: bool,
    email_verified: bool,
) -> None:
    conn.execute(
        """
        INSERT INTO branches (id, company_id, name, city, phone, manager_id, created_at, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, 1)
        """,
        (branch_id, company_name, branch_name, branch_name, None, str(user_id), created_at),
    )
    conn.execute(
        """
        INSERT INTO users (id, email, full_name, role, branch_id, company_id, created_at, hashed_password, phone, is_active, email_verified)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            email,
            full_name,
            UserRole.COMPANY_ADMIN.value,
            branch_id,
            company_name,
            created_at,
            hashed_password,
            None,
            1 if is_active else 0,
            1 if email_verified else 0,
        ),
    )


def _cleanup_legacy_registration(conn: sqlite3.Connection, *, branch_id: Optional[int], user_id: Optional[int]) -> None:
    if user_id is not None:
        conn.execute("DELETE FROM users WHERE id = ?", (int(user_id),))
    if branch_id is not None:
        conn.execute("DELETE FROM branches WHERE id = ?", (int(branch_id),))
    conn.commit()


def _cleanup_tenant_workspace(company_root: Optional[Path], created_company_root: bool) -> None:
    if created_company_root and company_root and company_root.exists():
        shutil.rmtree(company_root, ignore_errors=True)


def _utcnow() -> datetime:
    return datetime.utcnow()


def _seconds_until(value: Optional[datetime]) -> int:
    if value is None:
        return 0
    return max(int((value - _utcnow()).total_seconds()), 0)


def _generate_otp_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _generate_password_reset_token() -> str:
    return secrets.token_urlsafe(32)


def _set_legacy_user_status(email: str, *, is_active: bool, email_verified: bool) -> None:
    try:
        conn = _open_legacy_connection()
        try:
            _ensure_legacy_registration_tables(conn)
            conn.execute(
                "UPDATE users SET is_active = ?, email_verified = ? WHERE lower(email) = ?",
                (1 if is_active else 0, 1 if email_verified else 0, canonicalize_email(email)),
            )
            conn.commit()
        finally:
            conn.close()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to sync legacy user activation for %s: %s", email, exc)


def _sync_legacy_password_hash(email: str, hashed_password: str) -> None:
    try:
        conn = _open_legacy_connection()
        try:
            _ensure_legacy_registration_tables(conn)
            conn.execute(
                "UPDATE users SET hashed_password = ? WHERE lower(email) = ?",
                (hashed_password, canonicalize_email(email)),
            )
            conn.commit()
        finally:
            conn.close()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to sync legacy password for %s: %s", email, exc)


def _build_verification_challenge(
    *,
    email: str,
    message: str,
    otp_record: Optional[EmailVerificationOTP],
    email_sent: bool,
) -> "VerificationChallengeResponse":
    has_active_otp = otp_record is not None and not bool(getattr(otp_record, "used", False))
    return VerificationChallengeResponse(
        email=email,
        message=message,
        verification_required=True,
        email_sent=email_sent,
        expires_in=_seconds_until(otp_record.expires_at if has_active_otp else None),
        resend_available_in=EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS if has_active_otp else 0,
    )


def _active_verification_otp(db: Session, user_id: int) -> Optional[EmailVerificationOTP]:
    return (
        db.query(EmailVerificationOTP)
        .filter(EmailVerificationOTP.user_id == int(user_id), EmailVerificationOTP.used.is_(False))
        .order_by(EmailVerificationOTP.created_at.desc())
        .first()
    )


def _invalidate_verification_otps(db: Session, user_id: int, *, used_at: datetime) -> None:
    (
        db.query(EmailVerificationOTP)
        .filter(EmailVerificationOTP.user_id == int(user_id), EmailVerificationOTP.used.is_(False))
        .update(
            {
                EmailVerificationOTP.used: True,
                EmailVerificationOTP.used_at: used_at,
            },
            synchronize_session=False,
        )
    )


def _issue_verification_otp(db: Session, user: User) -> tuple[EmailVerificationOTP, str]:
    now = _utcnow()
    active_otp = _active_verification_otp(db, user.id)
    if active_otp and active_otp.expires_at > now:
        cooldown_deadline = active_otp.created_at + timedelta(seconds=EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS)
        if cooldown_deadline > now:
            remaining = _seconds_until(cooldown_deadline)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Please wait {remaining} seconds before requesting a new code.",
            )

    recent_window_start = now - timedelta(hours=1)
    recent_count = (
        db.query(EmailVerificationOTP)
        .filter(
            EmailVerificationOTP.user_id == int(user.id),
            EmailVerificationOTP.created_at >= recent_window_start,
        )
        .count()
    )
    if recent_count >= EMAIL_VERIFICATION_MAX_SENDS_PER_HOUR:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many verification code requests. Please try again later.",
        )

    _invalidate_verification_otps(db, user.id, used_at=now)
    otp_code = _generate_otp_code()
    otp_record = EmailVerificationOTP(
        user_id=user.id,
        otp_hash=get_password_hash(otp_code),
        expires_at=now + timedelta(minutes=EMAIL_VERIFICATION_OTP_MINUTES),
        attempt_count=0,
        max_attempts=EMAIL_VERIFICATION_MAX_ATTEMPTS,
        used=False,
    )
    db.add(otp_record)
    db.flush()
    return otp_record, otp_code


def _send_verification_email(user: User, company_name: str, otp_code: str) -> EmailDeliveryResult:
    html_body, text_body = render_email_verification_email(
        full_name=user.full_name,
        company_name=company_name,
        otp_code=otp_code,
        expires_minutes=EMAIL_VERIFICATION_OTP_MINUTES,
    )
    return send_transactional_email(
        recipient_email=user.email,
        subject="Verify your InsightPro account",
        html_body=html_body,
        text_body=text_body,
    )


def _issue_password_reset_token(db: Session, user: User) -> Optional[tuple[PasswordResetToken, str]]:
    now = _utcnow()
    active_token = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.user_id == int(user.id), PasswordResetToken.used.is_(False))
        .order_by(PasswordResetToken.created_at.desc())
        .first()
    )
    if active_token:
        cooldown_deadline = active_token.created_at + timedelta(seconds=PASSWORD_RESET_REQUEST_COOLDOWN_SECONDS)
        if cooldown_deadline > now:
            return None

    recent_count = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.user_id == int(user.id),
            PasswordResetToken.created_at >= now - timedelta(hours=1),
        )
        .count()
    )
    if recent_count >= PASSWORD_RESET_MAX_REQUESTS_PER_HOUR:
        return None

    (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.user_id == int(user.id), PasswordResetToken.used.is_(False))
        .update(
            {
                PasswordResetToken.used: True,
                PasswordResetToken.used_at: now,
            },
            synchronize_session=False,
        )
    )

    raw_token = _generate_password_reset_token()
    token_record = PasswordResetToken(
        user_id=user.id,
        token_hash=hash_one_time_token(raw_token),
        expires_at=now + timedelta(minutes=PASSWORD_RESET_TOKEN_MINUTES),
        used=False,
    )
    db.add(token_record)
    db.flush()
    return token_record, raw_token


def _find_reset_token_record(db: Session, token: str) -> Optional[PasswordResetToken]:
    token_hash = hash_one_time_token(token)
    return (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.token_hash == token_hash, PasswordResetToken.used.is_(False))
        .order_by(PasswordResetToken.created_at.desc())
        .first()
    )


def _send_password_reset_email(user: User, raw_token: str) -> EmailDeliveryResult:
    reset_url = build_frontend_url({
        "auth": "reset-password",
        "token": raw_token,
        "email": user.email,
    })
    html_body, text_body = render_password_reset_email(
        full_name=user.full_name,
        reset_url=reset_url,
        expires_minutes=PASSWORD_RESET_TOKEN_MINUTES,
    )
    return send_transactional_email(
        recipient_email=user.email,
        subject="Reset your InsightPro password",
        html_body=html_body,
        text_body=text_body,
    )


# -------------------------------------------------
# Request/Response Models
# -------------------------------------------------
class UserRegister(BaseModel):
    """Tenant registration request."""
    company_name: str
    branch_name: str
    full_name: str
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """User response model (without password)."""
    id: int
    email: str
    full_name: str
    role: str
    company_id: int
    branch_id: Optional[int] = None
    company_name: Optional[str] = None
    is_active: bool
    is_email_verified: bool
    created_at: str
    last_login: Optional[str] = None
    
    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: UserResponse


class VerificationChallengeResponse(BaseModel):
    """Pending verification response after registration or resend."""

    email: str
    message: str
    verification_required: bool = True
    email_sent: bool = True
    expires_in: int
    resend_available_in: int


class VerifyEmailOTPRequest(BaseModel):
    """Verify a newly registered account with a one-time password."""

    email: EmailStr
    otp: str


class ResendVerificationOTPRequest(BaseModel):
    """Request a new email verification OTP."""

    email: EmailStr


class ForgotPasswordRequest(BaseModel):
    """Request a password reset email."""

    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Reset password using a valid one-time token."""

    token: str
    password: str


class ActionMessageResponse(BaseModel):
    """Simple success message response."""

    message: str


class ResetTokenValidationResponse(BaseModel):
    """Reset token validation result for the frontend form."""

    valid: bool
    message: Optional[str] = None


class LoginRequest(BaseModel):
    """Login request."""
    email: EmailStr
    password: str


# -------------------------------------------------
# Authentication Endpoints
# -------------------------------------------------
@router.post("/register", response_model=VerificationChallengeResponse, status_code=status.HTTP_201_CREATED)
def register_user(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):
    """Provision a new tenant and start email verification for the first admin user."""
    company_name = (user_data.company_name or "").strip()
    branch_name = (user_data.branch_name or "").strip()
    full_name = (user_data.full_name or "").strip()
    normalized_email = canonicalize_email(user_data.email)

    if not company_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Company name is required",
        )

    if not branch_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Branch name is required",
        )

    if len(full_name) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Full name must be at least 2 characters long",
        )

    if len(user_data.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
        )

    existing_company = (
        db.query(Company)
        .filter(func.lower(Company.name) == company_name.lower())
        .first()
    )
    if existing_company:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Company name is already registered",
        )

    existing_user = find_user_by_email(db, normalized_email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    legacy_conn: Optional[sqlite3.Connection] = None
    company_root: Optional[Path] = None
    created_company_root = False
    legacy_committed = False
    shared_branch_id: Optional[int] = None
    shared_user_id: Optional[int] = None
    new_user: Optional[User] = None
    pending_otp: Optional[EmailVerificationOTP] = None
    pending_otp_code: Optional[str] = None

    try:
        legacy_conn = _open_legacy_connection()
        _ensure_legacy_registration_tables(legacy_conn)

        if _legacy_email_exists(legacy_conn, normalized_email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        company = Company(
            name=company_name,
            slug=_unique_company_slug(db, company_name),
            description=f"{company_name} workspace",
            data_directory=company_name,
            is_active=True,
        )
        db.add(company)
        db.flush()

        shared_branch_id = _next_shared_id(db, legacy_conn, Branch, "branches")
        shared_user_id = _next_shared_id(db, legacy_conn, User, "users")

        branch = Branch(
            id=shared_branch_id,
            company_id=company.id,
            name=branch_name,
            city=branch_name,
            is_active=True,
        )
        db.add(branch)
        db.flush()

        hashed_password = get_password_hash(user_data.password)
        new_user = User(
            id=shared_user_id,
            email=normalized_email,
            full_name=full_name,
            hashed_password=hashed_password,
            role=UserRole.COMPANY_ADMIN,
            company_id=company.id,
            branch_id=branch.id,
            is_active=False,
            is_email_verified=False,
        )
        db.add(new_user)
        db.flush()

        branch.manager_id = new_user.id
        db.flush()

        pending_otp, pending_otp_code = _issue_verification_otp(db, new_user)

        _sync_postgres_pk_sequence_if_needed(db, "branches")
        _sync_postgres_pk_sequence_if_needed(db, "users")

        created_at = (
            new_user.created_at.isoformat()
            if new_user.created_at is not None
            else datetime.utcnow().isoformat()
        )
        _insert_legacy_registration(
            legacy_conn,
            user_id=new_user.id,
            branch_id=branch.id,
            company_name=company.name,
            branch_name=branch.name,
            full_name=new_user.full_name,
            email=new_user.email,
            hashed_password=hashed_password,
            created_at=created_at,
            is_active=False,
            email_verified=False,
        )

        company_root = tenant_scope_dir(DB_DIR, company.name, None).parent
        created_company_root = not company_root.exists()
        ensure_tenant_directories(DB_DIR, company.name, None)
        ensure_tenant_directories(DB_DIR, company.name, branch.id)

        legacy_conn.commit()
        legacy_committed = True
        db.commit()
        db.refresh(new_user)
    except HTTPException:
        db.rollback()
        if legacy_conn is not None:
            legacy_conn.rollback()
            if legacy_committed:
                _cleanup_legacy_registration(legacy_conn, branch_id=shared_branch_id, user_id=shared_user_id)
        _cleanup_tenant_workspace(company_root, created_company_root)
        raise
    except (IntegrityError, sqlite3.Error):
        db.rollback()
        if legacy_conn is not None:
            legacy_conn.rollback()
            if legacy_committed:
                _cleanup_legacy_registration(legacy_conn, branch_id=shared_branch_id, user_id=shared_user_id)
        _cleanup_tenant_workspace(company_root, created_company_root)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration could not be completed. Please try again.",
        )
    except OSError:
        db.rollback()
        if legacy_conn is not None:
            legacy_conn.rollback()
            if legacy_committed:
                _cleanup_legacy_registration(legacy_conn, branch_id=shared_branch_id, user_id=shared_user_id)
        _cleanup_tenant_workspace(company_root, created_company_root)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Workspace provisioning failed. Please try again.",
        )
    finally:
        if legacy_conn is not None:
            legacy_conn.close()

    if new_user is None or pending_otp is None or pending_otp_code is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration could not be completed.",
        )

    challenge_otp_record = pending_otp
    email_sent = True
    message = "Registration successful. Enter the verification code sent to your email."
    try:
        delivery_result = _send_verification_email(new_user, company_name, pending_otp_code)
        if not delivery_result.delivered_externally:
            email_sent = False
            message = "Registration completed, but email delivery is running in console mode. Check backend logs for the verification code or configure SMTP to send real emails."
    except EmailDeliveryError as exc:
        logger.warning("Failed to send verification email to %s: %s", new_user.email, exc)
        email_sent = False
        message = "Registration completed, but the verification email could not be sent. Use resend to request a new code."

    return _build_verification_challenge(
        email=new_user.email,
        message=message,
        otp_record=challenge_otp_record,
        email_sent=email_sent,
    )


@router.post("/login", response_model=TokenResponse)
def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """Login and receive JWT access token.
    
    **Returns:**
    - JWT access token (valid for 24 hours by default)
    - User information
    """
    user = authenticate_user(db, login_data.email, login_data.password)
    
    if not user:
        pending_user = find_user_by_email(db, login_data.email)
        if pending_user and verify_password(login_data.password, pending_user.hashed_password):
            if not pending_user.is_email_verified:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Email address is not verified. Please verify your email to continue.",
                )
            if not pending_user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User account is inactive",
                )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return _to_token_response(user, db)


@router.post("/login/form", response_model=TokenResponse)
def login_form(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login endpoint compatible with OAuth2PasswordRequestForm.
    
    Used by FastAPI's automatic Swagger UI authentication.
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    
    if not user:
        pending_user = find_user_by_email(db, form_data.username)
        if pending_user and verify_password(form_data.password, pending_user.hashed_password):
            if not pending_user.is_email_verified:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Email address is not verified. Please verify your email to continue.",
                )
            if not pending_user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User account is inactive",
                )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return _to_token_response(user, db)


@router.post("/verify-email", response_model=TokenResponse)
def verify_email_otp(
    payload: VerifyEmailOTPRequest,
    db: Session = Depends(get_db),
):
    """Verify a registration OTP, activate the user, and issue a JWT."""

    otp_code = (payload.otp or "").strip()
    if len(otp_code) != 6 or not otp_code.isdigit():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code must be a 6-digit number.",
        )

    user = find_user_by_email(db, payload.email)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Verification request not found.")

    if user.is_email_verified and user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is already verified. Please sign in.")

    otp_record = _active_verification_otp(db, user.id)
    if otp_record is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active verification code found. Please request a new code.",
        )

    now = _utcnow()
    if otp_record.expires_at <= now:
        otp_record.used = True
        otp_record.used_at = now
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code expired. Please request a new code.",
        )

    if otp_record.attempt_count >= otp_record.max_attempts:
        otp_record.used = True
        otp_record.used_at = now
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many incorrect attempts. Please request a new code.",
        )

    if not verify_password(otp_code, otp_record.otp_hash):
        otp_record.attempt_count += 1
        if otp_record.attempt_count >= otp_record.max_attempts:
            otp_record.used = True
            otp_record.used_at = now
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many incorrect attempts. Please request a new code.",
            )
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect verification code.")

    _invalidate_verification_otps(db, user.id, used_at=now)
    user.is_active = True
    user.is_email_verified = True
    user.email_verified_at = now
    user.last_login = now
    db.commit()
    db.refresh(user)
    _set_legacy_user_status(user.email, is_active=True, email_verified=True)
    return _to_token_response(user, db)


@router.post("/verify-email/resend", response_model=VerificationChallengeResponse)
def resend_email_otp(
    payload: ResendVerificationOTPRequest,
    db: Session = Depends(get_db),
):
    """Issue and email a fresh OTP for a pending registration."""

    user = find_user_by_email(db, payload.email)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Verification request not found.")

    if user.is_email_verified:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is already verified. Please sign in.")

    otp_record, otp_code = _issue_verification_otp(db, user)
    db.commit()
    db.refresh(otp_record)

    challenge_otp_record = otp_record
    email_sent = True
    message = "A new verification code has been sent to your email."
    try:
        delivery_result = _send_verification_email(user, _safe_company_name(user, db) or "your workspace", otp_code)
        if not delivery_result.delivered_externally:
            email_sent = False
            message = "Email delivery is running in console mode. Check backend logs for the latest verification code or configure SMTP to send real emails."
    except EmailDeliveryError as exc:
        logger.warning("Failed to resend verification email to %s: %s", user.email, exc)
        email_sent = False
        message = "We could not send a new verification email right now. Please try again shortly."

    return _build_verification_challenge(
        email=user.email,
        message=message,
        otp_record=challenge_otp_record,
        email_sent=email_sent,
    )


@router.post("/forgot-password", response_model=ActionMessageResponse)
def forgot_password(
    payload: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    """Request a password reset email for an existing verified account."""

    user = find_user_by_email(db, payload.email)
    if not user:
        return ActionMessageResponse(message=GENERIC_PASSWORD_RESET_MESSAGE)

    # Pending registrations are inactive until the user proves email ownership.
    # A successful password reset uses the same mailbox proof, so allow recovery
    # for unverified accounts while still blocking already-disabled verified users.
    if user.is_email_verified and not user.is_active:
        return ActionMessageResponse(message=GENERIC_PASSWORD_RESET_MESSAGE)

    issued = _issue_password_reset_token(db, user)
    if issued is None:
        return ActionMessageResponse(message=GENERIC_PASSWORD_RESET_MESSAGE)

    token_record, raw_token = issued
    db.commit()
    db.refresh(token_record)

    try:
        delivery_result = _send_password_reset_email(user, raw_token)
        if not delivery_result.delivered_externally:
            logger.warning(
                "Password reset email for %s was rendered in console mode only. Configure SMTP to deliver real emails.",
                user.email,
            )
    except EmailDeliveryError as exc:
        logger.warning("Failed to send password reset email to %s: %s", user.email, exc)
        token_record.used = True
        token_record.used_at = _utcnow()
        db.commit()

    return ActionMessageResponse(message=GENERIC_PASSWORD_RESET_MESSAGE)


@router.get("/reset-password/validate", response_model=ResetTokenValidationResponse)
def validate_reset_password_token(
    token: str,
    db: Session = Depends(get_db),
):
    """Validate a reset token before rendering the password reset form."""

    token_record = _find_reset_token_record(db, token)
    if token_record is None or token_record.expires_at <= _utcnow():
        return ResetTokenValidationResponse(valid=False, message="Reset link is invalid or expired.")

    return ResetTokenValidationResponse(valid=True, message="Reset link is valid.")


@router.post("/reset-password", response_model=ActionMessageResponse)
def reset_password(
    payload: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    """Reset a password using a valid one-time reset token."""

    if len(payload.password or "") < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long",
        )

    token_record = _find_reset_token_record(db, payload.token)
    if token_record is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reset link is invalid or expired.")

    now = _utcnow()
    if token_record.expires_at <= now:
        token_record.used = True
        token_record.used_at = now
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reset link is invalid or expired.")

    user = token_record.user
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reset link is invalid or expired.")

    new_hash = get_password_hash(payload.password)
    user.hashed_password = new_hash
    auto_verified = False
    if not user.is_email_verified:
        user.is_email_verified = True
        user.email_verified_at = now
        user.is_active = True
        auto_verified = True

    (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.user_id == int(user.id), PasswordResetToken.used.is_(False))
        .update(
            {
                PasswordResetToken.used: True,
                PasswordResetToken.used_at: now,
            },
            synchronize_session=False,
        )
    )
    db.commit()
    _sync_legacy_password_hash(user.email, new_hash)
    if auto_verified:
        _set_legacy_user_status(user.email, is_active=True, email_verified=True)
    return ActionMessageResponse(message="Password updated successfully. You can sign in now.")


@router.get("/me", response_model=UserResponse)
def get_current_user_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current authenticated user's information.
    
    **Requires:**
    - Valid JWT token in Authorization header
    
    **Returns:**
    - User profile information
    """
    return _to_user_response(current_user, db)


@router.get("/verify")
def verify_token(current_user: User = Depends(get_current_user)):
    """Verify if a token is valid.
    
    Returns:
        {"valid": True, "email": "user@example.com"}
    """
    return {
        "valid": True,
        "email": current_user.email,
        "role": normalize_role(current_user.role).value,
        "company_id": current_user.company_id,
        "branch_id": current_user.branch_id,
    }
