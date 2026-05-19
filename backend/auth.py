"""
JWT Authentication utilities.

FEATURES:
- JWT token creation and validation
- Password hashing and verification
- User authentication
- Role-based authorization
"""

import hashlib
import os
import sqlite3
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Any

import bcrypt
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import func
from sqlalchemy.orm import Session

from .database.connection import get_db, SessionLocal
from .database.models import User, UserRole, Branch, Company

# Security configuration
# Keep consistent with backend/main.py to avoid token validation mismatches.
_default_secret = "sales-intelligence-secret-key-change-in-production-2024"
SECRET_KEY = os.getenv("JWT_SECRET_KEY", _default_secret)
ONE_TIME_TOKEN_SECRET = os.getenv("ONE_TIME_TOKEN_SECRET", SECRET_KEY)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 hours

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login/form")
BASE_DIR = Path(__file__).resolve().parent.parent
LEGACY_DATASETS_DB = BASE_DIR / "data" / "datasets.db"


# -------------------------------------------------
# Role normalization (legacy -> SaaS roles)
# -------------------------------------------------
def normalize_role(role: UserRole | str | None) -> UserRole:
    """Normalize legacy roles to the new SaaS role set.

    This keeps backward compatibility while allowing the codebase
    to reason in terms of SUPER_ADMIN/COMPANY_ADMIN/BRANCH_ADMIN.
    """

    raw = (role.value if isinstance(role, UserRole) else (role or "")).strip().lower()
    mapping = {
        "admin": UserRole.COMPANY_ADMIN,
        "company_admin": UserRole.COMPANY_ADMIN,
        "branch_manager": UserRole.BRANCH_ADMIN,
        "branch_admin": UserRole.BRANCH_ADMIN,
        "analyst": UserRole.VIEWER,
        "viewer": UserRole.VIEWER,
        "employee": UserRole.EMPLOYEE,
        "super_admin": UserRole.SUPER_ADMIN,
    }
    return mapping.get(raw, UserRole.VIEWER)


def is_company_admin(role: UserRole | str | None) -> bool:
    r = normalize_role(role)
    return r in {UserRole.SUPER_ADMIN, UserRole.COMPANY_ADMIN}


def can_manage_tenant_data(role: UserRole | str | None) -> bool:
    r = normalize_role(role)
    return r in {UserRole.SUPER_ADMIN, UserRole.COMPANY_ADMIN, UserRole.BRANCH_ADMIN}


def is_branch_scoped(role: UserRole | str | None) -> bool:
    r = normalize_role(role)
    return r in {UserRole.BRANCH_ADMIN, UserRole.EMPLOYEE}


class TenantScope:
    """Resolved tenant scope for the current request."""

    def __init__(
        self,
        *,
        company_id: int,
        company_name: Optional[str] = None,
        branch_id: Optional[int],
        role: UserRole,
        allowed_branch_ids: Optional[list[int]] = None,
    ):
        self.company_id = int(company_id)
        self.company_name = (company_name or "").strip() or None
        self.branch_id = int(branch_id) if branch_id is not None else None
        self.role = normalize_role(role)
        self.allowed_branch_ids = allowed_branch_ids or []


@dataclass(frozen=True)
class TokenClaims:
    sub: str
    role: UserRole
    company_id: int
    branch_id: Optional[int]
    allowed_branch_ids: list[int]


def canonicalize_email(email: str) -> str:
    """Normalize emails so uniqueness and authentication stay case-insensitive."""
    return str(email or "").strip().lower()


def find_user_by_email(db: Session, email: str) -> Optional[User]:
    """Resolve a user by email using a case-insensitive lookup."""
    normalized = canonicalize_email(email)
    if not normalized:
        return None
    return db.query(User).filter(func.lower(User.email) == normalized).first()


# -------------------------------------------------
# Password Utilities
# -------------------------------------------------
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Hash a password for storing."""
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def hash_one_time_token(value: str) -> str:
    """Hash high-entropy one-time tokens for lookup and invalidation."""
    raw = f"{ONE_TIME_TOKEN_SECRET}:{str(value or '').strip()}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


# -------------------------------------------------
# JWT Token Management
# -------------------------------------------------
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token.
    
    Args:
        data: Payload to encode (usually {"sub": user_email, "role": role, "company_id": id})
        expires_delta: Token expiration time
        
    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt


def _legacy_active_branch_ids(company_name: str) -> list[int]:
    if not company_name or not LEGACY_DATASETS_DB.exists():
        return []
    conn = sqlite3.connect(LEGACY_DATASETS_DB)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT id
            FROM branches
            WHERE company_id = ? AND is_active = 1
            ORDER BY id
            """,
            (company_name,),
        ).fetchall()
        return [int(row["id"]) for row in rows]
    finally:
        conn.close()


