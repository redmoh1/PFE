"""FastAPI backend for Intelligent Sales Overview Dashboard.

Exposes data endpoints for the React frontend to consume.
Run with: uvicorn backend.main:app --reload
"""

import sys
import logging
import os
import sqlite3
import json
import bcrypt
from pathlib import Path, PurePath
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
from functools import lru_cache
import shutil
import subprocess
import hashlib
from uuid import uuid4

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query, Request, UploadFile, File, Form, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr

# Ensure the project root is importable even when uvicorn is launched from backend/
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.auth import resolve_request_user_from_token, can_manage_tenant_data
from backend.upload_mapping import (
    apply_column_mapping,
    delete_pending_upload,
    get_pending_upload,
    list_mapping_profiles,
    prepare_dataset_upload,
    read_pending_upload_dataframe,
    save_mapping_profile,
    validate_mapping_configuration,
)

# JWT Authentication
try:
    from jose import JWTError, jwt
    JWT_ENABLED = True
except ImportError:
    JWT_ENABLED = False
    logging.warning("python-jose not installed. JWT authentication disabled.")

# Password hashing
try:
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    PASSLIB_ENABLED = True
except ImportError:
    PASSLIB_ENABLED = False
    logging.warning("passlib not installed. Using simple password verification.")

# Import Pipeline Controller - SINGLE SOURCE OF TRUTH
try:
    from src.pipeline_controller import (
        orchestrate_pipeline,
        hard_reset_derived_outputs,
        detect_data_deletion,
        get_pipeline_state,
        DERIVED_OUTPUT_FILES,
        CANONICAL_INPUT_FILES,
    )
    PIPELINE_CONTROLLER_AVAILABLE = True
    logging.info("Pipeline Controller imported successfully")
except ImportError as e:
    PIPELINE_CONTROLLER_AVAILABLE = False
    logging.warning(f"Pipeline Controller not available: {e}. Using fallback implementation.")

try:
    from src.tenant_paths import derived_output_paths, ensure_tenant_directories
except ImportError:
    derived_output_paths = None
    ensure_tenant_directories = None

# Ensure backend directory is in path for analytics_persistence import
_BACKEND_DIR = Path(__file__).resolve().parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

# Import Analytics Persistence Layer - DATABASE STORAGE
try:
    from analytics_persistence import (
        save_forecast_results,
        get_forecast_results,
        save_rfm_results,
        get_rfm_results,
        save_sentiment_results,
        get_sentiment_results,
        save_recommendation_results,
        get_recommendation_results,
        delete_all_analytics_for_tenant,
        delete_all_analytics_for_company,
        sync_csv_to_database,
    )
    ANALYTICS_PERSISTENCE_AVAILABLE = True
    logging.info("Analytics Persistence Layer imported successfully")
except ImportError as e:
    ANALYTICS_PERSISTENCE_AVAILABLE = False
    logging.warning(f"Analytics Persistence Layer not available: {e}. Using CSV-only storage.")

# Rate Limiting
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    RATE_LIMITING_ENABLED = True
except ImportError:
    RATE_LIMITING_ENABLED = False
    logging.warning("slowapi not installed. Rate limiting disabled. Install with: pip install slowapi")

# Environment Variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    logging.warning("python-dotenv not installed. Using default settings.")

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
OUTPUT_DIR = BASE_DIR / "output"
MODEL_PATH = BASE_DIR / "src" / "ml_lifecycle" / "model_registry" / "sales_forecast_model.pkl"
DB_PATH = DATA_DIR / "datasets.db"
PIPELINE_LOCK_PATH = DATA_DIR / ".pipeline.lock"

DATA_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "api.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

# New: Insights + Data Quality
try:
    from backend.insights import InsightsResponse, generate_insights
    from backend.data_quality import DataQualityReport, generate_data_quality_report
    INSIGHTS_AVAILABLE = True
except Exception as e:  # noqa: BLE001
    INSIGHTS_AVAILABLE = False
    logging.warning(f"Insights/DataQuality modules not available: {e}")
    class InsightsResponse(BaseModel):
        company_id: str
        generated_at: str
        insights: List[Dict[str, Any]]

    class DataQualityReport(BaseModel):
        company_id: str
        dataset: str
        generated_at: str
        row_count: int
        column_count: int
        date_column: Optional[str] = None
        date_min: Optional[str] = None
        date_max: Optional[str] = None
        missing_values: Dict[str, Any] = {}
        invalid_values: Dict[str, Any] = {}
        duplicates: Dict[str, Any] = {}
        outliers: Dict[str, Any] = {}
        quality_score: float = 0.0
        issues: List[Dict[str, Any]] = []

    def generate_insights(*args, **kwargs):
        return InsightsResponse(
            company_id="",
            generated_at=datetime.now(timezone.utc).isoformat(),
            insights=[],
        )

    def generate_data_quality_report(*args, **kwargs):
        return DataQualityReport(
            company_id="",
            dataset="sales",
            generated_at=datetime.now(timezone.utc).isoformat(),
            row_count=0,
            column_count=0,
        )

ALLOWED_DATASET_TYPES = {"sales", "customers", "reviews"}
MAX_PREVIEW_ROWS = 50

DATE_CANDIDATES = ["OrderDate", "Sale_Date", "Order_Date", "Date", "order_date"]
# IMPORTANT: Include "Price" for datasets that use Price instead of TotalPrice
REVENUE_CANDIDATES = ["TotalPrice", "Price", "Sales_Amount", "SalesAmount", "Revenue", "Sales", "Amount", "amount", "price"]
PRODUCT_CANDIDATES = ["Product", "ProductName", "product_name", "Description", "description", "ProductID", "Product_ID", "SKU"]
CITY_CANDIDATES = ["City", "city", "City_x", "City_y", "customer_city", "CustomerCity", "Region", "region", "Market"]
ORDER_ID_CANDIDATES = ["OrderID", "order_id", "id", "ID", "Order_Id", "InvoiceNo"]
CUSTOMER_ID_CANDIDATES = ["CustomerID", "Customer_ID", "customer_id", "CustomerId", "cust_id", "client_id"]

# =============================================================================
# JWT Configuration
# =============================================================================
# SECURITY: In production, JWT_SECRET_KEY MUST be set as an environment variable
# Never use the default in production - it's for development only
_default_secret = "sales-intelligence-secret-key-change-in-production-2024"
SECRET_KEY = os.getenv("JWT_SECRET_KEY", _default_secret)
if SECRET_KEY == _default_secret and os.getenv("ENVIRONMENT", "development") == "production":
    logger.critical("SECURITY ERROR: JWT_SECRET_KEY must be set in production!")
    raise RuntimeError("JWT_SECRET_KEY environment variable required in production")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

security = HTTPBearer(auto_error=False)

# Demo users for testing (in production, use database)
DEMO_USERS = {
    "admin@acme.com": {
        "id": "1",
        "email": "admin@acme.com",
        "name": "Admin User",
        "password_hash": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.OQbWIEPOZyAe9O",  # admin123
        "company": "Acme Corp",
        "company_id": 1,
        "branch_id": None,
        "role": "admin"
    },
    "analyst@acme.com": {
        "id": "2", 
        "email": "analyst@acme.com",
        "name": "Analyst User",
        "password_hash": "$2b$12$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi",  # analyst123
        "company": "Acme Corp",
        "company_id": 1,
        "branch_id": None,
        "role": "analyst"
    },
    "manager.setif@acme.com": {
        "id": "3",
        "email": "manager.setif@acme.com",
        "name": "Setif Branch Manager",
        "password_hash": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.OQbWIEPOZyAe9O",
        "company": "Acme Corp",
        "company_id": 1,
        "branch_id": 1,
        "role": "branch_manager"
    },
    "employee.setif@acme.com": {
        "id": "4",
        "email": "employee.setif@acme.com",
        "name": "Setif Employee",
        "password_hash": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.OQbWIEPOZyAe9O",
        "company": "Acme Corp",
        "company_id": 1,
        "branch_id": 1,
        "role": "employee"
    }
}

# Simple password for demo (when passlib is not available)
DEMO_PASSWORDS = {
    "admin@acme.com": "admin123",
    "analyst@acme.com": "analyst123",
    "manager.setif@acme.com": "admin123",
    "employee.setif@acme.com": "admin123"
}


# =============================================================================
# Authentication Models
# =============================================================================
class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    company: str
    company_id: Optional[int] = None
    branch_id: Optional[int] = None
    role: str


