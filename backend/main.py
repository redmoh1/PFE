"""FastAPI backend for Intelligent Sales Analytics Dashboard.

Exposes data endpoints for the React frontend to consume.
Run with: uvicorn backend.main:app --reload
"""

import sys
import logging
import os
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
from functools import lru_cache
import shutil
import subprocess
import hashlib

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query, Request, UploadFile, File, Form, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr

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
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
try:
    from pipeline_controller import (
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

ALLOWED_DATASET_TYPES = {"sales", "customers", "reviews"}
MAX_PREVIEW_ROWS = 50

DATE_CANDIDATES = ["OrderDate", "Sale_Date", "Order_Date", "Date", "order_date"]
# IMPORTANT: Include "Price" for datasets that use Price instead of TotalPrice
REVENUE_CANDIDATES = ["TotalPrice", "Price", "Sales_Amount", "SalesAmount", "Revenue", "Sales", "Amount", "amount", "price"]
PRODUCT_CANDIDATES = ["ProductID", "Product_ID", "Product", "SKU"]
CITY_CANDIDATES = ["City", "city", "Region", "region", "Market"]

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
        "role": "admin"
    },
    "analyst@acme.com": {
        "id": "2", 
        "email": "analyst@acme.com",
        "name": "Analyst User",
        "password_hash": "$2b$12$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi",  # analyst123
        "company": "Acme Corp",
        "company_id": 1,
        "role": "analyst"
    }
}

# Simple password for demo (when passlib is not available)
DEMO_PASSWORDS = {
    "admin@acme.com": "admin123",
    "analyst@acme.com": "analyst123"
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
    role: str


# =============================================================================
# Authentication Helpers
# =============================================================================
def verify_password(plain_password: str, hashed_password: str, email: str = None) -> bool:
    """Verify password - uses simple check for demo, bcrypt for production."""
    # Always check simple demo passwords first for reliability
    if email and email in DEMO_PASSWORDS:
        if plain_password == DEMO_PASSWORDS[email]:
            return True
    
    # Try bcrypt verification if passlib is available
    if PASSLIB_ENABLED:
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception as e:
            logger.warning(f"Password verification failed: {e}")
    
    return False


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
        if email in DEMO_USERS:
            user = DEMO_USERS[email].copy()
            user.pop("password_hash", None)
            return user
        return None
    
    if not JWT_ENABLED:
        return None
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email and email in DEMO_USERS:
            user = DEMO_USERS[email].copy()
            user.pop("password_hash", None)
            return user
    except JWTError:
        pass
    
    return None


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


def ensure_company_dir(company_id: str, dataset_type: str) -> Path:
    company_dir = DATA_DIR / company_id / dataset_type
    company_dir.mkdir(parents=True, exist_ok=True)
    return company_dir


def row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "company_id": row["company_id"],
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
    title="Sales Analytics API",
    description="Backend API for Intelligent Sales Analytics Dashboard",
    version="1.0.0",
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=ALLOWED_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    max_age=3600,  # Cache preflight requests for 1 hour
)
logger.info(f"CORS enabled for origins: {ALLOWED_ORIGINS}")


# ============================================================================
# Authentication Endpoints
# ============================================================================

