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
from datetime import datetime
from functools import lru_cache

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query, Request, UploadFile, File, Form, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel

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
MODEL_PATH = BASE_DIR / "src" / "ml_lifecycle" / "model_registry" / "sales_forecast_model.pkl"
DB_PATH = DATA_DIR / "datasets.db"

DATA_DIR.mkdir(exist_ok=True)

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
REVENUE_CANDIDATES = ["TotalPrice", "Sales_Amount", "SalesAmount", "Revenue", "Sales"]
PRODUCT_CANDIDATES = ["ProductID", "Product_ID", "Product", "SKU"]
CITY_CANDIDATES = ["City", "city", "Region", "region", "Market"]


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
# Pydantic Models
# ============================================================================


class KPIResponse(BaseModel):
    total_revenue: float
    total_orders: int
    average_order_value: float
    top_product: str
    top_city: str


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


@lru_cache(maxsize=1)
def get_cached_dataframes():
    """Cache loaded dataframes to avoid repeated file reads."""
    return {
        'df': df,
        'forecast_df': forecast_df,
        'sentiment_df': sentiment_df,
        'recommendation_df': recommendation_df
    }

@app.on_event("startup")
def load_data():
    """Load all data at startup."""
    global df, forecast_df, sentiment_df, recommendation_df, model, data_last_modified
    
    data_last_modified = datetime.utcnow()
    
    try:
        df = pd.read_csv(DATA_DIR / "cleaned_dataset.csv")
        df["OrderDate"] = pd.to_datetime(df["OrderDate"], errors="coerce")
        # Data quality check
        if df.empty or df["OrderDate"].isna().all():
            logger.error("Dataset is empty or all dates are invalid")
            df = None
        else:
            logger.info(f"Loaded {len(df)} sales records")
    except Exception as e:
        logger.warning(f"Could not load cleaned_dataset.csv: {e}")
        df = None

    try:
        forecast_df = pd.read_csv(DATA_DIR / "sales_forecast_future.csv")
        forecast_df["MonthStart"] = pd.to_datetime(forecast_df["MonthStart"], errors="coerce")
        logger.info(f"Loaded {len(forecast_df)} forecast records")
    except Exception as e:
        logger.warning(f"Could not load sales_forecast_future.csv: {e}")
        forecast_df = None

    try:
        sentiment_df = pd.read_csv(DATA_DIR / "sentiment_results.csv")
        logger.info(f"Loaded {len(sentiment_df)} sentiment records")
    except Exception as e:
        logger.warning(f"Could not load sentiment_results.csv: {e}")
        sentiment_df = None

    try:
        recommendation_df = pd.read_csv(DATA_DIR / "product_recommendations.csv")
        logger.info(f"Loaded {len(recommendation_df)} recommendation rules")
    except Exception as e:
        logger.warning(f"Could not load product_recommendations.csv: {e}")
        recommendation_df = None

    try:
        if MODEL_PATH.exists():
            model = joblib.load(MODEL_PATH)
            logger.info("Loaded forecasting model")
        else:
            logger.warning(f"Model not found at {MODEL_PATH}")
            model = None
    except Exception as e:
        logger.warning(f"Could not load model: {e}")
        model = None


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
    uploaded_at = datetime.utcnow().isoformat()
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
    
    ENTERPRISE BEHAVIOR:
    - Deleting ANY dataset triggers full cascade deletion
    - No stale analytics should remain on disk
    - APIs will return 204 until new data is uploaded and processed
    
    Args:
        dataset_type: Type of dataset being deleted (sales, customers, reviews)
        
    Returns:
        dict with deleted_files list and any errors
    """
    deleted_files = []
    errors = []
    
    logger.info(f"=" * 60)
    logger.info(f"CASCADING DELETION TRIGGERED for dataset_type={dataset_type}")
    logger.info(f"=" * 60)
    
    # Delete ALL derived ML outputs
    for filename in DERIVED_ML_FILES:
        file_path = DATA_DIR / filename
        try:
            if file_path.exists():
                file_path.unlink()
                deleted_files.append(filename)
                logger.info(f"[CASCADE DELETE] Deleted derived file: {filename}")
            else:
                logger.info(f"[CASCADE DELETE] File not found (already clean): {filename}")
        except Exception as e:
            error_msg = f"Failed to delete {filename}: {str(e)}"
            errors.append(error_msg)
            logger.error(f"[CASCADE DELETE] {error_msg}")
    
    # Also delete the canonical input file for this dataset type
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
                logger.info(f"[CASCADE DELETE] Deleted canonical input: {canonical_file}")
        except Exception as e:
            error_msg = f"Failed to delete canonical {canonical_file}: {str(e)}"
            errors.append(error_msg)
            logger.error(f"[CASCADE DELETE] {error_msg}")
    
    # Reset global DataFrames to None (no stale in-memory data)
    global df, forecast_df, sentiment_df, recommendation_df
    df = None
    forecast_df = None
    sentiment_df = None
    recommendation_df = None
    logger.info("[CASCADE DELETE] Reset all global DataFrames to None")
    
    logger.info(f"[CASCADE DELETE] Completed: {len(deleted_files)} files deleted, {len(errors)} errors")
    logger.info(f"=" * 60)
    
    return {
        "deleted_files": deleted_files,
        "errors": errors,
        "total_deleted": len(deleted_files),
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
    1. Copy uploaded file to canonical location (data/sales.csv)
    2. Run 01_eda.py (creates merged_data.csv)
    3. Run 02_cleaning_features.py (creates cleaned_dataset.csv)
    4. Run 04_rfm.py (creates rfm_table.csv)
    5. Run 05_recommendation.py (creates product_recommendations.csv)
    
    Returns:
        True if pipeline completed successfully, False otherwise
    """
    import shutil
    import subprocess
    
    try:
        # Step 1: Copy uploaded file to canonical location for ML scripts
        canonical_sales = DATA_DIR / "sales.csv"
        logger.info(f"Copying {uploaded_file} -> {canonical_sales}")
        shutil.copy2(uploaded_file, canonical_sales)
        
        # Step 2: Run EDA (Phase 1) - creates merged_data.csv
        logger.info("Running Phase 1: EDA...")
        result = subprocess.run(
            [sys.executable, str(BASE_DIR / "src" / "01_eda.py")],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            timeout=120
        )
        if result.returncode != 0:
            logger.error(f"Phase 1 EDA failed: {result.stderr}")
            return False
        logger.info("Phase 1 EDA completed successfully")
        
        # Step 3: Run Cleaning & Features (Phase 2) - creates cleaned_dataset.csv
        logger.info("Running Phase 2: Cleaning & Feature Engineering...")
        result = subprocess.run(
            [sys.executable, str(BASE_DIR / "src" / "02_cleaning_features.py")],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            timeout=120
        )
        if result.returncode != 0:
            logger.error(f"Phase 2 Cleaning failed: {result.stderr}")
            return False
        logger.info("Phase 2 Cleaning completed successfully")
        
        # Step 4: Run RFM Segmentation (Phase 4) - creates rfm_table.csv
        logger.info("Running Phase 4: RFM Segmentation...")
        result = subprocess.run(
            [sys.executable, str(BASE_DIR / "src" / "04_rfm.py")],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            timeout=120
        )
        # RFM may exit 0 with warning if CustomerID missing - that's OK
        if result.returncode != 0:
            logger.warning(f"Phase 4 RFM exited with code {result.returncode}: {result.stderr}")
        else:
            logger.info("Phase 4 RFM completed successfully")
        
        # Step 5: Run Recommendations (Phase 5) - creates product_recommendations.csv
        logger.info("Running Phase 5: Market Basket Analysis...")
        result = subprocess.run(
            [sys.executable, str(BASE_DIR / "src" / "05_recommendation.py")],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            timeout=180
        )
        if result.returncode != 0:
            logger.warning(f"Phase 5 Recommendations exited with code {result.returncode}: {result.stderr}")
        else:
            logger.info("Phase 5 Recommendations completed successfully")
        
        # Reload global DataFrames
        global df, recommendation_df
        try:
            df = pd.read_csv(DATA_DIR / "cleaned_dataset.csv")
            logger.info(f"Reloaded cleaned_dataset.csv: {len(df)} rows")
        except Exception as e:
            logger.warning(f"Could not reload cleaned_dataset: {e}")
        
        try:
            recommendation_df = pd.read_csv(DATA_DIR / "product_recommendations.csv")
            logger.info(f"Reloaded product_recommendations.csv: {len(recommendation_df)} rows")
        except Exception as e:
            logger.warning(f"Could not reload recommendations: {e}")
            recommendation_df = None
        
        return True
        
    except Exception as e:
        logger.error(f"Full sales pipeline failed: {e}")
        return False


