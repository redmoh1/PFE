"""
Phase 3: Sales Forecasting
Flexible & Robust Version (Academic + Production Ready)

=============================================================================
PROBLEM #2 FIX: Hard-Coded Column Assumptions
=============================================================================
This module now uses the Schema Resolver (when available) to auto-detect
column names, making it work with different data schemas.

=============================================================================
PROBLEM #4 FIX: Pipeline Rigidity  
=============================================================================
This module will gracefully fail if:
- No date column is found
- No revenue/value column is found
- Insufficient data for forecasting (<30 rows recommended)

The pipeline controller will skip forecasting if these conditions aren't met.
=============================================================================
"""

import sys
import os
import logging
from pathlib import Path
from typing import Tuple, Optional, Dict

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# -------------------------------------------------
# Paths & Logging
# -------------------------------------------------
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = Path(os.getenv("SI_DATA_DIR", str(BASE_DIR / "data")))
LOGS_DIR = BASE_DIR / "logs"
OUTPUT_DIR = Path(os.getenv("SI_OUTPUT_DIR", str(BASE_DIR / "output")))
PLOTS_DIR = Path(os.getenv("SI_PLOTS_DIR", str(OUTPUT_DIR / "plots")))
FORECASTS_DIR = Path(os.getenv("SI_FORECASTS_DIR", str(BASE_DIR / "output" / "forecasts")))
TENANT_ROOT = Path(os.getenv("SI_TENANT_ROOT", str(BASE_DIR / "data")))

LOGS_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
PLOTS_DIR.mkdir(exist_ok=True)
FORECASTS_DIR.mkdir(parents=True, exist_ok=True)

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
# Schema Resolver Integration
# -------------------------------------------------
try:
    from schema_resolver import SchemaResolver, SemanticField, can_perform_analysis
    SCHEMA_RESOLVER_AVAILABLE = True
    logger.info("Schema Resolver loaded successfully")
except ImportError:
    SCHEMA_RESOLVER_AVAILABLE = False
    logger.warning("Schema Resolver not available - using fallback column detection")


