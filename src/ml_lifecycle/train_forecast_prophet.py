"""Train Prophet-based sales forecasting model with versioning.

IMPROVEMENTS:
1. Prophet model as primary (seasonal time-series)
2. Model versioning and metadata tracking
3. Performance comparison with baseline
4. Automatic model selection based on validation metrics

Model Registry Structure:
- sales_forecast_prophet_v{version}.pkl
- sales_forecast_baseline_v{version}.pkl
- model_metadata.json (tracks versions, metrics, training dates)
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# Prophet import
try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False
    logging.warning("Prophet not installed. Install with: pip install prophet")

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
MODEL_REGISTRY = Path(__file__).resolve().parent / "model_registry"
METADATA_FILE = MODEL_REGISTRY / "model_metadata.json"

LOGS_DIR.mkdir(exist_ok=True)
MODEL_REGISTRY.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "forecast_training.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


def load_metadata() -> Dict:
    """Load model registry metadata."""
    if METADATA_FILE.exists():
        with open(METADATA_FILE, "r") as f:
            return json.load(f)
    return {"models": [], "current_version": 0}


def save_metadata(metadata: Dict):
    """Save model registry metadata."""
    with open(METADATA_FILE, "w") as f:
        json.dump(metadata, f, indent=2)
    logger.info(f"Metadata saved: {METADATA_FILE}")


def get_next_version() -> int:
    """Get next model version number."""
    metadata = load_metadata()
    return metadata.get("current_version", 0) + 1


def load_monthly_sales(input_path: Path) -> pd.DataFrame:
    """Load and aggregate sales data to monthly frequency."""
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    df = pd.read_csv(input_path)
    required_cols = {"OrderDate", "TotalPrice"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df["OrderDate"] = pd.to_datetime(df["OrderDate"], errors="coerce")
    df = df.dropna(subset=["OrderDate", "TotalPrice"])
    if df.empty:
        raise ValueError("No valid rows after parsing dates")

    # Monthly aggregation
    monthly = (
        df.groupby(pd.Grouper(key="OrderDate", freq="MS"))["TotalPrice"]
        .sum()
        .reset_index()
        .sort_values("OrderDate")
        .reset_index(drop=True)
    )
    
    if len(monthly) < 6:
        raise ValueError("Need at least 6 months of data for reliable training")

    logger.info(f"Loaded {len(monthly)} months of sales data")
    return monthly


def temporal_split(monthly: pd.DataFrame, test_size: float = 0.2) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Split time series data temporally (no shuffling)."""
    n_months = len(monthly)
    n_test = max(2, int(n_months * test_size))
    n_train = n_months - n_test
    
    if n_train < 4:
        raise ValueError("Insufficient training data. Need at least 4 months for training.")
    
    train = monthly.iloc[:n_train].copy()
    test = monthly.iloc[n_train:].copy()
    
    logger.info(f"Train: {len(train)} months, Test: {len(test)} months")
    return train, test


def train_baseline_model(train: pd.DataFrame, test: pd.DataFrame, version: int) -> Dict:
    """Train baseline Linear Regression model."""
    train = train.copy()
    test = test.copy()
    
    train["TimeIndex"] = range(len(train))
    test["TimeIndex"] = range(len(train), len(train) + len(test))
    
    X_train = train[["TimeIndex"]]
    y_train = train["TotalPrice"]
    X_test = test[["TimeIndex"]]
    y_test = test["TotalPrice"]
    
    model = LinearRegression()
    model.fit(X_train, y_train)
    
    # Evaluate on test set
    y_pred = model.predict(X_test)
    metrics = {
        "MAE": float(mean_absolute_error(y_test, y_pred)),
        "RMSE": float(np.sqrt(mean_squared_error(y_test, y_pred))),
        "R2": float(r2_score(y_test, y_pred)),
        "MAPE": float(np.mean(np.abs((y_test - y_pred) / y_test)) * 100),
    }
    
    # Save model
    model_path = MODEL_REGISTRY / f"sales_forecast_baseline_v{version}.pkl"
    joblib.dump({"model": model, "max_time_index": len(train) - 1}, model_path)
    
    logger.info(f"Baseline trained - MAE: {metrics['MAE']:.2f}, RMSE: {metrics['RMSE']:.2f}, MAPE: {metrics['MAPE']:.2f}%")
    
    return {
        "model_type": "LinearRegression",
        "model_path": str(model_path),
        "metrics": metrics,
    }


