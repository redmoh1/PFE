"""Train a monthly sales forecasting model and persist it to the registry.

Lifecycle stages covered:
1) Data prep (monthly aggregation, time index)
2) Time-aware split (no shuffling)
3) Baseline model training (Linear Regression)
4) Evaluation (MAE, RMSE, R2)
5) Model persistence (joblib -> model_registry)
"""

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
MODEL_REGISTRY = Path(__file__).resolve().parent / "model_registry"
MODEL_PATH = MODEL_REGISTRY / "sales_forecast_model.pkl"

LOGS_DIR.mkdir(exist_ok=True)
MODEL_REGISTRY.mkdir(exist_ok=True)

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
    """Load cleaned data, aggregate to monthly sales, and build MonthIndex feature."""
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
        raise ValueError("No valid rows after parsing dates and dropping nulls")

    monthly = (
        df.groupby(pd.Grouper(key="OrderDate", freq="MS"))["TotalPrice"]
        .sum()
        .reset_index()
        .sort_values("OrderDate")
        .reset_index(drop=True)
    )
    if len(monthly) < 3:
        raise ValueError("Need at least 3 months of data for a stable temporal split")

    monthly["MonthIndex"] = np.arange(len(monthly))
    return monthly


def split_time_series(monthly: pd.DataFrame, test_size: float = 0.2) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """Perform a temporal train/test split without shuffling."""
    if not 0 < test_size < 1:
        raise ValueError("test_size must be between 0 and 1")

    n_months = len(monthly)
    n_test = max(1, int(n_months * test_size))
    n_train = n_months - n_test
    if n_train < 2:
        raise ValueError("Insufficient training data after split; collect more history")

    X = monthly[["MonthIndex"]]
    y = monthly["TotalPrice"]

    X_train, X_test = X.iloc[:n_train], X.iloc[n_train:]
    y_train, y_test = y.iloc[:n_train], y.iloc[n_train:]
    return X_train, X_test, y_train, y_test


def train_model(X_train: pd.DataFrame, y_train: pd.Series) -> LinearRegression:
    """Train an interpretable Linear Regression baseline."""
    model = LinearRegression()
    model.fit(X_train, y_train)
    return model


def evaluate_model(model: LinearRegression, X: pd.DataFrame, y: pd.Series) -> dict:
    """Compute MAE, RMSE, and R2 for a given split (R2 guarded for tiny sets)."""
    preds = model.predict(X)
    mae = mean_absolute_error(y, preds)
    rmse = float(np.sqrt(mean_squared_error(y, preds)))
    r2 = r2_score(y, preds) if len(y) >= 2 else float("nan")
    return {"MAE": mae, "RMSE": rmse, "R2": r2}


def log_metrics(label: str, metrics: dict, sample_size: int) -> None:
    """Log metrics consistently and warn when R2 is undefined for tiny splits."""
    if sample_size < 2:
        logger.warning(f"{label}: only {sample_size} sample(s); R2 reported as nan")
    logger.info(
        f"{label} -> MAE: {metrics['MAE']:.2f}, RMSE: {metrics['RMSE']:.2f}, R2: {metrics['R2']:.4f}"
    )


def save_model(model: LinearRegression, output_path: Path) -> None:
    """Persist the trained model to disk using joblib."""
    output_path.parent.mkdir(exist_ok=True)
    joblib.dump(model, output_path)


def main() -> None:
    """Run the training + evaluation lifecycle and save the model."""
    try:
        logger.info("===== ML Lifecycle: Train -> Evaluate -> Persist =====")
        input_path = DATA_DIR / "cleaned_dataset.csv"

        # Stage 1: Data prep
        monthly = load_monthly_sales(input_path)
        logger.info(f"Prepared monthly data with {len(monthly)} periods (min={monthly['OrderDate'].min().date()}, max={monthly['OrderDate'].max().date()})")

        # Stage 2: Temporal split
        X_train, X_test, y_train, y_test = split_time_series(monthly, test_size=0.2)
        logger.info(f"Split into {len(X_train)} train months and {len(X_test)} test months")

        # Stage 3: Train
        model = train_model(X_train, y_train)

        # Stage 4: Evaluate
        train_metrics = evaluate_model(model, X_train, y_train)
        test_metrics = evaluate_model(model, X_test, y_test)
        log_metrics("Train", train_metrics, len(y_train))
        log_metrics("Test", test_metrics, len(y_test))

        # Stage 5: Persist model
        save_model(model, MODEL_PATH)
        logger.info(f"Model saved to {MODEL_PATH}")

        logger.info("===== Training lifecycle completed successfully =====")
    except (FileNotFoundError, ValueError) as err:
        logger.error(f"Validation error: {err}")
        sys.exit(1)
    except Exception as err:  # pragma: no cover - safety net
        logger.error(f"Unexpected error: {err}")
        sys.exit(1)


if __name__ == "__main__":
    main()