def resolve_forecasting_columns(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    """
    Resolve required columns for forecasting analysis.
    
    Forecasting requires:
    - date column (ORDER_DATE)
    - value column (TOTAL_PRICE or equivalent)
    
    Returns dict with resolved column names or None if not found.
    """
    if SCHEMA_RESOLVER_AVAILABLE:
        resolver = SchemaResolver()
        result = resolver.resolve(df, "sales")
        
        return {
            "date": result.get_column(SemanticField.ORDER_DATE),
            "value": result.get_column(SemanticField.TOTAL_PRICE)
        }
    else:
        # Fallback detection
        date_cols = ["OrderDate", "Sale_Date", "Order_Date", "Date", "order_date", "ds"]
        value_cols = ["TotalPrice", "Revenue", "Sales", "Amount", "total_price", "yhat"]
        
        date_col = next((c for c in date_cols if c in df.columns), None)
        value_col = next((c for c in value_cols if c in df.columns), None)
        
        return {"date": date_col, "value": value_col}


# -------------------------------------------------
# Load & Prepare Data
# -------------------------------------------------
def find_data_file() -> Path:
    """Find data file in multiple possible locations."""
    possible_paths = [
        OUTPUT_DIR / "cleaned_dataset.csv",
        DATA_DIR / "cleaned_dataset.csv",
        OUTPUT_DIR / "merged_data.csv",
        DATA_DIR / "sales.csv",
        DATA_DIR / "merged_data.csv",
    ]
    
    for path in possible_paths:
        if path.exists():
            logger.info(f"Found data file at: {path}")
            return path
    
    raise FileNotFoundError(
        f"No data file found. Searched in:\n" + 
        "\n".join(f"  - {p}" for p in possible_paths)
    )


def load_and_prepare_data(input_path: Path = None) -> pd.DataFrame:
    """
    Load and prepare data for forecasting.
    
    Uses Schema Resolver to auto-detect column names.
    """
    # Auto-detect file if not provided
    if input_path is None:
        input_path = find_data_file()
        
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    df = pd.read_csv(input_path)
    logger.info(f"Loaded {len(df)} records from {input_path}")

    # Use Schema Resolver to find columns
    resolved = resolve_forecasting_columns(df)
    date_col = resolved.get("date")
    value_col = resolved.get("value")
    
    if not date_col:
        raise ValueError(
            f"No date column found for forecasting. "
            f"Expected one of: OrderDate, Sale_Date, Date, etc. "
            f"Found: {list(df.columns)}"
        )
    
    if not value_col:
        raise ValueError(
            f"No value column found for forecasting. "
            f"Expected one of: TotalPrice, Revenue, Sales, Amount. "
            f"Found: {list(df.columns)}"
        )
    
    logger.info(f"Using columns: date='{date_col}', value='{value_col}'")
    
    # Rename to standard names for processing
    df = df.rename(columns={date_col: "OrderDate", value_col: "TotalPrice"})

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
    """
    Fit linear regression for time-series forecasting.
    
    NOTE: For production use, consider:
    1. Using proper time-series cross-validation (TimeSeriesSplit)
    2. Using Prophet or ARIMA for seasonality handling
    3. Adding proper holdout validation
    
    Current implementation uses all data for training due to limited data points.
    Metrics are in-sample (training) metrics - not true predictive accuracy.
    """
    X = monthly_sales[["TimeIndex"]]
    y = monthly_sales["TotalPrice"]

    n_samples = len(monthly_sales)
    
    # Use temporal train/test split when we have enough data
    if n_samples >= 6:
        # Reserve last 20% for validation (minimum 1 month)
        split_idx = max(int(n_samples * 0.8), n_samples - 2)
        X_train, X_val = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_val = y.iloc[:split_idx], y.iloc[split_idx:]
        
        model = LinearRegression()
        model.fit(X_train, y_train)
        
        # Out-of-sample metrics (more reliable)
        y_val_pred = model.predict(X_val)
        metrics = {
            "R2": r2_score(y_val, y_val_pred),
            "MAE": mean_absolute_error(y_val, y_val_pred),
            "RMSE": np.sqrt(mean_squared_error(y_val, y_val_pred)),
            "validation_months": len(y_val),
            "is_oos_metric": True,  # Out-of-sample
        }
        
        # Retrain on full data for final model
        model.fit(X, y)
        logger.info(f"Used temporal validation: {split_idx} train, {n_samples - split_idx} validation")
    else:
        # Too few samples for proper validation - use all data
        model = LinearRegression()
        model.fit(X, y)
        
        # In-sample metrics (less reliable, marked clearly)
        y_pred = model.predict(X)
        metrics = {
            "R2": r2_score(y, y_pred),
            "MAE": mean_absolute_error(y, y_pred),
            "RMSE": np.sqrt(mean_squared_error(y, y_pred)),
            "is_oos_metric": False,  # In-sample (training metrics)
        }
        logger.warning(f"Only {n_samples} months - using in-sample metrics (not reliable for accuracy)")

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

        # Use auto-detection to find data file
        monthly_sales = load_and_prepare_data()

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

        output_path = FORECASTS_DIR / "sales_forecast.csv"
        alias_path = TENANT_ROOT / "forecast.csv"
        forecast_df.to_csv(output_path, index=False)
        forecast_df.to_csv(alias_path, index=False)
        logger.info(f"Forecast saved to {output_path}")
        logger.info(f"Forecast alias saved to {alias_path}")

        logger.info("=" * 60)
        logger.info("PHASE 3 COMPLETED SUCCESSFULLY")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Forecasting failed: {e}")
        sys.exit(1)

# -------------------------------------------------
if __name__ == "__main__":
    main()