def _active_branch_ids(db: Session, company_id: int) -> list[int]:
    active_ids: set[int] = set()
    try:
        rows = db.connection().exec_driver_sql(
            """
            SELECT id
            FROM branches
            WHERE company_id = ? AND is_active = 1
            ORDER BY id
            """,
            (int(company_id),),
        ).fetchall()
        active_ids.update(int(row[0]) for row in rows if row and row[0] is not None)
    except Exception:
        active_ids = set()

    company = db.query(Company).filter(Company.id == int(company_id)).first()
    company_name = str(company.name).strip() if company and company.name else ""
    if company_name:
        active_ids.update(_legacy_active_branch_ids(company_name))

    return sorted(active_ids)


def build_access_token_payload(user: User, db: Session) -> dict:
    role = normalize_role(user.role)
    company_id = int(user.company_id)
    branch_id = int(user.branch_id) if user.branch_id is not None else None

    if is_branch_scoped(role):
        allowed_branch_ids = [branch_id] if branch_id is not None else []
    elif role == UserRole.SUPER_ADMIN:
        allowed_branch_ids = _active_branch_ids(db, company_id)
    else:
        allowed_branch_ids = _active_branch_ids(db, company_id)

    return {
        "sub": user.email,
        "role": role.value,
        "company_id": company_id,
        "branch_id": branch_id,
        "allowed_branch_ids": allowed_branch_ids,
    }


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT token.
    
    Returns:
        Token payload
        
    Raises:
        JWTError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise


# -------------------------------------------------
# User Authentication
# -------------------------------------------------
def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """Authenticate a user by email and password.
    
    Returns:
        User object if authentication successful, None otherwise
    """
    user = find_user_by_email(db, email)
    
    if not user:
        return None
    
    if not user.is_active:
        return None
    
    if not verify_password(password, user.hashed_password):
        return None
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    return user


def _credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _resolve_company_name(user: User, db: Session) -> Optional[str]:
    try:
        if getattr(user, "company", None) is not None and getattr(user.company, "name", None):
            return str(user.company.name).strip() or None
    except Exception:
        pass

    try:
        company = db.query(Company).filter(Company.id == int(user.company_id)).first()
        if company and company.name:
            return str(company.name).strip() or None
    except Exception:
        pass

    if int(getattr(user, "company_id", 0) or 0) == 1:
        return "Acme Corp"
    return None


def _validate_user_against_claims(user: Optional[User], claims: TokenClaims) -> User:
    credentials_exception = _credentials_exception()

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    normalized_role = normalize_role(user.role)
    if normalized_role != claims.role or int(user.company_id) != int(claims.company_id):
        raise credentials_exception

    user_branch_id = int(user.branch_id) if user.branch_id is not None else None
    if is_branch_scoped(claims.role) and user_branch_id != claims.branch_id:
        raise credentials_exception

    return user


def build_request_user_context(user: User, claims: Optional[TokenClaims], db: Session) -> dict[str, Any]:
    normalized_role = normalize_role(claims.role if claims is not None else user.role)
    company_name = _resolve_company_name(user, db)
    branch_id = int(user.branch_id) if user.branch_id is not None else None
    allowed_branch_ids = sorted(
        {
            int(item)
            for item in (claims.allowed_branch_ids if claims is not None else [])
            if item is not None
        }
    )
    if branch_id is not None and branch_id not in allowed_branch_ids:
        allowed_branch_ids.append(branch_id)

    legacy_company = company_name or ("Acme Corp" if int(user.company_id) == 1 else str(user.company_id))
    return {
        "id": str(user.id),
        "email": str(user.email),
        "name": str(user.full_name or user.email),
        "full_name": str(user.full_name or user.email),
        "company": legacy_company,
        "company_name": company_name,
        "company_id": int(user.company_id),
        "branch_id": branch_id,
        "role": normalized_role.value,
        "allowed_branch_ids": sorted(set(allowed_branch_ids)),
    }


def resolve_request_user_from_token(token: str) -> Optional[dict[str, Any]]:
    try:
        claims = _decode_token_claims(token)
    except HTTPException:
        return None

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == claims.sub).first()
        validated = _validate_user_against_claims(user, claims)
        return build_request_user_context(validated, claims, db)
    except HTTPException:
        return None
    finally:
        db.close()


# -------------------------------------------------
# FastAPI Dependencies for Authorization
# -------------------------------------------------
async def get_current_user(
    claims: TokenClaims = Depends(lambda token=Depends(oauth2_scheme): _decode_token_claims(token)),
    db: Session = Depends(get_db)
) -> User:
    """FastAPI dependency to get current authenticated user.
    
    Usage:
        @app.get("/me")
        def get_me(current_user: User = Depends(get_current_user)):
            return current_user
    """
    user = db.query(User).filter(User.email == claims.sub).first()
    return _validate_user_against_claims(user, claims)