@app.post("/api/auth/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """Authenticate user and return JWT token."""
    email = request.email.lower().strip()
    password = request.password
    
    # Check if user exists
    if email not in DEMO_USERS:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    user_data = DEMO_USERS[email]
    
    # Verify password
    if not verify_password(password, user_data["password_hash"], email):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Create access token
    access_token = create_access_token(data={"sub": email})
    
    # Prepare user response (without password)
    user_response = {
        "id": user_data["id"],
        "email": user_data["email"],
        "name": user_data["name"],
        "company": user_data["company"],
        "role": user_data["role"]
    }
    
    logger.info(f"User logged in: {email}")
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=user_response
    )


@app.get("/api/auth/me")
async def get_current_user_info(current_user: Dict = Depends(get_current_user)):
    """Get current authenticated user info."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return current_user


@app.get("/api/auth/verify")
async def verify_token(current_user: Dict = Depends(get_current_user)):
    """Verify if the current token is valid."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return {"valid": True, "user": current_user}


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


class TopProductResponse(BaseModel):
    product_id: str
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


def clear_all_caches_and_reset():
    """
    CRITICAL: Clear ALL in-memory caches and reset ALL global DataFrames.
    
    This function MUST be called:
    1. After deleting any dataset
    2. After uploading any dataset (before pipeline runs)
    3. After any pipeline completes
    
    ENTERPRISE BEHAVIOR:
    - No stale data should ever remain in memory
    - All APIs must fetch fresh data from disk after this call
    """
    global df, forecast_df, sentiment_df, recommendation_df, model, data_last_modified
    
    logger.info("=" * 60)
    logger.info("[CACHE CLEAR] Resetting ALL in-memory state")
    logger.info("=" * 60)
    
    # Reset all global DataFrames to None
    df = None
    forecast_df = None
    sentiment_df = None
    recommendation_df = None
    model = None
    data_last_modified = None
    
    logger.info("[CACHE CLEAR] All global DataFrames set to None")
    logger.info("[CACHE CLEAR] Memory state cleared - APIs will read fresh from disk")
    logger.info("=" * 60)


def reload_all_data_from_disk():
    """
    Reload all data from disk into global DataFrames.
    Called after pipeline completion to ensure fresh data is available.
    
    Returns:
        dict with status of each data source
    """
    global df, forecast_df, sentiment_df, recommendation_df, model, data_last_modified
    
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
        DATA_DIR / "cleaned_dataset.csv",
        DATA_DIR / "sales.csv",
        DATA_DIR / "merged_data.csv",
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
        DATA_DIR / "sales_forecast.csv",  # From 03_forecasting.py (Linear Regression)
        DATA_DIR / "sales_forecast_future.csv",
        BASE_DIR / "output" / "Acme Corp_forecast_prophet.csv",
        DATA_DIR / "forecast.csv",
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
    sentiment_path = DATA_DIR / "sentiment_results.csv"
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
    recs_path = DATA_DIR / "product_recommendations.csv"
    if recs_path.exists():
        try:
            recommendation_df = pd.read_csv(recs_path)
            logger.info(f"[DATA RELOAD] Loaded product_recommendations.csv: {len(recommendation_df)} rows")
            status["recommendations"] = True
        except Exception as e:
            logger.warning(f"[DATA RELOAD] Failed to load product_recommendations.csv: {e}")
            recommendation_df = None
    else:
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
    
    return status


@app.on_event("startup")
def load_data():
    """Load all data at startup."""
    reload_all_data_from_disk()


def require_company_id(request: Request) -> str:
    """Extract and validate company_id from request headers."""
    company_id = request.headers.get("X-Company-ID")
    if not company_id:
        raise HTTPException(status_code=400, detail="Missing X-Company-ID header")
    return company_id


def trigger_recommendation_pipeline(sales_file_path: Path) -> bool:
    """
    Trigger Market Basket Analysis (Apriori) pipeline.
    Generates product_recommendations.csv from sales transactions.
    
    Args:
        sales_file_path: Path to sales CSV with OrderID and ProductID columns
        
    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info(f"Triggering recommendation pipeline for: {sales_file_path}")
        
        # Import and run the recommendation script
        sys.path.insert(0, str(BASE_DIR / "src"))
        from src import recommendation as rec_module
        
        # Load sales data
        df = pd.read_csv(sales_file_path)
        
        # Validate required columns
        if 'OrderID' not in df.columns:
            logger.warning("OrderID column missing - cannot generate recommendations")
            return False
            
        product_col = None
        for col in ['ProductID', 'Product_ID', 'Product', 'SKU']:
            if col in df.columns:
                product_col = col
                break
                
        if not product_col:
            logger.warning("Product column missing - cannot generate recommendations")
            return False
        
        # Check if we have multi-product orders
        order_counts = df.groupby('OrderID').size()
        multi_product_orders = (order_counts > 1).sum()
        
        if multi_product_orders < 2:
            logger.warning(f"Only {multi_product_orders} multi-product orders - insufficient for recommendations")
            # Create empty recommendations file
            empty_df = pd.DataFrame(columns=['RuleID', 'IF', 'THEN', 'Support', 'Confidence', 'Lift'])
            empty_df.to_csv(DATA_DIR / "product_recommendations.csv", index=False)
            return False
        
        logger.info(f"Found {multi_product_orders} multi-product orders - proceeding with Apriori")
        
        # Run recommendation pipeline by calling the main script
        import subprocess
        result = subprocess.run(
            [sys.executable, str(BASE_DIR / "src" / "05_recommendation.py")],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode == 0:
            logger.info("Recommendation pipeline completed successfully")
            # Reload global recommendation_df
            global recommendation_df
            try:
                recommendation_df = pd.read_csv(DATA_DIR / "product_recommendations.csv")
                logger.info(f"Reloaded {len(recommendation_df)} recommendation rules")
            except:
                recommendation_df = None
            return True
        else:
            logger.error(f"Recommendation pipeline failed: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Error triggering recommendation pipeline: {e}")
        return False


def trigger_sentiment_pipeline(reviews_file_path: Path) -> bool:
    """
    Trigger NLP sentiment analysis pipeline.
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
        
        logger.info(f"Found {len(df)} reviews with text - proceeding with sentiment analysis")
        
        # Run sentiment pipeline
        import subprocess
        result = subprocess.run(
            [sys.executable, str(BASE_DIR / "src" / "06_sentiment.py")],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            timeout=180
        )
        
        if result.returncode == 0:
            logger.info("Sentiment pipeline completed successfully")
            # Reload global sentiment_df
            global sentiment_df
            try:
                sentiment_df = pd.read_csv(DATA_DIR / "sentiment_results.csv")
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


# ============================================================================
# Dataset metadata helpers (multi-tenant)
# ============================================================================


def list_datasets(company_id: str) -> List[Dict[str, Any]]:
    conn = get_db_connection()
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


def archive_existing(company_id: str, dataset_type: str) -> None:
    conn = get_db_connection()
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


def insert_dataset(company_id: str, dataset_type: str, file_name: str, file_path: Path, row_count: int) -> Dict[str, Any]:
    conn = get_db_connection()
    uploaded_at = datetime.now(timezone.utc).isoformat()
    cur = conn.execute(
        """
        INSERT INTO datasets (company_id, dataset_type, file_name, file_path, row_count, uploaded_at, is_active, is_deleted)
        VALUES (?, ?, ?, ?, ?, ?, 1, 0)
        """,
        (company_id, dataset_type, file_name, str(file_path), row_count, uploaded_at),
    )
    conn.commit()
    dataset_id = cur.lastrowid
    row = conn.execute("SELECT * FROM datasets WHERE id = ?", (dataset_id,)).fetchone()
    conn.close()
    return row_to_dict(row)


def get_dataset(dataset_id: int, company_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    row = conn.execute(
        "SELECT * FROM datasets WHERE id = ? AND company_id = ? AND is_deleted = 0",
        (dataset_id, company_id),
    ).fetchone()
    conn.close()
    return row_to_dict(row) if row else None


def get_active_dataset(company_id: str, dataset_type: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
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


def delete_dataset(dataset_id: int, company_id: str) -> None:
    conn = get_db_connection()
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


def cascade_delete_derived_files(dataset_type: str) -> dict:
    """
    Delete ALL derived ML output files when any dataset is deleted.
    
    SINGLE SOURCE OF TRUTH: Uses pipeline_controller.detect_data_deletion() when available.
    
    ENTERPRISE BEHAVIOR:
    - Deleting ANY dataset triggers full cascade deletion
    - No stale analytics should remain on disk
    - No stale data should remain in memory
    - APIs will return 204 until new data is uploaded and processed
    
    Args:
        dataset_type: Type of dataset being deleted (sales, customers, reviews)
        
    Returns:
        dict with deleted_files list and any errors
    """
    logger.info("=" * 60)
    logger.info(f"[CASCADE DELETE] TRIGGERED for dataset_type={dataset_type}")
    logger.info("=" * 60)
    
    # Use Pipeline Controller if available (PREFERRED - Single Source of Truth)
    if PIPELINE_CONTROLLER_AVAILABLE:
        logger.info("[CASCADE DELETE] Using Pipeline Controller (SINGLE SOURCE OF TRUTH)")
        try:
            result = detect_data_deletion(dataset_type)
            # Also clear in-memory caches
            clear_all_caches_and_reset()
            logger.info(f"[CASCADE DELETE] Pipeline Controller completed: {result}")
            return {
                "deleted_files": result.get("hard_reset", {}).get("deleted_files", []),
                "errors": result.get("hard_reset", {}).get("errors", []),
                "total_deleted": result.get("hard_reset", {}).get("deleted_count", 0),
                "memory_cleared": True,
            }
        except Exception as e:
            logger.error(f"[CASCADE DELETE] Pipeline Controller failed: {e}")
            logger.info("[CASCADE DELETE] Falling back to inline implementation")
    
    # FALLBACK: Inline implementation
    deleted_files = []
    errors = []
    
    # Step 1: Clear ALL in-memory caches FIRST
    logger.info("[CASCADE DELETE] Step 1: Clearing all in-memory caches...")
    clear_all_caches_and_reset()
    
    # Step 2: Delete ALL derived ML outputs
    logger.info("[CASCADE DELETE] Step 2: Deleting derived ML output files...")
    for filename in DERIVED_ML_FILES:
        file_path = DATA_DIR / filename
        try:
            if file_path.exists():
                file_path.unlink()
                deleted_files.append(filename)
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
        file_path = DATA_DIR / canonical_file
        try:
            if file_path.exists():
                file_path.unlink()
                deleted_files.append(canonical_file)
                logger.info(f"[CASCADE DELETE] ✓ Deleted canonical: {canonical_file}")
        except Exception as e:
            error_msg = f"Failed to delete canonical {canonical_file}: {str(e)}"
            errors.append(error_msg)
            logger.error(f"[CASCADE DELETE] ✗ {error_msg}")
    
    # Step 4: Clear output directory plots if they exist
    logger.info("[CASCADE DELETE] Step 4: Cleaning output directory...")
    output_dir = BASE_DIR / "output"
    plots_dir = output_dir / "plots"
    for output_file in ["eda_report.json", "kpis.csv", "monthly_sales.csv", "sales_by_city.csv", "top_products.csv"]:
        try:
            output_path = output_dir / output_file
            if output_path.exists():
                output_path.unlink()
                deleted_files.append(f"output/{output_file}")
                logger.info(f"[CASCADE DELETE] ✓ Deleted output: {output_file}")
        except Exception as e:
            logger.warning(f"[CASCADE DELETE] Could not delete output/{output_file}: {e}")
    
    # Step 5: Clear plots directory
    logger.info("[CASCADE DELETE] Step 5: Cleaning plots directory...")
    if plots_dir.exists():
        try:
            for plot_file in plots_dir.glob("*.png"):
                plot_file.unlink()
                deleted_files.append(f"plots/{plot_file.name}")
            logger.info("[CASCADE DELETE] ✓ Cleared plots directory")
        except Exception as e:
            logger.warning(f"[CASCADE DELETE] Could not clear plots: {e}")
    
    # Step 6: Clear model_registry directory
    logger.info("[CASCADE DELETE] Step 6: Cleaning model_registry directory...")
    model_registry_dir = BASE_DIR / "src" / "ml_lifecycle" / "model_registry"
    if model_registry_dir.exists():
        try:
            for model_file in model_registry_dir.glob("*"):
                if model_file.is_file():
                    model_file.unlink()
                    deleted_files.append(f"model_registry/{model_file.name}")
            logger.info("[CASCADE DELETE] ✓ Cleared model_registry directory")
        except Exception as e:
            logger.warning(f"[CASCADE DELETE] Could not clear model_registry: {e}")
    
    logger.info("=" * 60)
    logger.info(f"[CASCADE DELETE] COMPLETED: {len(deleted_files)} files deleted, {len(errors)} errors")
    logger.info("[CASCADE DELETE] All in-memory state cleared")
    logger.info("[CASCADE DELETE] APIs will return 204 (No Content) until new data is uploaded")
    logger.info("=" * 60)
    
    return {
        "deleted_files": deleted_files,
        "errors": errors,
        "total_deleted": len(deleted_files),
        "memory_cleared": True,
    }


def is_company_active(dataset_id: int, company_id: str) -> bool:
    conn = get_db_connection()
    row = conn.execute(
        "SELECT is_active FROM datasets WHERE id = ? AND company_id = ? AND is_deleted = 0",
        (dataset_id, company_id),
    ).fetchone()
    conn.close()
    return bool(row[0]) if row else False


def run_full_sales_pipeline(uploaded_file: Path) -> bool:
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
        clear_all_caches_and_reset()
        
        # Step 1: Copy uploaded file to canonical location for ML scripts
        canonical_sales = DATA_DIR / "sales.csv"
        logger.info(f"[PIPELINE] Step 1: Copying {uploaded_file.name} -> {canonical_sales}")
        shutil.copy2(uploaded_file, canonical_sales)
        logger.info("[PIPELINE] ✓ Sales file copied to canonical location")
        
        # Step 2: Run EDA (Phase 1) - creates merged_data.csv
        logger.info("[PIPELINE] Step 2: Running Phase 1 - EDA...")
        result = subprocess.run(
            [sys.executable, str(BASE_DIR / "src" / "01_eda.py")],
            cwd=str(BASE_DIR),
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
        cleaned_path = DATA_DIR / "cleaned_dataset.csv"
        if not cleaned_path.exists():
            logger.error("[PIPELINE] ✗ cleaned_dataset.csv was not created by Phase 1")
            return False
        logger.info("[PIPELINE] ✓ cleaned_dataset.csv verified (created by Phase 1)")
        
        # Step 4: Run RFM Segmentation (Phase 4) - creates rfm_table.csv
        logger.info("[PIPELINE] Step 4: Running Phase 4 - RFM Segmentation...")
        result = subprocess.run(
            [sys.executable, str(BASE_DIR / "src" / "04_rfm.py")],
            cwd=str(BASE_DIR),
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
        reload_status = reload_all_data_from_disk()
        
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


def run_sentiment_pipeline(uploaded_file: Path) -> bool:
    """
    Run sentiment analysis pipeline for reviews data:
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
        sentiment_path = DATA_DIR / "sentiment_results.csv"
        if sentiment_path.exists():
            sentiment_path.unlink()
            logger.info("[SENTIMENT PIPELINE] ✓ Old sentiment_results.csv deleted")
        
        # Step 1: Copy uploaded file to canonical location for ML scripts
        canonical_reviews = DATA_DIR / "customer_reviews.csv"
        logger.info(f"[SENTIMENT PIPELINE] Step 1: Copying {uploaded_file.name} -> {canonical_reviews}")
        shutil.copy2(uploaded_file, canonical_reviews)
        logger.info("[SENTIMENT PIPELINE] ✓ Reviews file copied to canonical location")
        
        # Step 2: Run Sentiment Analysis (Phase 6)
        logger.info("[SENTIMENT PIPELINE] Step 2: Running Phase 6 - Sentiment Analysis...")
        result = subprocess.run(
            [sys.executable, str(BASE_DIR / "src" / "06_sentiment.py")],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            timeout=300  # NLP can take longer
        )
        if result.returncode != 0:
            logger.error(f"[SENTIMENT PIPELINE] ✗ Sentiment analysis failed: {result.stderr}")
            return False
        logger.info("[SENTIMENT PIPELINE] ✓ Sentiment analysis completed")
        
        # Step 3: Reload sentiment data from disk
        logger.info("[SENTIMENT PIPELINE] Step 3: Reloading sentiment data from disk...")
        if sentiment_path.exists():
            try:
                sentiment_df = pd.read_csv(sentiment_path)
                logger.info(f"[SENTIMENT PIPELINE] ✓ Loaded sentiment_results.csv: {len(sentiment_df)} rows")
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


def trigger_pipeline(company_id: str, dataset_type: str, action: str, file_path: Optional[Path] = None) -> None:
    """
    Hook for automation workflows - triggers COMPLETE ML pipelines when data is uploaded.
    
    SINGLE SOURCE OF TRUTH: Uses pipeline_controller.orchestrate_pipeline() for all execution.
    
    Pipeline Flow:
    - Sales data upload → EDA → Cleaning → RFM → Recommendations
    - Reviews data upload → Sentiment Analysis
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
            result = orchestrate_pipeline(dataset_type, action, file_path)
            if result.get("execution", {}).get("success", False):
                logger.info(f"[TRIGGER] ✓ Pipeline Controller completed successfully")
            else:
                logger.warning(f"[TRIGGER] ⚠ Pipeline Controller had issues: {result}")
            
            # Reload data after pipeline completion
            reload_all_data_from_disk()
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
            success = run_full_sales_pipeline(file_path)
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
        logger.info(f"[TRIGGER] Triggering Sentiment Analysis Pipeline for {file_path}")
        try:
            success = run_sentiment_pipeline(file_path)
            if success:
                logger.info("[TRIGGER] ✓ Sentiment Analysis Pipeline completed - sentiment results regenerated")
            else:
                logger.warning("[TRIGGER] ⚠ Sentiment Analysis Pipeline failed - check logs for details")
        except Exception as e:
            logger.error(f"[TRIGGER] ✗ Error running sentiment pipeline: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    # Handle customers upload - copy to canonical location and re-run pipeline if sales exists
    if dataset_type == "customers" and file_path and action in ["upload", "replace"]:
        canonical_customers = DATA_DIR / "customers.csv"
        logger.info(f"[TRIGGER] Handling customers upload -> {canonical_customers}")
        try:
            shutil.copy2(file_path, canonical_customers)
            logger.info("[TRIGGER] ✓ Customers file copied to canonical location")
            
            # If sales.csv exists, re-run the pipeline to merge with new customers
            canonical_sales = DATA_DIR / "sales.csv"
            if canonical_sales.exists():
                logger.info("[TRIGGER] Sales data exists - re-running full pipeline to merge with customers")
                success = run_full_sales_pipeline(canonical_sales)
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


def load_active_sales_df(company_id: Optional[str] = None) -> pd.DataFrame:
    """Load the active sales dataset for a company; fallback to global df or direct files."""
    active: Optional[Dict[str, Any]] = None

    if company_id:
        active = get_active_dataset(company_id, "sales")
    else:
        active = get_latest_active_dataset("sales")

    if active and Path(active["file_path"]).exists():
        try:
            return pd.read_csv(Path(active["file_path"]))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to load active dataset %s: %s", active["file_path"], exc)

    # Fallback to legacy global dataset
    if df is not None and not df.empty:
        return df

    # Fallback to direct file search
    possible_files = [
        DATA_DIR / "sales.csv",
        DATA_DIR / "cleaned_dataset.csv",
        DATA_DIR / "merged_data.csv",
    ]
    
    for file_path in possible_files:
        if file_path.exists():
            try:
                loaded_df = pd.read_csv(file_path)
                if not loaded_df.empty:
                    logger.info(f"[FALLBACK] Loaded sales data from {file_path.name}")
                    return loaded_df
            except Exception as e:
                logger.warning(f"Failed to load {file_path}: {e}")
                continue

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

    product_col = next((c for c in PRODUCT_CANDIDATES if c in working.columns), None)
    working["__product"] = working[product_col].astype(str) if product_col else None

    city_col = next((c for c in CITY_CANDIDATES if c in working.columns), None)
    working["__city"] = working[city_col].astype(str) if city_col else None

    working = working[working["__order_date"].notna()].copy()
    return working


# ============================================================================
# API Endpoints
# ============================================================================


@app.get("/", tags=["Root"])
def root():
    """Root endpoint - redirects to API documentation."""
    return {
        "message": "Sales Analytics API is running",
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
    return list_datasets(company_id)


@app.post("/api/datasets/upload", response_model=DatasetMeta, tags=["Datasets"])
async def upload_dataset(
    request: Request,
    dataset_type: str = Form(...),
    file: UploadFile = File(...),
):
    company_id = require_company_id(request)
    dataset_type = dataset_type.lower()
    if dataset_type not in ALLOWED_DATASET_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported dataset_type")

    # Use lock to prevent concurrent upload/pipeline race conditions
    with pipeline_lock(f"upload-{dataset_type}-{company_id}"):
        target_dir = ensure_company_dir(company_id, dataset_type)
        safe_name = file.filename.replace(" ", "_")
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        target_path = target_dir / f"{timestamp}_{safe_name}"

        with target_path.open("wb") as fh:
            fh.write(await file.read())

        # Normalize sales schema to canonical columns for downstream jobs
        if dataset_type == "sales":
            try:
                raw_df = pd.read_csv(target_path)
                normalized = normalize_sales_dataframe(raw_df)
                canonical = pd.DataFrame({
                    "OrderID": raw_df.get("OrderID")
                    or raw_df.get("id")
                    or raw_df.get("ID")
                    or raw_df.get("Order_Id")
                    or range(1, len(normalized) + 1),
                    "OrderDate": normalized["__order_date"],
                    "TotalPrice": normalized["__total_price"],
                    "ProductID": normalized["__product"],
                    "City": normalized["__city"],
                })
                canonical.to_csv(target_path, index=False)
                row_count = len(canonical)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to normalize uploaded sales file %s: %s", target_path, exc)
                row_count = compute_row_count(target_path)
        else:
            row_count = compute_row_count(target_path)

        archive_existing(company_id, dataset_type)
        record = insert_dataset(company_id, dataset_type, safe_name, target_path, row_count)

        trigger_pipeline(company_id, dataset_type, action="upload", file_path=target_path)
        return record


@app.post("/api/datasets/{dataset_id}/replace", response_model=DatasetMeta, tags=["Datasets"])
async def replace_dataset(
    dataset_id: int,
    request: Request,
    file: UploadFile = File(...),
):
    company_id = require_company_id(request)
    current = get_dataset(dataset_id, company_id)
    if not current:
        raise HTTPException(status_code=404, detail="Dataset not found")

    dataset_type = current["dataset_type"]
    
    # Use lock to prevent concurrent replace/pipeline race conditions
    with pipeline_lock(f"replace-{dataset_type}-{company_id}"):
        target_dir = ensure_company_dir(company_id, dataset_type)
        safe_name = file.filename.replace(" ", "_")
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        target_path = target_dir / f"{timestamp}_{safe_name}"

        with target_path.open("wb") as fh:
            fh.write(await file.read())

        # Normalize sales schema to canonical columns for downstream jobs
        if dataset_type == "sales":
            try:
                raw_df = pd.read_csv(target_path)
                normalized = normalize_sales_dataframe(raw_df)
                
                # Build OrderID from multiple possible columns
                order_id_col = None
                for col in ["OrderID", "order_id", "id", "ID", "Order_Id"]:
                    if col in raw_df.columns:
                        order_id_col = raw_df[col]
                        break
                if order_id_col is None:
                    order_id_col = range(1, len(normalized) + 1)
                
                canonical = pd.DataFrame({
                    "OrderID": order_id_col,
                    "OrderDate": normalized["__order_date"],
                    "TotalPrice": normalized["__total_price"],
                    "ProductID": normalized["__product"],
                    "City": normalized["__city"],
                })
                canonical.to_csv(target_path, index=False)
                row_count = len(canonical)
                logger.info(f"Normalized sales file (replace): {safe_name} -> {row_count} rows")
            except Exception as exc:  # noqa: BLE001
                logger.error("Failed to normalize replaced sales file %s: %s", target_path, exc)
                raise HTTPException(status_code=400, detail=f"CSV validation failed: {str(exc)}") from exc
        else:
            row_count = compute_row_count(target_path)

        archive_existing(company_id, dataset_type)
        record = insert_dataset(company_id, dataset_type, safe_name, target_path, row_count)

        trigger_pipeline(company_id, dataset_type, action="replace", file_path=target_path)
        return record


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
    company_id = require_company_id(request)
    current = get_dataset(dataset_id, company_id)
    if not current:
        raise HTTPException(status_code=404, detail="Dataset not found")

    dataset_type = current["dataset_type"]
    logger.info(f"DELETE request for dataset_id={dataset_id}, type={dataset_type}, company={company_id}")
    
    # Mark as deleted in database
    delete_dataset(dataset_id, company_id)

    # Delete the raw uploaded file
    try:
        Path(current["file_path"]).unlink(missing_ok=True)
        logger.info(f"Deleted raw file: {current['file_path']}")
    except Exception as exc:
        logger.warning("Could not delete raw file %s: %s", current["file_path"], exc)

    # CASCADING DELETION: Delete ALL derived ML outputs
    cascade_result = cascade_delete_derived_files(dataset_type)
    
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
    current = get_dataset(dataset_id, company_id)
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
    Internal function to read RFM segmentation data FRESH from disk.
    
    CRITICAL: Always reads from disk, NEVER from cached globals.
    This ensures that after data deletion or upload, fresh results are returned.
    
    Returns:
        SegmentationMetadata if data exists, Response(204) if not
    """
    company_id = request.headers.get("X-Company-ID")
    rfm_path = DATA_DIR / "rfm_table.csv"
    
    logger.info(f"[RFM API] Checking for RFM data at: {rfm_path}")

    if not rfm_path.exists():
        logger.info(f"[RFM API] rfm_table.csv not found - returning 204 (No Content)")
        return Response(status_code=204)

    try:
        # ALWAYS read fresh from disk
        rfm_df = pd.read_csv(rfm_path)
        logger.info(f"[RFM API] Loaded rfm_table.csv: {len(rfm_df)} rows")
    except Exception as exc:
        logger.error(f"[RFM API] Failed to read rfm_table.csv: {exc}")
        raise HTTPException(status_code=500, detail="Unable to read rfm_table.csv") from exc

    if rfm_df.empty:
        logger.info("[RFM API] rfm_table.csv is empty - returning 204 (No Content)")
        return Response(status_code=204)
    
    if "Segment" not in rfm_df.columns:
        logger.warning("[RFM API] rfm_table.csv missing 'Segment' column - returning 204")
        return Response(status_code=204)

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
    for segment_name in rfm_df["Segment"].unique():
        segment_data = rfm_df[rfm_df["Segment"] == segment_name]
        avg_recency = float(segment_data["Recency"].mean()) if "Recency" in segment_data.columns else None
        avg_frequency = float(segment_data["Frequency"].mean()) if "Frequency" in segment_data.columns else None
        avg_monetary = float(segment_data["Monetary"].mean()) if "Monetary" in segment_data.columns else None

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
    last_calculated = datetime.fromtimestamp(Path(rfm_path).stat().st_mtime).isoformat()
    
    logger.info(f"[RFM API] Returning {len(segment_stats)} segments for {len(rfm_df)} customers")

    return SegmentationMetadata(
        total_customers=len(rfm_df),
        segments=segment_stats,
        last_calculated=last_calculated,
        data_source="rfm_table.csv",
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
):
    """Get high-level KPIs (revenue, orders, AOV, top product, top city) with dynamic percentage changes."""
    company_id = request.headers.get("X-Company-ID")
    sales_df = normalize_sales_dataframe(load_active_sales_df(company_id))

    # Determine current and previous periods for comparison
    # If date range specified, use that; otherwise use last 30 days
    now = pd.Timestamp.now()
    
    if start_date and end_date:
        current_end = pd.to_datetime(end_date)
        current_start = pd.to_datetime(start_date)
    else:
        # Default: last 30 days as current period
        current_end = sales_df["__order_date"].max() if not sales_df.empty else now
        current_start = current_end - pd.Timedelta(days=30)
    
    # Calculate period length for previous period comparison
    period_length = (current_end - current_start).days
    previous_end = current_start - pd.Timedelta(days=1)
    previous_start = previous_end - pd.Timedelta(days=period_length)
    
    # Filter data for current period
    current_df = sales_df[
        (sales_df["__order_date"] >= current_start) & 
        (sales_df["__order_date"] <= current_end)
    ].copy()
    
    # Filter data for previous period
    previous_df = sales_df[
        (sales_df["__order_date"] >= previous_start) & 
        (sales_df["__order_date"] <= previous_end)
    ].copy()

    if current_df.empty:
        raise HTTPException(status_code=404, detail="No data found for the specified date range")

    # Calculate current period KPIs
    total_revenue = float(current_df["__total_price"].sum())
    total_orders = len(current_df)
    aov = total_revenue / total_orders if total_orders > 0 else 0.0

    # Calculate previous period KPIs for comparison
    prev_revenue = float(previous_df["__total_price"].sum()) if not previous_df.empty else 0.0
    prev_orders = len(previous_df) if not previous_df.empty else 0
    prev_aov = prev_revenue / prev_orders if prev_orders > 0 else 0.0
    
    # Calculate percentage changes
    # Returns None if previous period has no data or zero value (cannot calculate meaningful change)
    def calc_pct_change(current: float, previous: float) -> Optional[float]:
        if previous == 0 or previous_df.empty:
            return None
        return round(((current - previous) / previous) * 100, 2)
    
    revenue_change = calc_pct_change(total_revenue, prev_revenue)
    orders_change = calc_pct_change(float(total_orders), float(prev_orders)) if prev_orders > 0 else None
    aov_change = calc_pct_change(aov, prev_aov) if prev_aov > 0 else None

    top_product = "N/A"
    if current_df.get("__product") is not None and current_df["__product"].notna().any():
        top_product = str(
            current_df.groupby("__product")["__total_price"].sum().idxmax()
        )

    top_city = "N/A"
    if current_df.get("__city") is not None and current_df["__city"].notna().any():
        top_city = str(
            current_df.groupby("__city")["__total_price"].sum().idxmax()
        )

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


def load_forecast_data() -> Optional[pd.DataFrame]:
    """Load forecast data from multiple possible sources."""
    forecast_files = [
        DATA_DIR / "sales_forecast.csv",  # From 03_forecasting.py (Linear Regression)
        DATA_DIR / "sales_forecast_future.csv",
        BASE_DIR / "output" / "Acme Corp_forecast_prophet.csv",
        DATA_DIR / "forecast.csv",
    ]
    
    for fpath in forecast_files:
        if fpath.exists():
            try:
                fdf = pd.read_csv(fpath)
                # Normalize column names
                date_cols = ["MonthStart", "ds", "date", "Date", "OrderDate"]
                date_col = next((c for c in date_cols if c in fdf.columns), None)
                if date_col:
                    fdf = fdf.rename(columns={date_col: "MonthStart"})
                    fdf["MonthStart"] = pd.to_datetime(fdf["MonthStart"], errors="coerce")
                
                # Normalize forecast column
                forecast_cols = ["ForecastedSales", "yhat", "forecast", "predicted"]
                forecast_col = next((c for c in forecast_cols if c in fdf.columns), None)
                if forecast_col:
                    fdf = fdf.rename(columns={forecast_col: "ForecastedSales"})
                
                logger.info(f"[FORECAST] Loaded forecast from {fpath.name}: {len(fdf)} rows")
                return fdf
            except Exception as e:
                logger.warning(f"Failed to load forecast from {fpath}: {e}")
    
    return None


@app.get("/api/monthly-sales", response_model=List[MonthlySalesResponse], tags=["Analytics"])
def get_monthly_sales(
    request: Request,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
):
    """Get monthly sales actuals and forecasts merged together."""
    company_id = request.headers.get("X-Company-ID")
    
    try:
        sales_df = normalize_sales_dataframe(load_active_sales_df(company_id))
    except Exception as e:
        logger.warning(f"Failed to load active sales data for {company_id}: {e}")
        sales_df = None
    
    # Build combined result - actual + forecast
    monthly_dict = {}  # month -> {actual, forecast}
    
    # Step 1: Add actual monthly sales from company data
    if sales_df is not None and not sales_df.empty and "__order_date" in sales_df.columns and "__total_price" in sales_df.columns:
        try:
            monthly = sales_df.groupby(pd.Grouper(key="__order_date", freq="MS"))["__total_price"].sum().reset_index()
            
            for _, row in monthly.iterrows():
                month_key = row["__order_date"].strftime("%Y-%m")
                if month_key not in monthly_dict:
                    monthly_dict[month_key] = {"actual": None, "forecast": None}
                monthly_dict[month_key]["actual"] = float(row["__total_price"])
            
            logger.info(f"Computed {len(monthly)} monthly sales for {company_id}")
        except Exception as e:
            logger.warning(f"Failed to compute monthly sales: {e}")

    # Step 2: Add forecast data (load fresh from disk)
    local_forecast_df = load_forecast_data()
    if local_forecast_df is not None and not local_forecast_df.empty:
        try:
            for _, row in local_forecast_df.iterrows():
                if "MonthStart" not in local_forecast_df.columns:
                    continue
                month_key = row["MonthStart"].strftime("%Y-%m")
                if month_key not in monthly_dict:
                    monthly_dict[month_key] = {"actual": None, "forecast": None}
                # Only add forecast if it's positive (avoid anomalous negative values)
                forecast_val = row.get("ForecastedSales", row.get("yhat", 0))
                if forecast_val and forecast_val > 0:
                    monthly_dict[month_key]["forecast"] = float(forecast_val)
            
            logger.info(f"Added {len([m for m in monthly_dict.values() if m['forecast']])} forecast records")
        except Exception as e:
            logger.warning(f"Failed to add forecasts: {e}")

    # Step 3: Filter by date range if provided
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
        )
        for month, data in sorted(monthly_dict.items())
    ]

    if not result:
        logger.warning(f"No monthly sales data for {company_id} (no actuals or forecasts)")
        return []

    logger.info(f"Returning {len(result)} combined monthly sales records for {company_id}")
    return result


