"""Evaluate the persisted sales forecast model on a temporal test split."""

import sys
import logging
from pathlib import Path
from typing import Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
MODEL_PATH = Path(__file__).resolve().parent / "model_registry" / "sales_forecast_model.pkl"

LOGS_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "forecast_lifecycle.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


def load_monthly_sales(input_path: Path) -> pd.DataFrame:
    """Load cleaned data, aggregate monthly, and add MonthIndex."""
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    df = pd.read_csv(input_path)
    required_cols = {"OrderDate", "TotalPrice"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df["OrderDate"] = pd.to_datetime(df["OrderDate"], errors="coerce")
    invalid_dates = df["OrderDate"].isna().sum()
    if invalid_dates > 0:
        logger.warning(f"Dropping {invalid_dates} rows with invalid dates")
    
    df = df.dropna(subset=["OrderDate", "TotalPrice"])
    if df.empty:
        raise ValueError("No valid rows after cleaning")

    monthly = (
        df.groupby(pd.Grouper(key="OrderDate", freq="MS"))["TotalPrice"]
        .sum()
        .reset_index()
        .sort_values("OrderDate")
        .reset_index(drop=True)
    )
    if len(monthly) < 3:
        raise ValueError(f"Need at least 3 months of data for evaluation, got {len(monthly)}")

    monthly["MonthIndex"] = np.arange(len(monthly))
    logger.info(f"Loaded {len(monthly)} monthly periods from {input_path}")
    return monthly


def split_time_series(monthly: pd.DataFrame, test_size: float = 0.2) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """Temporal split matching the training pipeline."""
    if not 0 < test_size < 1:
        raise ValueError("test_size must be between 0 and 1")

    n_months = len(monthly)
    if n_months < 3:
        raise ValueError(f"Cannot split {n_months} months; need at least 3")
    
    n_test = max(1, int(n_months * test_size))
    n_train = n_months - n_test
    if n_train < 2:
        raise ValueError(f"Insufficient training history: {n_train} train months < 2 required")

    X = monthly[["MonthIndex"]].copy()
    y = monthly["TotalPrice"].copy()
    X_train, X_test = X.iloc[:n_train], X.iloc[n_train:]
    y_train, y_test = y.iloc[:n_train], y.iloc[n_train:]
    
    logger.debug(f"Split: {n_train} train months, {n_test} test months")
    return X_train, X_test, y_train, y_test


def evaluate_model(model: LinearRegression, X: pd.DataFrame, y: pd.Series) -> dict:
    """Compute MAE, RMSE, and R2 with small-sample safety for R2."""
    preds = model.predict(X)
    mae = mean_absolute_error(y, preds)
    rmse = float(np.sqrt(mean_squared_error(y, preds)))
    r2 = r2_score(y, preds) if len(y) >= 2 else float("nan")
    return {"MAE": mae, "RMSE": rmse, "R2": r2}


def log_metrics(label: str, metrics: dict, sample_size: int) -> None:
    """Log metrics in a consistent, readable format."""
    if sample_size < 2:
        logger.warning(f"{label}: only {sample_size} sample(s); R2 not defined (reported as nan)")
    logger.info(
        f"{label} -> MAE: {metrics['MAE']:.2f} | RMSE: {metrics['RMSE']:.2f} | R2: {metrics['R2']:.4f}"
    )


def load_model(model_path: Path) -> LinearRegression:
    """Reload a persisted Linear Regression model."""
    if not model_path.parent.exists():
        raise FileNotFoundError(f"Model registry directory not found: {model_path.parent}")
    
    if not model_path.exists():
        raise FileNotFoundError(
            f"Saved model not found at {model_path}.\n"
            "Run train_forecast.py first to train and save the model."
        )
    
    try:
        model = joblib.load(model_path)
        logger.info(f"Successfully loaded model from {model_path}")
        return model
    except Exception as e:
        raise RuntimeError(f"Failed to load model: {e}")


def main() -> None:
    """Reload the saved model and report evaluation metrics on the held-out test split."""
    try:
        logger.info("===== ML Lifecycle: Evaluate persisted model =====")
        input_path = DATA_DIR / "cleaned_dataset.csv"

        # Load and prepare data
        monthly = load_monthly_sales(input_path)
        X_train, X_test, y_train, y_test = split_time_series(monthly, test_size=0.2)
        logger.info(f"Dataset split: {len(monthly)} total periods (train={len(X_train)}, test={len(X_test)})")

        # Load persisted model
        model = load_model(MODEL_PATH)

        # Evaluate on both train and test splits
        train_metrics = evaluate_model(model, X_train, y_train)
        test_metrics = evaluate_model(model, X_test, y_test)

        logger.info("--- Train Set Evaluation ---")
        log_metrics("Train", train_metrics, len(y_train))
        
        logger.info("--- Test Set Evaluation ---")
        log_metrics("Test", test_metrics, len(y_test))

        logger.info("===== Evaluation completed successfully =====")
        
    except FileNotFoundError as err:
        logger.error(f"File error: {err}")
        sys.exit(1)
    except ValueError as err:
        logger.error(f"Data validation error: {err}")
        sys.exit(1)
    except Exception as err:
        logger.error(f"Unexpected error during evaluation: {err}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
