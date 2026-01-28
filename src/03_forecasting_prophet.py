"""
Phase 3: Sales Forecasting - Prophet Implementation
Scientific Time-Series Forecasting with Seasonality and Trend Decomposition

WHY PROPHET:
- Handles seasonality (daily, weekly, yearly)
- Provides confidence intervals
- Robust to missing data and outliers
- Interpretable trend and seasonal components
- Better than Linear Regression for real-world sales data

COMPARISON:
- Linear Regression: Baseline (kept for comparison)
- Prophet: Production model with proper time-series handling
"""

import sys
import logging
from pathlib import Path
from typing import Dict, Tuple, Optional

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# Prophet import with fallback
try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False
    logging.warning("Prophet not installed. Install with: pip install prophet")

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
        logging.FileHandler(LOGS_DIR / "forecasting_prophet.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


# -------------------------------------------------
# Data Loading & Preparation
# -------------------------------------------------
def find_sales_file(company_name: str = None) -> Path:
    """Find sales data file in multiple possible locations.
    
    Search order:
    1. data/{company}/sales/cleaned_sales.csv
    2. data/{company}/sales/*.csv (any CSV)
    3. data/cleaned_dataset.csv
    4. data/sales.csv
    5. data/merged_data.csv
    """
    possible_paths = []
    
    if company_name:
        company_dir = DATA_DIR / company_name / "sales"
        possible_paths.append(company_dir / "cleaned_sales.csv")
        # Check for any CSV in company sales folder
        if company_dir.exists():
            for f in company_dir.glob("*.csv"):
                possible_paths.append(f)
    
    # Fallback to main data directory
    possible_paths.extend([
        DATA_DIR / "cleaned_dataset.csv",
        DATA_DIR / "sales.csv",
        DATA_DIR / "merged_data.csv",
    ])
    
    for path in possible_paths:
        if path.exists():
            logger.info(f"Found sales data at: {path}")
            return path
    
    raise FileNotFoundError(
        f"No sales data found. Searched in:\n" + 
        "\n".join(f"  - {p}" for p in possible_paths[:5])
    )


def load_and_prepare_data(input_path: Path) -> pd.DataFrame:
    """Load sales data and aggregate to monthly level.
    
    Returns:
        DataFrame with OrderDate and TotalPrice columns
    """
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    df = pd.read_csv(input_path)
    logger.info(f"Loaded {len(df)} records from {input_path}")

    # Auto-detect date and revenue columns
    date_col = None
    revenue_col = None
    
    date_candidates = ["OrderDate", "Sale_Date", "Order_Date", "Date", "order_date", "date"]
    revenue_candidates = ["TotalPrice", "Price", "Sales_Amount", "SalesAmount", "Revenue", "Sales", "Amount", "amount", "price", "total"]
    
    for col in date_candidates:
        if col in df.columns:
            date_col = col
            break
    
    for col in revenue_candidates:
        if col in df.columns:
            revenue_col = col
            break
    
    if not date_col:
        raise ValueError(f"No date column found. Available: {list(df.columns)}")
    if not revenue_col:
        raise ValueError(f"No revenue column found. Available: {list(df.columns)}")
    
    logger.info(f"Using columns: date={date_col}, revenue={revenue_col}")
    
    # Rename to standard names
    df = df.rename(columns={date_col: "OrderDate", revenue_col: "TotalPrice"})

    df["OrderDate"] = pd.to_datetime(df["OrderDate"], errors="coerce")
    df = df.dropna(subset=["OrderDate"])

    if df.empty:
        raise ValueError("No valid rows after date parsing")

    # Monthly aggregation
    monthly_sales = (
        df.groupby(pd.Grouper(key="OrderDate", freq="MS"))["TotalPrice"]
        .sum()
        .reset_index()
        .sort_values("OrderDate")
    )

    monthly_sales = monthly_sales[monthly_sales["TotalPrice"] > 0]

    if len(monthly_sales) < 3:
        raise ValueError("Need at least 3 months of data for forecasting")

    logger.info(f"Prepared {len(monthly_sales)} monthly data points")
    return monthly_sales


# -------------------------------------------------
# Baseline: Linear Regression (for comparison)
# -------------------------------------------------
def baseline_linear_regression(monthly_sales: pd.DataFrame, periods: int) -> Dict:
    """Baseline model: Simple linear regression on time index.
    
    Kept for comparison purposes.
    """
    monthly_sales = monthly_sales.copy()
    monthly_sales["TimeIndex"] = range(len(monthly_sales))
    
    X = monthly_sales[["TimeIndex"]]
    y = monthly_sales["TotalPrice"]

    model = LinearRegression()
    model.fit(X, y)

    y_pred = model.predict(X)
    metrics = {
        "model": "LinearRegression",
        "R2": float(r2_score(y, y_pred)),
        "MAE": float(mean_absolute_error(y, y_pred)),
        "RMSE": float(np.sqrt(mean_squared_error(y, y_pred))),
    }

    # Generate future predictions
    future_index = range(len(monthly_sales), len(monthly_sales) + periods)
    future_X = pd.DataFrame({"TimeIndex": future_index})
    future_sales = model.predict(future_X)
    
    # Create future dates
    last_date = monthly_sales["OrderDate"].max()
    future_dates = pd.date_range(start=last_date + pd.DateOffset(months=1), periods=periods, freq="MS")
    
    forecast_df = pd.DataFrame({
        "ds": future_dates,
        "yhat": future_sales,
        "yhat_lower": future_sales * 0.9,  # Simple ±10% interval
        "yhat_upper": future_sales * 1.1,
    })

    logger.info(f"Linear Regression - R²: {metrics['R2']:.4f}, MAE: {metrics['MAE']:,.2f}, RMSE: {metrics['RMSE']:,.2f}")
    
    return {
        "metrics": metrics,
        "forecast": forecast_df,
        "historical": monthly_sales[["OrderDate", "TotalPrice"]].rename(columns={"OrderDate": "ds", "TotalPrice": "y"}),
    }


# -------------------------------------------------
# Production: Prophet Forecasting
# -------------------------------------------------
def prophet_forecast(monthly_sales: pd.DataFrame, periods: int, 
                     yearly_seasonality: bool = True,
                     weekly_seasonality: bool = False,
                     changepoint_prior_scale: float = 0.05) -> Dict:
    """Production-grade time-series forecasting using Prophet.
    
    Args:
        monthly_sales: DataFrame with OrderDate and TotalPrice
        periods: Number of months to forecast ahead
        yearly_seasonality: Enable yearly seasonal patterns
        weekly_seasonality: Enable weekly patterns (usually False for monthly data)
        changepoint_prior_scale: Flexibility of trend changes (0.001-0.5)
        
    Returns:
        Dictionary containing:
        - metrics: MAE, RMSE, MAPE on historical data
        - forecast: Future predictions with confidence intervals
        - components: Trend and seasonality decomposition
        - historical: Historical data with predictions
    """
    if not PROPHET_AVAILABLE:
        raise ImportError("Prophet not installed. Run: pip install prophet")
    
    # Prepare data in Prophet format (ds, y)
    df_prophet = monthly_sales[["OrderDate", "TotalPrice"]].copy()
    df_prophet.columns = ["ds", "y"]
    
    # Initialize Prophet with custom settings
    model = Prophet(
        yearly_seasonality=yearly_seasonality,
        weekly_seasonality=weekly_seasonality,
        daily_seasonality=False,  # Not relevant for monthly data
        changepoint_prior_scale=changepoint_prior_scale,  # Controls trend flexibility
        seasonality_mode='multiplicative',  # Better for sales data with growing trends
        interval_width=0.95,  # 95% confidence interval
    )
    
    # Optional: Add custom seasonality (e.g., quarterly patterns)
    # model.add_seasonality(name='quarterly', period=91.25, fourier_order=5)
    
    # Fit the model
    logger.info("Training Prophet model...")
    model.fit(df_prophet)
    
    # Make predictions on historical data for validation
    historical_pred = model.predict(df_prophet)
    
    # Calculate metrics on historical data
    y_true = df_prophet["y"].values
    y_pred = historical_pred["yhat"].values
    
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    mape = np.mean(np.abs((y_true - y_pred) / y_true)) * 100  # Mean Absolute Percentage Error
    
    metrics = {
        "model": "Prophet",
        "MAE": float(mae),
        "RMSE": float(rmse),
        "MAPE": float(mape),  # Percentage error - easier to interpret
    }
    
    logger.info(f"Prophet - MAE: {mae:,.2f}, RMSE: {rmse:,.2f}, MAPE: {mape:.2f}%")
    
    # Generate future predictions
    future = model.make_future_dataframe(periods=periods, freq="MS")
    forecast = model.predict(future)
    
    # Split into historical and future
    forecast_future = forecast.tail(periods)[["ds", "yhat", "yhat_lower", "yhat_upper"]].reset_index(drop=True)
    forecast_historical = forecast.head(len(df_prophet))[["ds", "yhat", "yhat_lower", "yhat_upper"]]
    
    # Extract trend and seasonality components
    components = {
        "trend": forecast[["ds", "trend"]].to_dict("records"),
        "yearly": forecast[["ds", "yearly"]].to_dict("records") if yearly_seasonality else None,
    }
    
    return {
        "metrics": metrics,
        "forecast": forecast_future,
        "historical": df_prophet.merge(forecast_historical, on="ds"),
        "components": components,
        "model_params": {
            "changepoint_prior_scale": changepoint_prior_scale,
            "seasonality_mode": "multiplicative",
            "interval_width": 0.95,
        }
    }


# -------------------------------------------------
# Visualization
# -------------------------------------------------
def plot_forecast_comparison(baseline_result: Dict, prophet_result: Dict, 
                            company_name: str, output_path: Path):
    """Create comparison plot of baseline vs Prophet forecasts."""
    
    fig, axes = plt.subplots(2, 1, figsize=(14, 10))
    
    # --- Baseline Plot ---
    ax1 = axes[0]
    hist_baseline = baseline_result["historical"]
    forecast_baseline = baseline_result["forecast"]
    
    ax1.plot(hist_baseline["ds"], hist_baseline["y"], 'o-', label="Historical Sales", color="blue", alpha=0.6)
    ax1.plot(forecast_baseline["ds"], forecast_baseline["yhat"], 's--', label="Linear Regression Forecast", color="orange")
    ax1.fill_between(forecast_baseline["ds"], 
                     forecast_baseline["yhat_lower"], 
                     forecast_baseline["yhat_upper"], 
                     alpha=0.2, color="orange", label="Simple ±10% Interval")
    ax1.set_title(f"Baseline: Linear Regression - {company_name}", fontsize=12, fontweight="bold")
    ax1.set_xlabel("Date")
    ax1.set_ylabel("Sales")
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # --- Prophet Plot ---
    ax2 = axes[1]
    hist_prophet = prophet_result["historical"]
    forecast_prophet = prophet_result["forecast"]
    
    ax2.plot(hist_prophet["ds"], hist_prophet["y"], 'o-', label="Historical Sales", color="blue", alpha=0.6)
    ax2.plot(hist_prophet["ds"], hist_prophet["yhat"], '-', label="Prophet Fitted", color="green", alpha=0.5)
    ax2.plot(forecast_prophet["ds"], forecast_prophet["yhat"], 's-', label="Prophet Forecast", color="red")
    ax2.fill_between(forecast_prophet["ds"], 
                     forecast_prophet["yhat_lower"], 
                     forecast_prophet["yhat_upper"], 
                     alpha=0.3, color="red", label="95% Confidence Interval")
    ax2.set_title(f"Production: Prophet with Seasonality - {company_name}", fontsize=12, fontweight="bold")
    ax2.set_xlabel("Date")
    ax2.set_ylabel("Sales")
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info(f"Forecast comparison saved to {output_path}")


def plot_prophet_components(prophet_result: Dict, company_name: str, output_path: Path):
    """Plot trend and seasonality decomposition."""
    
    components = prophet_result["components"]
    
    fig, axes = plt.subplots(2, 1, figsize=(12, 8))
    
    # Trend
    trend_data = pd.DataFrame(components["trend"])
    axes[0].plot(trend_data["ds"], trend_data["trend"], color="darkblue", linewidth=2)
    axes[0].set_title(f"Trend Component - {company_name}", fontweight="bold")
    axes[0].set_xlabel("Date")
    axes[0].set_ylabel("Trend")
    axes[0].grid(True, alpha=0.3)
    
    # Yearly Seasonality
    if components["yearly"]:
        yearly_data = pd.DataFrame(components["yearly"])
        axes[1].plot(yearly_data["ds"], yearly_data["yearly"], color="darkgreen", linewidth=2)
        axes[1].set_title(f"Yearly Seasonality - {company_name}", fontweight="bold")
        axes[1].set_xlabel("Date")
        axes[1].set_ylabel("Seasonal Effect")
        axes[1].grid(True, alpha=0.3)
    else:
        axes[1].text(0.5, 0.5, "No Yearly Seasonality", ha="center", va="center", fontsize=14)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info(f"Components plot saved to {output_path}")


# -------------------------------------------------
# Main Execution
# -------------------------------------------------
def run_forecasting(company_name: str, periods: int = 6, use_prophet: bool = True) -> Dict:
    """Run forecasting pipeline with both baseline and Prophet.
    
    Args:
        company_name: Name of company (for file paths)
        periods: Number of months to forecast
        use_prophet: Whether to use Prophet (True) or only baseline (False)
        
    Returns:
        Dictionary with results from both models
    """
    # Find sales data file (searches multiple locations)
    input_file = find_sales_file(company_name)
    
    # Load data
    monthly_sales = load_and_prepare_data(input_file)
    
    results = {}
    
    # 1. Baseline Model
    logger.info("Running baseline Linear Regression...")
    baseline_result = baseline_linear_regression(monthly_sales, periods)
    results["baseline"] = baseline_result
    
    # 2. Prophet Model
    if use_prophet and PROPHET_AVAILABLE:
        logger.info("Running Prophet forecasting...")
        try:
            prophet_result = prophet_forecast(monthly_sales, periods)
            results["prophet"] = prophet_result
            
            # Save forecasts
            output_csv = OUTPUT_DIR / f"{company_name}_forecast_prophet.csv"
            prophet_result["forecast"].to_csv(output_csv, index=False)
            logger.info(f"Prophet forecast saved to {output_csv}")
            
            # Generate plots
            comparison_plot = PLOTS_DIR / f"{company_name}_forecast_comparison.png"
            plot_forecast_comparison(baseline_result, prophet_result, company_name, comparison_plot)
            
            components_plot = PLOTS_DIR / f"{company_name}_forecast_components.png"
            plot_prophet_components(prophet_result, company_name, components_plot)
            
        except Exception as e:
            logger.error(f"Prophet forecasting failed: {e}")
            logger.warning("Falling back to baseline only")
    else:
        logger.warning("Prophet not available, using baseline only")
    
    # Save baseline forecast
    baseline_csv = OUTPUT_DIR / f"{company_name}_forecast_baseline.csv"
    baseline_result["forecast"].to_csv(baseline_csv, index=False)
    
    return results


if __name__ == "__main__":
    import sys
    
    company = sys.argv[1] if len(sys.argv) > 1 else "Acme Corp"
    periods = int(sys.argv[2]) if len(sys.argv) > 2 else 6
    
    logger.info(f"Starting forecasting for {company}, {periods} months ahead")
    results = run_forecasting(company, periods)
    
    # Print summary
    print("\n" + "="*60)
    print("FORECASTING RESULTS SUMMARY")
    print("="*60)
    
    for model_name, model_result in results.items():
        print(f"\n{model_name.upper()}:")
        for metric, value in model_result["metrics"].items():
            if isinstance(value, float):
                print(f"  {metric}: {value:,.2f}")
            else:
                print(f"  {metric}: {value}")
    
    print("\n" + "="*60)