@app.get("/api/top-products", response_model=List[TopProductResponse], tags=["Analytics"])
def get_top_products(
    request: Request,
    limit: int = Query(5, ge=1, le=100),
):
    """Get top N products by revenue (limit: 1-100)."""
    company_id = request.headers.get("X-Company-ID")
    sales_df = normalize_sales_dataframe(load_active_sales_df(company_id))
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
            revenue=float(row["__total_price"]),
            order_count=int(row["order_count"]),
        )
        for _, row in top.iterrows()
    ]


@app.get("/api/top-cities", response_model=List[TopCityResponse], tags=["Analytics"])
def get_top_cities(
    request: Request,
    limit: int = Query(5, ge=1, le=50),
):
    """Get top N cities by revenue."""
    company_id = request.headers.get("X-Company-ID")
    sales_df = normalize_sales_dataframe(load_active_sales_df(company_id))
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
def get_sentiment_analysis():
    """
    Compute sentiment percentages and keywords from sentiment_results.csv.
    
    CRITICAL: Always reads FRESH from disk, never from cached globals.
    Returns 204 (No Content) when data is missing or empty.
    """
    sentiment_path = DATA_DIR / "sentiment_results.csv"
    
    logger.info(f"[SENTIMENT API] Checking for data at: {sentiment_path}")

    if not sentiment_path.exists():
        logger.info("[SENTIMENT API] sentiment_results.csv not found - returning 204")
        return Response(status_code=204)

    try:
        # ALWAYS read fresh from disk - use local variable, not global
        local_sentiment_df = pd.read_csv(sentiment_path)
        logger.info(f"[SENTIMENT API] Loaded sentiment_results.csv: {len(local_sentiment_df)} rows")
    except Exception as exc:
        logger.error(f"[SENTIMENT API] Failed to read sentiment_results.csv: {exc}")
        raise HTTPException(status_code=500, detail="Unable to read sentiment_results.csv") from exc

    if local_sentiment_df.empty:
        logger.info("[SENTIMENT API] sentiment_results.csv is empty - returning 204")
        return Response(status_code=204)

    sentiment_col = None
    for col in ["SentimentLabel", "Sentiment", "Label", "sentiment_label"]:
        if col in local_sentiment_df.columns:
            sentiment_col = col
            break

    if sentiment_col is None:
        logger.warning("[SENTIMENT API] Sentiment label column missing - returning 204")
        return Response(status_code=204)

    total = len(local_sentiment_df)
    sentiment_counts = local_sentiment_df[sentiment_col].value_counts().to_dict()

    sentiment_breakdown = [
        SentimentDetail(
            label=label,
            count=int(sentiment_counts.get(label, 0)),
            percentage=round((sentiment_counts.get(label, 0) / total) * 100, 2),
        )
        for label in ["Positive", "Neutral", "Negative"]
    ]

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

    last_analyzed = datetime.fromtimestamp(Path(sentiment_path).stat().st_mtime).isoformat()
    
    logger.info(f"[SENTIMENT API] Returning analysis for {total} reviews")

    return SentimentAnalysisResponse(
        total_reviews=total,
        sentiment_breakdown=sentiment_breakdown,
        top_keywords=top_keywords,
        last_analyzed=last_analyzed,
        data_source="sentiment_results.csv",
    )


