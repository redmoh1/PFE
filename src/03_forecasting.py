"""Phase 3: Sales Forecasting with enhanced error handling and metrics."""

import sys
import logging
from pathlib import Path
from typing import Tuple

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# Paths & Logging
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
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / 'forecasting.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def load_and_prepare_data(input_path: Path) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
    """Load and aggregate monthly sales data with validation."""
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    df = pd.read_csv(input_path)
    logger.info(f"Loaded {len(df)} records from {input_path}")
    
    if "OrderDate" not in df.columns or "TotalPrice" not in df.columns:
        raise ValueError("Missing required columns: OrderDate, TotalPrice")
    
    df["OrderDate"] = pd.to_datetime(df["OrderDate"], errors='coerce')
    invalid_dates = df["OrderDate"].isna().sum()
    if invalid_dates > 0:
        logger.warning(f"Dropping {invalid_dates} rows with invalid OrderDate")
        df = df.dropna(subset=["OrderDate"])
    
    if len(df) == 0:
        raise ValueError("No valid data after date parsing")
    
    # Use freq="MS" (Month Start) for stable cross-version pandas compatibility
    # Avoids deprecated/unstable "M" and "ME" aliases
    df = df.set_index("OrderDate")
    monthly_sales = (
        df
        .resample("MS")["TotalPrice"]
        .sum()
        .reset_index()
    )
    monthly_sales.columns = ["OrderDate", "TotalPrice"]
    
    # Filter out any months with zero sales (incomplete data)
    monthly_sales = monthly_sales[monthly_sales["TotalPrice"] > 0]
    
    if len(monthly_sales) < 3:
        raise ValueError(f"Insufficient monthly data for forecasting (have {len(monthly_sales)} months, need at least 3)")
    
    logger.info(f"Aggregated {len(df)} records into {len(monthly_sales)} monthly periods")
    
    monthly_sales["TimeIndex"] = range(len(monthly_sales))
    X = monthly_sales[["TimeIndex"]]
    y = monthly_sales["TotalPrice"]
    
    return monthly_sales, X, y


def train_forecast_model(X: pd.DataFrame, y: pd.Series) -> Tuple[LinearRegression, dict]:
    """Train model and compute evaluation metrics."""
    logger.info("Training Linear Regression model...")
    
    model = LinearRegression()
    model.fit(X, y)
    
    y_pred = model.predict(X)
    metrics = {
        "R2_Score": r2_score(y, y_pred),
        "MAE": mean_absolute_error(y, y_pred),
        "RMSE": np.sqrt(mean_squared_error(y, y_pred))
    }
    
    logger.info(f"Model R2 Score: {metrics['R2_Score']:.4f}")
    logger.info(f"Model MAE: {metrics['MAE']:,.2f}")
    logger.info(f"Model RMSE: {metrics['RMSE']:,.2f}")
    
    return model, metrics


def generate_forecast(model: LinearRegression, monthly_sales: pd.DataFrame,
                     periods: int = 6) -> Tuple[np.ndarray, pd.DatetimeIndex]:
    """Generate future sales forecast."""
    logger.info(f"Generating {periods}-month forecast...")
    
    future_index = range(len(monthly_sales), len(monthly_sales) + periods)
    future_X = pd.DataFrame({"TimeIndex": future_index})
    future_sales = model.predict(future_X)
    
    # Use freq="MS" (Month Start) for stable cross-version pandas compatibility
    last_date = monthly_sales["OrderDate"].iloc[-1]
    future_dates = pd.date_range(
        start=last_date + pd.DateOffset(months=1),
        periods=periods,
        freq="MS"
    )
    
    return future_sales, future_dates


def plot_and_save_forecast(monthly_sales: pd.DataFrame, y: pd.Series,
                          future_dates: pd.DatetimeIndex, future_sales: np.ndarray,
                          plots_dir: Path) -> None:
    """Generate and save forecast visualization at 300 DPI."""
    logger.info("Generating forecast visualization...")
    
    plt.style.use('seaborn-v0_8-darkgrid')
    fig, ax = plt.subplots(figsize=(12, 6))
    
    ax.plot(monthly_sales["OrderDate"], y, marker='o', linewidth=2,
            markersize=8, label='Actual Sales', color='#2E86AB')
    ax.plot(future_dates, future_sales, marker='x', linewidth=2,
            markersize=8, linestyle='--', label='Forecast', color='#A23B72')
    
    ax.set_xlabel("Date", fontsize=12)
    ax.set_ylabel("Sales Revenue", fontsize=12)
    ax.set_title("Sales Forecast (6 Months Ahead)", fontsize=14, fontweight='bold', pad=20)
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    
    plot_path = plots_dir / "sales_forecast.png"
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    logger.info(f"Forecast plot saved to {plot_path}")


def main() -> None:
    """Main execution for Phase 3: Sales Forecasting."""
    try:
        logger.info("=" * 60)
        logger.info("Phase 3: Sales Forecasting Started")
        logger.info("=" * 60)
        
        input_path = DATA_DIR / "cleaned_dataset.csv"
        monthly_sales, X, y = load_and_prepare_data(input_path)
        
        model, metrics = train_forecast_model(X, y)
        
        future_sales, future_dates = generate_forecast(model, monthly_sales, periods=6)
        
        plot_and_save_forecast(monthly_sales, y, future_dates, future_sales, PLOTS_DIR)
        
        forecast_df = pd.DataFrame({
            "OrderDate": future_dates,
            "ForecastedSales": future_sales
        })
        
        output_path = DATA_DIR / "sales_forecast.csv"
        forecast_df.to_csv(output_path, index=False)
        logger.info(f"Forecast saved to {output_path} with {len(forecast_df)} periods")
        
        logger.info("=" * 60)
        logger.info("Phase 3: Sales Forecasting Completed Successfully")
        logger.info("=" * 60)
        
    except FileNotFoundError as e:
        logger.error(f"File error: {e}")
        sys.exit(1)
    except ValueError as e:
        logger.error(f"Data validation error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
