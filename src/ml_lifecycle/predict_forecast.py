"""Generate forward-looking sales forecasts using the persisted model."""

import sys
import logging
from pathlib import Path
from typing import Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
MODEL_PATH = Path(__file__).resolve().parent / "model_registry" / "sales_forecast_model.pkl"
OUTPUT_PATH = DATA_DIR / "sales_forecast_future.csv"
MAX_PERIODS = 60  # safeguard against runaway horizon requests

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
        raise ValueError("Need at least 3 months to infer a trend")

    monthly["MonthIndex"] = np.arange(len(monthly))
    return monthly


def load_model(model_path: Path) -> LinearRegression:
    """Reload the persisted forecasting model."""
    if not model_path.exists():
        raise FileNotFoundError(f"Saved model not found: {model_path}")
    return joblib.load(model_path)


def build_future_features(monthly: pd.DataFrame, periods: int) -> Tuple[pd.DataFrame, pd.DatetimeIndex]:
    """Build future MonthIndex feature matrix and calendar months to predict."""
    if periods <= 0:
        raise ValueError("Number of periods must be positive")
    if periods > MAX_PERIODS:
        raise ValueError(f"Requested horizon {periods} exceeds max supported {MAX_PERIODS}")

    last_index = int(monthly["MonthIndex"].max())
    future_indices = np.arange(last_index + 1, last_index + periods + 1)
    future_X = pd.DataFrame({"MonthIndex": future_indices})

    last_date = monthly["OrderDate"].max()
    future_dates = pd.date_range(
        start=last_date + pd.offsets.MonthBegin(1), periods=periods, freq="MS"
    )
    return future_X, future_dates


def parse_periods_from_args(argv: list) -> int:
    """Parse the number of months to predict from CLI args, defaulting to 6."""
    if len(argv) < 2:
        return 6
    try:
        value = int(argv[1])
        if value <= 0:
            raise ValueError
        return min(value, MAX_PERIODS)
    except ValueError:
        raise ValueError("Argument for number of months must be an integer")


def log_forecast_summary(forecast_df: pd.DataFrame) -> None:
    """Log a concise preview of the forecast horizon and values."""
    if forecast_df.empty:
        logger.warning("Forecast dataframe is empty; nothing to persist")
        return
    start_month = forecast_df["MonthStart"].min().date()
    end_month = forecast_df["MonthStart"].max().date()
    logger.info(
        f"Forecast window: {start_month} -> {end_month} | Rows: {len(forecast_df)} | "
        f"Min: {forecast_df['ForecastedSales'].min():.2f}, Max: {forecast_df['ForecastedSales'].max():.2f}"
    )


def main() -> None:
    """Load the saved model and produce forward forecasts, saving to CSV."""
    try:
        logger.info("===== ML Lifecycle: Predict future sales =====")
        input_path = DATA_DIR / "cleaned_dataset.csv"
        periods = parse_periods_from_args(sys.argv)
        logger.info(f"Forecasting horizon: {periods} month(s)")

        monthly = load_monthly_sales(input_path)
        model = load_model(MODEL_PATH)
        logger.info(f"Loaded model from {MODEL_PATH}")

        future_X, future_dates = build_future_features(monthly, periods)
        forecasts = model.predict(future_X)

        forecast_df = pd.DataFrame(
            {"MonthStart": future_dates, "ForecastedSales": forecasts}
        )
        OUTPUT_PATH.parent.mkdir(exist_ok=True)
        forecast_df.to_csv(OUTPUT_PATH, index=False)
        logger.info(f"Saved future forecast to {OUTPUT_PATH} ({len(forecast_df)} rows)")

        log_forecast_summary(forecast_df)

        logger.info("===== Prediction step completed =====")
    except (FileNotFoundError, ValueError) as err:
        logger.error(f"Validation error: {err}")
        sys.exit(1)
    except Exception as err:  # pragma: no cover
        logger.error(f"Unexpected error: {err}")
        sys.exit(1)


if __name__ == "__main__":
    main()