@app.get("/api/sentiment", response_model=SentimentAnalysisResponse, tags=["Analytics"])
def get_sentiment_summary():
    """Alias of /api/sentiment-analysis with identical 204/real-data behavior."""
    return get_sentiment_analysis()


@app.get("/api/recommendations", response_model=List[RecommendationResponse], tags=["Analytics"])
def get_recommendations(limit: int = Query(10, ge=1, le=100)):
    """
    Return association rules from product_recommendations.csv.
    
    CRITICAL: Always reads FRESH from disk, never from cached globals.
    Returns 204 (No Content) when data is missing or empty.
    """
    recommendations_path = DATA_DIR / "product_recommendations.csv"
    
    logger.info(f"[RECOMMENDATIONS API] Checking for data at: {recommendations_path}")
    
    if not recommendations_path.exists():
        logger.info("[RECOMMENDATIONS API] product_recommendations.csv not found - returning 204")
        return Response(status_code=204)

    try:
        # ALWAYS read fresh from disk
        rules_df = pd.read_csv(recommendations_path)
        logger.info(f"[RECOMMENDATIONS API] Loaded product_recommendations.csv: {len(rules_df)} rows")
    except Exception as exc:
        logger.error(f"[RECOMMENDATIONS API] Failed to read product_recommendations.csv: {exc}")
        raise HTTPException(status_code=500, detail="Unable to read product_recommendations.csv") from exc

    if rules_df.empty:
        logger.info("[RECOMMENDATIONS API] product_recommendations.csv is empty - returning 204")
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
):
    """Get raw transaction data (paginated)."""
    company_id = request.headers.get("X-Company-ID")
    sales_df = load_active_sales_df(company_id)
    return sales_df.head(limit).to_dict(orient="records")


