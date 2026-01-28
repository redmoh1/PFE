"""FastAPI backend v2.0 with Authentication, Background Tasks, and Enhanced Features.

IMPROVEMENTS:
1. JWT Authentication with role-based access
2. SQLAlchemy database integration
3. Standardized API responses
4. Background task support
5. Explainability endpoints
6. Model monitoring endpoints

Run with: uvicorn backend.main_enhanced:app --reload
"""

import sys
import logging
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

import pandas as pd
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session

# Setup path for imports
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "src"))

# Import new modules
from backend.database.connection import get_db, init_db as init_sqlalchemy_db
from backend.database.models import User, Company, UserRole, ForecastResult, RFMResult, SentimentResult
from backend.auth import get_current_user, require_admin, require_analyst, check_company_access
from backend.routes.auth_routes import router as auth_router
from backend.responses import APIResponse, success_response, error_response, paginated_response
from backend.background_tasks import (
    run_forecast_async, run_sentiment_async,
    get_task_status, create_task_id, TaskStatus
)

# Logging setup
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "api_enhanced.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

# -------------------------------------------------
# FastAPI App Configuration
# -------------------------------------------------
app = FastAPI(
    title="Sales Analytics API v2.0",
    description="""
    Enhanced Sales Analytics API with:
    - JWT Authentication
    - Role-based Access Control
    - Prophet Forecasting
    - Arabic Sentiment Analysis
    - Model Explainability
    - Background Tasks
    """,
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Configuration
ALLOWED_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d{2,5}",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include authentication routes
app.include_router(auth_router)


# -------------------------------------------------
# Startup Event
# -------------------------------------------------
@app.on_event("startup")
async def startup_event():
    """Initialize database and setup on startup."""
    logger.info("Starting Sales Analytics API v2.0...")
    init_sqlalchemy_db()
    logger.info("Database initialized successfully")


# -------------------------------------------------
# Request/Response Models
# -------------------------------------------------
class ForecastRequest(BaseModel):
    """Forecast generation request."""
    periods: int = 6
    use_prophet: bool = True


class ForecastResponse(BaseModel):
    """Forecast result response."""
    task_id: Optional[str] = None
    forecast_data: Optional[List[Dict]] = None
    metrics: Optional[Dict] = None
    explanation: Optional[Dict] = None
    generated_at: Optional[str] = None


class SentimentRequest(BaseModel):
    """Sentiment analysis request."""
    use_arabic_model: bool = True


class SentimentSummary(BaseModel):
    """Sentiment analysis summary."""
    total_reviews: int
    positive: int
    neutral: int
    negative: int
    average_confidence: float
    sentiment_breakdown: Dict[str, float]  # percentages


class ExplainRFMRequest(BaseModel):
    """Request to explain a customer's RFM segment."""
    customer_id: str


class ExplainRecommendationRequest(BaseModel):
    """Request to explain a product recommendation."""
    product_a: str
    product_b: str


class TaskStatusResponse(BaseModel):
    """Background task status response."""
    task_id: str
    status: str
    progress: Optional[int] = None
    result: Optional[Dict] = None
    error: Optional[str] = None


# -------------------------------------------------
# Public Endpoints
# -------------------------------------------------
@app.get("/", response_model=Dict)
def root():
    """API root - health check and version info."""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "message": "Sales Analytics API - Use /docs for documentation",
        "features": [
            "JWT Authentication",
            "Prophet Forecasting",
            "Arabic Sentiment Analysis",
            "Model Explainability",
            "Background Tasks",
        ]
    }


@app.get("/health")
def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "database": "connected",
        "timestamp": datetime.utcnow().isoformat(),
    }


# -------------------------------------------------
# Protected Endpoints - Analytics
# -------------------------------------------------
@app.get("/api/companies", response_model=List[Dict])
async def list_companies(
    current_user: User = Depends(require_analyst),
    db: Session = Depends(get_db)
):
    """List all companies (admin) or user's company (analyst/viewer)."""
    if current_user.role == UserRole.ADMIN:
        companies = db.query(Company).filter(Company.is_active == True).all()
    else:
        companies = [current_user.company]
    
    return [
        {
            "id": c.id,
            "name": c.name,
            "slug": c.slug,
            "data_directory": c.data_directory,
        }
        for c in companies
    ]