def _decode_token_claims(token: str) -> TokenClaims:
    credentials_exception = _credentials_exception()

    try:
        payload = decode_access_token(token)
    except JWTError:
        raise credentials_exception

    subject = str(payload.get("sub") or "").strip()
    company_id_raw = payload.get("company_id")
    if not subject or company_id_raw is None:
        raise credentials_exception

    try:
        company_id = int(company_id_raw)
    except (TypeError, ValueError):
        raise credentials_exception

    branch_raw = payload.get("branch_id")
    try:
        branch_id = int(branch_raw) if branch_raw is not None else None
    except (TypeError, ValueError):
        raise credentials_exception

    role = normalize_role(payload.get("role"))
    allowed_branch_ids: list[int] = []
    raw_allowed = payload.get("allowed_branch_ids") or []
    if isinstance(raw_allowed, list):
        for item in raw_allowed:
            try:
                allowed_branch_ids.append(int(item))
            except (TypeError, ValueError):
                continue

    if branch_id is not None and branch_id not in allowed_branch_ids:
        allowed_branch_ids.append(branch_id)

    return TokenClaims(
        sub=subject,
        role=role,
        company_id=company_id,
        branch_id=branch_id,
        allowed_branch_ids=sorted(set(allowed_branch_ids)),
    )


async def get_token_claims(token: str = Depends(oauth2_scheme)) -> TokenClaims:
    return _decode_token_claims(token)


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Ensure user is active."""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def get_tenant_scope(
    branch_id: Optional[int] = None,
    claims: TokenClaims = Depends(get_token_claims),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TenantScope:
    """Resolve and validate effective company/branch scope for a request.

    - Company is always derived from the authenticated user.
    - Branch selection is allowed only when the user can access it.
    - Branch-scoped users are locked to their assigned branch.

    The `branch_id` parameter can come from query params when FastAPI injects it.
    """

    role = claims.role
    company_id = int(claims.company_id)
    company_name = None
    try:
        # Prefer a real Company.name when available.
        if getattr(current_user, "company", None) is not None:
            company_name = str(getattr(current_user.company, "name", "") or "").strip() or None
    except Exception:
        company_name = None

    # Branch-scoped roles are locked.
    if is_branch_scoped(role):
        if current_user.branch_id is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No branch assigned to current user")
        locked_branch_id = claims.branch_id if claims.branch_id is not None else int(current_user.branch_id)
        if branch_id is not None and int(branch_id) != int(locked_branch_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Branch access denied")
        allowed = [int(locked_branch_id)]
        return TenantScope(
            company_id=company_id,
            company_name=company_name,
            branch_id=int(locked_branch_id),
            role=role,
            allowed_branch_ids=allowed,
        )

    # Company-scoped roles should follow the current DB state, not stale token claims.
    # Tokens can outlive branch create/delete operations, so relying on the embedded
    # allowed_branch_ids list causes false "Branch access denied" responses.
    active_branch_ids = sorted(set(_active_branch_ids(db, company_id)))
    allowed_branch_ids: list[int] = active_branch_ids

    if branch_id is None:
        return TenantScope(
            company_id=company_id,
            company_name=company_name,
            branch_id=None,
            role=role,
            allowed_branch_ids=allowed_branch_ids,
        )

    wanted = int(branch_id)
    if wanted not in set(allowed_branch_ids):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Branch access denied")
    return TenantScope(
        company_id=company_id,
        company_name=company_name,
        branch_id=wanted,
        role=role,
        allowed_branch_ids=allowed_branch_ids,
    )


# -------------------------------------------------
# Role-Based Authorization
# -------------------------------------------------
def require_role(required_roles: list[UserRole]):
    """FastAPI dependency factory for role-based authorization.
    
    Usage:
        @app.delete("/users/{user_id}")
        def delete_user(
            user_id: int,
            current_user: User = Depends(require_role([UserRole.ADMIN]))
        ):
            # Only admins can access this endpoint
            pass
    """
    normalized_required_roles = {normalize_role(role) for role in required_roles}

    async def role_checker(
        current_user: User = Depends(get_current_user),
        claims: TokenClaims = Depends(get_token_claims),
    ) -> User:
        if claims.role not in normalized_required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {[r.value for r in normalized_required_roles]}"
            )
        return current_user
    
    return role_checker


# Convenience decorators for common roles
require_admin = require_role([UserRole.SUPER_ADMIN, UserRole.COMPANY_ADMIN])
require_tenant_manager = require_role([UserRole.SUPER_ADMIN, UserRole.COMPANY_ADMIN, UserRole.BRANCH_ADMIN])
require_analyst = require_role([UserRole.SUPER_ADMIN, UserRole.COMPANY_ADMIN, UserRole.BRANCH_ADMIN, UserRole.VIEWER])
require_viewer = require_role([UserRole.SUPER_ADMIN, UserRole.COMPANY_ADMIN, UserRole.BRANCH_ADMIN, UserRole.EMPLOYEE, UserRole.VIEWER])


# -------------------------------------------------
# Company-Based Data Isolation
# -------------------------------------------------
def check_company_access(user: User, company_id: int):
    """Verify user has access to a specific company's data.
    
    Raises HTTPException if user doesn't have access.
    """
    if int(user.company_id) != int(company_id) and normalize_role(user.role) != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You don't have permission to access this company's data."
        )