def run_sentiment_pipeline(uploaded_file: Path) -> bool:
    """
    Run sentiment analysis pipeline for reviews data:
    1. Copy uploaded file to canonical location (data/customer_reviews.csv)
    2. Run 06_sentiment.py (creates sentiment_results.csv)
    
    Returns:
        True if pipeline completed successfully, False otherwise
    """
    import shutil
    import subprocess
    
    try:
        # Step 1: Copy uploaded file to canonical location for ML scripts
        canonical_reviews = DATA_DIR / "customer_reviews.csv"
        logger.info(f"Copying {uploaded_file} -> {canonical_reviews}")
        shutil.copy2(uploaded_file, canonical_reviews)
        
        # Step 2: Run Sentiment Analysis (Phase 6)
        logger.info("Running Phase 6: Sentiment Analysis...")
        result = subprocess.run(
            [sys.executable, str(BASE_DIR / "src" / "06_sentiment.py")],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            timeout=300  # NLP can take longer
        )
        if result.returncode != 0:
            logger.error(f"Phase 6 Sentiment failed: {result.stderr}")
            return False
        logger.info("Phase 6 Sentiment completed successfully")
        
        # Reload global DataFrame
        global sentiment_df
        try:
            sentiment_df = pd.read_csv(DATA_DIR / "sentiment_results.csv")
            logger.info(f"Reloaded sentiment_results.csv: {len(sentiment_df)} rows")
        except Exception as e:
            logger.warning(f"Could not reload sentiment results: {e}")
            sentiment_df = None
        
        return True
        
    except Exception as e:
        logger.error(f"Sentiment pipeline failed: {e}")
        return False


