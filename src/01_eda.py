"""
Sales Intelligence Project - Phase 1: Data Collection & EDA
READY VERSION – generates merged_data.csv for Phase 2

=============================================================================
PROBLEM #2 FIX: Hard-Coded Column Assumptions
=============================================================================
This module now uses the Schema Resolver to auto-detect column names.
Instead of assuming fixed column names (OrderDate, CustomerID, etc.),
the system resolves semantic fields to actual column names dynamically.

=============================================================================
"""

import logging
import os
import sys
from pathlib import Path
from typing import Dict, Optional

import pandas as pd
import matplotlib.pyplot as plt

# -------------------------------------------------
# Paths & Logging
# -------------------------------------------------
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = Path(os.getenv("SI_DATA_DIR", str(BASE_DIR / "data")))
OUTPUT_DIR = Path(os.getenv("SI_OUTPUT_DIR", str(BASE_DIR / "output")))
PLOTS_DIR = Path(os.getenv("SI_PLOTS_DIR", str(OUTPUT_DIR / "plots")))
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
# Schema Resolver Integration
# -------------------------------------------------
try:
    from schema_resolver import (
        SchemaResolver,
        SemanticField,
        SchemaResolutionResult,
    )
    SCHEMA_RESOLVER_AVAILABLE = True
    logger.info("Schema Resolver loaded successfully")
except ImportError:
    SCHEMA_RESOLVER_AVAILABLE = False
    logger.warning("Schema Resolver not available - using fallback column detection")


def resolve_columns(df: pd.DataFrame, dataset_type: str = "sales") -> Dict[str, Optional[str]]:
    """
    Resolve semantic field names to actual column names in the dataframe.
    
    This is the KEY FUNCTION for decoupling business meaning from column names.
    
    Args:
        df: DataFrame to analyze
        dataset_type: Type of dataset
        
    Returns:
        Dict mapping semantic field names to actual column names (or None if not found)
    """
    if SCHEMA_RESOLVER_AVAILABLE:
        resolver = SchemaResolver()
        result = resolver.resolve(df, dataset_type)
        
        # Log the resolution results
        logger.info("=" * 40)
        logger.info("SCHEMA RESOLUTION RESULTS")
        for field, col in result.resolved_columns.items():
            logger.info(f"  {field.value} -> '{col}'")
        if result.unmapped_columns:
            logger.info(f"  Unmapped: {result.unmapped_columns}")
        logger.info("=" * 40)
        
        # Convert to simple dict for backward compatibility
        return {
            "order_date": result.get_column(SemanticField.ORDER_DATE),
            "customer_id": result.get_column(SemanticField.CUSTOMER_ID),
            "order_id": result.get_column(SemanticField.ORDER_ID),
            "product": result.get_column(SemanticField.PRODUCT),
            "quantity": result.get_column(SemanticField.QUANTITY),
            "unit_price": result.get_column(SemanticField.UNIT_PRICE),
            "total_price": result.get_column(SemanticField.TOTAL_PRICE),
            "city": result.get_column(SemanticField.CITY),
        }
    else:
        # Fallback: Manual column detection
        return _fallback_resolve_columns(df)