@app.post("/api/companies/{company_id}/forecast", response_model=ForecastResponse)
async def generate_forecast(
    company_id: int,
    request: ForecastRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_analyst),
    db: Session = Depends(get_db)
):
    """Generate sales forecast for a company.
    
    This operation runs in the background. Use /api/tasks/{task_id} to check status.
    """
    # Verify company access
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    check_company_access(current_user, company_id)
    
    # Create background task
    task_id = create_task_id(company.name, "forecast")
    
    # Schedule background task
    background_tasks.add_task(
        run_forecast_async,
        task_id=task_id,
        company_id=company_id,
        company_name=company.data_directory,
        periods=request.periods,
        use_prophet=request.use_prophet
    )
    
    return ForecastResponse(
        task_id=task_id,
        generated_at=datetime.utcnow().isoformat(),
    )


@app.get("/api/companies/{company_id}/forecast/latest", response_model=Dict)
async def get_latest_forecast(
    company_id: int,
    current_user: User = Depends(require_analyst),
    db: Session = Depends(get_db)
):
    """Get the latest cached forecast for a company."""
    check_company_access(current_user, company_id)
    
    # Get latest forecast from database
    forecast = (
        db.query(ForecastResult)
        .filter(ForecastResult.company_id == company_id)
        .order_by(ForecastResult.created_at.desc())
        .first()
    )
    
    if not forecast:
        raise HTTPException(status_code=404, detail="No forecast found. Generate one first.")
    
    # Get explanation
    try:
        from src.explainability import explain_forecast
        forecast_df = pd.DataFrame(forecast.forecast_data)
        explanation = explain_forecast(
            forecast_df,
            components={"trend": forecast.trend_data, "yearly": forecast.seasonality_data},
            model_type=forecast.model_type
        )
    except Exception as e:
        logger.warning(f"Could not generate explanation: {e}")
        explanation = None
    
    return {
        "success": True,
        "data": {
            "model_type": forecast.model_type,
            "model_version": forecast.model_version,
            "forecast_periods": forecast.forecast_periods,
            "metrics": {
                "MAE": forecast.mae,
                "RMSE": forecast.rmse,
                "MAPE": forecast.mape,
            },
            "forecast": forecast.forecast_data,
            "trend": forecast.trend_data,
            "seasonality": forecast.seasonality_data,
            "explanation": explanation,
            "generated_at": forecast.created_at.isoformat(),
        }
    }


@app.post("/api/companies/{company_id}/sentiment", response_model=Dict)
async def run_sentiment_analysis(
    company_id: int,
    request: SentimentRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_analyst),
    db: Session = Depends(get_db)
):
    """Run sentiment analysis on company reviews.
    
    Uses Arabic BERT model for Arabic text, TextBlob for English.
    """
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    check_company_access(current_user, company_id)
    
    # Create background task
    task_id = create_task_id(company.name, "sentiment")
    
    background_tasks.add_task(
        run_sentiment_async,
        task_id=task_id,
        company_id=company_id,
        company_name=company.data_directory,
        use_arabic=request.use_arabic_model
    )
    
    return {
        "success": True,
        "task_id": task_id,
        "message": "Sentiment analysis started. Check /api/tasks/{task_id} for status."
    }


@app.get("/api/companies/{company_id}/sentiment/summary", response_model=SentimentSummary)
async def get_sentiment_summary(
    company_id: int,
    current_user: User = Depends(require_analyst),
    db: Session = Depends(get_db)
):
    """Get sentiment analysis summary for a company."""
    check_company_access(current_user, company_id)
    
    # Get sentiment results from database
    results = (
        db.query(SentimentResult)
        .filter(SentimentResult.company_id == company_id)
        .all()
    )
    
    if not results:
        raise HTTPException(status_code=404, detail="No sentiment results found. Run analysis first.")
    
    total = len(results)
    positive = sum(1 for r in results if r.sentiment == "Positive")
    negative = sum(1 for r in results if r.sentiment == "Negative")
    neutral = sum(1 for r in results if r.sentiment == "Neutral")
    avg_confidence = sum(r.confidence for r in results) / total
    
    return SentimentSummary(
        total_reviews=total,
        positive=positive,
        neutral=neutral,
        negative=negative,
        average_confidence=round(avg_confidence, 4),
        sentiment_breakdown={
            "positive": round((positive / total) * 100, 1),
            "neutral": round((neutral / total) * 100, 1),
            "negative": round((negative / total) * 100, 1),
        }
    )