def trigger_pipeline(company_id: str, dataset_type: str, action: str, file_path: Optional[Path] = None) -> None:
    """
    Hook for automation workflows - triggers COMPLETE ML pipelines when data is uploaded.
    
    Pipeline Flow:
    - Sales data upload → EDA → Cleaning → RFM → Recommendations
    - Reviews data upload → Sentiment Analysis
    """
    logger.info(
        "Pipeline trigger | company=%s dataset=%s action=%s file=%s",
        company_id,
        dataset_type,
        action,
        file_path,
    )
    
    # Trigger FULL sales pipeline (EDA → Cleaning → RFM → Recommendations)
    if dataset_type == "sales" and file_path and action in ["upload", "replace"]:
        logger.info(f"Triggering FULL Sales Pipeline for {file_path}")
        try:
            success = run_full_sales_pipeline(file_path)
            if success:
                logger.info("Full Sales Pipeline completed - all ML outputs generated")
            else:
                logger.warning("Full Sales Pipeline had issues - check logs for details")
        except Exception as e:
            logger.error(f"Error running full sales pipeline: {e}")
    
    # Trigger sentiment pipeline for reviews data
    if dataset_type == "reviews" and file_path and action in ["upload", "replace"]:
        logger.info(f"Triggering Sentiment Analysis Pipeline for {file_path}")
        try:
            success = run_sentiment_pipeline(file_path)
            if success:
                logger.info("Sentiment Analysis Pipeline completed - sentiment results generated")
            else:
                logger.warning("Sentiment Analysis Pipeline failed - check logs for details")
        except Exception as e:
            logger.error(f"Error running sentiment pipeline: {e}")
    
    # Handle customers upload - copy to canonical location and re-run pipeline if sales exists
    if dataset_type == "customers" and file_path and action in ["upload", "replace"]:
        import shutil
        canonical_customers = DATA_DIR / "customers.csv"
        logger.info(f"Copying customers file to {canonical_customers}")
        try:
            shutil.copy2(file_path, canonical_customers)
            logger.info("Customers file copied to canonical location")
            
            # If sales.csv exists, re-run the pipeline to merge with new customers
            canonical_sales = DATA_DIR / "sales.csv"
            if canonical_sales.exists():
                logger.info("Sales data exists - re-running full pipeline to merge with customers")
                success = run_full_sales_pipeline(canonical_sales)
                if success:
                    logger.info("Pipeline re-run completed with new customer data")
                else:
                    logger.warning("Pipeline re-run had issues - check logs")
        except Exception as e:
            logger.error(f"Error handling customers upload: {e}")