@app.get("/api/summary", tags=["Analytics"])
def get_summary():
    """Get a complete summary of all available data."""
    summary = {
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
# NEW: Business Alerts API (Proactive Intelligence)
# =============================================================================

@app.get("/api/alerts", tags=["Intelligence"])
def get_business_alerts(
    request: Request,
    refresh: bool = Query(False, description="Force regeneration of alerts")
):
    """
    Get proactive business alerts for the company.
    
    Alerts are generated from:
    - Sales patterns (revenue decline, anomalies)
    - Customer behavior (churn risk, VIP inactivity)
    - Sentiment analysis (aspect complaints)
    - Forecasts (predicted shortfall)
    
    This endpoint transforms the dashboard from passive to proactive.
    """
    company_id = request.headers.get("X-Company-ID", "Acme Corp")
    
    # Check for cached alerts
    alerts_path = OUTPUT_DIR / f"{company_id}_alerts.json"
    
    if alerts_path.exists() and not refresh:
        try:
            with open(alerts_path, "r", encoding="utf-8") as f:
                alerts_data = json.load(f)
            logger.info(f"[ALERTS API] Returning cached alerts for {company_id}")
            return alerts_data
        except Exception as e:
            logger.warning(f"Failed to load cached alerts: {e}")
    
    # Generate fresh alerts
    try:
        # Import and run alert engine
        sys.path.insert(0, str(BASE_DIR / "src"))
        from alert_engine import run_alert_engine  # type: ignore
        
        alerts_data = run_alert_engine(company_id)
        logger.info(f"[ALERTS API] Generated {alerts_data.get('total_alerts', 0)} alerts for {company_id}")
        return alerts_data
        
    except ImportError:
        # Fallback: return empty alerts structure
        logger.warning("Alert engine not available, returning empty alerts")
        return {
            "company": company_id,
            "generated_at": datetime.now().isoformat(),
            "total_alerts": 0,
            "alerts": [],
            "by_severity": {"critical": 0, "warning": 0, "info": 0},
            "by_category": {"sales": 0, "customer": 0, "sentiment": 0, "forecast": 0}
        }
    except Exception as e:
        logger.error(f"Failed to generate alerts: {e}")
        raise HTTPException(status_code=500, detail=f"Alert generation failed: {str(e)}")


@app.post("/api/alerts/generate", tags=["Intelligence"])
def generate_alerts(request: Request):
    """Force regeneration of all business alerts."""
    company_id = request.headers.get("X-Company-ID", "Acme Corp")
    
    try:
        sys.path.insert(0, str(BASE_DIR / "src"))
        from alert_engine import run_alert_engine  # type: ignore
        
        alerts_data = run_alert_engine(company_id)
        return {
            "status": "success",
            "message": f"Generated {alerts_data.get('total_alerts', 0)} alerts",
            "alerts": alerts_data
        }
    except Exception as e:
        logger.error(f"Alert generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# NEW: Advanced Sentiment Analysis API (Arabic-First)
# =============================================================================

@app.get("/api/advanced-sentiment", tags=["Intelligence"])
def get_advanced_sentiment(
    request: Request,
    refresh: bool = Query(False, description="Force reanalysis of reviews")
):
    """
    Get advanced aspect-based sentiment analysis.
    
    Features:
    - Arabic language support
    - Aspect extraction (quality, price, delivery, service, packaging)
    - Per-aspect sentiment scoring
    - Actionable recommendations
    
    This is the KILLER FEATURE for MENA market differentiation.
    """
    company_id = request.headers.get("X-Company-ID", "Acme Corp")
    
    # Check for cached analysis
    sentiment_path = OUTPUT_DIR / f"{company_id}_advanced_sentiment.json"
    
    if sentiment_path.exists() and not refresh:
        try:
            with open(sentiment_path, "r", encoding="utf-8") as f:
                sentiment_data = json.load(f)
            logger.info(f"[ADV SENTIMENT API] Returning cached analysis for {company_id}")
            return sentiment_data
        except Exception as e:
            logger.warning(f"Failed to load cached sentiment: {e}")
    
    # Generate fresh analysis
    try:
        sys.path.insert(0, str(BASE_DIR / "src"))
        from advanced_sentiment import run_advanced_sentiment_analysis  # type: ignore
        
        sentiment_data = run_advanced_sentiment_analysis(company_id)
        logger.info(f"[ADV SENTIMENT API] Analyzed {sentiment_data.get('total_reviews', 0)} reviews for {company_id}")
        return sentiment_data
        
    except ImportError:
        logger.warning("Advanced sentiment module not available")
        return {
            "company": company_id,
            "error": "Advanced sentiment analysis module not available",
            "total_reviews": 0,
            "aspect_analysis": {},
            "alerts": [],
            "recommendations": []
        }
    except Exception as e:
        logger.error(f"Sentiment analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# NEW: Customer Lifetime Value (CLV) API
# =============================================================================

@app.get("/api/clv", tags=["Intelligence"])
def get_customer_clv(
    request: Request,
    refresh: bool = Query(False, description="Force recalculation of CLV")
):
    """
    Get Customer Lifetime Value analysis.
    
    Provides:
    - Historical and Predictive CLV per customer
    - CLV-based segmentation (Platinum, Gold, Silver, Bronze)
    - Acquisition cost recommendations
    - Top customer identification
    """
    company_id = request.headers.get("X-Company-ID", "Acme Corp")
    
    # Check for cached CLV data
    clv_path = OUTPUT_DIR / f"{company_id}_clv_insights.json"
    
    if clv_path.exists() and not refresh:
        try:
            with open(clv_path, "r", encoding="utf-8") as f:
                clv_data = json.load(f)
            logger.info(f"[CLV API] Returning cached CLV data for {company_id}")
            return clv_data
        except Exception as e:
            logger.warning(f"Failed to load cached CLV: {e}")
    
    # Calculate fresh CLV
    try:
        sys.path.insert(0, str(BASE_DIR / "src"))
        from clv_calculation import run_clv_analysis  # type: ignore
        
        clv_data = run_clv_analysis(company_id)
        logger.info(f"[CLV API] Calculated CLV for {company_id}")
        return clv_data
        
    except ImportError:
        logger.warning("CLV calculation module not available")
        return {
            "company": company_id,
            "error": "CLV calculation module not available",
            "insights": {"summary": {}, "segments": {}, "recommendations": []},
            "top_customers": []
        }
    except Exception as e:
        logger.error(f"CLV calculation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/clv/segments", tags=["Intelligence"])
def get_clv_segments(request: Request):
    """Get CLV segment breakdown."""
    company_id = request.headers.get("X-Company-ID", "Acme Corp")
    
    clv_csv_path = OUTPUT_DIR / f"{company_id}_clv_analysis.csv"
    
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
    - Key alerts requiring attention
    - Sentiment insights
    - CLV highlights
    - Actionable recommendations
    
    Designed for the "proactive intelligence" user experience.
    """
    company_id = request.headers.get("X-Company-ID", "Acme Corp")
    
    summary = {
        "company": company_id,
        "generated_at": datetime.now().isoformat(),
        "alerts": [],
        "sentiment_highlights": {},
        "clv_highlights": {},
        "top_recommendations": []
    }
    
    # Load alerts
    alerts_path = OUTPUT_DIR / f"{company_id}_alerts.json"
    if alerts_path.exists():
        try:
            with open(alerts_path, "r", encoding="utf-8") as f:
                alerts_data = json.load(f)
            # Get top 5 alerts
            summary["alerts"] = alerts_data.get("alerts", [])[:5]
            summary["alert_counts"] = alerts_data.get("by_severity", {})
        except Exception:
            pass
    
    # Load sentiment highlights
    sentiment_path = OUTPUT_DIR / f"{company_id}_advanced_sentiment.json"
    if sentiment_path.exists():
        try:
            with open(sentiment_path, "r", encoding="utf-8") as f:
                sentiment_data = json.load(f)
            summary["sentiment_highlights"] = {
                "total_reviews": sentiment_data.get("total_reviews", 0),
                "positive_rate": sentiment_data.get("sentiment_distribution", {}).get("positive_rate", 0),
                "arabic_percentage": sentiment_data.get("language_distribution", {}).get("arabic_percentage", 0),
                "top_issue": None
            }
            # Find top issue
            aspects = sentiment_data.get("aspect_analysis", {})
            worst_aspect = max(aspects.items(), key=lambda x: x[1].get("negative_pct", 0), default=(None, {}))
            if worst_aspect[0] and worst_aspect[1].get("negative_pct", 0) > 30:
                summary["sentiment_highlights"]["top_issue"] = {
                    "aspect": worst_aspect[0],
                    "negative_pct": worst_aspect[1].get("negative_pct", 0),
                    "icon": worst_aspect[1].get("icon", "⚠️")
                }
        except Exception:
            pass
    
    # Load CLV highlights
    clv_path = OUTPUT_DIR / f"{company_id}_clv_insights.json"
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
    
    # From alerts
    for alert in summary.get("alerts", []):
        if alert.get("severity") in ["critical", "warning"]:
            all_recommendations.append({
                "source": "alert",
                "priority": "high" if alert.get("severity") == "critical" else "medium",
                "title": alert.get("title", ""),
                "action": alert.get("recommendation", ""),
                "icon": alert.get("icon", "⚠️")
            })
    
    # From sentiment
    if sentiment_path.exists():
        try:
            with open(sentiment_path, "r", encoding="utf-8") as f:
                sentiment_data = json.load(f)
            for rec in sentiment_data.get("recommendations", [])[:2]:
                all_recommendations.append({
                    "source": "sentiment",
                    "priority": "medium",
                    "title": rec.get("message_en", ""),
                    "action": rec.get("action", ""),
                    "icon": rec.get("icon", "💡")
                })
        except Exception:
            pass
    
    summary["top_recommendations"] = all_recommendations[:5]
    
    return summary


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
