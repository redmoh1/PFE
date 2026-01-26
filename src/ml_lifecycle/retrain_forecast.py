"""Simulate new data arrival, retrain the forecast model, and overwrite the registry artifact."""

import sys
import logging
from datetime import datetime, timezone
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
MAX_SIM_PERIODS = 36  # safeguard against runaway simulation horizons

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
    """Load cleaned data, aggregate monthly, and add MonthIndex."""
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
        raise ValueError("No valid rows after cleaning")

    monthly = (
        df.groupby(pd.Grouper(key="OrderDate", freq="MS"))["TotalPrice"]
        .sum()
        .reset_index()
        .sort_values("OrderDate")
        .reset_index(drop=True)
    )
    if len(monthly) < 3:
        raise ValueError("Need at least 3 months of data before retraining")

    monthly["MonthIndex"] = np.arange(len(monthly))
    return monthly


def split_time_series(monthly: pd.DataFrame, test_size: float = 0.2) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """Temporal split that respects ordering."""
    if not 0 < test_size < 1:
        raise ValueError("test_size must be between 0 and 1")

    n_months = len(monthly)
    n_test = max(1, int(n_months * test_size))
    n_train = n_months - n_test
    if n_train < 2:
        raise ValueError("Insufficient training history after split")

    X = monthly[["MonthIndex"]]
    y = monthly["TotalPrice"]
    X_train, X_test = X.iloc[:n_train], X.iloc[n_train:]
    y_train, y_test = y.iloc[:n_train], y.iloc[n_train:]
    return X_train, X_test, y_train, y_test


def train_model(X_train: pd.DataFrame, y_train: pd.Series) -> LinearRegression:
    """Train Linear Regression baseline."""
    model = LinearRegression()
    model.fit(X_train, y_train)
    return model


def evaluate_model(model: LinearRegression, X: pd.DataFrame, y: pd.Series) -> dict:
    """Compute MAE, RMSE, and R2 with small-sample safety."""
    preds = model.predict(X)
    mae = mean_absolute_error(y, preds)
    rmse = float(np.sqrt(mean_squared_error(y, preds)))
    r2 = r2_score(y, preds) if len(y) >= 2 else float("nan")
    return {"MAE": mae, "RMSE": rmse, "R2": r2}


def log_metrics(label: str, metrics: dict, sample_size: int) -> None:
    """Consistent metric logging with context about sample size."""
    if sample_size < 2:
        logger.warning(f"{label}: only {sample_size} sample(s); R2 reported as nan")
    logger.info(
        f"{label} -> MAE: {metrics['MAE']:.2f}, RMSE: {metrics['RMSE']:.2f}, R2: {metrics['R2']:.4f}"
    )


def simulate_new_data(monthly: pd.DataFrame, model: LinearRegression, periods: int = 3, noise_pct: float = 0.05) -> pd.DataFrame:
    """Simulate arrival of future months using model forecasts plus controlled noise."""
    if periods <= 0:
        raise ValueError("Simulation periods must be positive")
    if periods > MAX_SIM_PERIODS:
        raise ValueError(f"Simulation horizon {periods} exceeds max supported {MAX_SIM_PERIODS}")
    if noise_pct < 0:
        raise ValueError("noise_pct must be non-negative")

    last_index = int(monthly["MonthIndex"].max())
    future_indices = np.arange(last_index + 1, last_index + periods + 1)
    future_X = pd.DataFrame({"MonthIndex": future_indices})

    last_date = monthly["OrderDate"].max()
    future_dates = pd.date_range(start=last_date + pd.offsets.MonthBegin(1), periods=periods, freq="MS")

    base_forecast = model.predict(future_X)
    rng = np.random.default_rng(42)
    noise = rng.normal(loc=0.0, scale=noise_pct, size=periods)
    simulated_sales = base_forecast * (1 + noise)

    simulated_df = pd.DataFrame(
        {
            "OrderDate": future_dates,
            "TotalPrice": simulated_sales,
            "MonthIndex": future_indices,
        }
    )
    extended = pd.concat([monthly, simulated_df], ignore_index=True)
    return extended


def main() -> None:
    """Retrain the model after simulating new data and overwrite the registry artifact."""
    try:
        logger.info("===== ML Lifecycle: Retrain with simulated new data =====")
        input_path = DATA_DIR / "cleaned_dataset.csv"

        monthly = load_monthly_sales(input_path)
        baseline_model = train_model(monthly[["MonthIndex"]], monthly["TotalPrice"])

        monthly_extended = simulate_new_data(monthly, baseline_model, periods=3, noise_pct=0.05)
        logger.info(f"Extended dataset from {len(monthly)} to {len(monthly_extended)} monthly periods")

        # Recompute MonthIndex to keep it sequential after extension
        monthly_extended = monthly_extended.sort_values("OrderDate").reset_index(drop=True)
        monthly_extended["MonthIndex"] = np.arange(len(monthly_extended))

        X_train, X_test, y_train, y_test = split_time_series(monthly_extended, test_size=0.2)
        model = train_model(X_train, y_train)

        train_metrics = evaluate_model(model, X_train, y_train)
        test_metrics = evaluate_model(model, X_test, y_test)
        log_metrics("Retrain Train", train_metrics, len(y_train))
        log_metrics("Retrain Test", test_metrics, len(y_test))

        MODEL_REGISTRY.mkdir(exist_ok=True)
        joblib.dump(model, MODEL_PATH)
        logger.info(f"Overwrote model at {MODEL_PATH}")
        logger.info(f"Retraining timestamp: {datetime.now(timezone.utc).isoformat()}")

        logger.info("===== Retraining completed and model updated =====")
    except (FileNotFoundError, ValueError) as err:
        logger.error(f"Validation error: {err}")
        sys.exit(1)
    except Exception as err:  # pragma: no cover
        logger.error(f"Unexpected error: {err}")
        sys.exit(1)


if __name__ == "__main__":
    main()