def load_active_sales_df(company_id: Optional[str] = None) -> pd.DataFrame:
    """Load the active sales dataset for a company; fallback to global df."""
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

    target_dir = ensure_company_dir(company_id, dataset_type)
    safe_name = file.filename.replace(" ", "_")
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
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
    target_dir = ensure_company_dir(company_id, dataset_type)
    safe_name = file.filename.replace(" ", "_")
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
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
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "sales_data": "available" if df is not None else "unavailable",
            "forecast_data": "available" if forecast_df is not None else "unavailable",
            "sentiment_data": "available" if sentiment_df is not None else "unavailable",
            "recommendation_data": "available" if recommendation_df is not None else "unavailable",
            "ml_model": "loaded" if model is not None else "not_loaded"
        },
        "version": "1.0.0"
    }




@app.get("/api/segmentation", response_model=SegmentationMetadata, tags=["Analytics"])
def get_segmentation(request: Request):
    """Return RFM segment counts from rfm_table.csv. 204 when missing/empty."""
    _ = request.headers.get("X-Company-ID")
    rfm_path = DATA_DIR / "rfm_table.csv"

    if not rfm_path.exists():
        logger.warning("RFM table not found; returning 204")
        return Response(status_code=204)

    try:
        rfm_df = pd.read_csv(rfm_path)
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to read RFM table: %s", exc)
        raise HTTPException(status_code=500, detail="Unable to read rfm_table.csv") from exc

    if rfm_df.empty or "Segment" not in rfm_df.columns:
        logger.warning("RFM table empty or missing Segment column; returning 204")
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

    return SegmentationMetadata(
        total_customers=len(rfm_df),
        segments=segment_stats,
        last_calculated=last_calculated,
        data_source="rfm_table.csv",
        model_version="RFM",
    )


