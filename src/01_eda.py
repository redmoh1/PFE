"""
Sales Intelligence Project - Phase 1: Data Collection & EDA
READY VERSION – generates merged_data.csv for Phase 2
"""

import logging
import sys
from pathlib import Path
from typing import Dict

import pandas as pd
import matplotlib.pyplot as plt

# -------------------------------------------------
# Paths & Logging
# -------------------------------------------------
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
PLOTS_DIR = OUTPUT_DIR / "plots"
LOGS_DIR = BASE_DIR / "logs"

OUTPUT_DIR.mkdir(exist_ok=True)
PLOTS_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "eda.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

# -------------------------------------------------
# Normalization
# -------------------------------------------------
def normalize_sales_df(sales: pd.DataFrame) -> pd.DataFrame:
    sales = sales.copy()

    # Rename common aliases
    rename_map = {
        "order_id": "OrderID",
        "customer_id": "CustomerID",
        "order_date": "OrderDate",
        "price": "Price",
        "quantity": "Quantity",
        "product": "Product",
    }
    for old, new in rename_map.items():
        if old in sales.columns and new not in sales.columns:
            sales.rename(columns={old: new}, inplace=True)

    # OrderDate (MANDATORY)
    if "OrderDate" not in sales.columns:
        raise ValueError("OrderDate is mandatory in sales data")
    sales["OrderDate"] = pd.to_datetime(sales["OrderDate"], errors="coerce")
    if sales["OrderDate"].isna().any():
        raise ValueError("Invalid OrderDate values found")

    # TotalPrice
    if "TotalPrice" not in sales.columns:
        if {"Price", "Quantity"}.issubset(sales.columns):
            sales["TotalPrice"] = (
                pd.to_numeric(sales["Price"], errors="coerce").fillna(0)
                * pd.to_numeric(sales["Quantity"], errors="coerce").fillna(0)
            )
            logger.info("Computed TotalPrice from Price * Quantity")
        else:
            sales["TotalPrice"] = 0.0
            logger.warning("TotalPrice missing – defaulting to 0")
    else:
        sales["TotalPrice"] = pd.to_numeric(sales["TotalPrice"], errors="coerce").fillna(0)

    return sales


def normalize_customers_df(customers: pd.DataFrame) -> pd.DataFrame:
    customers = customers.copy()
    if "city" in customers.columns and "City" not in customers.columns:
        customers.rename(columns={"city": "City"}, inplace=True)
    if "City" in customers.columns:
        customers["City"] = customers["City"].fillna("Unknown")
    return customers


# -------------------------------------------------
# Load Data
# -------------------------------------------------
def load_data():
    logger.info("=" * 60)
    logger.info("DATA LOADING PHASE")
    logger.info("=" * 60)

    sales_path = DATA_DIR / "sales.csv"
    if not sales_path.exists():
        raise FileNotFoundError("sales.csv is mandatory")

    sales = pd.read_csv(sales_path)
    logger.info(f"[OK] Loaded {len(sales)} sales records (MANDATORY)")

    customers_path = DATA_DIR / "customers.csv"
    customers = pd.read_csv(customers_path) if customers_path.exists() else pd.DataFrame()
    if customers.empty:
        logger.warning("[WARN] customers.csv not found – continuing without customers")

    reviews = pd.DataFrame()
    for name in ["customer_reviews.csv", "reviews.csv"]:
        path = DATA_DIR / name
        if path.exists():
            reviews = pd.read_csv(path)
            logger.info(f"[OK] Loaded {len(reviews)} review records from {name}")
            break

    return sales, customers, reviews


# -------------------------------------------------
# Cleaning
# -------------------------------------------------
def clean_data(customers: pd.DataFrame, sales: pd.DataFrame):
    logger.info("Cleaning data...")

    if not customers.empty and "CustomerID" in customers.columns:
        customers = customers.drop_duplicates(subset=["CustomerID"])

    initial = len(sales)
    sales = sales.dropna(subset=["OrderDate"])

    if (sales["TotalPrice"] < 0).any():
        sales = sales[sales["TotalPrice"] >= 0]

    removed = initial - len(sales)
    if removed > 0:
        logger.warning(f"Removed {removed} invalid sales records")

    logger.info("Data cleaning completed")
    return customers, sales