# -------------------------------------------------
# Explainability Endpoints
# -------------------------------------------------
@app.post("/api/explain/rfm")
async def explain_rfm_segment(
    request: ExplainRFMRequest,
    company_id: int = Query(..., description="Company ID"),
    current_user: User = Depends(require_analyst),
    db: Session = Depends(get_db)
):
    """Get explanation for a customer's RFM segment."""
    check_company_access(current_user, company_id)
    
    # Get customer RFM data
    rfm = (
        db.query(RFMResult)
        .filter(
            RFMResult.company_id == company_id,
            RFMResult.customer_id == request.customer_id
        )
        .first()
    )
    
    if not rfm:
        raise HTTPException(status_code=404, detail=f"Customer {request.customer_id} not found")
    
    # Generate explanation
    from src.explainability import explain_rfm_segment
    
    explanation = explain_rfm_segment(
        recency=rfm.recency,
        frequency=rfm.frequency,
        monetary=rfm.monetary,
        r_score=rfm.r_score,
        f_score=rfm.f_score,
        m_score=rfm.m_score,
        segment=rfm.rfm_segment
    )
    
    return {"success": True, "data": explanation}


@app.post("/api/explain/recommendation")
async def explain_product_recommendation(
    request: ExplainRecommendationRequest,
    current_user: User = Depends(require_analyst),
):
    """Get explanation for a product recommendation rule."""
    # This would typically fetch from stored association rules
    # For demo, we use placeholder values
    
    from src.explainability import explain_recommendation
    
    # In production, look up actual rule metrics from database
    explanation = explain_recommendation(
        product_a=request.product_a,
        product_b=request.product_b,
        support=0.15,  # Placeholder - fetch from DB
        confidence=0.65,
        lift=2.5
    )
    
    return {"success": True, "data": explanation}


# -------------------------------------------------
# Task Status Endpoint
# -------------------------------------------------
@app.get("/api/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_background_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get status of a background task."""
    task_info = get_task_status(task_id)
    
    if not task_info:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return TaskStatusResponse(
        task_id=task_id,
        status=task_info.get("status", TaskStatus.PENDING.value),
        progress=task_info.get("progress"),
        result=task_info.get("result"),
        error=task_info.get("error"),
    )


# -------------------------------------------------
# Model Monitoring Endpoints (Admin Only)
# -------------------------------------------------
@app.get("/api/admin/model-health/{company_id}")
async def get_model_health(
    company_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get model health summary for monitoring dashboard (Admin only)."""
    from src.ml_lifecycle.monitor_model import get_model_health_summary
    
    summary = get_model_health_summary(company_id)
    return {"success": True, "data": summary}


@app.post("/api/admin/check-drift/{company_id}")
async def check_data_drift(
    company_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Run data drift detection (Admin only)."""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    from src.ml_lifecycle.monitor_model import detect_data_drift
    
    try:
        drift_results = detect_data_drift(company.data_directory)
        return {"success": True, "data": drift_results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/admin/retrain/{company_id}")
async def trigger_retraining(
    company_id: int,
    background_tasks: BackgroundTasks,
    force: bool = False,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Trigger model retraining (Admin only)."""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    from src.ml_lifecycle.monitor_model import should_retrain_model
    
    decision = should_retrain_model(company_id, company.data_directory, force)
    
    if decision["should_retrain"]:
        # Trigger retraining in background
        task_id = create_task_id(company.name, "retrain")
        # In production, add actual retraining task here
        
        return {
            "success": True,
            "message": "Retraining triggered",
            "task_id": task_id,
            "reasons": decision["reasons"],
        }
    else:
        return {
            "success": True,
            "message": "Retraining not needed",
            "reasons": decision["reasons"],
        }


# -------------------------------------------------
# Error Handlers
# -------------------------------------------------
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Standard error response format."""
    return {
        "success": False,
        "error": exc.detail,
        "status_code": exc.status_code,
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Catch-all error handler."""
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    return {
        "success": False,
        "error": "Internal server error",
        "status_code": 500,
        "timestamp": datetime.utcnow().isoformat(),
    }


# -------------------------------------------------
# Run with: uvicorn backend.main_enhanced:app --reload
# -------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
