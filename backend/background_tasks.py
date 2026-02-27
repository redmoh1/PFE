"""
Background task management for heavy ML operations.

FEATURES:
- Async forecasting
- Async Customer Feedback
- Task status tracking
- Result caching

WHY:
- ML operations can take 10-60 seconds
- Don't block API responses
- Better user experience
- Enable batch processing
"""

import sys
import logging
import asyncio
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
from enum import Enum
import json
import importlib.util

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.database.connection import SessionLocal
from backend.database.models import ForecastResult, SentimentResult, Company

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


BASE_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = BASE_DIR / "src"


def _load_module_from_path(module_name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, str(file_path))
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module spec: {module_name} from {file_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TaskStatus(str, Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# In-memory task tracking (for simple implementation)
# For production, use Redis or database
TASK_REGISTRY: Dict[str, Dict] = {}


# -------------------------------------------------
# Background Task: Forecasting
# -------------------------------------------------
async def run_forecast_async(
    task_id: str,
    company_id: int,
    company_name: str,
    periods: int = 6,
    use_prophet: bool = True
):
    """Run sales forecasting in background.
    
    Args:
        task_id: Unique task identifier
        company_id: Company ID
        company_name: Company name
        periods: Forecast periods
        use_prophet: Use Prophet or baseline
    """
    TASK_REGISTRY[task_id] = {
        "status": TaskStatus.RUNNING,
        "started_at": datetime.utcnow().isoformat(),
        "progress": 0,
    }
    
    try:
        logger.info(f"Starting forecast task {task_id} for {company_name}")

        forecasting_module = _load_module_from_path(
            "forecasting_prophet",
            SRC_DIR / "03_forecasting_prophet.py",
        )
        run_forecasting = forecasting_module.run_forecasting
        
        # Run forecast
        TASK_REGISTRY[task_id]["progress"] = 50
        results = run_forecasting(company_name, periods=periods, use_prophet=use_prophet)
        
        # Save to database
        db = SessionLocal()
        try:
            model_result = results.get("prophet") or results.get("baseline")
            
            if model_result:
                forecast_record = ForecastResult(
                    company_id=company_id,
                    model_type=model_result["metrics"]["model"],
                    model_version=1,  # Get from model registry
                    forecast_periods=periods,
                    mae=model_result["metrics"].get("MAE"),
                    rmse=model_result["metrics"].get("RMSE"),
                    mape=model_result["metrics"].get("MAPE"),
                    r2=model_result["metrics"].get("R2"),
                    forecast_data=model_result["forecast"].to_dict("records"),
                    trend_data=model_result.get("components", {}).get("trend"),
                    seasonality_data=model_result.get("components", {}).get("yearly"),
                )
                db.add(forecast_record)
                db.commit()
                
                logger.info(f"Forecast results saved to database for {company_name}")
        finally:
            db.close()
        
        # Update task status
        TASK_REGISTRY[task_id] = {
            "status": TaskStatus.COMPLETED,
            "started_at": TASK_REGISTRY[task_id]["started_at"],
            "completed_at": datetime.utcnow().isoformat(),
            "progress": 100,
            "result": {
                "forecast_periods": periods,
                "model_type": model_result["metrics"]["model"] if model_result else "Unknown",
            }
        }
        
        logger.info(f"Forecast task {task_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Forecast task {task_id} failed: {e}", exc_info=True)
        TASK_REGISTRY[task_id] = {
            "status": TaskStatus.FAILED,
            "started_at": TASK_REGISTRY[task_id]["started_at"],
            "failed_at": datetime.utcnow().isoformat(),
            "error": str(e),
        }


# -------------------------------------------------
# Background Task: Customer Feedback
# -------------------------------------------------
async def run_sentiment_async(
    task_id: str,
    company_id: int,
    company_name: str,
    use_arabic: bool = True
):
    """Run Customer Feedback in background.
    
    Args:
        task_id: Unique task identifier
        company_id: Company ID
        company_name: Company name
        use_arabic: Use Arabic NLP model
    """
    TASK_REGISTRY[task_id] = {
        "status": TaskStatus.RUNNING,
        "started_at": datetime.utcnow().isoformat(),
        "progress": 0,
    }
    
    try:
        logger.info(f"Starting sentiment task {task_id} for {company_name}")

        sentiment_module = _load_module_from_path(
            "sentiment_arabic",
            SRC_DIR / "06_sentiment_arabic.py",
        )
        analyze_reviews = sentiment_module.analyze_reviews
        
        # Run analysis
        TASK_REGISTRY[task_id]["progress"] = 50
        results_df = analyze_reviews(company_name, use_arabic_model=use_arabic)
        
        # Save to database
        db = SessionLocal()
        try:
            # Clear old results for this company
            db.query(SentimentResult).filter(
                SentimentResult.company_id == company_id
            ).delete()
            
            # Insert new results (batch insert for performance)
            batch_size = 1000
            for i in range(0, len(results_df), batch_size):
                batch = results_df.iloc[i:i+batch_size]
                
                for _, row in batch.iterrows():
                    sentiment_record = SentimentResult(
                        company_id=company_id,
                        review_text=row.get("ReviewText", ""),
                        sentiment=row["sentiment"],
                        confidence=row["confidence"],
                        polarity=row["polarity"],
                        analysis_method=row["analysis_method"],
                        product_id=row.get("ProductID"),
                        rating=row.get("Rating"),
                    )
                    db.add(sentiment_record)
                
                db.commit()
                logger.info(f"Saved batch {i//batch_size + 1} of sentiment results")
            
            logger.info(f"All sentiment results saved to database for {company_name}")
        finally:
            db.close()
        
        # Update task status
        TASK_REGISTRY[task_id] = {
            "status": TaskStatus.COMPLETED,
            "started_at": TASK_REGISTRY[task_id]["started_at"],
            "completed_at": datetime.utcnow().isoformat(),
            "progress": 100,
            "result": {
                "total_reviews": len(results_df),
                "sentiment_distribution": results_df["sentiment"].value_counts().to_dict(),
            }
        }
        
        logger.info(f"Sentiment task {task_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Sentiment task {task_id} failed: {e}", exc_info=True)
        TASK_REGISTRY[task_id] = {
            "status": TaskStatus.FAILED,
            "started_at": TASK_REGISTRY[task_id]["started_at"],
            "failed_at": datetime.utcnow().isoformat(),
            "error": str(e),
        }


# -------------------------------------------------
# Task Management
# -------------------------------------------------
def get_task_status(task_id: str) -> Optional[Dict]:
    """Get status of a background task.
    
    Returns:
        Task status dictionary or None if task not found
    """
    return TASK_REGISTRY.get(task_id)


def create_task_id(company_name: str, task_type: str) -> str:
    """Generate unique task ID.
    
    Args:
        company_name: Company name
        task_type: "forecast" or "sentiment"
        
    Returns:
        Unique task identifier
    """
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    return f"{task_type}_{company_name.replace(' ', '_')}_{timestamp}"


def cleanup_old_tasks(max_age_hours: int = 24):
    """Remove old completed tasks from registry.
    
    Args:
        max_age_hours: Maximum age of tasks to keep
    """
    current_time = datetime.utcnow()
    tasks_to_remove = []
    
    for task_id, task_info in TASK_REGISTRY.items():
        if task_info["status"] in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            completed_at = task_info.get("completed_at") or task_info.get("failed_at")
            if completed_at:
                task_time = datetime.fromisoformat(completed_at)
                age_hours = (current_time - task_time).total_seconds() / 3600
                
                if age_hours > max_age_hours:
                    tasks_to_remove.append(task_id)
    
    for task_id in tasks_to_remove:
        del TASK_REGISTRY[task_id]
    
    if tasks_to_remove:
        logger.info(f"Cleaned up {len(tasks_to_remove)} old tasks")