def train_prophet_model(train: pd.DataFrame, test: pd.DataFrame, version: int) -> Dict:
    """Train Prophet time-series model with seasonality."""
    if not PROPHET_AVAILABLE:
        logger.warning("Prophet not available. Skipping.")
        return None
    
    # Prepare data in Prophet format
    train_prophet = train[["OrderDate", "TotalPrice"]].copy()
    train_prophet.columns = ["ds", "y"]
    
    test_prophet = test[["OrderDate", "TotalPrice"]].copy()
    test_prophet.columns = ["ds", "y"]
    
    # Train Prophet
    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=False,
        daily_seasonality=False,
        changepoint_prior_scale=0.05,
        seasonality_mode='multiplicative',
        interval_width=0.95,
    )
    
    logger.info("Training Prophet model...")
    model.fit(train_prophet)
    
    # Evaluate on test set
    test_forecast = model.predict(test_prophet[["ds"]])
    y_test = test_prophet["y"].values
    y_pred = test_forecast["yhat"].values
    
    metrics = {
        "MAE": float(mean_absolute_error(y_test, y_pred)),
        "RMSE": float(np.sqrt(mean_squared_error(y_test, y_pred))),
        "MAPE": float(np.mean(np.abs((y_test - y_pred) / y_test)) * 100),
    }
    
    # Save model
    model_path = MODEL_REGISTRY / f"sales_forecast_prophet_v{version}.pkl"
    joblib.dump(model, model_path)
    
    logger.info(f"Prophet trained - MAE: {metrics['MAE']:.2f}, RMSE: {metrics['RMSE']:.2f}, MAPE: {metrics['MAPE']:.2f}%")
    
    return {
        "model_type": "Prophet",
        "model_path": str(model_path),
        "metrics": metrics,
        "params": {
            "changepoint_prior_scale": 0.05,
            "seasonality_mode": "multiplicative",
            "yearly_seasonality": True,
        }
    }


def select_best_model(baseline_result: Dict, prophet_result: Dict) -> str:
    """Select best model based on MAPE (Mean Absolute Percentage Error).
    
    Lower MAPE is better - it's scale-independent and interpretable.
    """
    if prophet_result is None:
        logger.info("Prophet not available. Using baseline.")
        return "baseline"
    
    baseline_mape = baseline_result["metrics"]["MAPE"]
    prophet_mape = prophet_result["metrics"]["MAPE"]
    
    if prophet_mape < baseline_mape:
        logger.info(f"Prophet selected (MAPE: {prophet_mape:.2f}% vs {baseline_mape:.2f}%)")
        return "prophet"
    else:
        logger.info(f"Baseline selected (MAPE: {baseline_mape:.2f}% vs {prophet_mape:.2f}%)")
        return "baseline"


def train_and_register_models(company_name: str, test_size: float = 0.2) -> Dict:
    """Complete training pipeline with versioning and model selection.
    
    Returns:
        Dictionary with training results and selected model info
    """
    logger.info(f"Starting training pipeline for {company_name}")
    
    # Load data
    input_path = DATA_DIR / company_name / "sales" / "cleaned_sales.csv"
    monthly = load_monthly_sales(input_path)
    
    # Split data
    train, test = temporal_split(monthly, test_size)
    
    # Get version number
    version = get_next_version()
    logger.info(f"Training model version {version}")
    
    # Train both models
    baseline_result = train_baseline_model(train, test, version)
    prophet_result = train_prophet_model(train, test, version)
    
    # Select best model
    best_model_type = select_best_model(baseline_result, prophet_result)
    
    # Update metadata
    metadata = load_metadata()
    training_record = {
        "version": version,
        "company": company_name,
        "training_date": datetime.now().isoformat(),
        "train_months": len(train),
        "test_months": len(test),
        "baseline": baseline_result,
        "prophet": prophet_result,
        "selected_model": best_model_type,
    }
    
    metadata["models"].append(training_record)
    metadata["current_version"] = version
    metadata[f"current_{company_name}"] = {
        "version": version,
        "model_type": best_model_type,
    }
    save_metadata(metadata)
    
    # Create symlink to current best model (for easy loading)
    if best_model_type == "prophet" and prophet_result:
        current_model_path = MODEL_REGISTRY / "sales_forecast_model.pkl"
        source_path = Path(prophet_result["model_path"])
        if current_model_path.exists():
            current_model_path.unlink()
        joblib.dump(joblib.load(source_path), current_model_path)
        logger.info(f"Current model updated to Prophet v{version}")
    else:
        current_model_path = MODEL_REGISTRY / "sales_forecast_model.pkl"
        source_path = Path(baseline_result["model_path"])
        if current_model_path.exists():
            current_model_path.unlink()
        joblib.dump(joblib.load(source_path), current_model_path)
        logger.info(f"Current model updated to Baseline v{version}")
    
    logger.info("Training pipeline completed successfully")
    return training_record


if __name__ == "__main__":
    company = sys.argv[1] if len(sys.argv) > 1 else "Acme Corp"
    test_size = float(sys.argv[2]) if len(sys.argv) > 2 else 0.2
    
    try:
        result = train_and_register_models(company, test_size)
        
        print("\n" + "="*70)
        print(f"MODEL TRAINING COMPLETE - VERSION {result['version']}")
        print("="*70)
        print(f"Company: {result['company']}")
        print(f"Training Date: {result['training_date']}")
        print(f"Data Split: {result['train_months']} train, {result['test_months']} test")
        print("\nBASELINE METRICS:")
        for k, v in result['baseline']['metrics'].items():
            print(f"  {k}: {v:.2f}")
        
        if result['prophet']:
            print("\nPROPHET METRICS:")
            for k, v in result['prophet']['metrics'].items():
                print(f"  {k}: {v:.2f}")
        
        print(f"\nSELECTED MODEL: {result['selected_model'].upper()}")
        print("="*70 + "\n")
        
    except Exception as e:
        logger.error(f"Training failed: {e}", exc_info=True)
        sys.exit(1)
