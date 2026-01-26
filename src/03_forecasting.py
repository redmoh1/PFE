"""
Phase 3: Sales Forecasting
Flexible & Robust Version (Academic + Production Ready)
"""

import sys
import logging
from pathlib import Path
from typing import Tuple

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# -------------------------------------------------
# Paths & Logging
# -------------------------------------------------
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
OUTPUT_DIR = BASE_DIR / "output"
PLOTS_DIR = OUTPUT_DIR / "plots"

LOGS_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
PLOTS_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "forecasting.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

# -------------------------------------------------
# Load & Prepare Data
# -------------------------------------------------
def load_and_prepare_data(input_path: Path) -> pd.DataFrame:
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    df = pd.read_csv(input_path)
    logger.info(f"Loaded {len(df)} records from {input_path}")

    if not {"OrderDate", "TotalPrice"}.issubset(df.columns):
        raise ValueError("Missing required columns: OrderDate, TotalPrice")

    df["OrderDate"] = pd.to_datetime(df["OrderDate"], errors="coerce")
    df = df.dropna(subset=["OrderDate"])

    if df.empty:
        raise ValueError("No valid rows after date parsing")

    df = df.set_index("OrderDate")

    monthly_sales = (
        df.resample("MS")["TotalPrice"]
        .sum()
        .reset_index()
    )

    monthly_sales = monthly_sales[monthly_sales["TotalPrice"] > 0]

    if monthly_sales.empty:
        raise ValueError("No valid monthly sales data")

    monthly_sales["TimeIndex"] = range(len(monthly_sales))
    logger.info(f"Prepared {len(monthly_sales)} monthly data points")

    return monthly_sales

# -------------------------------------------------
# Forecasting Strategies
# -------------------------------------------------
def regression_forecast(monthly_sales: pd.DataFrame, periods: int):
    X = monthly_sales[["TimeIndex"]]
    y = monthly_sales["TotalPrice"]

    model = LinearRegression()
    model.fit(X, y)

    y_pred = model.predict(X)
    metrics = {
        "R2": r2_score(y, y_pred),
        "MAE": mean_absolute_error(y, y_pred),
        "RMSE": np.sqrt(mean_squared_error(y, y_pred)),
    }

    future_index = range(len(monthly_sales), len(monthly_sales) + periods)
    future_X = pd.DataFrame({"TimeIndex": future_index})
    future_sales = model.predict(future_X)

    logger.info("Regression-based forecasting applied")
    for k, v in metrics.items():
        logger.info(f"{k}: {v:,.2f}")

    return future_sales, metrics


def naive_forecast(last_value: float, periods: int):
    logger.warning("Using NAIVE forecasting (insufficient historical data)")
    return np.array([last_value] * periods), {
        "Strategy": "Naive (Last Value Repetition)"
    }

# -------------------------------------------------
# Plot
# -------------------------------------------------
def plot_forecast(monthly_sales, future_dates, future_sales):
    plt.style.use("seaborn-v0_8-darkgrid")
    fig, ax = plt.subplots(figsize=(12, 6))

    ax.plot(
        monthly_sales["OrderDate"],
        monthly_sales["TotalPrice"],
        marker="o",
        label="Actual Sales",
    )
    ax.plot(
        future_dates,
        future_sales,
        marker="x",
        linestyle="--",
        label="Forecast",
    )

    ax.set_title("Sales Forecast", fontsize=14, fontweight="bold")
    ax.set_xlabel("Date")
    ax.set_ylabel("Revenue")
    ax.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()

    path = PLOTS_DIR / "sales_forecast.png"
    plt.savefig(path, dpi=300)
    plt.close()

    logger.info(f"Forecast plot saved to {path}")

# -------------------------------------------------
# Main
# -------------------------------------------------
def main():
    try:
        logger.info("=" * 60)
        logger.info("PHASE 3: SALES FORECASTING")
        logger.info("=" * 60)

        input_path = DATA_DIR / "cleaned_dataset.csv"
        monthly_sales = load_and_prepare_data(input_path)

        periods = 6
        n_months = len(monthly_sales)

        if n_months >= 3:
            future_sales, metrics = regression_forecast(monthly_sales, periods)
        elif n_months == 2:
            logger.warning("Only 2 months available – regression without reliability metrics")
            future_sales, metrics = regression_forecast(monthly_sales, periods)
        else:
            last_value = monthly_sales["TotalPrice"].iloc[-1]
            future_sales, metrics = naive_forecast(last_value, periods)

        last_date = monthly_sales["OrderDate"].iloc[-1]
        future_dates = pd.date_range(
            start=last_date + pd.DateOffset(months=1),
            periods=periods,
            freq="MS",
        )

        plot_forecast(monthly_sales, future_dates, future_sales)

        forecast_df = pd.DataFrame({
            "OrderDate": future_dates,
            "ForecastedSales": future_sales
        })

        output_path = DATA_DIR / "sales_forecast.csv"
        forecast_df.to_csv(output_path, index=False)
        logger.info(f"Forecast saved to {output_path}")

        logger.info("=" * 60)
        logger.info("PHASE 3 COMPLETED SUCCESSFULLY")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Forecasting failed: {e}")
        sys.exit(1)

# -------------------------------------------------
if __name__ == "__main__":
    main()