class CreateBranchManagerRequest(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    password: str
    branch_id: int


class UpdateUserRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    password: Optional[str] = None


# =============================================================================
# Authentication Helpers
# =============================================================================
def verify_password(plain_password: str, hashed_password: str, email: str = None) -> bool:
    """Verify password - uses simple check for demo, bcrypt for production."""
    # Always check simple demo passwords first for reliability
    if email and email in DEMO_PASSWORDS:
        if plain_password == DEMO_PASSWORDS[email]:
            return True

    try:
        if hashed_password:
            return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        pass
    
    # Try bcrypt verification if passlib is available
    if PASSLIB_ENABLED:
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception as e:
            logger.warning(f"Password verification failed: {e}")
    
    return False


def hash_password_for_storage(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def create_access_token(data: dict) -> str:
    """Create JWT access token."""
    if not JWT_ENABLED:
        # Simple fallback token
        return f"demo-token-{data.get('sub', 'unknown')}"
    
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Optional[Dict]:
    """Extract current user from JWT token."""
    if not credentials:
        return None
    
    token = credentials.credentials
    
    # Handle demo token
    if token.startswith("demo-token-"):
        email = token.replace("demo-token-", "")
        resolved = resolve_effective_demo_user(email)
        if resolved:
            return resolved
        return None
    
    if not JWT_ENABLED:
        return None
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email:
            resolved = resolve_effective_demo_user(str(email))
            if resolved:
                return resolved
    except JWTError:
        pass
    
    return None


def resolve_db_user(email: str) -> Optional[Dict[str, Any]]:
    """Resolve a user stored in the local SQLite users table."""
    conn = None
    try:
        conn = get_db_connection()
        row = conn.execute(
            "SELECT id, email, full_name, role, branch_id, company_id FROM users WHERE email = ?",
            (email,),
        ).fetchone()
        if not row:
            return None
        role = str(row["role"] or "employee").strip().lower()
        company_id_raw = row["company_id"]
        branch_id_raw = row["branch_id"]
        resolved_company_id = int(company_id_raw) if company_id_raw and str(company_id_raw).isdigit() else 1
        return {
            "id": str(row["id"]),
            "email": str(row["email"]),
            "name": str(row["full_name"] or row["email"]),
            # Keep a human-readable name for the UI while using numeric company_id for scoping.
            "company": "Acme Corp" if resolved_company_id == 1 else f"Company {resolved_company_id}",
            "company_id": resolved_company_id,
            "branch_id": int(branch_id_raw) if branch_id_raw is not None else None,
            "role": role,
        }
    except Exception:
        return None
    finally:
        if conn is not None:
            conn.close()


def resolve_effective_demo_user(email: str) -> Optional[Dict[str, Any]]:
    """Resolve user profile with dynamic branch-manager assignment from DB."""
    base = DEMO_USERS.get(email)
    if not base:
        # Fallback: check database-created users
        return resolve_db_user(email)

    user = base.copy()
    role_norm = normalize_role_text(user.get("role"))
    company = str(user.get("company") or "Acme Corp").strip()
    user_id = str(user.get("id") or "").strip()

    # Company admins always keep global visibility.
    if role_norm in {"super_admin", "company_admin"}:
        user["branch_id"] = None
        user.pop("password_hash", None)
        return user

    conn = None
    try:
        conn = get_db_connection()
        if user_id:
            managed_row = conn.execute(
                """
                SELECT id
                FROM branches
                WHERE company_id = ? AND manager_id = ? AND is_active = 1
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (company, user_id),
            ).fetchone()
            if managed_row:
                user["role"] = "branch_manager"
                user["branch_id"] = int(managed_row["id"])

        # Guard against stale branch assignment (deleted/inactive branch).
        assigned_branch = user.get("branch_id")
        if assigned_branch is not None:
            branch_exists = conn.execute(
                """
                SELECT 1
                FROM branches
                WHERE company_id = ? AND id = ? AND is_active = 1
                LIMIT 1
                """,
                (company, int(assigned_branch)),
            ).fetchone()
            if not branch_exists:
                user["branch_id"] = None
    except Exception:
        pass
    finally:
        if conn is not None:
            conn.close()

    user.pop("password_hash", None)
    return user


def get_user_from_request(request: Request) -> Optional[Dict[str, Any]]:
    """Best-effort auth extraction from Authorization header."""
    auth = request.headers.get("Authorization") or ""
    if not auth.lower().startswith("bearer "):
        return None
    token = auth.split(" ", 1)[1].strip()
    if not token:
        return None

    if token.startswith("demo-token-"):
        email = token.replace("demo-token-", "")
        return resolve_effective_demo_user(email)

    return resolve_request_user_from_token(token)


def normalize_role_text(role: object) -> str:
    """Normalize legacy role strings to the new SaaS role set.

    This keeps current demo/SQLite users working while we migrate.
    """

    raw = str(role or "").strip().lower()
    mapping = {
        "super_admin": "super_admin",
        "company_admin": "company_admin",
        "branch_admin": "branch_admin",
        "admin": "company_admin",
        "branch_manager": "branch_admin",
        "employee": "employee",
        "viewer": "viewer",
        "analyst": "viewer",
    }
    return mapping.get(raw, "viewer")


def normalize_branch_id(branch_id: object) -> Optional[str]:
    value = str(branch_id or "").strip()
    if not value or value.upper() == "GLOBAL":
        return None
    return value


def resolve_branch_scope(request: Request) -> Optional[str]:
    """Resolve effective branch scope from request (query) + role restrictions.

    SECURITY:
    - We no longer trust X-Branch-ID as an authorization signal.
    - We accept an optional requested branch id (query param `branch_id`) but
      we validate it against the authenticated user and their assigned branch.
    """

    requested = normalize_branch_id(request.query_params.get("branch_id"))
    current_user = get_user_from_request(request)

    if not current_user:
        return requested or None

    role = normalize_role_text(current_user.get("role"))
    user_branch = current_user.get("branch_id")
    user_branch_text = normalize_branch_id(user_branch)

    # Branch-scoped users are locked to their assigned branch.
    if role in {"branch_admin", "employee"}:
        if not user_branch_text:
            raise HTTPException(status_code=403, detail="No branch assigned to current user")
        if requested and user_branch_text and requested != user_branch_text:
            raise HTTPException(status_code=403, detail="Branch access denied")
        return user_branch_text

    # Viewers can be either company-scoped (no assigned branch) or branch-scoped.
    if role == "viewer" and user_branch_text:
        if requested and requested != user_branch_text:
            raise HTTPException(status_code=403, detail="Branch access denied")
        return user_branch_text

    if requested:
        company_id = resolve_company_id_from_user(current_user)
        try:
            requested_id = int(requested)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid branch_id")
        conn = get_db_connection()
        try:
            row = conn.execute(
                """
                SELECT id
                FROM branches
                WHERE company_id = ? AND id = ? AND is_active = 1
                LIMIT 1
                """,
                (company_id, requested_id),
            ).fetchone()
        finally:
            conn.close()
        if not row:
            raise HTTPException(status_code=403, detail="Branch access denied")

    return requested or None


def require_authenticated_request(request: Request) -> Dict[str, Any]:
    user = get_user_from_request(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


def require_admin_request(request: Request) -> Dict[str, Any]:
    user = require_authenticated_request(request)
    role = normalize_role_text(user.get("role"))
    if role not in {"super_admin", "company_admin"}:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


def require_tenant_manager_request(request: Request) -> Dict[str, Any]:
    user = require_authenticated_request(request)
    if not can_manage_tenant_data(user.get("role")):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS datasets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id TEXT NOT NULL,
            dataset_type TEXT NOT NULL,
            file_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            row_count INTEGER NOT NULL DEFAULT 0,
            uploaded_at TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 0,
            is_deleted INTEGER NOT NULL DEFAULT 0
        );
        """
    )
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
        );
        """
    )
    # Migration: add phone column if missing (existing databases)
    try:
        conn.execute("ALTER TABLE branches ADD COLUMN phone TEXT")
    except Exception:
        pass  # column already exists
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            full_name TEXT,
            role TEXT NOT NULL DEFAULT 'employee',
            branch_id INTEGER,
            company_id TEXT,
            created_at TEXT NOT NULL
        );
        """
    )

    # Lightweight migrations for existing local databases.
    dataset_cols = [r["name"] for r in conn.execute("PRAGMA table_info(datasets)").fetchall()]
    if "branch_id" not in dataset_cols:
        conn.execute("ALTER TABLE datasets ADD COLUMN branch_id TEXT")

    branch_cols = [r["name"] for r in conn.execute("PRAGMA table_info(branches)").fetchall()]
    if "is_active" not in branch_cols:
        conn.execute("ALTER TABLE branches ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1")

    user_cols = [r["name"] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
    if "role" not in user_cols:
        conn.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'employee'")
    if "branch_id" not in user_cols:
        conn.execute("ALTER TABLE users ADD COLUMN branch_id INTEGER")
    if "hashed_password" not in user_cols:
        conn.execute("ALTER TABLE users ADD COLUMN hashed_password TEXT")
    if "phone" not in user_cols:
        conn.execute("ALTER TABLE users ADD COLUMN phone TEXT")

    # Seed default branches if none exist.
    existing_branches = conn.execute("SELECT COUNT(1) AS c FROM branches").fetchone()
    if not existing_branches or int(existing_branches["c"]) == 0:
        created_at = datetime.now(timezone.utc).isoformat()
        conn.executemany(
            """
            INSERT INTO branches (company_id, name, city, manager_id, created_at, is_active)
            VALUES (?, ?, ?, ?, ?, 1)
            """,
            [
                ("Acme Corp", "Setif", "Setif", "3", created_at),
                ("Acme Corp", "Algiers", "Algiers", None, created_at),
                ("Acme Corp", "Oran", "Oran", None, created_at),
            ],
        )

    conn.commit()
    conn.close()


# Ensure metadata store exists after definitions are loaded
init_db()


# =============================================================================
# Pipeline Concurrency Lock (prevents race conditions during file operations)
# =============================================================================
import threading
import time
from contextlib import contextmanager

_pipeline_lock = threading.Lock()
_pipeline_lock_timeout = 120  # seconds


@contextmanager
def pipeline_lock(operation: str = "pipeline"):
    """
    Acquire a lock before running pipeline operations.
    
    This prevents race conditions when multiple uploads happen simultaneously.
    Uses a threading lock for in-process synchronization.
    
    For multi-process deployments, consider using:
    - Redis distributed lock
    - PostgreSQL advisory locks
    - File-based locking with fcntl (Unix) or msvcrt (Windows)
    """
    acquired = _pipeline_lock.acquire(timeout=_pipeline_lock_timeout)
    if not acquired:
        logger.error(f"[LOCK] Failed to acquire pipeline lock for {operation} after {_pipeline_lock_timeout}s")
        raise HTTPException(
            status_code=503, 
            detail="Server busy processing another operation. Please try again."
        )
    
    try:
        logger.debug(f"[LOCK] Acquired pipeline lock for {operation}")
        yield
    finally:
        _pipeline_lock.release()
        logger.debug(f"[LOCK] Released pipeline lock for {operation}")


def ensure_company_dir(company_id: str, dataset_type: str, branch_id: Optional[str] = None) -> Path:
    branch_id = normalize_branch_id(branch_id)
    if ensure_tenant_directories is not None:
        tenant_dirs = ensure_tenant_directories(DATA_DIR, company_id, branch_id)
        return tenant_dirs["uploads"]

    if branch_id:
        company_dir = DATA_DIR / company_id / "branches" / str(branch_id) / dataset_type
    else:
        company_dir = DATA_DIR / company_id / dataset_type
    company_dir.mkdir(parents=True, exist_ok=True)
    return company_dir


def ensure_company_output_dir(company_id: str, branch_id: Optional[str] = None) -> Path:
    branch_id = normalize_branch_id(branch_id)
    if ensure_tenant_directories is not None:
        tenant_dirs = ensure_tenant_directories(DATA_DIR, company_id, branch_id)
        return tenant_dirs["outputs"]

    if branch_id:
        output_dir = OUTPUT_DIR / company_id / "branches" / str(branch_id)
    else:
        output_dir = OUTPUT_DIR / company_id
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def tenant_file_path(company_id: str, filename: str, branch_id: Optional[str] = None) -> Path:
    branch_id = normalize_branch_id(branch_id)
    if derived_output_paths is not None:
        file_map = derived_output_paths(DATA_DIR, company_id, branch_id)
        if filename in file_map:
            return file_map[filename]
    return ensure_company_dir(company_id, "uploads", branch_id=branch_id) / filename


def analytics_result_candidates(company_id: str, filename: str, branch_id: Optional[str] = None) -> List[Path]:
    """Return tenant-first result file candidates with legacy compatibility fallbacks."""
    candidates: List[Path] = [tenant_file_path(company_id, filename, branch_id=branch_id)]


    unique_candidates: List[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        unique_candidates.append(candidate)
    return unique_candidates


def load_aggregated_branch_output(
    company_id: str,
    filename: str,
    dataset_type: str,
) -> tuple[Optional[pd.DataFrame], Optional[str]]:
    """Load and concatenate branch-scoped outputs for a company.

    Returns a tuple of (dataframe, last_modified_iso) or (None, None).
    """
    frames: List[pd.DataFrame] = []
    timestamps: List[float] = []
    for dataset in list_active_datasets(company_id, dataset_type):
        branch_id = normalize_branch_id(dataset.get("branch_id"))
        if not branch_id:
            continue
        output_path = tenant_file_path(company_id, filename, branch_id=branch_id)
        if not output_path.exists():
            continue
        try:
            frame = pd.read_csv(output_path)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to read branch output %s: %s", output_path, exc)
            continue
        if frame is None or frame.empty:
            continue
        frames.append(frame)
        try:
            timestamps.append(output_path.stat().st_mtime)
        except Exception:
            continue

    if not frames:
        return None, None

    combined = pd.concat(frames, ignore_index=True)
    last_modified = None
    if timestamps:
        last_modified = datetime.fromtimestamp(max(timestamps)).isoformat()
    return combined, last_modified


def recommendation_result_candidates(company_id: str, branch_id: Optional[str] = None) -> List[Path]:
    """Return candidate paths for product recommendation outputs."""
    candidates = analytics_result_candidates(company_id, "product_recommendations.csv", branch_id=branch_id)
    if branch_id is not None:
        fallback_candidates = [
            DATA_DIR / "product_recommendations.csv",
            OUTPUT_DIR / "recommendations" / "product_recommendations.csv",
        ]
        for candidate in fallback_candidates:
            candidates.append(candidate)

    unique_candidates: List[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        unique_candidates.append(candidate)
    return unique_candidates


def resolve_active_dataset_source_path(company_id: str, dataset_type: str, branch_id: Optional[str] = None) -> Optional[Path]:
    """Resolve the best source CSV for an active tenant dataset."""
    branch_id = normalize_branch_id(branch_id)
    active = get_active_dataset(company_id, dataset_type, branch_id=branch_id)
    if active:
        active_path = Path(str(active.get("file_path") or ""))
        if active_path.exists():
            return active_path

    uploads_dir = ensure_company_dir(company_id, dataset_type, branch_id=branch_id)
    if uploads_dir.exists() and uploads_dir.is_dir():
        csvs = [path for path in uploads_dir.glob("*.csv") if path.is_file()]
        if csvs:
            return max(csvs, key=lambda path: path.stat().st_mtime)

    if branch_id is None:
        legacy_name = {
            "sales": "sales.csv",
            "reviews": "customer_reviews.csv",
            "customers": "customers.csv",
        }.get(dataset_type)
        if legacy_name:
            legacy_path = DATA_DIR / legacy_name
            if legacy_path.exists():
                return legacy_path

    return None


def build_tenant_ml_env(company_id: str, branch_id: Optional[str] = None, dataset_type: str = "sales") -> dict[str, str]:
    """Build environment variables for tenant-scoped ML subprocesses."""
    if ensure_tenant_directories is not None:
        tenant_dirs = ensure_tenant_directories(DATA_DIR, company_id, branch_id)
        data_dir = tenant_dirs["uploads"]
        output_dir = tenant_dirs["outputs"]
    else:
        tenant_dirs = None
        data_dir = ensure_company_dir(company_id, dataset_type, branch_id=branch_id)
        output_dir = ensure_company_output_dir(company_id, branch_id)
    plots_dir = output_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env.update(
        {
            "SI_COMPANY_ID": str(company_id),
            "SI_BRANCH_ID": str(branch_id or ""),
            "SI_TENANT_KEY": f"{company_id}::{branch_id or 'GLOBAL'}",
            "SI_DATA_DIR": str(data_dir),
            "SI_OUTPUT_DIR": str(output_dir),
            "SI_PLOTS_DIR": str(plots_dir),
        }
    )
    if tenant_dirs is not None:
        env.update(
            {
                "SI_TENANT_ROOT": str(tenant_dirs["scope"]),
                "SI_FORECASTS_DIR": str(tenant_dirs["forecasts"]),
                "SI_SEGMENTATION_DIR": str(tenant_dirs["segmentation"]),
                "SI_SENTIMENT_DIR": str(tenant_dirs["sentiment"]),
                "SI_RECOMMENDATIONS_DIR": str(tenant_dirs["recommendations"]),
                "SI_NOTIFICATIONS_DIR": str(tenant_dirs["notifications"]),
            }
        )
    return env


def row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "company_id": row["company_id"],
        "branch_id": row["branch_id"] if "branch_id" in row.keys() else None,
        "dataset_type": row["dataset_type"],
        "file_name": row["file_name"],
        "file_path": row["file_path"],
        "row_count": row["row_count"],
        "uploaded_at": row["uploaded_at"],
        "is_active": bool(row["is_active"]),
        "is_deleted": bool(row["is_deleted"]),
    }


def compute_row_count(file_path: Path) -> int:
    try:
        with file_path.open("r", encoding="utf-8", errors="ignore") as fh:
            # subtract header
            return max(sum(1 for _ in fh) - 1, 0)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not compute row count for %s: %s", file_path, exc)
        return 0


def load_preview(file_path: Path) -> Dict[str, Any]:
    if not file_path.exists():
        raise FileNotFoundError("File not found")

    df = pd.read_csv(file_path)
    rows = df.head(MAX_PREVIEW_ROWS)
    return {
        "columns": list(rows.columns),
        "rows": jsonable_encoder(rows.to_dict(orient="records")),
        "row_count": len(df),
    }


app = FastAPI(
    title="Sales Overview API",
    description="Backend API for Intelligent Sales Overview Dashboard",
    version="1.0.0",
)

# Inventory Management (Gestion de Stock)
# Kept in a dedicated router to avoid inflating this already-large module.
try:
    from backend.routes.auth_routes import router as auth_router

    app.include_router(auth_router)
    logger.info("Auth routes mounted under /api/auth")
except Exception as exc:  # noqa: BLE001
    logger.warning("Auth routes not available: %s", exc)

try:
    from backend.routes.inventory_routes import router as inventory_router

    app.include_router(inventory_router)
    logger.info("Inventory routes mounted under /inventory")
except Exception as exc:  # noqa: BLE001
    logger.warning("Inventory routes not available: %s", exc)

# Notifications (derived from inventory status)
try:
    from backend.routes.notifications_routes import router as notifications_router

    app.include_router(notifications_router)
    logger.info("Notifications routes mounted under /notifications")
except Exception as exc:  # noqa: BLE001
    logger.warning("Notifications routes not available: %s", exc)

# Alerts (derived from inventory status)
try:
    from backend.routes.alerts_routes import router as alerts_router

    app.include_router(alerts_router)
    logger.info("Alerts routes mounted under /alerts")
except Exception as exc:  # noqa: BLE001
    logger.warning("Alerts routes not available: %s", exc)
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # مؤقتًا للعرض
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup Rate Limiting
if RATE_LIMITING_ENABLED:
    limiter = Limiter(key_func=get_remote_address, default_limits=["100/hour"])
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    logger.info("Rate limiting enabled: 100 requests/hour default")
else:
    limiter = None
    logger.warning("Rate limiting is DISABLED - not recommended for production")

# Enable CORS for React frontend
# Read from environment or use defaults
ALLOWED_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    (
        "http://localhost:5173,http://localhost:3000,http://localhost:3001,http://localhost:3002," \
        "http://127.0.0.1:5173,http://127.0.0.1:3000,http://127.0.0.1:3001,http://127.0.0.1:3002"
    ),
).split(",")
# Allow broad localhost/127.0.0.1 in dev to avoid CORS flakiness across ports
ALLOWED_ORIGIN_REGEX = os.getenv("CORS_ORIGIN_REGEX", r"http://(localhost|127\.0\.0\.1):\d{2,5}")


logger.info(f"CORS enabled for origins: {ALLOWED_ORIGINS}")


# ============================================================================
# Pydantic Models
# ============================================================================


class KPIResponse(BaseModel):
    total_revenue: float
    total_orders: int
    average_order_value: float
    top_product: str
    top_city: str
    # Percentage changes (None = comparison unavailable)
    revenue_change: Optional[float] = None
    orders_change: Optional[float] = None
    aov_change: Optional[float] = None


class MonthlySalesResponse(BaseModel):
    month: str
    actual_sales: Optional[float]
    forecasted_sales: Optional[float]
    forecast_lower: Optional[float] = None
    forecast_upper: Optional[float] = None


class TopProductResponse(BaseModel):
    product_id: str
    product_name: Optional[str] = None
    revenue: float
    order_count: int


class TopCityResponse(BaseModel):
    city: str
    revenue: float
    order_count: int


class SentimentResponse(BaseModel):
    positive: int
    neutral: int
    negative: int
    total: int


class RecommendationResponse(BaseModel):
    if_product: str
    then_product: str
    confidence: float
    lift: float


class RFMSegmentResponse(BaseModel):
    segment: str
    customer_count: int
    color: str
    avg_recency: Optional[float] = None
    avg_frequency: Optional[float] = None
    avg_monetary: Optional[float] = None


class SegmentationMetadata(BaseModel):
    total_customers: int
    segments: List[RFMSegmentResponse]
    last_calculated: Optional[str] = None
    data_source: str = "rfm_table.csv"
    model_version: str = "RFM"


class SentimentDetail(BaseModel):
    label: str
    count: int
    percentage: float


class SentimentAnalysisResponse(BaseModel):
    total_reviews: int
    sentiment_breakdown: List[SentimentDetail]
    top_keywords: List[str]
    last_analyzed: Optional[str] = None
    data_source: str = "sentiment_results.csv"


class DatasetMeta(BaseModel):
    id: int
    company_id: str
    branch_id: Optional[str] = None
    dataset_type: str
    file_name: str
    row_count: int
    uploaded_at: str
    is_active: bool


class DatasetPreview(BaseModel):
    id: int
    file_name: str
    dataset_type: str
    uploaded_at: str
    row_count: int
    columns: List[str]
    rows: List[Dict[str, Any]]


class MappingFieldDefinitionResponse(BaseModel):
    key: str
    label: str
    required: bool
    description: str
    canonical_column: str


class DatasetUploadPreparationResponse(BaseModel):
    upload_id: str
    dataset_type: str
    file_name: str
    row_count: int
    columns: List[str]
    preview_rows: List[Dict[str, Any]]
    fields: List[MappingFieldDefinitionResponse]
    suggested_mapping: Dict[str, Optional[str]]
    saved_mapping: Dict[str, Optional[str]]
    initial_mapping: Dict[str, Optional[str]]
    mapping_source: Optional[str] = None
    profile_id: Optional[int] = None
    replace_dataset_id: Optional[int] = None
    expires_at: str


class DatasetMappingValidationRequest(BaseModel):
    upload_id: str
    mapping: Dict[str, Optional[str]]


class DatasetMappingValidationResponse(BaseModel):
    valid: bool
    errors: List[str]
    warnings: List[str]
    mapping: Dict[str, Optional[str]]


class DatasetMappingConfirmRequest(BaseModel):
    upload_id: str
    mapping: Dict[str, Optional[str]]
    save_mapping: bool = True


class DatasetMappingConfirmResponse(BaseModel):
    dataset: DatasetMeta
    mapping_saved: bool
    standardized_columns: List[str]


class DatasetMappingCancelRequest(BaseModel):
    upload_id: str


class SavedMappingProfileResponse(BaseModel):
    id: int
    company_id: str
    branch_id: Optional[str] = None
    user_id: Optional[str] = None
    dataset_type: str
    source_columns: List[str]
    mapping: Dict[str, Optional[str]]
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    last_used_at: Optional[str] = None


class BranchCreateRequest(BaseModel):
    name: str
    city: str
    phone: Optional[str] = None
    manager_id: Optional[str] = None


class BranchUpdateRequest(BaseModel):
    name: Optional[str] = None
    city: Optional[str] = None
    phone: Optional[str] = None
    manager_id: Optional[str] = None
    is_active: Optional[bool] = None


class ManagerInfo(BaseModel):
    id: str
    name: str
    email: str
    phone: Optional[str] = None


class BranchResponse(BaseModel):
    id: int
    name: str
    city: str
    phone: Optional[str] = None
    manager_id: Optional[str] = None
    manager_name: Optional[str] = None
    manager: Optional[ManagerInfo] = None
    created_at: str
    status: str


class AssignManagerRequest(BaseModel):
    user_id: int


def _latest_branch_manager_id(branch_id: int, company_id: str) -> Optional[str]:
    """Return the most recent DB-backed branch manager for a branch."""
    try:
        conn = get_db_connection()
        try:
            row = conn.execute(
                """
                SELECT id
                FROM users
                WHERE company_id = ? AND branch_id = ? AND lower(role) = 'branch_manager'
                ORDER BY datetime(created_at) DESC, id DESC
                LIMIT 1
                """,
                (company_id, branch_id),
            ).fetchone()
            if row:
                return str(row["id"])
        finally:
            conn.close()
    except Exception:
        pass
    return None


def _manager_name_from_id(manager_id: Optional[str]) -> Optional[str]:
    """Resolve a human-readable name for a manager_id.

    Checks DEMO_USERS first, then falls back to the local `users` table
    so that database-only users are also covered.
    """
    if not manager_id:
        return None
    # 1) Check in-memory demo users
    for user in DEMO_USERS.values():
        if str(user.get("id")) == str(manager_id):
            return str(user.get("name") or user.get("email") or "")
    # 2) Fallback: query the users table
    try:
        conn = get_db_connection()
        try:
            row = conn.execute(
                "SELECT full_name, email FROM users WHERE id = ?",
                (int(manager_id),),
            ).fetchone()
            if row:
                return str(row["full_name"] or row["email"] or "")
        finally:
            conn.close()
    except Exception:
        pass
    return None


def _manager_info_from_id(manager_id: Optional[str]) -> Optional[ManagerInfo]:
    """Resolve full manager details (id, name, email, phone) for a manager_id."""
    if not manager_id:
        return None
    # 1) Check in-memory demo users
    for user in DEMO_USERS.values():
        if str(user.get("id")) == str(manager_id):
            return ManagerInfo(
                id=str(user.get("id")),
                name=str(user.get("name") or user.get("email") or ""),
                email=str(user.get("email") or ""),
                phone=user.get("phone"),
            )
    # 2) Fallback: query the users table
    try:
        conn = get_db_connection()
        try:
            row = conn.execute(
                "SELECT id, full_name, email, phone FROM users WHERE id = ?",
                (int(manager_id),),
            ).fetchone()
            if row:
                return ManagerInfo(
                    id=str(row["id"]),
                    name=str(row["full_name"] or row["email"] or ""),
                    email=str(row["email"] or ""),
                    phone=row["phone"] if row["phone"] else None,
                )
        finally:
            conn.close()
    except Exception:
        pass
    return None


def _resolve_branch_manager(branch_row: sqlite3.Row, company_id: str) -> tuple[Optional[str], Optional[ManagerInfo]]:
    """Resolve branch manager from the branch row or fallback branch_manager users."""
    manager_id = str(branch_row["manager_id"]) if branch_row["manager_id"] is not None else None
    manager = _manager_info_from_id(manager_id)
    if manager is not None:
        return manager_id, manager

    fallback_manager_id = _latest_branch_manager_id(int(branch_row["id"]), company_id)
    if not fallback_manager_id:
        return None, None

    return fallback_manager_id, _manager_info_from_id(fallback_manager_id)


def _build_branch_response(branch_row: sqlite3.Row, company_id: str) -> BranchResponse:
    manager_id, manager = _resolve_branch_manager(branch_row, company_id)
    return BranchResponse(
        id=int(branch_row["id"]),
        name=str(branch_row["name"]),
        city=str(branch_row["city"]),
        phone=str(branch_row["phone"]) if branch_row["phone"] else None,
        manager_id=manager_id,
        manager_name=manager.name if manager is not None else None,
        manager=manager,
        created_at=str(branch_row["created_at"]),
        status="Active" if int(branch_row["is_active"] or 0) == 1 else "Inactive",
    )


def _sync_demo_user_manager_assignment(
    *,
    company_id: str,
    branch_id: int,
    manager_id: Optional[str],
    previous_manager_id: Optional[str] = None,
) -> None:
    """Synchronize demo users after branch manager assignment changes."""

    # Assign manager to this branch.
    if manager_id:
        for email, user in DEMO_USERS.items():
            if str(user.get("id") or "") == str(manager_id):
                user["company"] = company_id
                user["branch_id"] = int(branch_id)
                if normalize_role_text(user.get("role")) not in {"super_admin", "company_admin"}:
                    user["role"] = "branch_manager"
                DEMO_USERS[email] = user
                break

    # If manager changed, detach previous manager unless they still manage another active branch.
    if previous_manager_id and str(previous_manager_id) != str(manager_id):
        conn = get_db_connection()
        try:
            still_manages = conn.execute(
                """
                SELECT 1
                FROM branches
                WHERE company_id = ? AND manager_id = ? AND is_active = 1
                LIMIT 1
                """,
                (company_id, str(previous_manager_id)),
            ).fetchone()
        finally:
            conn.close()

        if not still_manages:
            for email, user in DEMO_USERS.items():
                if str(user.get("id") or "") == str(previous_manager_id):
                    if normalize_role_text(user.get("role")) not in {"super_admin", "company_admin"}:
                        user["branch_id"] = None
                    DEMO_USERS[email] = user
                    break


def _persist_user_branch_role(user_id: str, company_id: str, branch_id: Optional[int], role: str) -> None:
    """Best-effort persistence to local users table (for compatibility with DB-backed setups)."""
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT id FROM users WHERE id = ?", (int(user_id),)).fetchone()
        if row:
            conn.execute(
                """
                UPDATE users
                SET role = ?, branch_id = ?, company_id = ?
                WHERE id = ?
                """,
                (role, branch_id, company_id, int(user_id)),
            )
        conn.commit()
    except Exception:
        pass
    finally:
        conn.close()


@app.get("/api/users", tags=["Users"])
def list_users_for_company(request: Request):
    """Return users for the current company.

    Merges in-memory DEMO_USERS with any extra rows in the local `users`
    table so that database-created users also appear in the Assign Manager
    dropdown.
    """
    current_user = require_authenticated_request(request)
    company_id = require_company_id(request)
    role = normalize_role_text(current_user.get("role"))
    current_branch = str(current_user.get("branch_id") or "").strip()

    try:
        seen_ids: set = set()
        rows: List[Dict[str, Any]] = []

        # 1) In-memory demo users
        for user in DEMO_USERS.values():
            resolved_user = resolve_effective_demo_user(str(user.get("email") or ""))
            if not resolved_user:
                continue
            if str(user.get("company")) != str(company_id):
                continue
            if role in {"branch_admin", "employee"} and current_branch and str(resolved_user.get("branch_id") or "") != current_branch:
                continue
            uid = str(resolved_user.get("id"))
            seen_ids.add(uid)
            rows.append(
                {
                    "id": uid,
                    "name": str(resolved_user.get("name") or resolved_user.get("email") or ""),
                    "email": str(resolved_user.get("email") or ""),
                    "role": str(resolved_user.get("role") or "employee"),
                    "branch_id": resolved_user.get("branch_id"),
                }
            )

        # 2) Database users not already covered by DEMO_USERS
        try:
            conn = get_db_connection()
            try:
                db_users = conn.execute(
                    "SELECT id, email, full_name, role, branch_id FROM users WHERE company_id = ?",
                    (company_id,),
                ).fetchall()
                for dbr in db_users:
                    uid = str(dbr["id"])
                    if uid in seen_ids:
                        continue
                    if role in {"branch_admin", "employee"} and current_branch and str(dbr["branch_id"] or "") != current_branch:
                        continue
                    seen_ids.add(uid)
                    rows.append(
                        {
                            "id": uid,
                            "name": str(dbr["full_name"] or dbr["email"] or ""),
                            "email": str(dbr["email"] or ""),
                            "role": str(dbr["role"] or "employee"),
                            "branch_id": dbr["branch_id"],
                        }
                    )
            finally:
                conn.close()
        except Exception as exc:
            logger.warning("Failed to query users table: %s", exc)

        return rows
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Unexpected error listing users")
        raise HTTPException(status_code=500, detail="Internal server error") from exc


@app.post("/api/users/create-branch-manager", tags=["Users"])
def create_branch_manager(payload: CreateBranchManagerRequest, request: Request):
    """Create a new branch manager user and assign to a branch.

    Admin-only endpoint.
    """
    require_admin_request(request)
    company_id = require_company_id(request)

    # Validate inputs
    name = (payload.name or "").strip()
    email = (payload.email or "").strip().lower()
    phone = (payload.phone or "").strip() or None
    password = payload.password or ""
    branch_id = payload.branch_id

    if not name:
        raise HTTPException(status_code=400, detail="Name is required")
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    hashed = hash_password_for_storage(password)

    conn = get_db_connection()
    try:
        # Check duplicate email
        existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
        if email in DEMO_USERS:
            raise HTTPException(status_code=400, detail="Email already registered")

        # Verify branch exists and belongs to same company
        branch_row = conn.execute(
            "SELECT id FROM branches WHERE id = ? AND company_id = ? AND is_active = 1",
            (branch_id, company_id),
        ).fetchone()
        if not branch_row:
            raise HTTPException(status_code=404, detail="Branch not found or inactive")

        created_at = datetime.now(timezone.utc).isoformat()
        cur = conn.execute(
            """
            INSERT INTO users (email, full_name, role, branch_id, company_id, created_at, hashed_password, phone)
            VALUES (?, ?, 'branch_manager', ?, ?, ?, ?, ?)
            """,
            (email, name, branch_id, company_id, created_at, hashed, phone),
        )
        new_id = cur.lastrowid

        # Link the new manager to the branch
        conn.execute(
            "UPDATE branches SET manager_id = ? WHERE id = ? AND company_id = ?",
            (str(new_id), int(branch_id), company_id),
        )
        conn.commit()

        # Also create user in the SQLAlchemy auth database so login works
        try:
            from backend.database.connection import SessionLocal
            from backend.database.models import User as SAUser, UserRole as SARole, Company as SACompany
            sa_db = SessionLocal()
            try:
                # Check not already in auth DB
                sa_existing = sa_db.query(SAUser).filter(SAUser.email == email).first()
                if not sa_existing:
                    # Resolve numeric company_id from company name
                    sa_company = sa_db.query(SACompany).filter(SACompany.name == company_id).first()
                    sa_company_id = sa_company.id if sa_company else 1
                    sa_user = SAUser(
                        email=email,
                        full_name=name,
                        hashed_password=hashed,
                        role=SARole.BRANCH_MANAGER,
                        company_id=sa_company_id,
                        branch_id=int(branch_id),
                        is_active=True,
                    )
                    sa_db.add(sa_user)
                    sa_db.commit()
                    logger.info("Auth DB user created for %s (company_id=%s)", email, sa_company_id)
            finally:
                sa_db.close()
        except Exception as sa_exc:
            logger.warning("Failed to create user in auth DB: %s", sa_exc)

        logger.info("Branch manager created: id=%s email=%s branch=%s", new_id, email, branch_id)

        return {
            "id": str(new_id),
            "email": email,
            "name": name,
            "phone": phone,
            "role": "branch_manager",
            "branch_id": branch_id,
            "company": company_id,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error creating branch manager")
        raise HTTPException(status_code=500, detail="Internal server error") from exc
    finally:
        conn.close()


@app.put("/api/users/{user_id}", tags=["Users"])
def update_user(user_id: int, payload: UpdateUserRequest, request: Request):
    """Update a user's profile information. Admin-only."""
    require_admin_request(request)
    company_id = require_company_id(request)

    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT id, email, full_name, phone, role, company_id FROM users WHERE id = ? AND company_id = ?",
            (user_id, company_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="User not found")

        next_name = payload.name.strip() if payload.name is not None else str(row["full_name"] or "")
        next_phone = payload.phone.strip() if payload.phone is not None else (row["phone"] if row["phone"] else None)
        next_email = payload.email.strip().lower() if payload.email is not None else str(row["email"])

        if not next_name:
            raise HTTPException(status_code=400, detail="Name is required")
        if not next_email:
            raise HTTPException(status_code=400, detail="Email is required")

        # Check email uniqueness if changed
        if next_email != str(row["email"]).lower():
            dup = conn.execute("SELECT id FROM users WHERE email = ? AND id != ?", (next_email, user_id)).fetchone()
            if dup:
                raise HTTPException(status_code=400, detail="Email already in use")
            demo = DEMO_USERS.get(next_email)
            if demo and str(demo.get("id", "")) != str(user_id):
                raise HTTPException(status_code=400, detail="Email already in use")

        # Optional password update
        if payload.password is not None:
            if len(payload.password) < 8:
                raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
            hashed = hash_password_for_storage(payload.password)
            conn.execute(
                "UPDATE users SET full_name = ?, email = ?, phone = ?, hashed_password = ? WHERE id = ?",
                (next_name, next_email, next_phone, hashed, user_id),
            )
        else:
            conn.execute(
                "UPDATE users SET full_name = ?, email = ?, phone = ? WHERE id = ?",
                (next_name, next_email, next_phone, user_id),
            )
        conn.commit()

        try:
            from backend.database.connection import SessionLocal
            from backend.database.models import User as SAUser

            sa_db = SessionLocal()
            try:
                sa_user = sa_db.query(SAUser).filter(SAUser.email == str(row["email"])).first()
                if sa_user:
                    sa_user.full_name = next_name
                    sa_user.email = next_email
                    if payload.password is not None:
                        sa_user.hashed_password = hashed
                    sa_db.commit()
            finally:
                sa_db.close()
        except Exception as sa_exc:
            logger.warning("Failed to update user in auth DB: %s", sa_exc)

        # Sync in-memory DEMO_USERS cache so changes are immediately visible
        for demo_email, demo_user in list(DEMO_USERS.items()):
            if str(demo_user.get("id", "")) == str(user_id):
                demo_user["name"] = next_name
                demo_user["phone"] = next_phone
                if next_email != demo_email:
                    # Email changed — re-key the dict entry
                    demo_user["email"] = next_email
                    DEMO_USERS[next_email] = demo_user
                    del DEMO_USERS[demo_email]
                    if demo_email in DEMO_PASSWORDS:
                        DEMO_PASSWORDS[next_email] = DEMO_PASSWORDS.pop(demo_email)
                break

        logger.info("User updated: id=%s email=%s", user_id, next_email)
        return {
            "id": str(user_id),
            "name": next_name,
            "email": next_email,
            "phone": next_phone,
            "role": str(row["role"]),
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error updating user %s", user_id)
        raise HTTPException(status_code=500, detail="Internal server error") from exc
    finally:
        conn.close()


@app.get("/api/branches", response_model=List[BranchResponse], tags=["Branches"])
def list_branches_endpoint(request: Request):
    current_user = require_authenticated_request(request)
    company_id = require_company_id(request)
    role = normalize_role_text(current_user.get("role"))
    user_branch = current_user.get("branch_id")

    conn = get_db_connection()
    try:
        if role in {"super_admin", "company_admin"}:
            rows = conn.execute(
                """
                SELECT id, name, city, phone, manager_id, created_at, is_active
                FROM branches
                WHERE company_id = ?
                ORDER BY created_at DESC
                """,
                (company_id,),
            ).fetchall()
        else:
            if user_branch is None:
                return []
            rows = conn.execute(
                """
                SELECT id, name, city, phone, manager_id, created_at, is_active
                FROM branches
                WHERE company_id = ? AND id = ?
                ORDER BY created_at DESC
                """,
                (company_id, int(user_branch)),
            ).fetchall()

        return [_build_branch_response(r, company_id) for r in rows]
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error listing branches for company=%s", company_id)
        raise HTTPException(status_code=500, detail="Internal server error") from exc
    finally:
        conn.close()


@app.get("/branches", response_model=List[BranchResponse], tags=["Branches"])
def list_branches_endpoint_alias(request: Request):
    return list_branches_endpoint(request)


@app.post("/api/branches", response_model=BranchResponse, tags=["Branches"])
def create_branch_endpoint(payload: BranchCreateRequest, request: Request):
    require_admin_request(request)
    company_id = require_company_id(request)

    # --- input validation ---
    branch_name = (payload.name or "").strip()
    branch_city = (payload.city or "").strip()
    if not branch_name:
        raise HTTPException(status_code=400, detail="Branch name is required")
    if not branch_city:
        raise HTTPException(status_code=400, detail="City is required")

    conn = get_db_connection()
    try:
        if payload.manager_id:
            manager_user = next(
                (u for u in DEMO_USERS.values() if str(u.get("id") or "") == str(payload.manager_id)),
                None,
            )
            if not manager_user:
                db_mgr = conn.execute(
                    "SELECT id, role, company_id FROM users WHERE id = ?",
                    (int(payload.manager_id),),
                ).fetchone()
                if not db_mgr:
                    raise HTTPException(status_code=404, detail="Assigned manager not found")
                if str(db_mgr["company_id"] or "") != str(company_id):
                    raise HTTPException(status_code=400, detail="Assigned manager must belong to the same company")
                if normalize_role_text(db_mgr["role"]) in {"super_admin", "company_admin"}:
                    raise HTTPException(status_code=400, detail="Admin cannot be assigned as branch manager")
            else:
                if str(manager_user.get("company") or "") != str(company_id):
                    raise HTTPException(status_code=400, detail="Assigned manager must belong to the same company")
                if normalize_role_text(manager_user.get("role")) in {"super_admin", "company_admin"}:
                    raise HTTPException(status_code=400, detail="Admin cannot be assigned as branch manager")

        created_at = datetime.now(timezone.utc).isoformat()
        cur = conn.execute(
            """
            INSERT INTO branches (company_id, name, city, phone, manager_id, created_at, is_active)
            VALUES (?, ?, ?, ?, ?, ?, 1)
            """,
            (company_id, branch_name, branch_city, (payload.phone or "").strip() or None, payload.manager_id, created_at),
        )
        conn.commit()
        branch_id = int(cur.lastrowid)
        row = conn.execute(
            "SELECT id, name, city, phone, manager_id, created_at, is_active FROM branches WHERE id = ?",
            (branch_id,),
        ).fetchone()

        _sync_demo_user_manager_assignment(
            company_id=company_id,
            branch_id=branch_id,
            manager_id=str(payload.manager_id) if payload.manager_id is not None else None,
        )

        logger.info("Branch created: id=%s name=%s company=%s", branch_id, branch_name, company_id)
        return _build_branch_response(row, company_id)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error creating branch for company=%s", company_id)
        raise HTTPException(status_code=500, detail="Internal server error") from exc
    finally:
        conn.close()


@app.post("/branches", response_model=BranchResponse, tags=["Branches"])
def create_branch_endpoint_alias(payload: BranchCreateRequest, request: Request):
    return create_branch_endpoint(payload, request)


@app.put("/api/branches/{branch_id}", response_model=BranchResponse, tags=["Branches"])
def update_branch_endpoint(branch_id: int, payload: BranchUpdateRequest, request: Request):
    require_admin_request(request)
    company_id = require_company_id(request)

    # --- input validation ---
    if payload.name is not None and not payload.name.strip():
        raise HTTPException(status_code=400, detail="Branch name cannot be empty")
    if payload.city is not None and not payload.city.strip():
        raise HTTPException(status_code=400, detail="City cannot be empty")

    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT id, name, city, phone, manager_id, created_at, is_active FROM branches WHERE id = ? AND company_id = ?",
            (branch_id, company_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Branch not found")

        if payload.manager_id:
            manager_user = next(
                (u for u in DEMO_USERS.values() if str(u.get("id") or "") == str(payload.manager_id)),
                None,
            )
            if not manager_user:
                db_mgr = conn.execute(
                    "SELECT id, role, company_id FROM users WHERE id = ?",
                    (int(payload.manager_id),),
                ).fetchone()
                if not db_mgr:
                    raise HTTPException(status_code=404, detail="Assigned manager not found")
                if str(db_mgr["company_id"] or "") != str(company_id):
                    raise HTTPException(status_code=400, detail="Assigned manager must belong to the same company")
                if normalize_role_text(db_mgr["role"]) in {"super_admin", "company_admin"}:
                    raise HTTPException(status_code=400, detail="Admin cannot be assigned as branch manager")
            else:
                if str(manager_user.get("company") or "") != str(company_id):
                    raise HTTPException(status_code=400, detail="Assigned manager must belong to the same company")
                if normalize_role_text(manager_user.get("role")) in {"super_admin", "company_admin"}:
                    raise HTTPException(status_code=400, detail="Admin cannot be assigned as branch manager")

        previous_manager_id = str(row["manager_id"]) if row["manager_id"] is not None else None

        next_name = payload.name.strip() if payload.name is not None else str(row["name"])
        next_city = payload.city.strip() if payload.city is not None else str(row["city"])
        next_phone = payload.phone.strip() if payload.phone is not None else (str(row["phone"]) if row["phone"] else None)
        next_manager_id = payload.manager_id if payload.manager_id is not None else row["manager_id"]
        next_is_active = int(payload.is_active) if payload.is_active is not None else int(row["is_active"] or 0)

        conn.execute(
            """
            UPDATE branches
            SET name = ?, city = ?, phone = ?, manager_id = ?, is_active = ?
            WHERE id = ? AND company_id = ?
            """,
            (next_name, next_city, next_phone or None, next_manager_id, next_is_active, branch_id, company_id),
        )
        conn.commit()

        updated = conn.execute(
            "SELECT id, name, city, phone, manager_id, created_at, is_active FROM branches WHERE id = ?",
            (branch_id,),
        ).fetchone()

        _sync_demo_user_manager_assignment(
            company_id=company_id,
            branch_id=branch_id,
            manager_id=str(next_manager_id) if next_manager_id is not None else None,
            previous_manager_id=previous_manager_id,
        )

        logger.info("Branch updated: id=%s company=%s", branch_id, company_id)
        return _build_branch_response(updated, company_id)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error updating branch %s for company=%s", branch_id, company_id)
        raise HTTPException(status_code=500, detail="Internal server error") from exc
    finally:
        conn.close()


@app.put("/branches/{branch_id}", response_model=BranchResponse, tags=["Branches"])
def update_branch_endpoint_alias(branch_id: int, payload: BranchUpdateRequest, request: Request):
    return update_branch_endpoint(branch_id, payload, request)


@app.post("/api/branches/{branch_id}/assign-manager", response_model=BranchResponse, tags=["Branches"])
def assign_branch_manager_endpoint(branch_id: int, payload: AssignManagerRequest, request: Request):
    require_admin_request(request)
    company_id = require_company_id(request)

    manager_id = str(payload.user_id)
    manager_user = next(
        (u for u in DEMO_USERS.values() if str(u.get("id") or "") == manager_id),
        None,
    )
    if not manager_user:
        raise HTTPException(status_code=404, detail="Assigned manager not found")
    if str(manager_user.get("company") or "") != str(company_id):
        raise HTTPException(status_code=400, detail="Assigned manager must belong to the same company")
    if normalize_role_text(manager_user.get("role")) in {"super_admin", "company_admin"}:
        raise HTTPException(status_code=400, detail="Admin cannot be assigned as branch manager")

    conn = get_db_connection()
    try:
        branch_row = conn.execute(
            "SELECT id, name, city, phone, manager_id, created_at, is_active FROM branches WHERE id = ? AND company_id = ?",
            (branch_id, company_id),
        ).fetchone()
        if not branch_row:
            raise HTTPException(status_code=404, detail="Branch not found")

        previous_manager_id = str(branch_row["manager_id"]) if branch_row["manager_id"] is not None else None
        conn.execute(
            "UPDATE branches SET manager_id = ? WHERE id = ? AND company_id = ?",
            (manager_id, branch_id, company_id),
        )
        conn.commit()

        _sync_demo_user_manager_assignment(
            company_id=company_id,
            branch_id=branch_id,
            manager_id=manager_id,
            previous_manager_id=previous_manager_id,
        )
        _persist_user_branch_role(manager_id, company_id, branch_id, "branch_manager")

        updated = conn.execute(
            "SELECT id, name, city, phone, manager_id, created_at, is_active FROM branches WHERE id = ? AND company_id = ?",
            (branch_id, company_id),
        ).fetchone()

        logger.info("Manager assigned: user_id=%s -> branch_id=%s company=%s", manager_id, branch_id, company_id)
        return _build_branch_response(updated, company_id)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error assigning manager to branch %s", branch_id)
        raise HTTPException(status_code=500, detail="Internal server error") from exc
    finally:
        conn.close()


@app.post("/branches/{branch_id}/assign-manager", response_model=BranchResponse, tags=["Branches"])
def assign_branch_manager_endpoint_alias(branch_id: int, payload: AssignManagerRequest, request: Request):
    return assign_branch_manager_endpoint(branch_id, payload, request)


@app.delete("/api/branches/{branch_id}", tags=["Branches"])
def delete_branch_endpoint(branch_id: int, request: Request):
    require_admin_request(request)
    company_id = require_company_id(request)
    conn = get_db_connection()
    try:
        existing = conn.execute(
            "SELECT manager_id FROM branches WHERE id = ? AND company_id = ?",
            (branch_id, company_id),
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Branch not found")

        conn.execute(
            "DELETE FROM branches WHERE id = ? AND company_id = ?",
            (branch_id, company_id),
        )
        conn.commit()

        _sync_demo_user_manager_assignment(
            company_id=company_id,
            branch_id=branch_id,
            manager_id=None,
            previous_manager_id=(str(existing["manager_id"]) if existing["manager_id"] is not None else None),
        )

        logger.info("Branch deleted: id=%s company=%s", branch_id, company_id)
        return {"ok": True, "deleted": branch_id}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error deleting branch %s for company=%s", branch_id, company_id)
        raise HTTPException(status_code=500, detail="Internal server error") from exc
    finally:
        conn.close()


@app.delete("/branches/{branch_id}", tags=["Branches"])
def delete_branch_endpoint_alias(branch_id: int, request: Request):
    return delete_branch_endpoint(branch_id, request)


def _compute_branch_analytics_payload(company_id: str, branch_id: int) -> Optional[Dict[str, Any]]:
    if not company_has_active_dataset(company_id, "sales", branch_id=str(branch_id)):
        return None

    try:
        sales_df = normalize_sales_dataframe(load_active_sales_df(company_id, branch_id=str(branch_id)))
    except HTTPException as exc:
        if exc.status_code in {404, 503}:
            return None
        raise

    if sales_df.empty:
        return None

    total_revenue = float(sales_df["__total_price"].sum())
    total_orders = int(len(sales_df))
    top_city = "N/A"
    if sales_df.get("__city") is not None and sales_df["__city"].notna().any():
        top_city = str(sales_df.groupby("__city")["__total_price"].sum().idxmax())
    top_product = "N/A"
    if sales_df.get("__product") is not None and sales_df["__product"].notna().any():
        top_product = str(sales_df.groupby("__product")["__total_price"].sum().idxmax())

    return {
        "branch_id": int(branch_id),
        "total_revenue": total_revenue,
        "total_orders": total_orders,
        "average_order_value": (total_revenue / total_orders) if total_orders > 0 else 0.0,
        "top_city": top_city,
        "top_product": top_product,
    }


@app.get("/api/branches/performance", tags=["Branches"])
def list_branch_performance_endpoint(request: Request):
    current_user = require_authenticated_request(request)
    company_id = require_company_id(request)
    role = normalize_role_text(current_user.get("role"))
    user_branch = current_user.get("branch_id")

    conn = get_db_connection()
    try:
        if role in {"super_admin", "company_admin"}:
            rows = conn.execute(
                """
                SELECT id, name
                FROM branches
                WHERE company_id = ? AND is_active = 1
                ORDER BY created_at DESC
                """,
                (company_id,),
            ).fetchall()
        else:
            if user_branch is None:
                return []
            rows = conn.execute(
                """
                SELECT id, name
                FROM branches
                WHERE company_id = ? AND id = ? AND is_active = 1
                ORDER BY created_at DESC
                """,
                (company_id, int(user_branch)),
            ).fetchall()
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error listing branch performance for company=%s", company_id)
        raise HTTPException(status_code=500, detail="Internal server error") from exc
    finally:
        conn.close()

    performance = []
    for row in rows:
        analytics = _compute_branch_analytics_payload(company_id, int(row["id"]))
        if analytics is None:
            continue
        performance.append(
            {
                "id": int(row["id"]),
                "name": str(row["name"]),
                "sales": float(analytics["total_revenue"]),
            }
        )

    return performance


@app.get("/branches/performance", tags=["Branches"])
def list_branch_performance_endpoint_alias(request: Request):
    return list_branch_performance_endpoint(request)


@app.get("/api/branches/{branch_id}/analytics", tags=["Branches"])
def branch_analytics_endpoint(branch_id: int, request: Request):
    current_user = require_authenticated_request(request)
    company_id = require_company_id(request)
    role = normalize_role_text(current_user.get("role"))
    user_branch = current_user.get("branch_id")
    if role in {"branch_admin", "employee"} and str(user_branch) != str(branch_id):
        raise HTTPException(status_code=403, detail="Branch access denied")

    analytics = _compute_branch_analytics_payload(company_id, branch_id)
    if analytics is None:
        return Response(status_code=204)

    return analytics


@app.get("/branches/{branch_id}/analytics", tags=["Branches"])
def branch_analytics_endpoint_alias(branch_id: int, request: Request):
    return branch_analytics_endpoint(branch_id, request)


# ============================================================================
# Data Loading Helpers
# ============================================================================

# Global DataFrames - NEVER CACHED, always reload from disk for freshness
df = None
forecast_df = None
sentiment_df = None
recommendation_df = None
model = None
data_last_modified = None
TENANT_RUNTIME_CACHE: Dict[str, Dict[str, Any]] = {}
ACTIVE_RUNTIME_CACHE_KEY: Optional[str] = None


def _runtime_tenant_key(company_id: Optional[str] = None, branch_id: Optional[str] = None) -> str:
    return f"{str(company_id or '__global__').strip()}::{str(branch_id or 'GLOBAL').strip()}"


def _get_runtime_cache_entry(company_id: Optional[str] = None, branch_id: Optional[str] = None) -> Dict[str, Any]:
    return TENANT_RUNTIME_CACHE.get(_runtime_tenant_key(company_id, branch_id), {})


def clear_all_caches_and_reset(company_id: Optional[str] = None, branch_id: Optional[str] = None):
    """
    Clear in-memory caches for a single tenant, or all tenants when no scope is provided.
    
    This function MUST be called:
    1. After deleting any dataset
    2. After uploading any dataset (before pipeline runs)
    3. After any pipeline completes
    
    ENTERPRISE BEHAVIOR:
    - No stale data should ever remain in memory
    - All APIs must fetch fresh data from disk after this call
    """
    global df, forecast_df, sentiment_df, recommendation_df, model, data_last_modified, ACTIVE_RUNTIME_CACHE_KEY
    
    logger.info("=" * 60)
    if company_id is None:
        logger.info("[CACHE CLEAR] Resetting ALL in-memory state")
    else:
        logger.info(f"[CACHE CLEAR] Resetting in-memory state for {company_id} / {branch_id or 'GLOBAL'}")
    logger.info("=" * 60)

    if company_id is None:
        TENANT_RUNTIME_CACHE.clear()
        ACTIVE_RUNTIME_CACHE_KEY = None
        df = None
        forecast_df = None
        sentiment_df = None
        recommendation_df = None
        model = None
        data_last_modified = None
    else:
        cache_key = _runtime_tenant_key(company_id, branch_id)
        TENANT_RUNTIME_CACHE.pop(cache_key, None)
        if ACTIVE_RUNTIME_CACHE_KEY == cache_key:
            ACTIVE_RUNTIME_CACHE_KEY = None
            df = None
            forecast_df = None
            sentiment_df = None
            recommendation_df = None
            model = None
            data_last_modified = None
    
    logger.info("[CACHE CLEAR] All global DataFrames set to None")
    logger.info("[CACHE CLEAR] Memory state cleared - APIs will read fresh from disk")
    logger.info("=" * 60)


def reload_all_data_from_disk(company_id: str = "Acme Corp", branch_id: Optional[str] = None):
    """
    Reload all data from disk into global DataFrames.
    Called after pipeline completion to ensure fresh data is available.
    
    Returns:
        dict with status of each data source
    """
    global df, forecast_df, sentiment_df, recommendation_df, model, data_last_modified, ACTIVE_RUNTIME_CACHE_KEY
    
    logger.info("=" * 60)
    logger.info("[DATA RELOAD] Reloading all data from disk")
    logger.info("=" * 60)
    
    status = {
        "cleaned_dataset": False,
        "forecast": False,
        "sentiment": False,
        "recommendations": False,
        "model": False
    }
    
    data_last_modified = datetime.now(timezone.utc)
    
    # Load cleaned dataset - search multiple possible files
    possible_data_files = [
        tenant_file_path(company_id, "cleaned_dataset.csv", branch_id=branch_id),
        tenant_file_path(company_id, "sales.csv", branch_id=branch_id),
        tenant_file_path(company_id, "merged_data.csv", branch_id=branch_id),
    ]
    
    df = None
    for data_path in possible_data_files:
        if data_path.exists():
            try:
                df = pd.read_csv(data_path)
                # Auto-detect date column
                date_cols = ["OrderDate", "Sale_Date", "Order_Date", "Date", "order_date"]
                date_col = next((c for c in date_cols if c in df.columns), None)
                if date_col:
                    df = df.rename(columns={date_col: "OrderDate"})
                    df["OrderDate"] = pd.to_datetime(df["OrderDate"], errors="coerce")
                
                if df.empty:
                    logger.warning(f"[DATA RELOAD] {data_path.name} is empty")
                    df = None
                    continue
                else:
                    logger.info(f"[DATA RELOAD] Loaded {data_path.name}: {len(df)} rows")
                    status["cleaned_dataset"] = True
                    break
            except Exception as e:
                logger.warning(f"[DATA RELOAD] Failed to load {data_path.name}: {e}")
                df = None
    
    if df is None:
        logger.info("[DATA RELOAD] No sales data file found")
    
    # Load forecast - search multiple possible files
    forecast_files = [
        tenant_file_path(company_id, "sales_forecast.csv", branch_id=branch_id),
        tenant_file_path(company_id, "sales_forecast_future.csv", branch_id=branch_id),
        ensure_company_output_dir(company_id, branch_id) / "forecasts" / "forecast.csv",
        ensure_company_dir(company_id, "sales", branch_id=branch_id) / "forecast.csv",
    ]
    
    forecast_df = None
    for forecast_path in forecast_files:
        if forecast_path.exists():
            try:
                forecast_df = pd.read_csv(forecast_path)
                # Auto-detect date column
                date_cols = ["MonthStart", "ds", "date", "Date", "OrderDate"]
                date_col = next((c for c in date_cols if c in forecast_df.columns), None)
                if date_col and date_col != "MonthStart":
                    forecast_df = forecast_df.rename(columns={date_col: "MonthStart"})
                if "MonthStart" in forecast_df.columns:
                    forecast_df["MonthStart"] = pd.to_datetime(forecast_df["MonthStart"], errors="coerce")
                logger.info(f"[DATA RELOAD] Loaded {forecast_path.name}: {len(forecast_df)} rows")
                status["forecast"] = True
                break
            except Exception as e:
                logger.warning(f"[DATA RELOAD] Failed to load {forecast_path.name}: {e}")
                forecast_df = None
    
    if forecast_df is None:
        logger.info("[DATA RELOAD] No forecast file found")
    
    # Load sentiment
    sentiment_path = tenant_file_path(company_id, "sentiment_results.csv", branch_id=branch_id)
    if sentiment_path.exists():
        try:
            sentiment_df = pd.read_csv(sentiment_path)
            logger.info(f"[DATA RELOAD] Loaded sentiment_results.csv: {len(sentiment_df)} rows")
            status["sentiment"] = True
        except Exception as e:
            logger.warning(f"[DATA RELOAD] Failed to load sentiment_results.csv: {e}")
            sentiment_df = None
    else:
        sentiment_df = None
    
    # Load recommendations
    recommendation_df = None
    recs_path = None
    for candidate in recommendation_result_candidates(company_id, branch_id=branch_id):
        if candidate.exists():
            recs_path = candidate
            break
    if recs_path is not None:
        try:
            recommendation_df = pd.read_csv(recs_path)
            logger.info(f"[DATA RELOAD] Loaded product_recommendations.csv: {len(recommendation_df)} rows")
            status["recommendations"] = True
        except Exception as e:
            logger.warning(f"[DATA RELOAD] Failed to load product_recommendations.csv: {e}")
            recommendation_df = None
    
    # Load model
    if MODEL_PATH.exists():
        try:
            model = joblib.load(MODEL_PATH)
            logger.info("[DATA RELOAD] Loaded forecasting model")
            status["model"] = True
        except Exception as e:
            logger.warning(f"[DATA RELOAD] Failed to load model: {e}")
            model = None
    else:
        model = None
    
    logger.info(f"[DATA RELOAD] Status: {status}")
    logger.info("=" * 60)

    cache_key = _runtime_tenant_key(company_id, branch_id)
    TENANT_RUNTIME_CACHE[cache_key] = {
        "df": df,
        "forecast_df": forecast_df,
        "sentiment_df": sentiment_df,
        "recommendation_df": recommendation_df,
        "model": model,
        "data_last_modified": data_last_modified,
    }
    ACTIVE_RUNTIME_CACHE_KEY = cache_key
    
    return status


@app.on_event("startup")
def load_data():
    """Load all data at startup - sync CSV to database for persistence."""
    reload_all_data_from_disk()
    
    # Sync existing tenant CSV files to database for persistence across restarts
    if ANALYTICS_PERSISTENCE_AVAILABLE:
        try:
            logger.info("[STARTUP] Syncing existing tenant CSV data to database...")
            sync_results: dict[str, dict[str, bool]] = {}
            for company_dir in sorted([p for p in DATA_DIR.iterdir() if p.is_dir()]):
                company_name = company_dir.name
                sales_dir = company_dir / "sales"
                reviews_dir = company_dir / "reviews"
                if sales_dir.exists():
                    sync_results[f"{company_name}:sales"] = sync_csv_to_database(company_name, sales_dir)
                if reviews_dir.exists():
                    sync_results[f"{company_name}:reviews"] = sync_csv_to_database(company_name, reviews_dir)
                branches_dir = company_dir / "branches"
                if branches_dir.exists():
                    for branch_dir in sorted([p for p in branches_dir.iterdir() if p.is_dir()]):
                        branch_sales_dir = branch_dir / "sales"
                        branch_reviews_dir = branch_dir / "reviews"
                        if branch_sales_dir.exists():
                            sync_results[f"{company_name}:{branch_dir.name}:sales"] = sync_csv_to_database(company_name, branch_sales_dir)
                        if branch_reviews_dir.exists():
                            sync_results[f"{company_name}:{branch_dir.name}:reviews"] = sync_csv_to_database(company_name, branch_reviews_dir)
            logger.info(f"[STARTUP] Database sync complete: {sync_results}")
        except Exception as e:
            logger.warning(f"[STARTUP] Failed to sync CSV to database: {e}")


def require_company_id(request: Request) -> str:
    """Resolve company_id from the authenticated JWT context.

    SECURITY:
    - Never trust X-Company-ID from the client for authorization.
    - Company scope is always derived server-side from the authenticated user.
    """

    user = get_user_from_request(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    return resolve_company_id_from_user(user)


def resolve_company_id_from_user(user: Dict[str, Any]) -> str:
    company = str(user.get("company") or "").strip()
    if company:
        return company

    company_id = user.get("company_id")
    if company_id is None:
        raise HTTPException(status_code=403, detail="No company assigned to current user")
    # Best-effort mapping for legacy single-company installs.
    try:
        if int(company_id) == 1:
            return "Acme Corp"
    except Exception:
        pass
    return str(company_id).strip()


def trigger_recommendation_pipeline(sales_file_path: Path, company_id: str = "Acme Corp", branch_id: Optional[str] = None) -> bool:
    """
    Trigger Market Basket Analysis (Apriori) pipeline.
    Generates product_recommendations.csv from sales transactions.
    
    Args:
        sales_file_path: Path to sales CSV with OrderID and ProductID columns
        
    Returns:
        True if successful, False otherwise
    """
    global recommendation_df
    
    try:
        logger.info(f"[TRIGGER RECO] Starting recommendations pipeline for: {sales_file_path}")
        
        # Load sales data
        df = pd.read_csv(sales_file_path)
        logger.info(f"[TRIGGER RECO] Loaded {len(df)} rows from sales file")
        
        # Validate required columns
        order_candidates = ['OrderID', 'Order_ID', 'order_id', 'InvoiceNo']
        order_col = next((c for c in order_candidates if c in df.columns), None)
        
        if not order_col:
            logger.warning("[TRIGGER RECO] OrderID column missing - cannot generate recommendations")
            return False
            
        product_col = None
        for col in ['ProductID', 'Product_ID', 'Product', 'SKU', 'Product_Name']:
            if col in df.columns:
                product_col = col
                break
                
        if not product_col:
            logger.warning("[TRIGGER RECO] Product column missing - cannot generate recommendations")
            return False
        
        # Check if we have multi-product orders
        order_counts = df.groupby(order_col).size()
        multi_product_orders = (order_counts > 1).sum()
        
        if multi_product_orders < 2:
            logger.warning(f"[TRIGGER RECO] Only {multi_product_orders} multi-product orders - insufficient for recommendations")
            # Create empty recommendations file
            empty_df = pd.DataFrame(columns=['RuleID', 'IF', 'THEN', 'Support', 'Confidence', 'Lift'])
            empty_df.to_csv(tenant_file_path(company_id, "product_recommendations.csv", branch_id=branch_id), index=False)
            return False
        
        logger.info(f"[TRIGGER RECO] Found {multi_product_orders} multi-product orders - proceeding with Apriori")
        
        # Copy sales file to canonical location (data/sales.csv) for the pipeline
        canonical_sales = tenant_file_path(company_id, "sales.csv", branch_id=branch_id)
        shutil.copy2(sales_file_path, canonical_sales)
        logger.info(f"[TRIGGER RECO] Copied to canonical location: {canonical_sales}")
        
        # Run recommendation pipeline by calling the main script
        result = subprocess.run(
            [sys.executable, str(BASE_DIR / "src" / "05_recommendation.py")],
            cwd=str(BASE_DIR),
            env=build_tenant_ml_env(company_id, branch_id, dataset_type="sales"),
            capture_output=True,
            text=True,
            timeout=180
        )
        
        if result.returncode == 0:
            logger.info("[TRIGGER RECO] Recommendations pipeline completed successfully")
            # Reload global recommendation_df
            reco_path = tenant_file_path(company_id, "product_recommendations.csv", branch_id=branch_id)
            resolved_path = None
            for candidate in recommendation_result_candidates(company_id, branch_id=branch_id):
                if candidate.exists():
                    resolved_path = candidate
                    break
            if resolved_path is not None and resolved_path != reco_path:
                try:
                    reco_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(resolved_path, reco_path)
                    resolved_path = reco_path
                except Exception as exc:
                    logger.warning("[TRIGGER RECO] Failed to sync recommendations output: %s", exc)
            if resolved_path is not None and resolved_path.exists():
                try:
                    recommendation_df = pd.read_csv(resolved_path)
                    logger.info(f"[TRIGGER RECO] Loaded {len(recommendation_df)} recommendation rules")
                    return True
                except Exception as e:
                    logger.error(f"[TRIGGER RECO] Failed to reload recommendations: {e}")
                    return False
            else:
                logger.warning("[TRIGGER RECO] product_recommendations.csv not created despite successful exit")
                return False
        else:
            logger.error(f"[TRIGGER RECO] Recommendations pipeline failed: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"[TRIGGER RECO] Error triggering recommendations pipeline: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def trigger_sentiment_pipeline(reviews_file_path: Path, company_id: str = "Acme Corp", branch_id: Optional[str] = None) -> bool:
    """
    Trigger NLP Customer Feedback pipeline.
    Generates sentiment_results.csv from customer reviews.
    
    Args:
        reviews_file_path: Path to reviews CSV with review text
        
    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info(f"Triggering sentiment pipeline for: {reviews_file_path}")
        
        # Validate reviews file has text column
        df = pd.read_csv(reviews_file_path)
        
        text_col = None
        for col in ['ReviewText', 'review_text', 'Review', 'text', 'Text', 'comment']:
            if col in df.columns:
                text_col = col
                break
                
        if not text_col:
            logger.warning("Review text column missing - cannot analyze sentiment")
            return False
        
        if df[text_col].isna().all():
            logger.warning("All review texts are empty - cannot analyze sentiment")
            return False
        
        logger.info(f"Found {len(df)} reviews with text - proceeding with Customer Feedback")
        
        # Run sentiment pipeline
        import subprocess
        result = subprocess.run(
            [sys.executable, str(BASE_DIR / "src" / "06_sentiment.py")],
            cwd=str(BASE_DIR),
            env=build_tenant_ml_env(company_id, branch_id, dataset_type="reviews"),
            capture_output=True,
            text=True,
            timeout=180
        )
        
        if result.returncode == 0:
            logger.info("Sentiment pipeline completed successfully")
            # Reload global sentiment_df
            global sentiment_df
            try:
                sentiment_df = pd.read_csv(tenant_file_path(company_id, "sentiment_results.csv", branch_id=branch_id))
                logger.info(f"Reloaded {len(sentiment_df)} sentiment records")
            except:
                sentiment_df = None
            return True
        else:
            logger.error(f"Sentiment pipeline failed: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Error triggering sentiment pipeline: {e}")
        return False


def trigger_rfm_pipeline(sales_file_path: Path, company_id: str = "Acme Corp", branch_id: Optional[str] = None) -> bool:
    """
    Trigger RFM Segmentation analysis pipeline.
    Generates rfm_table.csv from sales transactions.
    
    Args:
        sales_file_path: Path to sales CSV with CustomerID, OrderDate, TotalPrice columns
        company_id: Company identifier for database sync
        
    Returns:
        True if successful, False otherwise
    """
    global rfm_df
    
    try:
        logger.info(f"[TRIGGER RFM] Starting RFM pipeline for: {sales_file_path}")
        
        # Load sales data to validate
        df = pd.read_csv(sales_file_path)
        logger.info(f"[TRIGGER RFM] Loaded {len(df)} rows from sales file")
        
        # Validate required columns for RFM (CustomerID, date, value)
        customer_candidates = ['CustomerID', 'Customer_ID', 'customer_id', 'CustomerId']
        date_candidates = ['OrderDate', 'Sale_Date', 'Order_Date', 'Date', 'order_date']
        value_candidates = ['TotalPrice', 'Price', 'Sales_Amount', 'Revenue', 'Amount', 'Total_Price']
        
        customer_col = next((c for c in customer_candidates if c in df.columns), None)
        date_col = next((c for c in date_candidates if c in df.columns), None)
        value_col = next((c for c in value_candidates if c in df.columns), None)
        
        if not customer_col:
            logger.warning("[TRIGGER RFM] CustomerID column missing - cannot generate RFM")
            return False
            
        if not date_col or not value_col:
            logger.warning(f"[TRIGGER RFM] Missing required columns: date={date_col}, value={value_col}")
            return False
        
        # Check we have unique customers
        unique_customers = df[customer_col].nunique()
        if unique_customers < 2:
            logger.warning(f"[TRIGGER RFM] Only {unique_customers} unique customers - insufficient for RFM")
            return False
        
        logger.info(f"[TRIGGER RFM] Found {unique_customers} unique customers - proceeding with RFM")
        
        # Copy sales file to canonical location (data/sales.csv) for the pipeline
        canonical_sales = tenant_file_path(company_id, "sales.csv", branch_id=branch_id)
        shutil.copy2(sales_file_path, canonical_sales)
        logger.info(f"[TRIGGER RFM] Copied to canonical location: {canonical_sales}")
        
        # Run RFM pipeline
        result = subprocess.run(
            [sys.executable, str(BASE_DIR / "src" / "04_rfm.py")],
            cwd=str(BASE_DIR),
            env=build_tenant_ml_env(company_id, branch_id, dataset_type="sales"),
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode == 0:
            logger.info("[TRIGGER RFM] RFM pipeline completed successfully")
            # Reload global rfm_df
            rfm_path = tenant_file_path(company_id, "rfm_table.csv", branch_id=branch_id)
            if rfm_path.exists():
                try:
                    rfm_df = pd.read_csv(rfm_path)
                    logger.info(f"[TRIGGER RFM] Loaded {len(rfm_df)} RFM records")
                    
                    # Sync to database for persistence
                    if ANALYTICS_PERSISTENCE_AVAILABLE:
                        try:
                            save_rfm_results(rfm_df, company_id, branch_id=branch_id)
                            logger.info("[TRIGGER RFM] Synced RFM results to database")
                        except Exception as e:
                            logger.warning(f"[TRIGGER RFM] Database sync failed: {e}")
                    return True
                except Exception as e:
                    logger.error(f"[TRIGGER RFM] Failed to reload RFM data: {e}")
                    return False
            else:
                logger.warning("[TRIGGER RFM] rfm_table.csv not created despite successful exit")
                return False
        else:
            logger.error(f"[TRIGGER RFM] RFM pipeline failed: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"[TRIGGER RFM] Error triggering RFM pipeline: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


# ============================================================================
# Dataset metadata helpers (multi-tenant)
# ============================================================================


def list_datasets(company_id: str, branch_id: Optional[str] = None) -> List[Dict[str, Any]]:
    branch_id = normalize_branch_id(branch_id)
    conn = get_db_connection()
    if branch_id:
        rows = conn.execute(
            """
            SELECT * FROM datasets
            WHERE company_id = ? AND branch_id = ? AND is_deleted = 0
            ORDER BY uploaded_at DESC
            """,
            (company_id, branch_id),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT * FROM datasets
            WHERE company_id = ? AND is_deleted = 0
            ORDER BY uploaded_at DESC
            """,
            (company_id,),
        ).fetchall()
    conn.close()
    return [row_to_dict(r) for r in rows]


def list_active_datasets(company_id: str, dataset_type: str) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    rows = conn.execute(
        """
        SELECT * FROM datasets
        WHERE company_id = ? AND dataset_type = ? AND is_deleted = 0 AND is_active = 1
        ORDER BY uploaded_at DESC
        """,
        (company_id, dataset_type),
    ).fetchall()
    conn.close()
    return [row_to_dict(r) for r in rows]


def get_branch_record(company_id: str, branch_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    row = conn.execute(
        """
        SELECT * FROM branches
        WHERE company_id = ? AND id = ? AND is_active = 1
        LIMIT 1
        """,
        (company_id, branch_id),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def company_has_any_dataset(company_id: str, branch_id: Optional[str] = None) -> bool:
    """Return True when this tenant has at least one uploaded dataset.

    We use this as the gate for all analytics endpoints so that a first-time
    tenant starts with an empty dashboard (204) until they upload data.
    """
    try:
        branch_id = normalize_branch_id(branch_id)
        conn = get_db_connection()
        if branch_id:
            row = conn.execute(
                """
                SELECT 1 FROM datasets
                WHERE company_id = ? AND branch_id = ? AND is_deleted = 0
                LIMIT 1
                """,
                (company_id, branch_id),
            ).fetchone()
        else:
            row = conn.execute(
                """
                SELECT 1 FROM datasets
                WHERE company_id = ? AND is_deleted = 0
                LIMIT 1
                """,
                (company_id,),
            ).fetchone()
        conn.close()
        return row is not None
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to check datasets for company %s: %s", company_id, exc)
        return False


def company_has_active_dataset(company_id: str, dataset_type: str, branch_id: Optional[str] = None) -> bool:
    """Return True when this tenant has an ACTIVE (current) dataset of a given type."""
    try:
        branch_id = normalize_branch_id(branch_id)
        conn = get_db_connection()
        if branch_id:
            row = conn.execute(
                """
                SELECT 1 FROM datasets
                WHERE company_id = ?
                  AND branch_id = ?
                  AND dataset_type = ?
                  AND is_deleted = 0
                  AND is_active = 1
                LIMIT 1
                """,
                (company_id, branch_id, dataset_type),
            ).fetchone()
            if row is None:
                row = conn.execute(
                    """
                    SELECT 1 FROM datasets
                    WHERE company_id = ?
                      AND dataset_type = ?
                      AND is_deleted = 0
                      AND is_active = 1
                                            AND (
                                                branch_id IS NULL
                                                OR TRIM(CAST(branch_id AS TEXT)) = ''
                                                OR UPPER(TRIM(CAST(branch_id AS TEXT))) = 'GLOBAL'
                                            )
                    LIMIT 1
                    """,
                    (company_id, dataset_type),
                ).fetchone()
        else:
            row = conn.execute(
                """
                SELECT 1 FROM datasets
                WHERE company_id = ?
                  AND dataset_type = ?
                  AND is_deleted = 0
                  AND is_active = 1
                LIMIT 1
                """,
                (company_id, dataset_type),
            ).fetchone()
        conn.close()
        return row is not None
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Failed to check active dataset for company %s type %s: %s",
            company_id,
            dataset_type,
            exc,
        )
        return False


def archive_existing(company_id: str, dataset_type: str, branch_id: Optional[str] = None) -> None:
    branch_id = normalize_branch_id(branch_id)
    conn = get_db_connection()
    if branch_id:
        conn.execute(
            """
            UPDATE datasets
            SET is_active = 0
            WHERE company_id = ? AND branch_id = ? AND dataset_type = ? AND is_deleted = 0
            """,
            (company_id, branch_id, dataset_type),
        )
    else:
        conn.execute(
            """
            UPDATE datasets
            SET is_active = 0
            WHERE company_id = ? AND dataset_type = ? AND is_deleted = 0
            """,
            (company_id, dataset_type),
        )
    conn.commit()
    conn.close()


def insert_dataset(
    company_id: str,
    dataset_type: str,
    file_name: str,
    file_path: Path,
    row_count: int,
    branch_id: Optional[str] = None,
) -> Dict[str, Any]:
    branch_id = normalize_branch_id(branch_id)
    conn = get_db_connection()
    uploaded_at = datetime.now(timezone.utc).isoformat()
    cur = conn.execute(
        """
        INSERT INTO datasets (company_id, branch_id, dataset_type, file_name, file_path, row_count, uploaded_at, is_active, is_deleted)
        VALUES (?, ?, ?, ?, ?, ?, ?, 1, 0)
        """,
        (company_id, branch_id, dataset_type, file_name, str(file_path), row_count, uploaded_at),
    )
    conn.commit()
    dataset_id = cur.lastrowid
    row = conn.execute("SELECT * FROM datasets WHERE id = ?", (dataset_id,)).fetchone()
    conn.close()
    return row_to_dict(row)


def get_dataset(dataset_id: int, company_id: str, branch_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    branch_id = normalize_branch_id(branch_id)
    conn = get_db_connection()
    if branch_id:
        row = conn.execute(
            "SELECT * FROM datasets WHERE id = ? AND company_id = ? AND branch_id = ? AND is_deleted = 0",
            (dataset_id, company_id, branch_id),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT * FROM datasets WHERE id = ? AND company_id = ? AND is_deleted = 0",
            (dataset_id, company_id),
        ).fetchone()
    conn.close()
    return row_to_dict(row) if row else None


def get_active_dataset(company_id: str, dataset_type: str, branch_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    branch_id = normalize_branch_id(branch_id)
    conn = get_db_connection()
    if branch_id:
        row = conn.execute(
            """
            SELECT * FROM datasets
            WHERE company_id = ? AND branch_id = ? AND dataset_type = ? AND is_deleted = 0 AND is_active = 1
            ORDER BY uploaded_at DESC
            LIMIT 1
            """,
            (company_id, branch_id, dataset_type),
        ).fetchone()
        if row is None:
            row = conn.execute(
                """
                SELECT * FROM datasets
                WHERE company_id = ? AND dataset_type = ? AND is_deleted = 0 AND is_active = 1
                                    AND (
                                        branch_id IS NULL
                                        OR TRIM(CAST(branch_id AS TEXT)) = ''
                                        OR UPPER(TRIM(CAST(branch_id AS TEXT))) = 'GLOBAL'
                                    )
                ORDER BY uploaded_at DESC
                LIMIT 1
                """,
                (company_id, dataset_type),
            ).fetchone()
    else:
        row = conn.execute(
            """
            SELECT * FROM datasets
            WHERE company_id = ? AND dataset_type = ? AND is_deleted = 0 AND is_active = 1
            ORDER BY uploaded_at DESC
            LIMIT 1
            """,
            (company_id, dataset_type),
        ).fetchone()
    conn.close()
    return row_to_dict(row) if row else None


def _filter_sales_df_for_branch_scope(df: pd.DataFrame, company_id: str, branch_id: Optional[str]) -> pd.DataFrame:
    if df is None or df.empty or not branch_id:
        return df

    branch_id_text = str(branch_id).strip()

    id_columns = ["branch_id", "BranchID", "branchId"]
    for column in id_columns:
        if column in df.columns:
            scoped = df[df[column].astype(str).str.strip() == branch_id_text].copy()
            return scoped

    return df


def get_latest_active_dataset(dataset_type: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    row = conn.execute(
        """
        SELECT * FROM datasets
        WHERE dataset_type = ? AND is_deleted = 0 AND is_active = 1
        ORDER BY uploaded_at DESC
        LIMIT 1
        """,
        (dataset_type,),
    ).fetchone()
    conn.close()
    return row_to_dict(row) if row else None


def delete_dataset(dataset_id: int, company_id: str, branch_id: Optional[str] = None) -> None:
    branch_id = normalize_branch_id(branch_id)
    conn = get_db_connection()
    if branch_id:
        conn.execute(
            """
            UPDATE datasets
            SET is_deleted = 1, is_active = 0
            WHERE id = ? AND company_id = ? AND branch_id = ?
            """,
            (dataset_id, company_id, branch_id),
        )
    else:
        conn.execute(
            """
            UPDATE datasets
            SET is_deleted = 1, is_active = 0
            WHERE id = ? AND company_id = ?
            """,
            (dataset_id, company_id),
        )
    conn.commit()
    conn.close()


# ============================================================================
# CASCADING DELETION - Delete all derived ML outputs
# ============================================================================

# List of all derived ML output files that must be deleted on cascade
DERIVED_ML_FILES = [
    "merged_data.csv",
    "cleaned_dataset.csv", 
    "rfm_table.csv",
    "product_recommendations.csv",
    "sentiment_results.csv",
    "sales_forecast.csv",
    "sales_forecast_future.csv",
    # Additional output files that may be generated
    "eda_report.json",
    "kpis.csv",
    "monthly_sales.csv",
    "sales_by_city.csv",
    "top_products.csv",
]

# Canonical input files that get copied from uploads
CANONICAL_INPUT_FILES = [
    "sales.csv",
    "customers.csv",
    "customer_reviews.csv",
]


def cascade_delete_derived_files(dataset_type: str, company_id: str = "Acme Corp", branch_id: Optional[str] = None) -> dict:
    """
    Delete derived ML output files for the affected tenant scope when a dataset is deleted.
    
    ENTERPRISE BEHAVIOR:
    - Deleting ANY dataset triggers full cascade deletion
    - No stale analytics should remain on disk OR in database
    - No stale data should remain in memory
    - APIs will return 204 until new data is uploaded and processed
    
    Args:
        dataset_type: Type of dataset being deleted (sales, customers, reviews)
        company_id: Company identifier for multi-tenant support
        branch_id: Optional branch scope for tenant isolation
        
    Returns:
        dict with deleted_files list and any errors
    """
    logger.info("=" * 60)
    logger.info(f"[CASCADE DELETE] TRIGGERED for dataset_type={dataset_type}, company={company_id}, branch={branch_id or 'GLOBAL'}")
    logger.info("=" * 60)
    
    # Delete from DATABASE FIRST (persistent storage)
    db_deleted = {}
    if ANALYTICS_PERSISTENCE_AVAILABLE:
        logger.info("[CASCADE DELETE] Step 0: Deleting analytics from DATABASE...")
        try:
            db_deleted = delete_all_analytics_for_tenant(company_id, branch_id=branch_id)
            logger.info(f"[CASCADE DELETE] Database records deleted: {db_deleted}")
        except Exception as e:
            logger.error(f"[CASCADE DELETE] Failed to delete from database: {e}")
    
    # Use Pipeline Controller if available (PREFERRED - Single Source of Truth)
    if PIPELINE_CONTROLLER_AVAILABLE:
        logger.info("[CASCADE DELETE] Using Pipeline Controller (SINGLE SOURCE OF TRUTH)")
        try:
            result = hard_reset_derived_outputs(company_id=company_id, branch_id=branch_id)
            clear_all_caches_and_reset(company_id, branch_id=branch_id)
            logger.info(f"[CASCADE DELETE] Pipeline Controller completed: {result}")
            return {
                "deleted_files": result.get("deleted_files", []),
                "errors": result.get("errors", []),
                "total_deleted": result.get("deleted_count", 0),
                "db_deleted": db_deleted,
                "memory_cleared": True,
            }
        except Exception as e:
            logger.error(f"[CASCADE DELETE] Pipeline Controller failed: {e}")
            logger.info("[CASCADE DELETE] Falling back to inline implementation")
    
    # FALLBACK: Inline implementation
    deleted_files = []
    errors = []
    
    # Step 1: Clear ALL in-memory caches FIRST
    logger.info("[CASCADE DELETE] Step 1: Clearing in-memory caches for tenant scope...")
    clear_all_caches_and_reset(company_id, branch_id=branch_id)
    
    # Step 2: Delete ALL derived ML outputs
    logger.info("[CASCADE DELETE] Step 2: Deleting derived ML output files...")
    for filename in DERIVED_ML_FILES:
        file_path = tenant_file_path(company_id, filename, branch_id=branch_id)
        try:
            if file_path.exists():
                file_path.unlink()
                deleted_files.append(str(file_path.relative_to(BASE_DIR)).replace("\\", "/"))
                logger.info(f"[CASCADE DELETE] ✓ Deleted: {filename}")
            else:
                logger.debug(f"[CASCADE DELETE] File not found (already clean): {filename}")
        except Exception as e:
            error_msg = f"Failed to delete {filename}: {str(e)}"
            errors.append(error_msg)
            logger.error(f"[CASCADE DELETE] ✗ {error_msg}")
    
    # Step 3: Also delete the canonical input file for this dataset type
    logger.info("[CASCADE DELETE] Step 3: Deleting canonical input file...")
    canonical_map = {
        "sales": "sales.csv",
        "customers": "customers.csv",
        "reviews": "customer_reviews.csv",
    }
    
    canonical_file = canonical_map.get(dataset_type)
    if canonical_file:
        file_path = tenant_file_path(company_id, canonical_file, branch_id=branch_id)
        try:
            if file_path.exists():
                file_path.unlink()
                deleted_files.append(str(file_path.relative_to(BASE_DIR)).replace("\\", "/"))
                logger.info(f"[CASCADE DELETE] ✓ Deleted canonical: {canonical_file}")
        except Exception as e:
            error_msg = f"Failed to delete canonical {canonical_file}: {str(e)}"
            errors.append(error_msg)
            logger.error(f"[CASCADE DELETE] ✗ {error_msg}")
    
    # Step 4: Clear output directory plots if they exist
    logger.info("[CASCADE DELETE] Step 4: Cleaning output directory...")
    output_dir = ensure_company_output_dir(company_id, branch_id)
    plots_dir = output_dir / "plots"
    forecasts_dir = output_dir / "forecasts"
    for output_file in ["eda_report.json", "kpis.csv", "monthly_sales.csv", "sales_by_city.csv", "top_products.csv"]:
        try:
            output_path = output_dir / output_file
            if output_path.exists():
                output_path.unlink()
                deleted_files.append(str(output_path.relative_to(BASE_DIR)).replace("\\", "/"))
                logger.info(f"[CASCADE DELETE] ✓ Deleted output: {output_file}")
        except Exception as e:
            logger.warning(f"[CASCADE DELETE] Could not delete {output_path}: {e}")

    if forecasts_dir.exists():
        try:
            for forecast_file in forecasts_dir.glob("*"):
                if forecast_file.is_file():
                    forecast_file.unlink()
                    deleted_files.append(str(forecast_file.relative_to(BASE_DIR)).replace("\\", "/"))
            logger.info("[CASCADE DELETE] ✓ Cleared scoped forecasts directory")
        except Exception as e:
            logger.warning(f"[CASCADE DELETE] Could not clear scoped forecasts: {e}")
    
    # Step 5: Clear plots directory
    logger.info("[CASCADE DELETE] Step 5: Cleaning plots directory...")
    if plots_dir.exists():
        try:
            for plot_file in plots_dir.glob("*.png"):
                plot_file.unlink()
                deleted_files.append(str(plot_file.relative_to(BASE_DIR)).replace("\\", "/"))
            logger.info("[CASCADE DELETE] ✓ Cleared plots directory")
        except Exception as e:
            logger.warning(f"[CASCADE DELETE] Could not clear plots: {e}")
    
    logger.info("[CASCADE DELETE] Step 6: Leaving shared model_registry untouched for tenant-scoped delete")
    
    logger.info("=" * 60)
    logger.info(f"[CASCADE DELETE] COMPLETED: {len(deleted_files)} files deleted, {len(errors)} errors")
    logger.info("[CASCADE DELETE] All in-memory state cleared")
    logger.info("[CASCADE DELETE] APIs will return 204 (No Content) until new data is uploaded")
    logger.info("=" * 60)
    
    return {
        "deleted_files": deleted_files,
        "errors": errors,
        "total_deleted": len(deleted_files),
        "db_deleted": db_deleted,
        "memory_cleared": True,
    }


def is_company_active(dataset_id: int, company_id: str, branch_id: Optional[str] = None) -> bool:
    branch_id = normalize_branch_id(branch_id)
    conn = get_db_connection()
    if branch_id:
        row = conn.execute(
            "SELECT is_active FROM datasets WHERE id = ? AND company_id = ? AND branch_id = ? AND is_deleted = 0",
            (dataset_id, company_id, branch_id),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT is_active FROM datasets WHERE id = ? AND company_id = ? AND is_deleted = 0",
            (dataset_id, company_id),
        ).fetchone()
    conn.close()
    return bool(row[0]) if row else False


def run_full_sales_pipeline(uploaded_file: Path, company_id: str = "Acme Corp", branch_id: Optional[str] = None) -> bool:
    """
    Run the COMPLETE ML pipeline for sales data:
    1. Clear all caches first (no stale data)
    2. Copy uploaded file to canonical location (data/sales.csv)
    3. Run 01_eda.py (creates merged_data.csv AND cleaned_dataset.csv)
    4. Run 04_rfm.py (creates rfm_table.csv) - conditional on CustomerID
    5. Run 05_recommendation.py (creates product_recommendations.csv)
    6. Reload all data into memory
    
    Returns:
        True if pipeline completed successfully, False otherwise
    """
    
    try:
        logger.info("=" * 60)
        logger.info("[PIPELINE] FULL SALES PIPELINE STARTED")
        logger.info(f"[PIPELINE] Input file: {uploaded_file}")
        logger.info("=" * 60)
        
        # Step 0: Clear all caches FIRST to ensure no stale data
        logger.info("[PIPELINE] Step 0: Clearing all caches before pipeline...")
        clear_all_caches_and_reset(company_id, branch_id=branch_id)
        
        # Step 1: Copy uploaded file to canonical location for ML scripts
        canonical_sales = tenant_file_path(company_id, "sales.csv", branch_id=branch_id)
        logger.info(f"[PIPELINE] Step 1: Copying {uploaded_file.name} -> {canonical_sales}")
        shutil.copy2(uploaded_file, canonical_sales)
        logger.info("[PIPELINE] ✓ Sales file copied to canonical location")
        
        # Step 2: Run EDA (Phase 1) - creates merged_data.csv
        logger.info("[PIPELINE] Step 2: Running Phase 1 - EDA...")
        result = subprocess.run(
            [sys.executable, str(BASE_DIR / "src" / "01_eda.py")],
            cwd=str(BASE_DIR),
            env=build_tenant_ml_env(company_id, branch_id, dataset_type="sales"),
            capture_output=True,
            text=True,
            timeout=120
        )
        if result.returncode != 0:
            logger.error(f"[PIPELINE] ✗ Phase 1 EDA failed: {result.stderr}")
            return False
        logger.info("[PIPELINE] ✓ Phase 1 EDA completed")
        
        # Step 3: Skip Phase 2 - 01_eda.py now creates cleaned_dataset.csv directly
        # Verify cleaned_dataset.csv was created
        cleaned_path = tenant_file_path(company_id, "cleaned_dataset.csv", branch_id=branch_id)
        if not cleaned_path.exists():
            logger.error("[PIPELINE] ✗ cleaned_dataset.csv was not created by Phase 1")
            return False
        logger.info("[PIPELINE] ✓ cleaned_dataset.csv verified (created by Phase 1)")
        
        # Step 4: Run RFM Segmentation (Phase 4) - creates rfm_table.csv
        logger.info("[PIPELINE] Step 4: Running Phase 4 - RFM Segmentation...")
        result = subprocess.run(
            [sys.executable, str(BASE_DIR / "src" / "04_rfm.py")],
            cwd=str(BASE_DIR),
            env=build_tenant_ml_env(company_id, branch_id, dataset_type="sales"),
            capture_output=True,
            text=True,
            timeout=120
        )
        # RFM may exit 0 with warning if CustomerID missing - that's OK
        if result.returncode != 0:
            logger.warning(f"[PIPELINE] ⚠ Phase 4 RFM exited with code {result.returncode}")
            if result.stderr:
                logger.warning(f"[PIPELINE] RFM stderr: {result.stderr[:500]}")
        else:
            logger.info("[PIPELINE] ✓ Phase 4 RFM completed")
        
        # Step 5: Run Recommendations (Phase 5) - creates product_recommendations.csv
        logger.info("[PIPELINE] Step 5: Running Phase 5 - Market Basket Analysis...")
        result = subprocess.run(
            [sys.executable, str(BASE_DIR / "src" / "05_recommendation.py")],
            cwd=str(BASE_DIR),
            env=build_tenant_ml_env(company_id, branch_id, dataset_type="sales"),
            capture_output=True,
            text=True,
            timeout=180
        )
        if result.returncode != 0:
            logger.warning(f"[PIPELINE] ⚠ Phase 5 Recommendations exited with code {result.returncode}")
            if result.stderr:
                logger.warning(f"[PIPELINE] Recommendations stderr: {result.stderr[:500]}")
        else:
            logger.info("[PIPELINE] ✓ Phase 5 Recommendations completed")
        
        # Step 6: Reload ALL data from disk into memory
        logger.info("[PIPELINE] Step 6: Reloading all data from disk...")
        reload_status = reload_all_data_from_disk(company_id=company_id, branch_id=branch_id)
        
        # Step 7: Sync CSV results to DATABASE for persistence
        if ANALYTICS_PERSISTENCE_AVAILABLE:
            logger.info("[PIPELINE] Step 7: Syncing analytics results to DATABASE...")
            try:
                sync_status = sync_csv_to_database(company_id, ensure_company_dir(company_id, "sales", branch_id=branch_id))
                logger.info(f"[PIPELINE] Database sync complete: {sync_status}")
            except Exception as e:
                logger.warning(f"[PIPELINE] Database sync failed: {e}")
        
        logger.info("=" * 60)
        logger.info("[PIPELINE] FULL SALES PIPELINE COMPLETED SUCCESSFULLY")
        logger.info(f"[PIPELINE] Reload status: {reload_status}")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"[PIPELINE] ✗ Full sales pipeline failed with exception: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def run_sentiment_pipeline(uploaded_file: Path, company_id: str = "Acme Corp", branch_id: Optional[str] = None) -> bool:
    """
    Run Customer Feedback pipeline for reviews data:
    1. Clear sentiment cache first (no stale data)
    2. Copy uploaded file to canonical location (data/customer_reviews.csv)
    3. Run 06_sentiment.py (creates sentiment_results.csv)
    4. Reload sentiment data into memory
    
    Returns:
        True if pipeline completed successfully, False otherwise
    """
    global sentiment_df
    
    try:
        logger.info("=" * 60)
        logger.info("[SENTIMENT PIPELINE] STARTED")
        logger.info(f"[SENTIMENT PIPELINE] Input file: {uploaded_file}")
        logger.info("=" * 60)
        
        # Step 0: Clear sentiment data first
        logger.info("[SENTIMENT PIPELINE] Step 0: Clearing old sentiment data...")
        sentiment_df = None
        sentiment_path = tenant_file_path(company_id, "sentiment_results.csv", branch_id=branch_id)
        if sentiment_path.exists():
            sentiment_path.unlink()
            logger.info("[SENTIMENT PIPELINE] ✓ Old sentiment_results.csv deleted")
        
        # Step 1: Copy uploaded file to canonical location for ML scripts
        canonical_reviews = tenant_file_path(company_id, "customer_reviews.csv", branch_id=branch_id)
        logger.info(f"[SENTIMENT PIPELINE] Step 1: Copying {uploaded_file.name} -> {canonical_reviews}")
        shutil.copy2(uploaded_file, canonical_reviews)
        logger.info("[SENTIMENT PIPELINE] ✓ Reviews file copied to canonical location")
        
        # Step 2: Run Customer Feedback (Phase 6)
        logger.info("[SENTIMENT PIPELINE] Step 2: Running Phase 6 - Customer Feedback...")
        result = subprocess.run(
            [sys.executable, str(BASE_DIR / "src" / "06_sentiment.py")],
            cwd=str(BASE_DIR),
            env=build_tenant_ml_env(company_id, branch_id, dataset_type="reviews"),
            capture_output=True,
            text=True,
            timeout=300  # NLP can take longer
        )
        if result.returncode != 0:
            logger.error(f"[SENTIMENT PIPELINE] ✗ Customer Feedback failed: {result.stderr}")
            return False
        logger.info("[SENTIMENT PIPELINE] ✓ Customer Feedback completed")
        
        # Step 3: Reload sentiment data from disk
        logger.info("[SENTIMENT PIPELINE] Step 3: Reloading sentiment data from disk...")
        if sentiment_path.exists():
            try:
                sentiment_df = pd.read_csv(sentiment_path)
                logger.info(f"[SENTIMENT PIPELINE] ✓ Loaded sentiment_results.csv: {len(sentiment_df)} rows")
                
                # Step 4: Sync to DATABASE for persistence
                if ANALYTICS_PERSISTENCE_AVAILABLE:
                    logger.info("[SENTIMENT PIPELINE] Step 4: Syncing to DATABASE...")
                    try:
                        save_sentiment_results(sentiment_df, company_id, branch_id=branch_id)
                        logger.info("[SENTIMENT PIPELINE] ✓ Synced sentiment to database")
                    except Exception as e:
                        logger.warning(f"[SENTIMENT PIPELINE] Database sync failed: {e}")
            except Exception as e:
                logger.warning(f"[SENTIMENT PIPELINE] ⚠ Could not reload sentiment results: {e}")
                sentiment_df = None
        else:
            logger.warning("[SENTIMENT PIPELINE] ⚠ sentiment_results.csv not created by pipeline")
            sentiment_df = None
        
        logger.info("=" * 60)
        logger.info("[SENTIMENT PIPELINE] COMPLETED SUCCESSFULLY")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"[SENTIMENT PIPELINE] ✗ Failed with exception: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def trigger_pipeline(company_id: str, dataset_type: str, action: str, file_path: Optional[Path] = None, branch_id: Optional[str] = None) -> None:
    """
    Hook for automation workflows - triggers COMPLETE ML pipelines when data is uploaded.
    
    SINGLE SOURCE OF TRUTH: Uses pipeline_controller.orchestrate_pipeline() for all execution.
    
    Pipeline Flow:
    - Sales data upload → EDA → Cleaning → RFM → Recommendations
    - Reviews data upload → Customer Feedback
    - Customers data upload → Copy + Re-run full pipeline if sales exists
    
    CRITICAL: Each upload clears previous results first to ensure no stale data.
    """
    logger.info("=" * 60)
    logger.info(f"[TRIGGER] Pipeline trigger received")
    logger.info(f"[TRIGGER] Company: {company_id}")
    logger.info(f"[TRIGGER] Dataset: {dataset_type}")
    logger.info(f"[TRIGGER] Action: {action}")
    logger.info(f"[TRIGGER] File: {file_path}")
    logger.info("=" * 60)
    
    # Use Pipeline Controller if available (PREFERRED - Single Source of Truth)
    if PIPELINE_CONTROLLER_AVAILABLE:
        logger.info("[TRIGGER] Using Pipeline Controller (SINGLE SOURCE OF TRUTH)")
        try:
            result = orchestrate_pipeline(dataset_type, action, file_path, company_id=company_id, branch_id=branch_id)
            success = bool(result.get("execution", {}).get("success", False))
            if success:
                logger.info(f"[TRIGGER] ✓ Pipeline Controller completed successfully")
            else:
                logger.warning(f"[TRIGGER] ⚠ Pipeline Controller had issues: {result}")

            # Clear cached "intelligence" outputs so dashboard stops showing stale insights
            try:
                for cached_name in [
                    f"{company_id}_clv_insights.json",
                ]:
                    cached_path = OUTPUT_DIR / cached_name
                    if cached_path.exists():
                        cached_path.unlink()
                        logger.info("[TRIGGER] ✓ Deleted cached output: %s", cached_name)
            except Exception as exc:  # noqa: BLE001
                logger.warning("[TRIGGER] Failed clearing cached intelligence outputs: %s", exc)
            
            # Reload data after pipeline completion
            reload_all_data_from_disk(company_id=company_id, branch_id=branch_id)

            # CRITICAL: Sync freshly generated CSV outputs to DB so DB-first endpoints don't return stale data
            if ANALYTICS_PERSISTENCE_AVAILABLE:
                try:
                    # Ensure DB reflects the latest pipeline outputs for this tenant
                    delete_all_analytics_for_tenant(company_id, branch_id=branch_id)
                    sync_status = sync_csv_to_database(
                        company_id,
                        ensure_company_dir(company_id, "sales", branch_id=branch_id),
                    )
                    logger.info("[TRIGGER] Database sync complete for %s/%s: %s", company_id, branch_id or "GLOBAL", sync_status)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("[TRIGGER] Database sync failed for %s/%s: %s", company_id, branch_id or "GLOBAL", exc)
            return
            
        except Exception as e:
            logger.error(f"[TRIGGER] ✗ Pipeline Controller failed: {e}")
            logger.info("[TRIGGER] Falling back to inline implementation")
    
    # FALLBACK: Inline implementation (only if Pipeline Controller unavailable)
    logger.warning("[TRIGGER] Using FALLBACK inline implementation")
    
    # Trigger FULL sales pipeline (EDA → Cleaning → RFM → Recommendations)
    if dataset_type == "sales" and file_path and action in ["upload", "replace"]:
        logger.info(f"[TRIGGER] Triggering FULL Sales Pipeline for {file_path}")
        try:
            success = run_full_sales_pipeline(file_path, company_id=company_id, branch_id=branch_id)
            if success:
                logger.info("[TRIGGER] ✓ Full Sales Pipeline completed - all ML outputs regenerated")
            else:
                logger.warning("[TRIGGER] ⚠ Full Sales Pipeline had issues - check logs for details")
        except Exception as e:
            logger.error(f"[TRIGGER] ✗ Error running full sales pipeline: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    # Trigger sentiment pipeline for reviews data
    if dataset_type == "reviews" and file_path and action in ["upload", "replace"]:
        logger.info(f"[TRIGGER] Triggering Customer Feedback Pipeline for {file_path}")
        try:
            success = run_sentiment_pipeline(file_path, company_id=company_id, branch_id=branch_id)
            if success:
                logger.info("[TRIGGER] ✓ Customer Feedback Pipeline completed - sentiment results regenerated")
            else:
                logger.warning("[TRIGGER] ⚠ Customer Feedback Pipeline failed - check logs for details")
        except Exception as e:
            logger.error(f"[TRIGGER] ✗ Error running sentiment pipeline: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    # Handle customers upload - copy to canonical location and re-run pipeline if sales exists
    if dataset_type == "customers" and file_path and action in ["upload", "replace"]:
        canonical_customers = tenant_file_path(company_id, "customers.csv", branch_id=branch_id)
        logger.info(f"[TRIGGER] Handling customers upload -> {canonical_customers}")
        try:
            shutil.copy2(file_path, canonical_customers)
            logger.info("[TRIGGER] ✓ Customers file copied to canonical location")
            
            # If sales.csv exists, re-run the pipeline to merge with new customers
            canonical_sales = tenant_file_path(company_id, "sales.csv", branch_id=branch_id)
            if canonical_sales.exists():
                logger.info("[TRIGGER] Sales data exists - re-running full pipeline to merge with customers")
                success = run_full_sales_pipeline(canonical_sales, company_id=company_id, branch_id=branch_id)
                if success:
                    logger.info("[TRIGGER] ✓ Pipeline re-run completed with new customer data")
                else:
                    logger.warning("[TRIGGER] ⚠ Pipeline re-run had issues - check logs")
            else:
                logger.info("[TRIGGER] No sales data yet - customers stored, waiting for sales upload")
        except Exception as e:
            logger.error(f"[TRIGGER] ✗ Error handling customers upload: {e}")
            import traceback
            logger.error(traceback.format_exc())


def load_active_sales_df(company_id: Optional[str] = None, branch_id: Optional[str] = None) -> pd.DataFrame:
    """Load the active sales dataset for a company; fallback to global df or direct files."""
    active: Optional[Dict[str, Any]] = None
    cached_df = _get_runtime_cache_entry(company_id, branch_id).get("df")

    if cached_df is not None and not cached_df.empty:
        return cached_df

    if company_id and not branch_id:
        # Admin "All Branches": aggregate all active branch datasets for this company.
        active_datasets = list_active_datasets(company_id, "sales")
        if active_datasets:
            frames: List[pd.DataFrame] = []
            for item in active_datasets:
                file_path = Path(str(item.get("file_path") or ""))
                if not file_path.exists():
                    continue
                try:
                    temp_df = pd.read_csv(file_path)
                    if temp_df is None or temp_df.empty:
                        continue
                    if "branch_id" not in temp_df.columns:
                        temp_df["branch_id"] = item.get("branch_id")
                    frames.append(temp_df)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Failed to load active branch dataset %s: %s", file_path, exc)
            if frames:
                return pd.concat(frames, ignore_index=True)

    if company_id:
        active = get_active_dataset(company_id, "sales", branch_id=branch_id)
    else:
        active = get_latest_active_dataset("sales")

    if active and Path(active["file_path"]).exists():
        try:
            loaded_df = pd.read_csv(Path(active["file_path"]))
            if company_id and branch_id:
                return _filter_sales_df_for_branch_scope(loaded_df, company_id, branch_id)
            return loaded_df
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to load active dataset %s: %s", active["file_path"], exc)

    # Fallback (multi-tenant): if a company folder exists but DB isn't initialized,
    # load the newest CSV from data/<company>/sales/*.csv.
    if company_id:
        if branch_id:
            company_sales_dir = DATA_DIR / company_id / "branches" / str(branch_id) / "sales"
        else:
            company_sales_dir = DATA_DIR / company_id / "sales"
        try:
            if company_sales_dir.exists() and company_sales_dir.is_dir():
                csvs = [p for p in company_sales_dir.glob("*.csv") if p.is_file()]
                if csvs:
                    newest = max(csvs, key=lambda p: p.stat().st_mtime)
                    loaded_df = pd.read_csv(newest)
                    if loaded_df is not None and not loaded_df.empty:
                        logger.info("[FALLBACK] Loaded sales data from %s", newest)
                        if branch_id:
                            return _filter_sales_df_for_branch_scope(loaded_df, company_id, branch_id)
                        return loaded_df
        except Exception as exc:  # noqa: BLE001
            logger.warning("[FALLBACK] Failed to load company sales CSVs for %s: %s", company_id, exc)

    # Fallback to legacy global dataset mirror
    if df is not None and not df.empty:
        return df

    raise HTTPException(status_code=503, detail="No sales data available")


def normalize_sales_dataframe(source_df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with resilient revenue/date/product/city columns."""
    if source_df is None or source_df.empty:
        raise HTTPException(status_code=404, detail="No sales data available")

    working = source_df.copy()

    date_col = next((c for c in DATE_CANDIDATES if c in working.columns), None)
    if not date_col:
        raise HTTPException(status_code=400, detail="Missing date column. Expected one of: OrderDate, Sale_Date, Order_Date, Date")
    working["__order_date"] = pd.to_datetime(working[date_col], errors="coerce")

    revenue_col = next((c for c in REVENUE_CANDIDATES if c in working.columns), None)
    if revenue_col:
        revenue_series = pd.to_numeric(working[revenue_col], errors="coerce")
    elif {"Unit_Price", "Quantity_Sold"}.issubset(set(working.columns)):
        revenue_series = pd.to_numeric(working["Unit_Price"], errors="coerce") * pd.to_numeric(working["Quantity_Sold"], errors="coerce")
        if "Discount" in working.columns:
            revenue_series *= (1 - pd.to_numeric(working["Discount"], errors="coerce").fillna(0))
    else:
        revenue_series = pd.Series(0.0, index=working.index)
    working["__total_price"] = pd.to_numeric(revenue_series, errors="coerce").fillna(0)

    product_col = _resolve_display_product_column(working)
    working["__product"] = working[product_col].astype(str) if product_col else None

    city_col = next((c for c in CITY_CANDIDATES if c in working.columns), None)
    working["__city"] = working[city_col].astype(str) if city_col else None

    working = working[working["__order_date"].notna()].copy()
    return working


def sanitize_uploaded_filename(filename: Optional[str], fallback: str = "upload.csv") -> str:
    raw_name = PurePath(str(filename or "")).name.replace("\x00", "").strip()
    safe_name = "".join(ch if ch.isalnum() or ch in {".", "-", "_"} else "_" for ch in raw_name)
    safe_name = safe_name.strip("._") or fallback
    suffix = PurePath(safe_name).suffix.lower()
    if not suffix:
        safe_name = f"{safe_name}.csv"
    return safe_name


def build_upload_storage_names(filename: Optional[str]) -> tuple[str, str]:
    original_name = sanitize_uploaded_filename(filename)
    suffix = PurePath(original_name).suffix.lower() or ".csv"
    return original_name, f"{uuid4().hex}{suffix}"


def _resolve_first_existing_column(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    return next((column for column in candidates if column in df.columns), None)


def _resolve_display_product_column(df: pd.DataFrame) -> Optional[str]:
    preferred_candidates = ["Product", "product", "ProductName", "product_name", "Description", "description", "Item", "item"]
    return _resolve_first_existing_column(df, preferred_candidates) or _resolve_first_existing_column(df, PRODUCT_CANDIDATES)


def build_canonical_sales_dataframe(raw_df: pd.DataFrame) -> pd.DataFrame:
    normalized = normalize_sales_dataframe(raw_df)
    if normalized.empty:
        raise HTTPException(status_code=400, detail="Sales CSV must contain at least one row with a valid order date")

    order_id_col = _resolve_first_existing_column(raw_df, ORDER_ID_CANDIDATES)
    if order_id_col:
        order_values = raw_df.loc[normalized.index, order_id_col].reset_index(drop=True)
    else:
        order_values = pd.Series(range(1, len(normalized) + 1), dtype="int64")

    product_id_col = _resolve_first_existing_column(raw_df, PRODUCT_CANDIDATES)
    if product_id_col is None:
        raise HTTPException(
            status_code=400,
            detail=f"Missing product column. Expected one of: {', '.join(PRODUCT_CANDIDATES)}",
        )
    product_display_col = _resolve_display_product_column(raw_df) or product_id_col

    city_col = _resolve_first_existing_column(raw_df, CITY_CANDIDATES)
    city_values = (
        raw_df.loc[normalized.index, city_col].reset_index(drop=True)
        if city_col is not None
        else pd.Series(["Unknown"] * len(normalized), dtype="object")
    )
    customer_id_col = _resolve_first_existing_column(raw_df, CUSTOMER_ID_CANDIDATES)
    customer_values = (
        raw_df.loc[normalized.index, customer_id_col].reset_index(drop=True)
        if customer_id_col is not None
        else None
    )

    canonical = pd.DataFrame(
        {
            "OrderID": order_values,
            "OrderDate": normalized["__order_date"].reset_index(drop=True),
            "TotalPrice": normalized["__total_price"].reset_index(drop=True),
            "ProductID": raw_df.loc[normalized.index, product_id_col].reset_index(drop=True),
            "Product": raw_df.loc[normalized.index, product_display_col].reset_index(drop=True),
            "City": city_values,
        }
    )

    if customer_values is not None:
        canonical["CustomerID"] = customer_values

    product_series = canonical["ProductID"].astype(str).str.strip()
    if product_series.eq("").all() or product_series.eq("None").all() or product_series.eq("nan").all():
        raise HTTPException(status_code=400, detail="Sales CSV product values are empty")

    canonical["ProductID"] = product_series.replace({"": "Unknown", "None": "Unknown", "nan": "Unknown"})
    display_product_series = canonical["Product"].astype(str).str.strip().replace({"": pd.NA, "None": pd.NA, "nan": pd.NA})
    canonical["Product"] = display_product_series.fillna(canonical["ProductID"])
    canonical["City"] = canonical["City"].astype(str).str.strip().replace({"": "Unknown", "None": "Unknown", "nan": "Unknown"})
    if "CustomerID" in canonical.columns:
        canonical["CustomerID"] = canonical["CustomerID"].astype(str).str.strip().replace({"": pd.NA, "None": pd.NA, "nan": pd.NA})
    return canonical


def build_canonical_customers_dataframe(raw_df: pd.DataFrame) -> pd.DataFrame:
    customer_col = _resolve_first_existing_column(raw_df, CUSTOMER_ID_CANDIDATES)
    if customer_col is None:
        raise HTTPException(status_code=400, detail="Customers CSV requires a Customer ID column")

    canonical = pd.DataFrame({"CustomerID": raw_df[customer_col].astype(str).str.strip()})
    canonical["CustomerID"] = canonical["CustomerID"].replace({"": pd.NA, "None": pd.NA, "nan": pd.NA})
    if canonical["CustomerID"].isna().all():
        raise HTTPException(status_code=400, detail="Customers CSV customer identifiers are empty")

    if "CustomerName" in raw_df.columns:
        canonical["CustomerName"] = raw_df["CustomerName"].astype(str).str.strip().replace({"": pd.NA, "None": pd.NA, "nan": pd.NA})
    if "City" in raw_df.columns:
        canonical["City"] = raw_df["City"].astype(str).str.strip().replace({"": "Unknown", "None": "Unknown", "nan": "Unknown"})

    canonical = canonical[canonical["CustomerID"].notna()].copy()
    if canonical.empty:
        raise HTTPException(status_code=400, detail="Customers CSV customer identifiers are empty")
    return canonical


def build_canonical_reviews_dataframe(raw_df: pd.DataFrame) -> pd.DataFrame:
    text_col = _resolve_first_existing_column(raw_df, ["ReviewText", "review_text", "Review", "comment", "Comment", "text", "Text", "feedback", "Feedback"])
    if text_col is None:
        raise HTTPException(status_code=400, detail="Reviews CSV requires a review text column")

    canonical = pd.DataFrame({"ReviewText": raw_df[text_col].astype(str).str.strip()})
    canonical["ReviewText"] = canonical["ReviewText"].replace({"": pd.NA, "None": pd.NA, "nan": pd.NA})
    if canonical["ReviewText"].isna().all():
        raise HTTPException(status_code=400, detail="Reviews CSV review text values are empty")

    if "Rating" in raw_df.columns:
        canonical["Rating"] = pd.to_numeric(raw_df["Rating"], errors="coerce")
    if "ReviewDate" in raw_df.columns:
        review_dates = pd.to_datetime(raw_df["ReviewDate"], errors="coerce")
        canonical["ReviewDate"] = review_dates.dt.strftime("%Y-%m-%d")
    if "CustomerID" in raw_df.columns:
        canonical["CustomerID"] = raw_df["CustomerID"].astype(str).str.strip().replace({"": pd.NA, "None": pd.NA, "nan": pd.NA})
    if "CustomerName" in raw_df.columns:
        canonical["CustomerName"] = raw_df["CustomerName"].astype(str).str.strip().replace({"": pd.NA, "None": pd.NA, "nan": pd.NA})
    if "ProductID" in raw_df.columns:
        canonical["ProductID"] = raw_df["ProductID"].astype(str).str.strip().replace({"": pd.NA, "None": pd.NA, "nan": pd.NA})

    canonical = canonical[canonical["ReviewText"].notna()].copy()
    if canonical.empty:
        raise HTTPException(status_code=400, detail="Reviews CSV review text values are empty")
    return canonical


def _apply_sales_filters(
    normalized_df: pd.DataFrame,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    city: Optional[str] = None,
    product: Optional[str] = None,
) -> pd.DataFrame:
    """Apply optional date/city/product filters to a normalized sales dataframe."""
    if normalized_df is None or normalized_df.empty:
        return normalized_df

    filtered = normalized_df

    if city:
        if filtered.get("__city") is None:
            return filtered.iloc[0:0]
        city_norm = city.strip().lower()
        filtered = filtered[filtered["__city"].astype(str).str.strip().str.lower() == city_norm]

    if product:
        if filtered.get("__product") is None:
            return filtered.iloc[0:0]
        product_norm = product.strip().lower()
        filtered = filtered[filtered["__product"].astype(str).str.strip().str.lower() == product_norm]

    if start_date:
        start_dt = pd.to_datetime(start_date, errors="coerce")
        if pd.notna(start_dt):
            filtered = filtered[filtered["__order_date"] >= start_dt]

    if end_date:
        end_dt = pd.to_datetime(end_date, errors="coerce")
        if pd.notna(end_dt):
            filtered = filtered[filtered["__order_date"] <= end_dt]

    return filtered


def _filter_raw_sales_df(
    raw_df: pd.DataFrame,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    city: Optional[str] = None,
    product: Optional[str] = None,
) -> pd.DataFrame:
    """Filter raw sales df using normalized columns, returning original columns/rows."""
    if raw_df is None or raw_df.empty:
        return raw_df

    normalized = normalize_sales_dataframe(raw_df)
    filtered_norm = _apply_sales_filters(
        normalized,
        start_date=start_date,
        end_date=end_date,
        city=city,
        product=product,
    )
    if filtered_norm is None or filtered_norm.empty:
        return raw_df.iloc[0:0]
    return raw_df.loc[filtered_norm.index]


# ============================================================================
# API Endpoints
# ============================================================================


@app.get("/", tags=["Root"])
def root():
    """Root endpoint - redirects to API documentation."""
    return {
        "message": "Sales Overview API is running",
        "version": "1.0.0",
        "status": "operational",
        "data_loaded": df is not None,
        "last_updated": data_last_modified.isoformat() if data_last_modified else None,
        "docs": "/docs",
        "health": "/api/health",
        "endpoints": [
            "/api/kpis",
            "/api/monthly-sales",
            "/api/top-products",
            "/api/top-cities",
            "/api/sentiment",
            "/api/recommendations",
            "/api/raw-data",
            "/api/summary",
        ],
    }


# ============================================================================
# Dataset Management (multi-tenant, production-grade)
# ============================================================================


@app.get("/api/datasets", response_model=List[DatasetMeta], tags=["Datasets"])
def list_company_datasets(request: Request):
    company_id = require_company_id(request)
    branch_id = resolve_branch_scope(request)
    return list_datasets(company_id, branch_id=branch_id)


def _resolve_upload_actor(request: Request) -> tuple[Dict[str, Any], str, str, Optional[str]]:
    current_user = require_tenant_manager_request(request)
    company_id = require_company_id(request)
    branch_id = normalize_branch_id(resolve_branch_scope(request))
    user_role = normalize_role_text((current_user or {}).get("role"))
    if user_role in {"super_admin", "company_admin"} and not branch_id:
        raise HTTPException(status_code=400, detail="Branch selection is required for admin uploads")
    user_key = str((current_user or {}).get("id") or (current_user or {}).get("email") or "").strip() or None
    return current_user, company_id, branch_id, user_key


@app.post("/api/datasets/upload", response_model=DatasetUploadPreparationResponse, tags=["Datasets"])
async def upload_dataset(
    request: Request,
    dataset_type: str = Form(...),
    file: UploadFile = File(...),
):
    try:
        init_db()
        _, company_id, branch_id, user_key = _resolve_upload_actor(request)
        dataset_type = dataset_type.lower()
        if dataset_type not in ALLOWED_DATASET_TYPES:
            raise HTTPException(status_code=400, detail="Unsupported dataset_type")
        return prepare_dataset_upload(
            company_id=company_id,
            branch_id=branch_id,
            user_id=user_key,
            dataset_type=dataset_type,
            original_filename=file.filename or "upload.csv",
            file_bytes=await file.read(),
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        import traceback
        logger.error("[UPLOAD] Unhandled error in /api/datasets/upload: %s", exc)
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": "Upload failed", "detail": str(exc)},
        )


@app.post("/api/datasets/{dataset_id}/replace", response_model=DatasetUploadPreparationResponse, tags=["Datasets"])
async def replace_dataset(
    dataset_id: int,
    request: Request,
    file: UploadFile = File(...),
):
    _, company_id, branch_id, user_key = _resolve_upload_actor(request)
    current = get_dataset(dataset_id, company_id, branch_id=branch_id)
    if not current:
        raise HTTPException(status_code=404, detail="Dataset not found")

    return prepare_dataset_upload(
        company_id=company_id,
        branch_id=branch_id,
        user_id=user_key,
        dataset_type=str(current["dataset_type"]).lower(),
        original_filename=file.filename or current.get("file_name") or "upload.csv",
        file_bytes=await file.read(),
        replace_dataset_id=dataset_id,
    )


@app.post("/api/datasets/upload/validate", response_model=DatasetMappingValidationResponse, tags=["Datasets"])
def validate_dataset_upload_mapping(request: Request, payload: DatasetMappingValidationRequest):
    _, company_id, branch_id, user_key = _resolve_upload_actor(request)
    pending_upload = get_pending_upload(payload.upload_id, company_id, branch_id, user_key)
    return validate_mapping_configuration(
        pending_upload["dataset_type"],
        pending_upload["columns"],
        payload.mapping,
    )


@app.get("/api/datasets/mappings/{dataset_type}", response_model=List[SavedMappingProfileResponse], tags=["Datasets"])
def get_saved_dataset_mappings(dataset_type: str, request: Request):
    _, company_id, branch_id, user_key = _resolve_upload_actor(request)
    dataset_type = dataset_type.lower()
    if dataset_type not in ALLOWED_DATASET_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported dataset_type")
    return list_mapping_profiles(company_id, branch_id, user_key, dataset_type)


@app.post("/api/datasets/upload/confirm", response_model=DatasetMappingConfirmResponse, tags=["Datasets"])
def confirm_dataset_upload(request: Request, payload: DatasetMappingConfirmRequest):
    try:
        init_db()
        _, company_id, branch_id, user_key = _resolve_upload_actor(request)
        pending_upload = get_pending_upload(payload.upload_id, company_id, branch_id, user_key)
        dataset_type = str(pending_upload["dataset_type"]).lower()
        validation = validate_mapping_configuration(dataset_type, pending_upload["columns"], payload.mapping)
        if not validation["valid"]:
            raise HTTPException(status_code=422, detail={"errors": validation["errors"], "warnings": validation["warnings"]})

        with pipeline_lock(f"confirm-{dataset_type}-{company_id}-{branch_id or 'all'}"):
            raw_df = read_pending_upload_dataframe(pending_upload)
            mapped_df = apply_column_mapping(raw_df, dataset_type, validation["mapping"])

            if dataset_type == "sales":
                canonical_df = build_canonical_sales_dataframe(mapped_df)
            elif dataset_type == "customers":
                canonical_df = build_canonical_customers_dataframe(mapped_df)
            elif dataset_type == "reviews":
                canonical_df = build_canonical_reviews_dataframe(mapped_df)
            else:
                raise HTTPException(status_code=400, detail="Unsupported dataset_type")

            target_dir = ensure_company_dir(company_id, dataset_type, branch_id=branch_id)
            original_name, stored_name = build_upload_storage_names(pending_upload.get("file_name"))
            target_path = target_dir / stored_name
            canonical_df.to_csv(target_path, index=False)

            replace_dataset_id = pending_upload.get("replace_dataset_id")
            if replace_dataset_id:
                existing = get_dataset(int(replace_dataset_id), company_id, branch_id=branch_id)
                if not existing:
                    target_path.unlink(missing_ok=True)
                    raise HTTPException(status_code=404, detail="Dataset to replace no longer exists")

            archive_existing(company_id, dataset_type, branch_id=branch_id)
            record = insert_dataset(
                company_id,
                dataset_type,
                original_name,
                target_path,
                int(len(canonical_df)),
                branch_id=branch_id,
            )
            trigger_action = "replace" if replace_dataset_id else "upload"
            trigger_pipeline(company_id, dataset_type, action=trigger_action, file_path=target_path, branch_id=branch_id)

            if payload.save_mapping:
                save_mapping_profile(
                    company_id=company_id,
                    branch_id=branch_id,
                    user_id=user_key,
                    dataset_type=dataset_type,
                    columns=pending_upload["columns"],
                    mapping=validation["mapping"],
                )

            delete_pending_upload(payload.upload_id)
            return {
                "dataset": record,
                "mapping_saved": bool(payload.save_mapping),
                "standardized_columns": [str(column) for column in canonical_df.columns],
            }
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        import traceback
        logger.error("[UPLOAD CONFIRM] Failed confirming mapped upload: %s", exc)
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": "Mapping confirmation failed", "detail": str(exc)},
        )


@app.post("/api/datasets/upload/cancel", tags=["Datasets"])
def cancel_dataset_upload(request: Request, payload: DatasetMappingCancelRequest):
    _, company_id, branch_id, user_key = _resolve_upload_actor(request)
    get_pending_upload(payload.upload_id, company_id, branch_id, user_key)
    delete_pending_upload(payload.upload_id)
    return {"ok": True}


@app.delete("/api/datasets/{dataset_id}", tags=["Datasets"])
def delete_dataset_endpoint(dataset_id: int, request: Request):
    """
    Delete a dataset with CASCADING deletion of all derived ML outputs.
    
    ENTERPRISE BEHAVIOR:
    - Deletes the raw dataset file
    - Deletes ALL derived ML outputs (RFM, recommendations, sentiment, etc.)
    - Resets in-memory DataFrames
    - APIs will return 204 until new data is uploaded
    """
    require_tenant_manager_request(request)
    company_id = require_company_id(request)
    branch_id = resolve_branch_scope(request)
    current = get_dataset(dataset_id, company_id, branch_id=branch_id)
    if not current:
        raise HTTPException(status_code=404, detail="Dataset not found")

    target_branch_id = str(current.get("branch_id") or "").strip() or None
    if target_branch_id and target_branch_id.upper() == "GLOBAL":
        target_branch_id = None

    dataset_type = current["dataset_type"]
    logger.info(f"DELETE request for dataset_id={dataset_id}, type={dataset_type}, company={company_id}")
    
    # Mark as deleted in database
    delete_dataset(dataset_id, company_id, branch_id=target_branch_id)

    # Delete the raw uploaded file
    try:
        Path(current["file_path"]).unlink(missing_ok=True)
        logger.info(f"Deleted raw file: {current['file_path']}")
    except Exception as exc:
        logger.warning("Could not delete raw file %s: %s", current["file_path"], exc)

    # CASCADING DELETION: Delete ALL derived ML outputs (from disk AND database)
    cascade_result = cascade_delete_derived_files(dataset_type, company_id, branch_id=target_branch_id)
    
    return {
        "status": "deleted",
        "id": dataset_id,
        "dataset_type": dataset_type,
        "cascade_deletion": cascade_result,
        "message": "Dataset and all derived analytics deleted. Re-upload data to regenerate analytics."
    }


@app.get("/api/datasets/{dataset_id}/preview", response_model=DatasetPreview, tags=["Datasets"])
def preview_dataset(dataset_id: int, request: Request):
    company_id = require_company_id(request)
    branch_id = resolve_branch_scope(request)
    current = get_dataset(dataset_id, company_id, branch_id=branch_id)
    if not current:
        raise HTTPException(status_code=404, detail="Dataset not found")

    try:
        preview_payload = load_preview(Path(current["file_path"]))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Dataset file missing")
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Preview failed: {exc}") from exc

    return DatasetPreview(
        id=current["id"],
        file_name=current["file_name"],
        dataset_type=current["dataset_type"],
        uploaded_at=current["uploaded_at"],
        row_count=preview_payload["row_count"],
        columns=preview_payload["columns"],
        rows=preview_payload["rows"],
    )


@app.get("/api/health", tags=["Health"])
def health_check():
    """Health check endpoint with component status."""
    return {
        "status": "healthy" if df is not None else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": {
            "sales_data": "available" if df is not None else "unavailable",
            "forecast_data": "available" if forecast_df is not None else "unavailable",
            "sentiment_data": "available" if sentiment_df is not None else "unavailable",
            "recommendation_data": "available" if recommendation_df is not None else "unavailable",
            "ml_model": "loaded" if model is not None else "not_loaded"
        },
        "version": "1.0.0"
    }


def _get_rfm_segmentation_data(request: Request):
    """
    Internal function to read RFM segmentation data from DATABASE first, then CSV fallback.
    
    PRIORITY ORDER:
    1. Database (SQLite) - persists across container restarts
    2. CSV file fallback - for backward compatibility
    3. AUTO-RUN: If both missing but sales data exists, run RFM pipeline automatically
    
    Returns:
        SegmentationMetadata if data exists, Response(204) if not
    """
    current_user = require_authenticated_request(request)
    company_id = require_company_id(request)
    branch_id = resolve_branch_scope(request)
    if not company_has_active_dataset(company_id, "sales", branch_id=branch_id):
        return Response(status_code=204)

    rfm_df = None
    rfm_candidates = analytics_result_candidates(company_id, "rfm_table.csv", branch_id=branch_id)
    rfm_path = rfm_candidates[0]
    result_path_used: Optional[Path] = None

    if ANALYTICS_PERSISTENCE_AVAILABLE:
        try:
            rfm_df = get_rfm_results(company_id, branch_id=branch_id)
            if rfm_df is not None and not rfm_df.empty:
                logger.info(f"[RFM API] Loaded {len(rfm_df)} records from DATABASE")
        except Exception as e:
            logger.warning(f"[RFM API] Database read failed: {e}, falling back to CSV")
            rfm_df = None

    if rfm_df is None or rfm_df.empty:
        read_error: Optional[Exception] = None
        for candidate in rfm_candidates:
            if not candidate.exists():
                continue
            try:
                rfm_df = pd.read_csv(candidate)
                result_path_used = candidate
                logger.info(f"[RFM API] Loaded {len(rfm_df)} records from CSV: {candidate}")
                break
            except Exception as exc:
                logger.warning(f"[RFM API] Failed to read fallback CSV {candidate}: {exc}")
                read_error = exc

        if (rfm_df is None or rfm_df.empty) and branch_id is None:
            aggregated_df, aggregated_ts = load_aggregated_branch_output(
                company_id,
                "rfm_table.csv",
                "sales",
            )
            if aggregated_df is not None and not aggregated_df.empty:
                rfm_df = aggregated_df
                if aggregated_ts:
                    result_path_used = Path("aggregated")
                logger.info(f"[RFM API] Loaded {len(rfm_df)} records from branch aggregation")

        if rfm_df is None or rfm_df.empty:
            sales_file = resolve_active_dataset_source_path(company_id, "sales", branch_id=branch_id)
            if sales_file is not None:
                if not can_manage_tenant_data(current_user.get("role")):
                    logger.info("[RFM API] Skipping auto-run for non-admin role=%s", current_user.get("role"))
                    return Response(status_code=204)
                logger.info(f"[RFM API] No cached result found - auto-running RFM pipeline from {sales_file}")
                if trigger_rfm_pipeline(sales_file, company_id=company_id, branch_id=branch_id):
                    for candidate in rfm_candidates:
                        if not candidate.exists():
                            continue
                        try:
                            rfm_df = pd.read_csv(candidate)
                            result_path_used = candidate
                            logger.info(f"[RFM API] Loaded {len(rfm_df)} records after auto-run from {candidate}")
                            break
                        except Exception as exc:
                            logger.warning(f"[RFM API] Failed to read auto-generated CSV {candidate}: {exc}")
                            read_error = exc

        if (rfm_df is None or rfm_df.empty) and read_error is not None:
            raise HTTPException(status_code=500, detail="Unable to read rfm_table.csv") from read_error

    if rfm_df is None or rfm_df.empty:
        return Response(status_code=204)

    segment_col = next((col for col in ["Segment", "segment", "RFM_Segment", "rfm_segment"] if col in rfm_df.columns), None)
    if segment_col is None:
        return Response(status_code=204)

    recency_col = next((col for col in ["Recency", "recency"] if col in rfm_df.columns), None)
    frequency_col = next((col for col in ["Frequency", "frequency"] if col in rfm_df.columns), None)
    monetary_col = next((col for col in ["Monetary", "monetary"] if col in rfm_df.columns), None)

    segment_colors = {
        "Champions": "#22C55E",
        "Loyal": "#2563EB",
        "Potential Loyalists": "#64748B",
        "At Risk": "#F59E0B",
        "Need Attention": "#F97316",
        "Hibernating": "#EF4444",
        "Lost": "#6B7280",
    }

    segment_stats: List[RFMSegmentResponse] = []
    for segment_name in rfm_df[segment_col].dropna().unique():
        segment_data = rfm_df[rfm_df[segment_col] == segment_name]
        avg_recency = float(segment_data[recency_col].mean()) if recency_col else None
        avg_frequency = float(segment_data[frequency_col].mean()) if frequency_col else None
        avg_monetary = float(segment_data[monetary_col].mean()) if monetary_col else None

        segment_stats.append(
            RFMSegmentResponse(
                segment=segment_name,
                customer_count=len(segment_data),
                color=segment_colors.get(segment_name, "#9CA3AF"),
                avg_recency=avg_recency,
                avg_frequency=avg_frequency,
                avg_monetary=avg_monetary,
            )
        )

    segment_stats.sort(key=lambda x: x.customer_count, reverse=True)
    last_calculated = datetime.fromtimestamp(result_path_used.stat().st_mtime).isoformat() if result_path_used and result_path_used.exists() else datetime.now().isoformat()

    return SegmentationMetadata(
        total_customers=len(rfm_df),
        segments=segment_stats,
        last_calculated=last_calculated,
        data_source=result_path_used.name if result_path_used else "database",
        model_version="RFM",
    )


@app.get("/api/segmentation", response_model=SegmentationMetadata, tags=["Analytics"])
def get_segmentation(request: Request):
    """Return RFM segment counts from rfm_table.csv. 204 when missing/empty."""
    return _get_rfm_segmentation_data(request)


@app.get("/api/rfm", response_model=SegmentationMetadata, tags=["Analytics"])
def get_rfm(request: Request):
    """Alias for /api/segmentation - Return RFM segment counts. 204 when missing/empty."""
    return _get_rfm_segmentation_data(request)


@app.get("/api/kpis", response_model=KPIResponse, tags=["Analytics"])
async def get_kpis(
    request: Request,
    start_date: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    end_date: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    city: Optional[str] = Query(None),
    product: Optional[str] = Query(None),
):
    """Get high-level KPIs (revenue, orders, AOV, top product, top city) with dynamic percentage changes."""
    company_id = require_company_id(request)
    branch_id = resolve_branch_scope(request)
    if not company_has_active_dataset(company_id, "sales", branch_id=branch_id):
        return Response(status_code=204)

    sales_df = normalize_sales_dataframe(load_active_sales_df(company_id, branch_id=branch_id))
    sales_df = _apply_sales_filters(sales_df, city=city, product=product)

    now = pd.Timestamp.now()
    if start_date and end_date:
        current_end = pd.to_datetime(end_date)
        current_start = pd.to_datetime(start_date)
    else:
        current_end = sales_df["__order_date"].max() if not sales_df.empty else now
        current_start = current_end - pd.Timedelta(days=30)

    period_length = (current_end - current_start).days
    previous_end = current_start - pd.Timedelta(days=1)
    previous_start = previous_end - pd.Timedelta(days=period_length)

    current_df = _apply_sales_filters(
        sales_df,
        start_date=current_start.strftime("%Y-%m-%d"),
        end_date=current_end.strftime("%Y-%m-%d"),
    ).copy()
    previous_df = _apply_sales_filters(
        sales_df,
        start_date=previous_start.strftime("%Y-%m-%d"),
        end_date=previous_end.strftime("%Y-%m-%d"),
    ).copy()

    if current_df.empty:
        return Response(status_code=204)

    total_revenue = float(current_df["__total_price"].sum())
    total_orders = len(current_df)
    aov = total_revenue / total_orders if total_orders > 0 else 0.0

    prev_revenue = float(previous_df["__total_price"].sum()) if not previous_df.empty else 0.0
    prev_orders = len(previous_df) if not previous_df.empty else 0
    prev_aov = prev_revenue / prev_orders if prev_orders > 0 else 0.0

    def calc_pct_change(current: float, previous: float) -> Optional[float]:
        if previous == 0 or previous_df.empty:
            return None
        return round(((current - previous) / previous) * 100, 2)

    revenue_change = calc_pct_change(total_revenue, prev_revenue)
    orders_change = calc_pct_change(float(total_orders), float(prev_orders)) if prev_orders > 0 else None
    aov_change = calc_pct_change(aov, prev_aov) if prev_aov > 0 else None

    top_product = "N/A"
    if current_df.get("__product") is not None and current_df["__product"].notna().any():
        top_product = str(current_df.groupby("__product")["__total_price"].sum().idxmax())

    top_city = "N/A"
    if current_df.get("__city") is not None and current_df["__city"].notna().any():
        top_city = str(current_df.groupby("__city")["__total_price"].sum().idxmax())

    return KPIResponse(
        total_revenue=total_revenue,
        total_orders=total_orders,
        average_order_value=aov,
        top_product=top_product,
        top_city=top_city,
        revenue_change=revenue_change,
        orders_change=orders_change,
        aov_change=aov_change,
    )


# =============================================================================
# NEW: Decision Insights (rule-based, deterministic)
# =============================================================================


@app.get("/api/insights", response_model=InsightsResponse, tags=["Intelligence"])
def get_decision_insights(
    request: Request,
    limit: int = Query(8, ge=1, le=20),
):
    """Return deterministic, rule-based decision insights based on current metrics and ML outputs.

    Notes:
    - This endpoint is intentionally non-ML (rule-based) and deterministic.
    - It reads existing outputs (forecast/RFM/sentiment/recommendations) when available.
    """
    if not INSIGHTS_AVAILABLE:
        # Keep backward compatibility if module missing
        company_id = require_company_id(request)
        return InsightsResponse(company_id=company_id, generated_at=datetime.now(timezone.utc).isoformat(), insights=[])

    company_id = require_company_id(request)
    branch_id = resolve_branch_scope(request)
    if not company_has_active_dataset(company_id, "sales", branch_id=branch_id):
        return Response(status_code=204)

    try:
        sales_df = normalize_sales_dataframe(load_active_sales_df(company_id, branch_id=branch_id))
    except Exception:
        # No data available -> 204 so UI can show empty state
        return Response(status_code=204)

    forecast_df = load_forecast_data(company_id, branch_id=branch_id)

    rfm_df = None
    rfm_path = tenant_file_path(company_id, "rfm_table.csv", branch_id=branch_id)
    if rfm_path.exists():
        try:
            rfm_df = pd.read_csv(rfm_path)
        except Exception:
            rfm_df = None

    sentiment_df_local = None
    if company_has_active_dataset(company_id, "reviews", branch_id=branch_id):
        sentiment_path = tenant_file_path(company_id, "sentiment_results.csv", branch_id=branch_id)
        if sentiment_path.exists():
            try:
                sentiment_df_local = pd.read_csv(sentiment_path)
            except Exception:
                sentiment_df_local = None

    recs_df = None
    recs_path = tenant_file_path(company_id, "product_recommendations.csv", branch_id=branch_id)
    if recs_path.exists():
        try:
            recs_df = pd.read_csv(recs_path)
        except Exception:
            recs_df = None

    return generate_insights(
        company_id=company_id,
        sales_df=sales_df,
        forecast_df=forecast_df,
        rfm_df=rfm_df,
        sentiment_df=sentiment_df_local,
        recommendations_df=recs_df,
        limit=limit,
    )


# =============================================================================
# NEW: Data Quality Report
# =============================================================================


@app.get("/api/data-quality", response_model=DataQualityReport, tags=["Data"])
def get_data_quality_report(
    request: Request,
):
    """Return a structured data-quality report for the active sales dataset.

    Checks missing values, invalid date/numeric parses, duplicates, and outliers.
    """
    if not INSIGHTS_AVAILABLE:
        # Uses the same flag (modules are shipped together)
        raise HTTPException(status_code=503, detail="Data quality module not available")

    company_id = require_company_id(request)
    branch_id = resolve_branch_scope(request)
    if not company_has_active_dataset(company_id, "sales", branch_id=branch_id):
        return Response(status_code=204)

    try:
        raw_df = load_active_sales_df(company_id, branch_id=branch_id)
    except Exception:
        return Response(status_code=204)

    report = generate_data_quality_report(company_id=company_id, dataset="sales", df=raw_df)
    return report


def load_forecast_data(company_id: str = "Acme Corp", branch_id: Optional[str] = None) -> Optional[pd.DataFrame]:
    """Load forecast data from DATABASE first, then CSV fallback.
    
    PRIORITY ORDER:
    1. Database (SQLite) - persists across container restarts
    2. CSV file fallback - for backward compatibility
    """
    def _normalize_forecast_frame(frame: pd.DataFrame) -> Optional[pd.DataFrame]:
        if frame is None or frame.empty:
            return None
        fdf = frame.copy()
        date_cols = ["MonthStart", "ds", "date", "Date", "OrderDate"]
        date_col = next((c for c in date_cols if c in fdf.columns), None)
        if date_col:
            fdf = fdf.rename(columns={date_col: "MonthStart"})
            fdf["MonthStart"] = pd.to_datetime(fdf["MonthStart"], errors="coerce")

        forecast_cols = ["ForecastedSales", "yhat", "forecast", "predicted"]
        forecast_col = next((c for c in forecast_cols if c in fdf.columns), None)
        if forecast_col:
            fdf = fdf.rename(columns={forecast_col: "ForecastedSales"})

        lower_cols = ["ForecastLower", "forecast_lower", "yhat_lower"]
        lower_col = next((c for c in lower_cols if c in fdf.columns), None)
        if lower_col and lower_col != "ForecastLower":
            fdf = fdf.rename(columns={lower_col: "ForecastLower"})

        upper_cols = ["ForecastUpper", "forecast_upper", "yhat_upper"]
        upper_col = next((c for c in upper_cols if c in fdf.columns), None)
        if upper_col and upper_col != "ForecastUpper":
            fdf = fdf.rename(columns={upper_col: "ForecastUpper"})

        return fdf
    # Try database first (persistent storage)
    if ANALYTICS_PERSISTENCE_AVAILABLE:
        try:
            fdf = get_forecast_results(company_id, branch_id=branch_id)
            if fdf is not None and not fdf.empty:
                logger.info(f"[FORECAST] Loaded {len(fdf)} records from DATABASE")
                return fdf
        except Exception as e:
            logger.warning(f"[FORECAST] Database read failed: {e}, falling back to CSV")
    
    # Fallback to tenant-scoped CSV files only
    forecast_files = [
        tenant_file_path(company_id, "forecast.csv", branch_id=branch_id),
        tenant_file_path(company_id, "sales_forecast.csv", branch_id=branch_id),
        tenant_file_path(company_id, "sales_forecast_future.csv", branch_id=branch_id),
        ensure_company_output_dir(company_id, branch_id) / f"{company_id}_forecast_prophet.csv",
        ensure_company_dir(company_id, "sales", branch_id=branch_id) / "forecast.csv",
    ]
    
    for fpath in forecast_files:
        if fpath.exists():
            try:
                fdf = _normalize_forecast_frame(pd.read_csv(fpath))
                if fdf is None or fdf.empty:
                    continue
                
                logger.info(f"[FORECAST] Loaded forecast from {fpath.name}: {len(fdf)} rows")
                
                # Sync to database for future requests
                if ANALYTICS_PERSISTENCE_AVAILABLE:
                    try:
                        forecast_data = fdf.to_dict(orient="records")
                        save_forecast_results(forecast_data, company_id, branch_id=branch_id, model_type="LinearRegression")
                        logger.info("[FORECAST] Synced CSV data to database")
                    except Exception as e:
                        logger.warning(f"[FORECAST] Failed to sync to database: {e}")
                
                return fdf
            except Exception as e:
                logger.warning(f"Failed to load forecast from {fpath}: {e}")

    if branch_id is None:
        aggregated_frames: List[pd.DataFrame] = []
        for dataset in list_active_datasets(company_id, "sales"):
            branch = normalize_branch_id(dataset.get("branch_id"))
            if not branch:
                continue
            branch_files = [
                tenant_file_path(company_id, "forecast.csv", branch_id=branch),
                tenant_file_path(company_id, "sales_forecast.csv", branch_id=branch),
                tenant_file_path(company_id, "sales_forecast_future.csv", branch_id=branch),
                ensure_company_output_dir(company_id, branch) / f"{company_id}_forecast_prophet.csv",
                ensure_company_dir(company_id, "sales", branch_id=branch) / "forecast.csv",
            ]
            for fpath in branch_files:
                if not fpath.exists():
                    continue
                try:
                    fdf = _normalize_forecast_frame(pd.read_csv(fpath))
                    if fdf is None or fdf.empty:
                        continue
                    aggregated_frames.append(fdf)
                    break
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Failed to load branch forecast %s: %s", fpath, exc)

        if aggregated_frames:
            combined = pd.concat(aggregated_frames, ignore_index=True)
            if "MonthStart" in combined.columns:
                sum_cols = [
                    col
                    for col in ["ForecastedSales", "ForecastLower", "ForecastUpper"]
                    if col in combined.columns
                ]
                for col in sum_cols:
                    combined[col] = pd.to_numeric(combined[col], errors="coerce")
                aggregated = (
                    combined.dropna(subset=["MonthStart"])
                    .groupby("MonthStart", as_index=False)[sum_cols]
                    .sum()
                    .sort_values("MonthStart")
                )
                logger.info(f"[FORECAST] Aggregated {len(aggregated)} forecast rows across branches")
                return aggregated
    
    return None


@app.get("/api/monthly-sales", response_model=List[MonthlySalesResponse], tags=["Analytics"])
def get_monthly_sales(
    request: Request,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    product: Optional[str] = Query(None),
):
    """Get monthly sales actuals and forecasts merged together."""
    company_id = require_company_id(request)
    branch_id = resolve_branch_scope(request)
    if not company_has_active_dataset(company_id, "sales", branch_id=branch_id):
        return Response(status_code=204)

    def _to_float(value: Any) -> Optional[float]:
        try:
            if value is None:
                return None
            f = float(value)
            if pd.isna(f):
                return None
            return f
        except Exception:
            try:
                f = pd.to_numeric(value, errors="coerce")
                if pd.isna(f):
                    return None
                return float(f)
            except Exception:
                return None
    
    try:
        sales_df = normalize_sales_dataframe(load_active_sales_df(company_id, branch_id=branch_id))
    except Exception as e:
        logger.warning(f"Failed to load active sales data for {company_id}: {e}")
        sales_df = None
    
    # Build combined result - actual + forecast
    monthly_dict = {}  # month -> {actual, forecast, forecast_lower, forecast_upper}
    
    # Step 1: Add actual monthly sales from company data
    if sales_df is not None and not sales_df.empty and "__order_date" in sales_df.columns and "__total_price" in sales_df.columns:
        try:
            sales_df = _apply_sales_filters(sales_df, start_date=start_date, end_date=end_date, city=city, product=product)
            monthly = sales_df.groupby(pd.Grouper(key="__order_date", freq="MS"))["__total_price"].sum().reset_index()
            
            for _, row in monthly.iterrows():
                month_key = row["__order_date"].strftime("%Y-%m")
                if month_key not in monthly_dict:
                    monthly_dict[month_key] = {"actual": None, "forecast": None, "forecast_lower": None, "forecast_upper": None}
                monthly_dict[month_key]["actual"] = float(row["__total_price"])
            
            logger.info(f"Computed {len(monthly)} monthly sales for {company_id}")
        except Exception as e:
            logger.warning(f"Failed to compute monthly sales: {e}")

    # Step 2: Add forecast data (load from database or CSV)
    # Only include global forecast when NOT segmenting by city/product.
    local_forecast_df = None
    if not city and not product:
        local_forecast_df = load_forecast_data(company_id, branch_id=branch_id)

    if local_forecast_df is not None and not local_forecast_df.empty:
        try:
            for _, row in local_forecast_df.iterrows():
                if "MonthStart" not in local_forecast_df.columns:
                    continue
                month_start = row.get("MonthStart")
                if month_start is None or (isinstance(month_start, float) and pd.isna(month_start)):
                    continue

                try:
                    month_dt = pd.to_datetime(month_start, errors="coerce")
                except Exception:
                    month_dt = None
                if month_dt is None or pd.isna(month_dt):
                    continue

                month_key = month_dt.strftime("%Y-%m")
                if month_key not in monthly_dict:
                    monthly_dict[month_key] = {"actual": None, "forecast": None, "forecast_lower": None, "forecast_upper": None}
                # Only add forecast if it's positive (avoid anomalous negative values)
                forecast_val = _to_float(row.get("ForecastedSales", row.get("yhat", row.get("forecast", row.get("predicted")))) )
                if forecast_val is not None and forecast_val > 0:
                    monthly_dict[month_key]["forecast"] = forecast_val

                lower_val = _to_float(row.get("ForecastLower", row.get("forecast_lower", row.get("yhat_lower"))))
                upper_val = _to_float(row.get("ForecastUpper", row.get("forecast_upper", row.get("yhat_upper"))))
                if lower_val is not None:
                    monthly_dict[month_key]["forecast_lower"] = lower_val
                if upper_val is not None:
                    monthly_dict[month_key]["forecast_upper"] = upper_val
            
            logger.info(f"Added {len([m for m in monthly_dict.values() if m['forecast']])} forecast records")
        except Exception as e:
            logger.warning(f"Failed to add forecasts: {e}")

    # Step 3: Filter by date range if provided (month string compare)
    if start_date:
        start_dt = pd.to_datetime(start_date)
        start_key = start_dt.strftime("%Y-%m")
        monthly_dict = {k: v for k, v in monthly_dict.items() if k >= start_key}
    if end_date:
        end_dt = pd.to_datetime(end_date)
        end_key = end_dt.strftime("%Y-%m")
        monthly_dict = {k: v for k, v in monthly_dict.items() if k <= end_key}

    # Step 4: Convert to response format
    result = [
        MonthlySalesResponse(
            month=month,
            actual_sales=data["actual"],
            forecasted_sales=data["forecast"],
            forecast_lower=data.get("forecast_lower"),
            forecast_upper=data.get("forecast_upper"),
        )
        for month, data in sorted(monthly_dict.items())
    ]

    if not result:
        logger.warning(f"No monthly sales data for {company_id} (no actuals or forecasts)")
        return []

    logger.info(f"Returning {len(result)} combined monthly sales records for {company_id}")
    return result


@app.post("/api/forecast/generate", tags=["Analytics"])
def generate_forecast(request: Request):
    """Generate a new sales forecast using the existing forecasting script.

    This endpoint makes the Forecasting page's "Generate Forecast" button actually
    produce `data/sales_forecast.csv`, which `/api/monthly-sales` merges into results.
    """
    require_tenant_manager_request(request)
    company_id = require_company_id(request)
    branch_id = resolve_branch_scope(request)
    if not company_has_active_dataset(company_id, "sales", branch_id=branch_id):
        return Response(status_code=204)

    script_path = BASE_DIR / "src" / "03_forecasting.py"
    if not script_path.exists():
        raise HTTPException(status_code=500, detail="Forecasting script not found")

    with pipeline_lock(operation="forecast-generate"):
        # Ensure the forecasting script has a canonical input file to read.
        # The script searches under DATA_DIR for cleaned_dataset.csv/sales.csv.
        try:
            active_sales_df = load_active_sales_df(company_id, branch_id=branch_id)
            tenant_env = build_tenant_ml_env(company_id, branch_id, dataset_type="sales")
            canonical_sales = Path(tenant_env["SI_DATA_DIR"]) / "sales.csv"
            active_sales_df.to_csv(canonical_sales, index=False)
            logger.info("[FORECAST] Wrote canonical input: %s (%d rows)", canonical_sales, len(active_sales_df))
        except Exception as exc:  # noqa: BLE001
            logger.warning("[FORECAST] Failed writing canonical sales.csv for %s: %s", company_id, exc)

        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(BASE_DIR),
            env=build_tenant_ml_env(company_id, branch_id, dataset_type="sales"),
            capture_output=True,
            text=True,
            timeout=240,
        )

        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "Forecast generation failed").strip()
            raise HTTPException(status_code=500, detail=detail)

        # Validate that the script produced the expected output.
        forecast_csv = Path(tenant_env.get("SI_FORECASTS_DIR", tenant_env["SI_OUTPUT_DIR"])) / "sales_forecast.csv"
        forecast_alias = Path(tenant_env.get("SI_TENANT_ROOT", tenant_env["SI_OUTPUT_DIR"])) / "forecast.csv"
        if not forecast_csv.exists() and not forecast_alias.exists():
            raise HTTPException(
                status_code=500,
                detail=f"Forecast script completed but did not create {forecast_csv} or {forecast_alias}. Check backend logs for details.",
            )

        try:
            validated_forecast_path = forecast_csv if forecast_csv.exists() else forecast_alias
            fdf = pd.read_csv(validated_forecast_path)
            if fdf.empty:
                raise HTTPException(
                    status_code=500,
                    detail="Forecast file is empty. Ensure your sales dataset has valid dates and revenue values.",
                )
            # Ensure we have a numeric forecast column with at least one positive value.
            forecast_col = None
            for c in ["ForecastedSales", "yhat", "forecast", "predicted"]:
                if c in fdf.columns:
                    forecast_col = c
                    break
            if not forecast_col:
                raise HTTPException(
                    status_code=500,
                    detail=f"Forecast file is missing a forecast column. Found columns: {list(fdf.columns)}",
                )
            values = pd.to_numeric(fdf[forecast_col], errors="coerce")
            if not (values.fillna(0) > 0).any():
                raise HTTPException(
                    status_code=500,
                    detail="Forecast values were not positive/valid. Check your dataset and forecasting script output.",
                )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Failed to validate forecast output: {exc}")

        # Reload any generated outputs and optionally persist to DB.
        try:
            reload_all_data_from_disk(company_id=company_id, branch_id=branch_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[FORECAST] Reload after generate failed: %s", exc)

        if ANALYTICS_PERSISTENCE_AVAILABLE:
            try:
                if forecast_csv.exists() or forecast_alias.exists():
                    # Reuse validated dataframe
                    if 'fdf' not in locals():
                        fdf = pd.read_csv(forecast_csv if forecast_csv.exists() else forecast_alias)
                    # Normalize columns similarly to load_forecast_data
                    if "OrderDate" in fdf.columns and "MonthStart" not in fdf.columns:
                        fdf = fdf.rename(columns={"OrderDate": "MonthStart"})
                    if "MonthStart" in fdf.columns:
                        fdf["MonthStart"] = pd.to_datetime(fdf["MonthStart"], errors="coerce")
                    if "ForecastedSales" not in fdf.columns:
                        forecast_col = next((c for c in ["yhat", "forecast", "predicted"] if c in fdf.columns), None)
                        if forecast_col:
                            fdf = fdf.rename(columns={forecast_col: "ForecastedSales"})
                    save_forecast_results(fdf.to_dict(orient="records"), company_id, branch_id=branch_id, model_type="LinearRegression")
            except Exception as exc:  # noqa: BLE001
                logger.warning("[FORECAST] Persist after generate failed: %s", exc)

    return {"success": True}


@app.get("/api/top-products", response_model=List[TopProductResponse], tags=["Analytics"])
def get_top_products(
    request: Request,
    limit: int = Query(5, ge=1, le=100),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    product: Optional[str] = Query(None),
):
    """Get top N products by revenue (limit: 1-100)."""
    company_id = require_company_id(request)
    branch_id = resolve_branch_scope(request)
    if not company_has_active_dataset(company_id, "sales", branch_id=branch_id):
        return Response(status_code=204)

    sales_df = normalize_sales_dataframe(load_active_sales_df(company_id, branch_id=branch_id))
    sales_df = _apply_sales_filters(sales_df, start_date=start_date, end_date=end_date, city=city, product=product)
    if sales_df is None or sales_df.empty:
        return Response(status_code=204)
    product_series = sales_df.get("__product")
    if product_series is None or not product_series.notna().any():
        raise HTTPException(status_code=404, detail="No product column found (expected one of ProductID, Product_ID, Product, SKU)")

    top = (
        sales_df.dropna(subset=["__product"]).groupby("__product")
        .agg({"__total_price": "sum", "__product": "count"})
        .rename(columns={"__product": "order_count"})
        .sort_values("__total_price", ascending=False)
        .head(limit)
        .reset_index()
    )

    return [
        TopProductResponse(
            product_id=str(row["__product"]),
            product_name=str(row["__product"]),
            revenue=float(row["__total_price"]),
            order_count=int(row["order_count"]),
        )
        for _, row in top.iterrows()
    ]


@app.get("/api/top-cities", response_model=List[TopCityResponse], tags=["Analytics"])
def get_top_cities(
    request: Request,
    limit: int = Query(5, ge=1, le=50),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    product: Optional[str] = Query(None),
):
    """Get top N cities by revenue."""
    company_id = require_company_id(request)
    branch_id = resolve_branch_scope(request)
    if not company_has_active_dataset(company_id, "sales", branch_id=branch_id):
        return Response(status_code=204)

    sales_df = normalize_sales_dataframe(load_active_sales_df(company_id, branch_id=branch_id))
    sales_df = _apply_sales_filters(sales_df, start_date=start_date, end_date=end_date, city=city, product=product)
    if sales_df is None or sales_df.empty:
        return Response(status_code=204)
    city_series = sales_df.get("__city")
    if city_series is None or not city_series.notna().any():
        raise HTTPException(status_code=404, detail="No city/region column found (expected one of City, Region, Market)")

    top = (
        sales_df.dropna(subset=["__city"]).groupby("__city")
        .agg({"__total_price": "sum", "__city": "count"})
        .rename(columns={"__city": "order_count"})
        .sort_values("__total_price", ascending=False)
        .head(limit)
        .reset_index()
    )

    return [
        TopCityResponse(
            city=str(row["__city"]),
            revenue=float(row["__total_price"]),
            order_count=int(row["order_count"]),
        )
        for _, row in top.iterrows()
    ]


@app.get("/api/sentiment-analysis", response_model=SentimentAnalysisResponse, tags=["Analytics"])
def get_sentiment_analysis(request: Request):
    """
    Compute sentiment percentages and keywords from CSV file ONLY.
    
    FIX: Skip database entirely - always read fresh from CSV to ensure
    the pre-calculated Sentiment column (Positive/Negative) is used.
    
    Returns 204 (No Content) when data is missing or empty.
    """
    company_id = require_company_id(request)
    branch_id = resolve_branch_scope(request)
    # IMPORTANT: Sentiment must only be available if reviews were uploaded.
    if not company_has_active_dataset(company_id, "reviews", branch_id=branch_id):
        return Response(status_code=204)

    local_sentiment_df = None
    data_source_used = "none"
    sentiment_candidates = analytics_result_candidates(company_id, "sentiment_results.csv", branch_id=branch_id)
    sentiment_path = sentiment_candidates[0]
    sentiment_path_used: Optional[Path] = None
    
    # =========================================================================
    # DIAGNOSTIC: Always load from CSV to use the pre-calculated Sentiment column
    # The CSV contains accurate Positive/Negative labels from TextBlob polarity.
    # Database may have stale or incorrectly synced data.
    # =========================================================================
    logger.info(f"[SENTIMENT DIAGNOSTIC] ========== API HIT ==========")
    logger.info(f"[SENTIMENT DIAGNOSTIC] Company: {company_id}")
    logger.info(f"[SENTIMENT DIAGNOSTIC] CSV Path candidates: {[str(path) for path in sentiment_candidates]}")
    logger.info(f"[SENTIMENT DIAGNOSTIC] Tenant CSV Exists: {sentiment_path.exists()}")

    read_error: Optional[Exception] = None
    for candidate in sentiment_candidates:
        if not candidate.exists():
            continue
        try:
            local_sentiment_df = pd.read_csv(candidate)
            sentiment_path_used = candidate
            data_source_used = f"CSV:{candidate}"
            logger.info(f"[SENTIMENT DIAGNOSTIC] Loaded from CSV: {len(local_sentiment_df)} rows")
            logger.info(f"[SENTIMENT DIAGNOSTIC] Columns: {local_sentiment_df.columns.tolist()}")

            if "Sentiment" in local_sentiment_df.columns:
                value_counts = local_sentiment_df["Sentiment"].value_counts().to_dict()
                logger.info(f"[SENTIMENT DIAGNOSTIC] df['Sentiment'].value_counts(): {value_counts}")
            elif "SentimentLabel" in local_sentiment_df.columns:
                value_counts = local_sentiment_df["SentimentLabel"].value_counts().to_dict()
                logger.info(f"[SENTIMENT DIAGNOSTIC] df['SentimentLabel'].value_counts(): {value_counts}")
            else:
                logger.warning("[SENTIMENT DIAGNOSTIC] No Sentiment column found!")
            break
        except Exception as exc:
            logger.warning(f"[SENTIMENT DIAGNOSTIC] Failed to read CSV {candidate}: {exc}")
            read_error = exc

    aggregated_timestamp: Optional[str] = None
    if local_sentiment_df is None and branch_id is None:
        aggregated_df, aggregated_ts = load_aggregated_branch_output(
            company_id,
            "sentiment_results.csv",
            "reviews",
        )
        if aggregated_df is not None and not aggregated_df.empty:
            local_sentiment_df = aggregated_df
            aggregated_timestamp = aggregated_ts
            data_source_used = "aggregated-branches"
            logger.info(f"[SENTIMENT DIAGNOSTIC] Aggregated sentiment from branches: {len(local_sentiment_df)} rows")

    if local_sentiment_df is None:
        if read_error is not None:
            raise HTTPException(status_code=500, detail="Unable to read sentiment_results.csv") from read_error
        logger.info("[SENTIMENT DIAGNOSTIC] sentiment_results.csv NOT FOUND - returning 204")
        return Response(status_code=204)

    if local_sentiment_df.empty:
        logger.info("[SENTIMENT DIAGNOSTIC] CSV is empty - returning 204")
        return Response(status_code=204)

    sentiment_col = None
    for col in ["SentimentLabel", "Sentiment", "Label", "sentiment_label"]:
        if col in local_sentiment_df.columns:
            sentiment_col = col
            break

    if sentiment_col is None:
        logger.warning("[SENTIMENT DIAGNOSTIC] Sentiment label column missing - returning 204")
        return Response(status_code=204)

    total = len(local_sentiment_df)
    sentiment_counts = local_sentiment_df[sentiment_col].value_counts().to_dict()
    
    # DIAGNOSTIC: Log the actual counts being used for aggregation
    logger.info(f"[SENTIMENT DIAGNOSTIC] Using column: '{sentiment_col}'")
    logger.info(f"[SENTIMENT DIAGNOSTIC] Raw sentiment_counts: {sentiment_counts}")
    logger.info(f"[SENTIMENT DIAGNOSTIC] Total reviews: {total}")
    logger.info(f"[SENTIMENT DIAGNOSTIC] Data source: CSV (database bypassed)")

    sentiment_breakdown = [
        SentimentDetail(
            label=label,
            count=int(sentiment_counts.get(label, 0)),
            percentage=round((sentiment_counts.get(label, 0) / total) * 100, 2),
        )
        for label in ["Positive", "Neutral", "Negative"]
    ]
    
    # DIAGNOSTIC: Log the final breakdown being sent to frontend
    logger.info(f"[SENTIMENT DIAGNOSTIC] Final breakdown: Positive={sentiment_counts.get('Positive', 0)}, Neutral={sentiment_counts.get('Neutral', 0)}, Negative={sentiment_counts.get('Negative', 0)}")

    text_col = None
    if "CleanedText" in local_sentiment_df.columns:
        text_col = "CleanedText"
    elif "ReviewText" in local_sentiment_df.columns:
        text_col = "ReviewText"

    top_keywords: List[str] = []
    if text_col:
        positive_reviews = local_sentiment_df[local_sentiment_df[sentiment_col] == "Positive"]
        if not positive_reviews.empty:
            text = " ".join(positive_reviews[text_col].astype(str).tolist()).lower()
            stop_words = {"the", "a", "and", "or", "is", "it", "to", "but", "i", "this", "that", "of", "in", "for"}
            words = [w for w in text.split() if len(w) > 3 and w not in stop_words]
            from collections import Counter

            word_freq = Counter(words)
            top_keywords = [word for word, _ in word_freq.most_common(5)]

    if sentiment_path_used:
        last_analyzed = datetime.fromtimestamp(sentiment_path_used.stat().st_mtime).isoformat()
    elif aggregated_timestamp:
        last_analyzed = aggregated_timestamp
    else:
        last_analyzed = datetime.now().isoformat()
    
    logger.info(f"[SENTIMENT API] Returning analysis for {total} reviews")

    return SentimentAnalysisResponse(
        total_reviews=total,
        sentiment_breakdown=sentiment_breakdown,
        top_keywords=top_keywords,
        last_analyzed=last_analyzed,
        data_source=sentiment_path_used.name if sentiment_path_used else data_source_used,
    )


@app.post("/api/sentiment/analyze", tags=["Analytics"])
def analyze_sentiment(request: Request):
    """Run sentiment analysis for the active tenant reviews dataset."""
    require_tenant_manager_request(request)
    company_id = require_company_id(request)
    branch_id = resolve_branch_scope(request)
    reviews_file = resolve_active_dataset_source_path(company_id, "reviews", branch_id=branch_id)

    if reviews_file is None or not reviews_file.exists():
        raise HTTPException(status_code=404, detail="No active reviews dataset found")

    with pipeline_lock(operation=f"sentiment-analyze-{company_id}-{branch_id or 'all'}"):
        success = run_sentiment_pipeline(reviews_file, company_id=company_id, branch_id=branch_id)

    if not success:
        raise HTTPException(status_code=500, detail="Sentiment analysis failed")

    return {"success": True, "message": "Sentiment analysis completed"}


@app.get("/api/sentiment", response_model=SentimentAnalysisResponse, tags=["Analytics"])
def get_sentiment_summary(request: Request):
    """Alias of /api/sentiment-analysis with identical 204/real-data behavior."""
    return get_sentiment_analysis(request)


@app.get("/api/recommendations", response_model=List[RecommendationResponse], tags=["Analytics"])
def get_recommendations(request: Request, limit: int = Query(10, ge=1, le=100)):
    """
    Return association rules from DATABASE first, then CSV fallback.
    
    PRIORITY ORDER:
    1. Database (SQLite) - persists across container restarts
    2. CSV file fallback - for backward compatibility
    3. AUTO-RUN: If both missing but sales data exists, run Recommendations pipeline automatically
    
    Returns 204 (No Content) when data is missing or empty.
    """
    current_user = require_authenticated_request(request)
    company_id = require_company_id(request)
    branch_id = resolve_branch_scope(request)
    if not company_has_active_dataset(company_id, "sales", branch_id=branch_id):
        return Response(status_code=204)

    rules_df = None
    recommendations_path = None
    recs_candidates = recommendation_result_candidates(company_id, branch_id=branch_id)
    for candidate in recs_candidates:
        if candidate.exists():
            recommendations_path = candidate
            break
    
    # Try database first (persistent storage)
    if ANALYTICS_PERSISTENCE_AVAILABLE:
        try:
            rules_df = get_recommendation_results(company_id, branch_id=branch_id)
            if rules_df is not None and not rules_df.empty:
                logger.info(f"[RECOMMENDATIONS API] Loaded {len(rules_df)} records from DATABASE")
        except Exception as e:
            logger.warning(f"[RECOMMENDATIONS API] Database read failed: {e}, falling back to CSV")
            rules_df = None
    
    # Fallback to CSV file
    if rules_df is None or rules_df.empty:
        logger.info(f"[RECOMMENDATIONS API] Checking for data at CSV: {recommendations_path}")

        if recommendations_path is None:
            if branch_id is None:
                aggregated_df, _ = load_aggregated_branch_output(
                    company_id,
                    "product_recommendations.csv",
                    "sales",
                )
                if aggregated_df is not None and not aggregated_df.empty:
                    rules_df = aggregated_df
                    logger.info("[RECOMMENDATIONS API] Loaded recommendations from branch aggregation")

            if rules_df is None or rules_df.empty:
                # AUTO-RUN FALLBACK: If no recommendations exist but sales data is available, run pipeline
                logger.info("[RECOMMENDATIONS API] product_recommendations.csv not found - checking for sales data to auto-generate")

                # Look for sales data in company folder or canonical location
                sales_file = None
                company_sales_dir = ensure_company_dir(company_id, "sales", branch_id=branch_id)
                if company_sales_dir.exists() and company_sales_dir.is_dir():
                    csvs = [p for p in company_sales_dir.glob("*.csv") if p.is_file()]
                    if csvs:
                        sales_file = max(csvs, key=lambda p: p.stat().st_mtime)
                        logger.info(f"[RECOMMENDATIONS API] Found company sales file: {sales_file}")

                # Fallback to canonical location
                if not sales_file:
                    canonical_sales = tenant_file_path(company_id, "sales.csv", branch_id=branch_id)
                    if canonical_sales.exists():
                        sales_file = canonical_sales
                        logger.info(f"[RECOMMENDATIONS API] Found canonical sales file: {sales_file}")

                if sales_file:
                    if not can_manage_tenant_data(current_user.get("role")):
                        logger.info("[RECOMMENDATIONS API] Skipping auto-run for non-admin role=%s", current_user.get("role"))
                        return Response(status_code=204)
                    logger.info(f"[RECOMMENDATIONS API] Auto-running recommendations pipeline from: {sales_file}")
                    success = trigger_recommendation_pipeline(sales_file, company_id=company_id, branch_id=branch_id)
                    recommendations_path = None
                    for candidate in recs_candidates:
                        if candidate.exists():
                            recommendations_path = candidate
                            break
                    if success and recommendations_path is not None:
                        # Reload from newly generated file
                        try:
                            rules_df = pd.read_csv(recommendations_path)
                            logger.info(f"[RECOMMENDATIONS API] Auto-generated recommendations: {len(rules_df)} rules")

                            # Sync to database for future requests
                            if ANALYTICS_PERSISTENCE_AVAILABLE and rules_df is not None and not rules_df.empty:
                                try:
                                    save_recommendation_results(rules_df, company_id, branch_id=branch_id)
                                    logger.info("[RECOMMENDATIONS API] Synced auto-generated data to database")
                                except Exception as e:
                                    logger.warning(f"[RECOMMENDATIONS API] Failed to sync to database: {e}")
                        except Exception as e:
                            logger.error(f"[RECOMMENDATIONS API] Failed to read auto-generated recommendations: {e}")
                            return Response(status_code=204)
                    else:
                        logger.warning("[RECOMMENDATIONS API] Auto-run recommendations pipeline failed - returning 204")
                        return Response(status_code=204)
                else:
                    logger.info("[RECOMMENDATIONS API] No sales data available to auto-generate recommendations - returning 204")
                    return Response(status_code=204)
        else:
            try:
                rules_df = pd.read_csv(recommendations_path)
                logger.info(f"[RECOMMENDATIONS API] Loaded product_recommendations.csv: {len(rules_df)} rows")

                # Sync to database for future requests
                if ANALYTICS_PERSISTENCE_AVAILABLE and not rules_df.empty:
                    try:
                        save_recommendation_results(rules_df, company_id, branch_id=branch_id)
                        logger.info("[RECOMMENDATIONS API] Synced CSV data to database")
                    except Exception as e:
                        logger.warning(f"[RECOMMENDATIONS API] Failed to sync to database: {e}")
            except Exception as exc:
                logger.error(f"[RECOMMENDATIONS API] Failed to read product_recommendations.csv: {exc}")
                raise HTTPException(status_code=500, detail="Unable to read product_recommendations.csv") from exc

    if rules_df is None or rules_df.empty:
        logger.info("[RECOMMENDATIONS API] No recommendation data available - returning 204")
        return Response(status_code=204)

    if "Confidence" in rules_df.columns:
        rules_df = rules_df[rules_df["Confidence"] > 0]
    if "Lift" in rules_df.columns:
        rules_df = rules_df.sort_values("Lift", ascending=False)

    rules_df = rules_df.head(limit)
    if rules_df.empty:
        logger.info("[RECOMMENDATIONS API] No valid rules after filtering - returning 204")
        return Response(status_code=204)

    results: List[RecommendationResponse] = []
    for _, row in rules_df.iterrows():
        # Handle multiple possible column name formats
        if_col = None
        for col_name in ["IF (Buy)", "IF", "Antecedent", "if_product", "antecedents"]:
            if col_name in row.index:
                if_col = col_name
                break
        if if_col is None:
            if_col = "if_product"
            
        then_col = None
        for col_name in ["THEN (Recommend)", "THEN", "Consequent", "then_product", "consequents"]:
            if col_name in row.index:
                then_col = col_name
                break
        if then_col is None:
            then_col = "then_product"
            
        conf_col = "Confidence" if "Confidence" in row.index else "confidence"
        lift_col = "Lift" if "Lift" in row.index else "lift"

        results.append(
            RecommendationResponse(
                if_product=str(row.get(if_col, "")),
                then_product=str(row.get(then_col, "")),
                confidence=float(row.get(conf_col, 0.0)),
                lift=float(row.get(lift_col, 0.0)),
            )
        )

    logger.info(f"[RECOMMENDATIONS API] Returning {len(results)} recommendation rules")
    return results


@app.get("/api/raw-data", tags=["Data"])
def get_raw_data(
    request: Request,
    limit: int = Query(100, ge=1, le=10000),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    product: Optional[str] = Query(None),
):
    """Get raw transaction data (paginated)."""
    company_id = require_company_id(request)
    branch_id = resolve_branch_scope(request)
    if not company_has_active_dataset(company_id, "sales", branch_id=branch_id):
        return Response(status_code=204)

    sales_df = load_active_sales_df(company_id, branch_id=branch_id)
    filtered_df = _filter_raw_sales_df(sales_df, start_date=start_date, end_date=end_date, city=city, product=product)
    return filtered_df.head(limit).to_dict(orient="records")


@app.get("/api/summary", tags=["Analytics"])
def get_summary():
    """Get a complete summary of all available data."""
    summary = {
        "status": "healthy" if df is not None else "degraded",
        "data_status": "available" if df is not None else "unavailable",
        "sales_records": len(df) if df is not None else 0,
        "forecast_records": len(forecast_df) if forecast_df is not None else 0,
        "sentiment_records": len(sentiment_df) if sentiment_df is not None else 0,
        "recommendation_rules": len(recommendation_df) if recommendation_df is not None else 0,
        "model_loaded": model is not None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return summary


# =============================================================================
# NEW: Customer Lifetime Value (CLV) API
# =============================================================================

@app.get("/api/clv", tags=["Intelligence"])
def get_customer_clv(
    request: Request,
    refresh: bool = Query(True, description="Force recalculation of CLV (default: true to avoid stale results)")
):
    """
    Get Customer Lifetime Value analysis.
    
    Provides:
    - Historical and Predictive CLV per customer
    - CLV-based segmentation (Platinum, Gold, Silver, Bronze)
    - Acquisition cost recommendations
    - Top customer identification
    """
    company_id = require_company_id(request)
    branch_id = resolve_branch_scope(request)
    if not company_has_active_dataset(company_id, "sales", branch_id=branch_id):
        return Response(status_code=204)
    
    # Check for cached CLV data
    clv_suffix = f"{company_id}_branch_{branch_id}" if branch_id else company_id
    clv_path = ensure_company_output_dir(company_id, branch_id) / f"{clv_suffix}_clv_insights.json"
    
    if clv_path.exists() and not refresh:
        try:
            with open(clv_path, "r", encoding="utf-8") as f:
                clv_data = json.load(f)
            logger.info(f"[CLV API] Returning cached CLV data for {company_id}")
            return JSONResponse(content=jsonable_encoder(clv_data), headers={"Cache-Control": "no-store"})
        except Exception as e:
            logger.warning(f"Failed to load cached CLV: {e}")
    
    # Calculate fresh CLV
    try:
        sys.path.insert(0, str(BASE_DIR / "src"))
        from clv_calculation import run_clv_analysis  # type: ignore
        
        clv_data = run_clv_analysis(company_id)
        if branch_id:
            clv_data["branch_id"] = branch_id
        logger.info(f"[CLV API] Calculated CLV for {company_id}")
        return JSONResponse(content=jsonable_encoder(clv_data), headers={"Cache-Control": "no-store"})
        
    except ImportError:
        logger.warning("CLV calculation module not available")
        return JSONResponse(content={
            "company": company_id,
            "error": "CLV calculation module not available",
            "insights": {"summary": {}, "segments": {}, "recommendations": []},
            "top_customers": []
        }, headers={"Cache-Control": "no-store"})
    except Exception as e:
        logger.error(f"CLV calculation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/clv/segments", tags=["Intelligence"])
def get_clv_segments(request: Request):
    """Get CLV segment breakdown."""
    company_id = require_company_id(request)
    branch_id = resolve_branch_scope(request)
    if not company_has_active_dataset(company_id, "sales", branch_id=branch_id):
        return Response(status_code=204)
    
    clv_suffix = f"{company_id}_branch_{branch_id}" if branch_id else company_id
    clv_csv_path = ensure_company_output_dir(company_id, branch_id) / f"{clv_suffix}_clv_analysis.csv"
    
    if not clv_csv_path.exists():
        # Try to generate it
        return get_customer_clv(request, refresh=True)
    
    try:
        clv_df = pd.read_csv(clv_csv_path)
        
        if 'clv_segment' not in clv_df.columns:
            return {"error": "CLV segments not calculated", "segments": {}}
        
        segment_summary = clv_df.groupby('clv_segment').agg({
            'average_clv': ['count', 'sum', 'mean']
        }).round(2)
        
        segment_summary.columns = ['customer_count', 'total_clv', 'avg_clv']
        
        return {
            "company": company_id,
            "segments": segment_summary.to_dict('index'),
            "total_customers": len(clv_df),
            "total_clv": float(clv_df['average_clv'].sum())
        }
    except Exception as e:
        logger.error(f"Failed to get CLV segments: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# NEW: Intelligence Dashboard Summary
# =============================================================================

@app.get("/api/intelligence-summary", tags=["Intelligence"])
def get_intelligence_summary(request: Request):
    """
    Get a complete intelligence summary for the dashboard.
    
    This is the main endpoint for the enhanced dashboard, combining:
    - CLV highlights
    - Actionable recommendations
    """
    company_id = require_company_id(request)
    branch_id = resolve_branch_scope(request)
    if not company_has_active_dataset(company_id, "sales", branch_id=branch_id):
        return Response(status_code=204)
    
    summary = {
        "company": company_id,
        "branch_id": branch_id,
        "generated_at": datetime.now().isoformat(),
        "clv_highlights": {},
        "top_recommendations": []
    }
    
    # Load CLV highlights
    clv_suffix = f"{company_id}_branch_{branch_id}" if branch_id else company_id
    clv_path = ensure_company_output_dir(company_id, branch_id) / f"{clv_suffix}_clv_insights.json"
    if clv_path.exists():
        try:
            with open(clv_path, "r", encoding="utf-8") as f:
                clv_data = json.load(f)
            insights = clv_data.get("insights", {})
            summary["clv_highlights"] = {
                "average_clv": insights.get("summary", {}).get("average_clv", 0),
                "total_customers": insights.get("summary", {}).get("total_customers", 0),
                "platinum_customers": insights.get("segments", {}).get("Platinum", {}).get("count", 0),
                "platinum_value_pct": insights.get("segments", {}).get("Platinum", {}).get("pct_of_total", 0)
            }
        except Exception:
            pass
    
    # Compile top recommendations from all sources
    all_recommendations = []
    
    summary["top_recommendations"] = all_recommendations[:5]
    
    return summary


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