@app.get("/api/kpis", response_model=KPIResponse, tags=["Analytics"])
async def get_kpis(
    request: Request,
    start_date: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    end_date: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
):
    """Get high-level KPIs (revenue, orders, AOV, top product, top city)."""
    company_id = request.headers.get("X-Company-ID")
    sales_df = normalize_sales_dataframe(load_active_sales_df(company_id))

    # Validate and apply date filters on normalized column
    filtered_df = sales_df.copy()
    try:
        if start_date:
            start = pd.to_datetime(start_date)
            filtered_df = filtered_df[filtered_df["__order_date"] >= start]
        if end_date:
            end = pd.to_datetime(end_date)
            filtered_df = filtered_df[filtered_df["__order_date"] <= end]
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Invalid date format: {exc}") from exc

    if filtered_df.empty:
        raise HTTPException(status_code=404, detail="No data found for the specified date range")

    total_revenue = float(filtered_df["__total_price"].sum())
    total_orders = len(filtered_df)
    aov = total_revenue / total_orders if total_orders > 0 else 0.0

    top_product = "N/A"
    if filtered_df.get("__product") is not None and filtered_df["__product"].notna().any():
        top_product = str(
            filtered_df.groupby("__product")["__total_price"].sum().idxmax()
        )

    top_city = "N/A"
    if filtered_df.get("__city") is not None and filtered_df["__city"].notna().any():
        top_city = str(
            filtered_df.groupby("__city")["__total_price"].sum().idxmax()
        )

    return KPIResponse(
        total_revenue=total_revenue,
        total_orders=total_orders,
        average_order_value=aov,
        top_product=top_product,
        top_city=top_city,
    )


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

    # Step 2: Add forecast data (blend with actuals or standalone)
    if forecast_df is not None and not forecast_df.empty:
        try:
            for _, row in forecast_df.iterrows():
                month_key = row["MonthStart"].strftime("%Y-%m")
                if month_key not in monthly_dict:
                    monthly_dict[month_key] = {"actual": None, "forecast": None}
                # Only add forecast if it's positive (avoid anomalous negative values)
                if row["ForecastedSales"] > 0:
                    monthly_dict[month_key]["forecast"] = float(row["ForecastedSales"])
            
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
    """Compute sentiment percentages and keywords from sentiment_results.csv. 204 when missing/empty."""
    sentiment_path = DATA_DIR / "sentiment_results.csv"

    if not sentiment_path.exists():
        logger.warning("Sentiment file missing; returning 204")
        return Response(status_code=204)

    try:
        sentiment_df = pd.read_csv(sentiment_path)
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to read sentiment_results.csv: %s", exc)
        raise HTTPException(status_code=500, detail="Unable to read sentiment_results.csv") from exc

    if sentiment_df.empty:
        logger.warning("Sentiment file empty; returning 204")
        return Response(status_code=204)

    sentiment_col = None
    for col in ["SentimentLabel", "Sentiment", "Label", "sentiment_label"]:
        if col in sentiment_df.columns:
            sentiment_col = col
            break

    if sentiment_col is None:
        logger.warning("Sentiment label column missing; returning 204")
        return Response(status_code=204)

    total = len(sentiment_df)
    sentiment_counts = sentiment_df[sentiment_col].value_counts().to_dict()

    sentiment_breakdown = [
        SentimentDetail(
            label=label,
            count=int(sentiment_counts.get(label, 0)),
            percentage=round((sentiment_counts.get(label, 0) / total) * 100, 2),
        )
        for label in ["Positive", "Neutral", "Negative"]
    ]

    text_col = None
    if "CleanedText" in sentiment_df.columns:
        text_col = "CleanedText"
    elif "ReviewText" in sentiment_df.columns:
        text_col = "ReviewText"

    top_keywords: List[str] = []
    if text_col:
        positive_reviews = sentiment_df[sentiment_df[sentiment_col] == "Positive"]
        if not positive_reviews.empty:
            text = " ".join(positive_reviews[text_col].astype(str).tolist()).lower()
            stop_words = {"the", "a", "and", "or", "is", "it", "to", "but", "i", "this", "that", "of", "in", "for"}
            words = [w for w in text.split() if len(w) > 3 and w not in stop_words]
            from collections import Counter

            word_freq = Counter(words)
            top_keywords = [word for word, _ in word_freq.most_common(5)]

    last_analyzed = datetime.fromtimestamp(Path(sentiment_path).stat().st_mtime).isoformat()

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
    """Return association rules from product_recommendations.csv. 204 when missing/empty."""

    recommendations_path = DATA_DIR / "product_recommendations.csv"
    if not recommendations_path.exists():
        logger.warning("product_recommendations.csv missing; returning 204")
        return Response(status_code=204)

    try:
        rules_df = pd.read_csv(recommendations_path)
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to read product_recommendations.csv: %s", exc)
        raise HTTPException(status_code=500, detail="Unable to read product_recommendations.csv") from exc

    if rules_df.empty:
        logger.warning("Recommendation CSV empty; returning 204")
        return Response(status_code=204)

    if "Confidence" in rules_df.columns:
        rules_df = rules_df[rules_df["Confidence"] > 0]
    if "Lift" in rules_df.columns:
        rules_df = rules_df.sort_values("Lift", ascending=False)

    rules_df = rules_df.head(limit)
    if rules_df.empty:
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
        "timestamp": datetime.utcnow().isoformat(),
    }
    return summary


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
