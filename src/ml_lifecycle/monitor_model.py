"""
ML Model Monitoring and Data Drift Detection

FEATURES:
- Track model performance over time
- Detect data distribution shifts
- Automatic retraining triggers
- Performance degradation alerts

WHY THIS MATTERS:
- Real-world data changes over time (concept drift)
- Model accuracy degrades without retraining
- Early detection prevents bad predictions
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional, List

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import mean_absolute_error, mean_squared_error

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.database.connection import SessionLocal
from backend.database.models import ModelPerformanceLog, Company

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
MODEL_REGISTRY = Path(__file__).resolve().parent / "model_registry"

LOGS_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "model_monitoring.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


# -------------------------------------------------
# Performance Tracking
# -------------------------------------------------
def log_model_performance(
    company_id: int,
    company_name: str,
    model_type: str,
    model_version: int,
    mae: float,
    rmse: float,
    mape: Optional[float],
    training_samples: int,
    test_samples: int,
    feature_stats: Optional[Dict] = None
):
    """Log model performance metrics to database.
    
    Args:
        company_id: Company ID
        company_name: Company name (for logging)
        model_type: "Prophet" or "LinearRegression"
        model_version: Model version number
        mae, rmse, mape: Performance metrics
        training_samples, test_samples: Data sizes
        feature_stats: Optional statistics about features (for drift detection)
    """
    db = SessionLocal()
    
    try:
        # Check for performance degradation
        performance_degraded, retrain_recommended = check_performance_degradation(
            db, company_id, mape or mae
        )
        
        # Create log entry
        log_entry = ModelPerformanceLog(
            company_id=company_id,
            model_type=model_type,
            model_version=model_version,
            mae=mae,
            rmse=rmse,
            mape=mape,
            training_samples=training_samples,
            test_samples=test_samples,
            feature_stats=feature_stats,
            performance_degraded=performance_degraded,
            retrain_recommended=retrain_recommended,
        )
        
        db.add(log_entry)
        db.commit()
        
        logger.info(f"Model performance logged for {company_name} v{model_version}")
        logger.info(f"  MAE: {mae:.2f}, RMSE: {rmse:.2f}, MAPE: {mape:.2f}%")
        
        if performance_degraded:
            logger.warning(f"⚠️  Performance degradation detected for {company_name}!")
        
        if retrain_recommended:
            logger.warning(f"🔄 Retraining recommended for {company_name}")
        
    except Exception as e:
        logger.error(f"Failed to log performance: {e}")
        db.rollback()
    finally:
        db.close()


def check_performance_degradation(
    db, 
    company_id: int, 
    current_mape: float,
    threshold: float = 10.0  # 10% degradation threshold
) -> tuple[bool, bool]:
    """Check if current performance is significantly worse than historical.
    
    Returns:
        (performance_degraded, retrain_recommended)
    """
    # Get last 5 performance logs
    recent_logs = (
        db.query(ModelPerformanceLog)
        .filter(ModelPerformanceLog.company_id == company_id)
        .order_by(ModelPerformanceLog.logged_at.desc())
        .limit(5)
        .all()
    )
    
    if len(recent_logs) < 2:
        return False, False  # Not enough history
    
    # Calculate average historical MAPE
    historical_mapes = [log.mape for log in recent_logs if log.mape is not None]
    if not historical_mapes:
        return False, False
    
    avg_historical_mape = np.mean(historical_mapes)
    
    # Check if current performance is significantly worse
    degradation_pct = ((current_mape - avg_historical_mape) / avg_historical_mape) * 100
    
    performance_degraded = degradation_pct > threshold
    retrain_recommended = degradation_pct > (threshold * 1.5)  # 15% worse
    
    if performance_degraded:
        logger.info(f"Performance degradation: {degradation_pct:.1f}% worse than average")
    
    return performance_degraded, retrain_recommended


# -------------------------------------------------
# Data Drift Detection
# -------------------------------------------------
def detect_data_drift(
    company_name: str,
    reference_window: int = 90,  # days
    current_window: int = 30,  # days
    significance_level: float = 0.05
) -> Dict:
    """Detect data distribution shifts using statistical tests.
    
    WHY: Data changes over time (seasonality, trends, market shifts).
    When distribution shifts significantly, model retraining is needed.
    
    APPROACH:
    - Compare recent data to historical baseline
    - Use Kolmogorov-Smirnov test for distribution similarity
    - Track mean, std, and key percentiles
    
    Args:
        company_name: Company name
        reference_window: Days of historical data as baseline
        current_window: Days of recent data to compare
        significance_level: p-value threshold for drift detection
        
    Returns:
        Dictionary with drift detection results
    """
    sales_file = DATA_DIR / company_name / "sales" / "cleaned_sales.csv"
    
    if not sales_file.exists():
        raise FileNotFoundError(f"Sales data not found: {sales_file}")
    
    df = pd.read_csv(sales_file)
    df["OrderDate"] = pd.to_datetime(df["OrderDate"])
    
    # Split into reference and current periods
    latest_date = df["OrderDate"].max()
    reference_start = latest_date - timedelta(days=reference_window + current_window)
    reference_end = latest_date - timedelta(days=current_window)
    current_start = reference_end
    
    reference_data = df[
        (df["OrderDate"] >= reference_start) & (df["OrderDate"] < reference_end)
    ]["TotalPrice"].values
    
    current_data = df[
        df["OrderDate"] >= current_start
    ]["TotalPrice"].values
    
    if len(reference_data) < 30 or len(current_data) < 10:
        logger.warning("Insufficient data for drift detection")
        return {
            "drift_detected": False,
            "reason": "insufficient_data",
            "reference_samples": len(reference_data),
            "current_samples": len(current_data),
        }
    
    # Kolmogorov-Smirnov test (distribution similarity)
    ks_statistic, ks_pvalue = stats.ks_2samp(reference_data, current_data)
    
    # Distribution statistics
    ref_mean = np.mean(reference_data)
    cur_mean = np.mean(current_data)
    mean_shift_pct = ((cur_mean - ref_mean) / ref_mean) * 100
    
    ref_std = np.std(reference_data)
    cur_std = np.std(current_data)
    std_shift_pct = ((cur_std - ref_std) / ref_std) * 100
    
    # Drift detection
    drift_detected = ks_pvalue < significance_level
    
    results = {
        "drift_detected": drift_detected,
        "ks_statistic": float(ks_statistic),
        "ks_pvalue": float(ks_pvalue),
        "significance_level": significance_level,
        "reference_mean": float(ref_mean),
        "current_mean": float(cur_mean),
        "mean_shift_percent": float(mean_shift_pct),
        "reference_std": float(ref_std),
        "current_std": float(cur_std),
        "std_shift_percent": float(std_shift_pct),
        "reference_samples": len(reference_data),
        "current_samples": len(current_data),
        "reference_period": f"{reference_window} days",
        "current_period": f"{current_window} days",
    }
    
    logger.info(f"Data Drift Detection for {company_name}:")
    logger.info(f"  Drift Detected: {drift_detected} (p-value: {ks_pvalue:.4f})")
    logger.info(f"  Mean Shift: {mean_shift_pct:+.1f}%")
    logger.info(f"  Std Shift: {std_shift_pct:+.1f}%")
    
    if drift_detected:
        logger.warning(f"⚠️  Data drift detected for {company_name}! Consider retraining.")
    
    return results


# -------------------------------------------------
# Automatic Retraining Decision
# -------------------------------------------------
def should_retrain_model(
    company_id: int,
    company_name: str,
    force: bool = False
) -> Dict:
    """Decide if model should be retrained based on multiple factors.
    
    Criteria:
    1. Performance degradation > 10%
    2. Data drift detected (p < 0.05)
    3. Last training was > 30 days ago
    4. Manual force flag
    
    Returns:
        Dictionary with decision and reasons
    """
    db = SessionLocal()
    
    try:
        # 1. Check recent performance
        recent_log = (
            db.query(ModelPerformanceLog)
            .filter(ModelPerformanceLog.company_id == company_id)
            .order_by(ModelPerformanceLog.logged_at.desc())
            .first()
        )
        
        reasons = []
        
        if force:
            reasons.append("Manual retraining requested")
            return {
                "should_retrain": True,
                "reasons": reasons,
                "urgency": "high",
            }
        
        # 2. Check performance degradation
        performance_issue = False
        if recent_log and recent_log.performance_degraded:
            reasons.append("Performance degraded beyond threshold")
            performance_issue = True
        
        # 3. Check data drift
        try:
            drift_results = detect_data_drift(company_name)
            if drift_results["drift_detected"]:
                reasons.append(f"Data drift detected (p={drift_results['ks_pvalue']:.4f})")
                performance_issue = True
        except Exception as e:
            logger.warning(f"Could not check data drift: {e}")
        
        # 4. Check time since last training
        if recent_log:
            days_since_training = (datetime.utcnow() - recent_log.logged_at).days
            if days_since_training > 30:
                reasons.append(f"Last training was {days_since_training} days ago")
                performance_issue = True
        else:
            reasons.append("No training history found")
            performance_issue = True
        
        # Determine urgency
        urgency = "high" if len(reasons) >= 2 else "medium"
        
        decision = {
            "should_retrain": performance_issue,
            "reasons": reasons if performance_issue else ["Model performing well"],
            "urgency": urgency if performance_issue else "low",
            "last_training": recent_log.logged_at.isoformat() if recent_log else None,
        }
        
        logger.info(f"Retraining decision for {company_name}: {decision['should_retrain']}")
        for reason in decision["reasons"]:
            logger.info(f"  - {reason}")
        
        return decision
        
    finally:
        db.close()


# -------------------------------------------------
# Monitoring Dashboard Data
# -------------------------------------------------
def get_model_health_summary(company_id: int) -> Dict:
    """Get overall model health metrics for monitoring dashboard.
    
    Returns:
        Summary of model performance, trends, and alerts
    """
    db = SessionLocal()
    
    try:
        # Get last 30 days of logs
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        logs = (
            db.query(ModelPerformanceLog)
            .filter(
                ModelPerformanceLog.company_id == company_id,
                ModelPerformanceLog.logged_at >= thirty_days_ago
            )
            .order_by(ModelPerformanceLog.logged_at.asc())
            .all()
        )
        
        if not logs:
            return {
                "status": "no_data",
                "message": "No performance logs found",
            }
        
        latest = logs[-1]
        
        # Calculate trends
        mape_values = [log.mape for log in logs if log.mape is not None]
        mape_trend = "improving" if len(mape_values) > 1 and mape_values[-1] < mape_values[0] else "degrading"
        
        return {
            "status": "healthy" if not latest.performance_degraded else "needs_attention",
            "current_mape": latest.mape,
            "current_mae": latest.mae,
            "current_rmse": latest.rmse,
            "model_version": latest.model_version,
            "model_type": latest.model_type,
            "last_evaluation": latest.logged_at.isoformat(),
            "performance_trend": mape_trend,
            "alerts": {
                "performance_degraded": latest.performance_degraded,
                "retrain_recommended": latest.retrain_recommended,
            },
            "logs_count": len(logs),
        }
        
    finally:
        db.close()


if __name__ == "__main__":
    company = sys.argv[1] if len(sys.argv) > 1 else "Acme Corp"
    
    print("\n" + "="*70)
    print(f"ML MONITORING REPORT: {company}")
    print("="*70)
    
    # Data drift detection
    try:
        drift_results = detect_data_drift(company)
        print("\nDATA DRIFT ANALYSIS:")
        print(f"  Status: {'⚠️  DRIFT DETECTED' if drift_results['drift_detected'] else '✓ No drift'}")
        print(f"  KS p-value: {drift_results['ks_pvalue']:.4f}")
        print(f"  Mean shift: {drift_results['mean_shift_percent']:+.1f}%")
        print(f"  Std shift: {drift_results['std_shift_percent']:+.1f}%")
    except Exception as e:
        print(f"\n  Could not perform drift analysis: {e}")
    
    print("\n" + "="*70 + "\n")