# -------------------------------------------------
# Merge
# -------------------------------------------------
def merge_data(sales: pd.DataFrame, customers: pd.DataFrame) -> pd.DataFrame:
    logger.info("=" * 60)
    logger.info("DATA MERGING PHASE")
    logger.info("=" * 60)

    if not customers.empty and "CustomerID" in sales.columns and "CustomerID" in customers.columns:
        df = pd.merge(sales, customers, on="CustomerID", how="left")
        logger.info(f"[OK] Merge complete: {len(df)} records")
    else:
        df = sales.copy()
        logger.info("[SKIP] No customer enrichment applied")

    return df


# -------------------------------------------------
# KPIs
# -------------------------------------------------
def compute_kpis(df: pd.DataFrame) -> Dict[str, float]:
    return {
        "Total Sales Revenue": df["TotalPrice"].sum(),
        "Total Orders": df["OrderID"].nunique(),
        "Total Customers": df["CustomerID"].nunique() if "CustomerID" in df.columns else 0,
        "Average Order Value": df["TotalPrice"].mean(),
        "Median Order Value": df["TotalPrice"].median(),
        "Total Products Sold": df["Product"].nunique() if "Product" in df.columns else 0,
    }


# -------------------------------------------------
# EDA
# -------------------------------------------------
def perform_eda(df: pd.DataFrame):
    logger.info("Performing EDA...")

    df["Month"] = df["OrderDate"].dt.to_period("M").astype(str)
    monthly_sales = df.groupby("Month")["TotalPrice"].sum()

    top_products = (
        df.groupby("Product")["TotalPrice"]
        .sum()
        .sort_values(ascending=False)
        .head(5)
    )

    if "City" in df.columns:
        sales_by_city = df.groupby("City")["TotalPrice"].sum().sort_values(ascending=False)
    else:
        logger.info("[SKIP] City-based EDA skipped")
        sales_by_city = pd.Series(dtype=float)

    return monthly_sales, top_products, sales_by_city


# -------------------------------------------------
# Plots
# -------------------------------------------------
def plot_results(monthly_sales, top_products, sales_by_city):
    plt.figure(figsize=(10, 5))
    monthly_sales.plot(marker="o")
    plt.title("Monthly Sales")
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "monthly_sales.png")
    plt.close()

    plt.figure(figsize=(8, 5))
    top_products.plot(kind="bar")
    plt.title("Top Products")
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "top_products.png")
    plt.close()

    if not sales_by_city.empty:
        plt.figure(figsize=(8, 5))
        sales_by_city.plot(kind="bar")
        plt.title("Sales by City")
        plt.tight_layout()
        plt.savefig(PLOTS_DIR / "sales_by_city.png")
        plt.close()


# -------------------------------------------------
# Main
# -------------------------------------------------
def main():
    try:
        logger.info("=" * 60)
        logger.info("PHASE 1: DATA COLLECTION & EDA STARTED")
        logger.info("=" * 60)

        sales, customers, reviews = load_data()
        sales = normalize_sales_df(sales)
        customers = normalize_customers_df(customers)

        customers, sales = clean_data(customers, sales)
        df = merge_data(sales, customers)

        # 🔥 IMPORTANT: save for Phase 2
        df.to_csv(DATA_DIR / "merged_data.csv", index=False)
        logger.info("[OK] merged_data.csv generated for Phase 2")
        
        # Also save as cleaned_dataset.csv for ML pipelines (04_rfm, 05_recommendation, etc.)
        df.to_csv(DATA_DIR / "cleaned_dataset.csv", index=False)
        logger.info("[OK] cleaned_dataset.csv generated for ML pipelines")

        kpis = compute_kpis(df)
        for k, v in kpis.items():
            logger.info(f"{k}: {v:,.2f}")

        monthly_sales, top_products, sales_by_city = perform_eda(df)
        plot_results(monthly_sales, top_products, sales_by_city)

        logger.info("PHASE 1 COMPLETED SUCCESSFULLY")

    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