def _fallback_resolve_columns(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    """Fallback column resolution when Schema Resolver is not available."""
    columns = set(df.columns)
    
    def find_column(candidates):
        for c in candidates:
            if c in columns:
                return c
        return None
    
    return {
        "order_date": find_column(["OrderDate", "order_date", "Sale_Date", "Date"]),
        "customer_id": find_column(["CustomerID", "customer_id", "Customer_ID", "cust_id"]),
        "order_id": find_column(["OrderID", "order_id", "Order_ID", "InvoiceNo"]),
        "product": find_column(["Product", "product", "ProductName", "Item", "Description"]),
        "quantity": find_column(["Quantity", "quantity", "Qty", "Units"]),
        "unit_price": find_column(["UnitPrice", "unit_price", "Price", "price"]),
        "total_price": find_column(["TotalPrice", "total_price", "Revenue", "Sales", "Amount"]),
        "city": find_column(["City", "city", "Location", "Region"]),
    }

# -------------------------------------------------
# Normalization (Now uses Schema Resolver)
# -------------------------------------------------
def normalize_sales_df(sales: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize sales dataframe to have canonical column names.
    
    PROBLEM #2 FIX: Instead of assuming fixed column names, we now:
    1. Resolve semantic fields to actual column names
    2. Create canonical columns with standard names
    3. Handle missing columns gracefully
    """
    sales = sales.copy()
    
    # Use Schema Resolver to find columns
    resolved = resolve_columns(sales, "sales")
    
    # Create canonical columns from resolved fields
    # ORDER DATE (MANDATORY)
    date_col = resolved.get("order_date")
    if date_col and date_col in sales.columns:
        sales["OrderDate"] = pd.to_datetime(sales[date_col], errors="coerce")
        if date_col != "OrderDate":
            logger.info(f"Mapped '{date_col}' -> 'OrderDate'")
    else:
        raise ValueError(
            f"Sales data requires a date column. "
            f"Expected one of: OrderDate, order_date, Sale_Date, Date. "
            f"Found: {list(sales.columns)}"
        )
    
    if sales["OrderDate"].isna().all():
        raise ValueError("All OrderDate values are invalid")
    
    # CUSTOMER ID (OPTIONAL but useful for RFM)
    customer_col = resolved.get("customer_id")
    if customer_col and customer_col in sales.columns:
        sales["CustomerID"] = sales[customer_col]
        if customer_col != "CustomerID":
            logger.info(f"Mapped '{customer_col}' -> 'CustomerID'")
    else:
        logger.warning("No CustomerID column found - RFM analysis will be unavailable")
    
    # ORDER ID (OPTIONAL)
    order_col = resolved.get("order_id")
    if order_col and order_col in sales.columns:
        sales["OrderID"] = sales[order_col]
        if order_col != "OrderID":
            logger.info(f"Mapped '{order_col}' -> 'OrderID'")
    else:
        # Generate synthetic order IDs
        sales["OrderID"] = range(1, len(sales) + 1)
        logger.info("Generated synthetic OrderID values")
    
    # PRODUCT (OPTIONAL but useful for recommendations)
    product_col = resolved.get("product")
    if product_col and product_col in sales.columns:
        sales["Product"] = sales[product_col]
        if product_col != "Product":
            logger.info(f"Mapped '{product_col}' -> 'Product'")
    else:
        logger.warning("No Product column found - Recommendations will be unavailable")
    
    # QUANTITY (OPTIONAL)
    qty_col = resolved.get("quantity")
    if qty_col and qty_col in sales.columns:
        sales["Quantity"] = pd.to_numeric(sales[qty_col], errors="coerce").fillna(1)
        if qty_col != "Quantity":
            logger.info(f"Mapped '{qty_col}' -> 'Quantity'")
    else:
        sales["Quantity"] = 1
    
    # UNIT PRICE (OPTIONAL)
    price_col = resolved.get("unit_price")
    if price_col and price_col in sales.columns:
        sales["Price"] = pd.to_numeric(sales[price_col], errors="coerce").fillna(0)
        if price_col != "Price":
            logger.info(f"Mapped '{price_col}' -> 'Price'")
    
    # TOTAL PRICE (MANDATORY for analysis)
    total_col = resolved.get("total_price")
    if total_col and total_col in sales.columns:
        sales["TotalPrice"] = pd.to_numeric(sales[total_col], errors="coerce").fillna(0)
        if total_col != "TotalPrice":
            logger.info(f"Mapped '{total_col}' -> 'TotalPrice'")
    elif "Price" in sales.columns and "Quantity" in sales.columns:
        sales["TotalPrice"] = sales["Price"] * sales["Quantity"]
        logger.info("Computed TotalPrice from Price × Quantity")
    else:
        raise ValueError(
            f"Sales data requires a value column. "
            f"Expected one of: TotalPrice, Revenue, Sales, Amount. "
            f"Or provide Price and Quantity columns."
        )

    return sales


def normalize_customers_df(customers: pd.DataFrame) -> pd.DataFrame:
    """Normalize customers dataframe using schema resolution."""
    if customers.empty:
        return customers
    
    customers = customers.copy()
    resolved = resolve_columns(customers, "customers")
    
    # City column
    city_col = resolved.get("city")
    if city_col and city_col in customers.columns:
        customers["City"] = customers[city_col].fillna("Unknown")
        if city_col != "City":
            logger.info(f"Mapped '{city_col}' -> 'City'")
    
    # CustomerID
    customer_col = resolved.get("customer_id")
    if customer_col and customer_col in customers.columns and customer_col != "CustomerID":
        customers["CustomerID"] = customers[customer_col]
        logger.info(f"Mapped '{customer_col}' -> 'CustomerID'")
    
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
        df.to_csv(OUTPUT_DIR / "merged_data.csv", index=False)
        logger.info("[OK] merged_data.csv generated for Phase 2")
        
        # Also save as cleaned_dataset.csv for ML pipelines (04_rfm, 05_recommendation, etc.)
        df.to_csv(OUTPUT_DIR / "cleaned_dataset.csv", index=False)
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
