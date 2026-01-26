"""
Sales Intelligence Project - Phase 1: Data Collection & Exploratory Data Analysis

This module handles:
- Loading customer and sales data
- Data cleaning and validation
- Merging datasets
- Computing key performance indicators (KPIs)
- Performing exploratory data analysis
- Generating and saving visualizations

Author: Sales Intelligence Team
Date: January 2026
"""

import logging
import sys
from pathlib import Path
from typing import Dict, Tuple, Any

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# -------------------------------------------------
# Configuration and Setup
# -------------------------------------------------
# Define paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
PLOTS_DIR = OUTPUT_DIR / "plots"
LOGS_DIR = BASE_DIR / "logs"

# Create necessary directories before configuring logging
OUTPUT_DIR.mkdir(exist_ok=True)
PLOTS_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# Configure logging after ensuring log directory exists
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / 'eda.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# -------------------------------------------------
# Column Aliases & Normalization Helpers
# -------------------------------------------------

# Accepted alias sets mapped to canonical names used by this script
SALES_ALIAS_MAP = {
    "OrderID": ["OrderID", "order_id", "Order_Id", "id", "ID", "orderid"],
    "CustomerID": ["CustomerID", "customer_id", "Customer_Id", "cust_id"],
    "OrderDate": ["OrderDate", "Sale_Date", "Order_Date", "Date", "order_date"],
    "TotalPrice": ["TotalPrice", "Sales_Amount", "SalesAmount", "Revenue", "Sales", "amount", "totalprice"],
    "Product": ["Product", "ProductID", "Product_ID", "SKU", "product"],
    "City": ["City", "city", "Location", "Region", "region", "Market"],
}

CUSTOMER_ALIAS_MAP = {
    "CustomerID": ["CustomerID", "customer_id", "Customer_Id", "cust_id"],
    "City": ["City", "city", "Location", "Region", "region", "Market"],
}

def _rename_first_match(df: pd.DataFrame, aliases: Tuple[str, ...], target: str) -> bool:
    """Rename the first existing alias column to the target name.

    Returns True if a column was found and renamed, else False.
    """
    for col in aliases:
        if col in df.columns:
            if col != target:
                df.rename(columns={col: target}, inplace=True)
            return True
    return False

def normalize_sales_df(sales: pd.DataFrame) -> pd.DataFrame:
    """Normalize sales dataframe columns to canonical names and types.

    - Resolves aliases for OrderID, CustomerID, OrderDate, TotalPrice, Product, City
    - Computes TotalPrice if missing from Unit_Price * Quantity_Sold (adjusts for Discount if present)
    - Parses dates and coerces numeric types
    """
    sales = sales.copy()

    # Rename columns using alias map
    for target, aliases in SALES_ALIAS_MAP.items():
        _rename_first_match(sales, tuple(aliases), target)

    # Compute TotalPrice if not present
    if "TotalPrice" not in sales.columns:
        if {"Unit_Price", "Quantity_Sold"}.issubset(set(sales.columns)):
            tp = pd.to_numeric(sales["Unit_Price"], errors="coerce") * pd.to_numeric(sales["Quantity_Sold"], errors="coerce")
            if "Discount" in sales.columns:
                tp = tp * (1 - pd.to_numeric(sales["Discount"], errors="coerce").fillna(0))
            sales["TotalPrice"] = tp.fillna(0)
            logger.info("Computed TotalPrice from Unit_Price and Quantity_Sold")
        else:
            sales["TotalPrice"] = pd.to_numeric(sales.get("TotalPrice", 0), errors="coerce").fillna(0)

    # Ensure date parsing (MANDATORY)
    if "OrderDate" not in sales.columns:
        logger.error("[FAIL] CRITICAL: OrderDate is mandatory but not found in sales data")
        raise ValueError("OrderDate column is required for all sales records")
    
    sales["OrderDate"] = pd.to_datetime(sales["OrderDate"], errors="coerce")
    
    # Validate OrderDate has no NaT values
    if sales["OrderDate"].isna().any():
        invalid_dates = sales["OrderDate"].isna().sum()
        logger.error(f"[FAIL] OrderDate validation failed: {invalid_dates} invalid date values")
        raise ValueError(f"OrderDate contains {invalid_dates} invalid dates - all OrderDates must be parseable")

    # Hierarchical OrderID generation strategy
    orderid_strategy = None
    
    # Strategy 1: Use existing OrderID
    if "OrderID" in sales.columns and not sales["OrderID"].isna().all():
        valid_orderids = sales["OrderID"].notna().sum()
        if valid_orderids > 0:
            orderid_strategy = "existing"
            logger.info(f"[OK] OrderID STRATEGY 1: Using existing OrderID column ({valid_orderids} records)")
    
    # Strategy 2: Generate from CustomerID + OrderDate
    if orderid_strategy is None and "CustomerID" in sales.columns:
        valid_customer_dates = (sales["CustomerID"].notna() & sales["OrderDate"].notna()).sum()
        if valid_customer_dates > 0:
            orderid_strategy = "customer_date"
            # Generate OrderID as CustomerID + OrderDate (YYYY-MM-DD)
            order_dates = sales["OrderDate"].dt.strftime("%Y-%m-%d")
            sales["OrderID"] = sales["CustomerID"].astype(str) + "_" + order_dates
            logger.warning(
                f"[WARN] OrderID STRATEGY 2: Generated surrogate IDs from CustomerID+OrderDate (YYYY-MM-DD) "
                f"for {valid_customer_dates} records. "
                f"Multiple products purchased by same customer on same day treated as one order."
            )
    
    # Strategy 3: Fallback - incremental row numbers
    if orderid_strategy is None:
        orderid_strategy = "incremental"
        sales["OrderID"] = [f"ORD_{i+1:06d}" for i in range(len(sales))]
        logger.warning(
            f"[WARN] OrderID STRATEGY 3 (Fallback): Generated incremental OrderIDs (ORD_000001, ORD_000002, ...) "
            f"for {len(sales)} records. Each row treated as separate order."
        )

    # Coerce identifiers to string for robustness
    for id_col in ["OrderID", "CustomerID", "Product", "City"]:
        if id_col in sales.columns:
            sales[id_col] = sales[id_col].astype(str)

    return sales

def normalize_customers_df(customers: pd.DataFrame) -> pd.DataFrame:
    """Normalize customers dataframe columns to canonical names."""
    customers = customers.copy()
    for target, aliases in CUSTOMER_ALIAS_MAP.items():
        _rename_first_match(customers, tuple(aliases), target)
    # Fill City fallback
    if "City" in customers.columns:
        customers["City"] = customers["City"].fillna("Unknown").astype(str)
    return customers

def normalize_datasets(customers: pd.DataFrame, sales: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Apply normalization to both datasets and return canonical versions."""
    return normalize_customers_df(customers), normalize_sales_df(sales)

# -------------------------------------------------
# Data Loading
# -------------------------------------------------
def load_data() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Load sales (MANDATORY), customers (OPTIONAL), and reviews (OPTIONAL) datasets.
    
    Returns:
        Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]: Sales, customers (or empty), reviews (or empty)
        
    Raises:
        FileNotFoundError: If MANDATORY sales.csv is not found
        pd.errors.EmptyDataError: If sales.csv is empty
    """
    try:
        logger.info("=" * 60)
        logger.info("DATA LOADING PHASE")
        logger.info("=" * 60)
        
        # MANDATORY: sales.csv
        sales_path = DATA_DIR / "sales.csv"
        if not sales_path.exists():
            logger.error(f"CRITICAL: Mandatory file missing: {sales_path}")
            raise FileNotFoundError(f"Sales file not found: {sales_path}. Pipeline cannot continue without sales data.")
        
        sales = pd.read_csv(sales_path)
        if sales.empty:
            raise pd.errors.EmptyDataError("Sales file is empty")
        logger.info(f"[OK] Loaded {len(sales)} sales records (MANDATORY)")
        
        # OPTIONAL: customers.csv
        customers_path = DATA_DIR / "customers.csv"
        if customers_path.exists():
            try:
                customers = pd.read_csv(customers_path)
                logger.info(f"[OK] Loaded {len(customers)} customer records (OPTIONAL)")
            except Exception as e:
                logger.warning(f"[WARN] Failed to load customers.csv: {e}. Continuing without customer data.")
                customers = pd.DataFrame()
        else:
            logger.warning(f"[WARN] customers.csv not found at {customers_path}. Continuing without customer data.")
            customers = pd.DataFrame()
        
        # OPTIONAL: reviews.csv or customer_reviews.csv
        reviews = pd.DataFrame()
        for reviews_filename in ["customer_reviews.csv", "reviews.csv"]:
            reviews_path = DATA_DIR / reviews_filename
            if reviews_path.exists():
                try:
                    reviews = pd.read_csv(reviews_path)
                    logger.info(f"[OK] Loaded {len(reviews)} review records from {reviews_filename} (OPTIONAL)")
                    break
                except Exception as e:
                    logger.warning(f"[WARN] Failed to load {reviews_filename}: {e}")
        
        if reviews.empty:
            logger.warning(f"[WARN] No review files found. Sentiment analysis will be disabled.")
        
        logger.info("=" * 60)
        return sales, customers, reviews
        
    except Exception as e:
        logger.error(f"Error loading data: {e}")
        raise

# -------------------------------------------------
# Data Validation
# -------------------------------------------------
def validate_data(sales: pd.DataFrame, customers: pd.DataFrame) -> bool:
    """
    Validate that required columns exist in the datasets.
    
    Args:
        sales: Sales dataframe (MANDATORY)
        customers: Customer dataframe (OPTIONAL - can be empty)
        
    Returns:
        bool: True if validation passes
        
    Raises:
        ValueError: If required sales columns are missing
    """
    logger.info("=" * 60)
    logger.info("DATA VALIDATION PHASE")
    logger.info("=" * 60)
    
    # MANDATORY: Sales columns
    required_sales_cols = ["OrderID", "OrderDate", "TotalPrice"]
    missing_sales_cols = set(required_sales_cols) - set(sales.columns)
    
    if missing_sales_cols:
        logger.error(f"[FAIL] Missing MANDATORY sales columns: {missing_sales_cols}")
        raise ValueError(f"Missing required sales columns: {missing_sales_cols}")
    
    logger.info(f"[OK] Sales data validated: All mandatory columns present")
    
    # OPTIONAL: Customer columns (only validate if customers exist)
    if not customers.empty:
        required_customer_cols = ["CustomerID", "City"]
        missing_customer_cols = set(required_customer_cols) - set(customers.columns)
        
        if missing_customer_cols:
            logger.warning(f"[WARN] Customer data exists but missing columns: {missing_customer_cols}. Will proceed without customer enrichment.")
            return True
        
        logger.info(f"[OK] Customer data validated: All expected columns present")
    else:
        logger.info(f"[SKIP] No customer data to validate (file was optional and not found)")
    
    logger.info("=" * 60)
    return True

# -------------------------------------------------
# Data Cleaning
# -------------------------------------------------
def clean_data(customers: pd.DataFrame, sales: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Clean and preprocess customer and sales data.
    
    Args:
        customers: Raw customer dataframe
        sales: Raw sales dataframe
        
    Returns:
        Tuple[pd.DataFrame, pd.DataFrame]: Cleaned dataframes
    """
    try:
        logger.info("Cleaning data...")
        
        # Clean customers
        customers = customers.copy()
        if "City" in customers.columns:
            customers["City"] = customers["City"].fillna("Unknown")
        customers = customers.drop_duplicates(subset=["CustomerID"]) if "CustomerID" in customers.columns else customers
        
        # Clean sales
        sales = sales.copy()
        if "OrderDate" in sales.columns:
            sales["OrderDate"] = pd.to_datetime(sales["OrderDate"], errors="coerce")
        if "TotalPrice" in sales.columns:
            sales["TotalPrice"] = pd.to_numeric(sales["TotalPrice"], errors="coerce").fillna(0)
        
        # Remove invalid records
        initial_sales_count = len(sales)
        if "OrderDate" in sales.columns:
            sales = sales.dropna(subset=["OrderDate"])
        if "TotalPrice" in sales.columns:
            sales = sales[sales["TotalPrice"] > 0]
        
        removed_records = initial_sales_count - len(sales)
        if removed_records > 0:
            logger.warning(f"Removed {removed_records} invalid sales records")
        
        logger.info("Data cleaning completed")
        return customers, sales
        
    except Exception as e:
        logger.error(f"Error cleaning data: {e}")
        raise

# -------------------------------------------------
# Data Merging
# -------------------------------------------------
def merge_data(sales: pd.DataFrame, customers: pd.DataFrame) -> pd.DataFrame:
    """
    Merge sales with optional customer data using LEFT JOIN.
    Sales data is ALWAYS preserved even if no customers exist.
    
    Args:
        sales: Sales dataframe (MANDATORY)
        customers: Customer dataframe (OPTIONAL - can be empty)
        
    Returns:
        pd.DataFrame: Merged dataframe (always contains all sales records)
    """
    try:
        logger.info("=" * 60)
        logger.info("DATA MERGING PHASE")
        logger.info("=" * 60)
        
        # Start with sales as base (ALWAYS preserved)
        df = sales.copy()
        
        # LEFT JOIN with customers if available
        if not customers.empty and "CustomerID" in sales.columns and "CustomerID" in customers.columns:
            logger.info(f"Performing LEFT JOIN: {len(sales)} sales with {len(customers)} customers...")
            # Ensure CustomerID has consistent type for merge (both as string)
            sales_copy = sales.copy()
            customers_copy = customers.copy()
            sales_copy["CustomerID"] = sales_copy["CustomerID"].astype(str)
            customers_copy["CustomerID"] = customers_copy["CustomerID"].astype(str)
            df = pd.merge(sales_copy, customers_copy, on="CustomerID", how="left")
            
            # Resolve duplicate City columns from merge
            if "City_x" in df.columns or "City_y" in df.columns:
                df["City"] = df.get("City_x", df.get("City_y"))
                if "City_y" in df.columns:
                    df["City"] = df["City"].fillna(df["City_y"])
                # Drop helper duplicate columns
                for col in ["City_x", "City_y"]:
                    if col in df.columns:
                        df.drop(columns=[col], inplace=True)
            
            unmatched = df[df.get("City", pd.Series()).isna()].shape[0] if "City" in df.columns else 0
            if unmatched > 0:
                logger.warning(f"[WARN] {unmatched} sales records have no matching customer (will use sales data only)")
            logger.info(f"[OK] Merge complete: {len(df)} records (all sales preserved)")
        else:
            if customers.empty:
                logger.info(f"[SKIP] No customer data available - using sales data only")
            elif "CustomerID" not in sales.columns:
                logger.warning(f"[WARN] CustomerID missing in sales - cannot join with customers")
            elif "CustomerID" not in customers.columns:
                logger.warning(f"[WARN] CustomerID missing in customers - cannot join")
            logger.info(f"[OK] Using sales data only: {len(df)} records")
        
        logger.info("=" * 60)
        return df
        
    except Exception as e:
        logger.error(f"Error merging data: {e}")
        raise

# -------------------------------------------------
# KPI Computation
# -------------------------------------------------
def compute_kpis(df: pd.DataFrame) -> Dict[str, float]:
    """
    Calculate key performance indicators from the merged dataset.
    
    Args:
        df: Merged dataframe with sales and customer data
        
    Returns:
        Dict[str, float]: Dictionary of KPI names and values
    """
    try:
        logger.info("Computing KPIs...")
        
        kpis = {
            "Total Sales Revenue": df["TotalPrice"].sum(),
            "Total Orders": df["OrderID"].nunique(),
            "Total Customers": df["CustomerID"].nunique() if "CustomerID" in df.columns else 0,
            "Average Order Value": df["TotalPrice"].mean(),
            "Median Order Value": df["TotalPrice"].median(),
            "Total Products Sold": df["Product"].nunique() if "Product" in df.columns else 0
        }
        
        logger.info("KPIs computed successfully")
        return kpis
        
    except Exception as e:
        logger.error(f"Error computing KPIs: {e}")
        raise

# -------------------------------------------------
# Exploratory Data Analysis
# -------------------------------------------------
def perform_eda(df: pd.DataFrame) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Perform exploratory data analysis on the merged dataset.
    
    Args:
        df: Merged dataframe
        
    Returns:
        Tuple containing:
        - monthly_sales: Sales aggregated by month
        - top_products: Top 5 products by revenue
        - sales_by_city: Sales aggregated by city
    """
    try:
        logger.info("Performing exploratory data analysis...")
        
        # Add month column
        df["Month"] = df["OrderDate"].dt.to_period("M").astype(str)
        
        # Monthly sales trend
        monthly_sales = df.groupby("Month")["TotalPrice"].sum().sort_index()
        
        # Top 5 products
        top_products = (
            df.groupby("Product")["TotalPrice"]
            .sum()
            .sort_values(ascending=False)
            .head(5)
        )
        
        # Sales by city
        sales_by_city = (
            df.groupby("City")["TotalPrice"]
            .sum()
            .sort_values(ascending=False)
        )
        
        logger.info("EDA completed successfully")
        return monthly_sales, top_products, sales_by_city
        
    except Exception as e:
        logger.error(f"Error performing EDA: {e}")
        raise

# -------------------------------------------------
# Visualization
# -------------------------------------------------
def plot_results(monthly_sales: pd.Series, top_products: pd.Series, 
                sales_by_city: pd.Series) -> None:
    """
    Generate and save visualization plots for EDA results.
    
    Args:
        monthly_sales: Monthly sales data
        top_products: Top products data
        sales_by_city: Sales by city data
    """
    try:
        logger.info("Generating visualizations...")
        
        # Set style
        plt.style.use('seaborn-v0_8-darkgrid')
        
        # 1. Monthly Sales Trend
        fig, ax = plt.subplots(figsize=(12, 6))
        monthly_sales.plot(ax=ax, marker='o', linewidth=2, markersize=8, color='#2E86AB')
        ax.set_title("Monthly Sales Trend", fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel("Month", fontsize=12)
        ax.set_ylabel("Total Sales Revenue", fontsize=12)
        ax.grid(True, alpha=0.3)
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.savefig(PLOTS_DIR / "monthly_sales_trend.png", dpi=300, bbox_inches='tight')
        plt.close()
        
        # 2. Top 5 Products
        fig, ax = plt.subplots(figsize=(10, 6))
        top_products.plot(kind='bar', ax=ax, color='#A23B72')
        ax.set_title("Top 5 Products by Revenue", fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel("Product", fontsize=12)
        ax.set_ylabel("Total Revenue", fontsize=12)
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.savefig(PLOTS_DIR / "top_5_products.png", dpi=300, bbox_inches='tight')
        plt.close()
        
        # 3. Sales by City
        fig, ax = plt.subplots(figsize=(12, 6))
        sales_by_city.plot(kind='bar', ax=ax, color='#F18F01')
        ax.set_title("Sales Distribution by City", fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel("City", fontsize=12)
        ax.set_ylabel("Total Sales", fontsize=12)
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.savefig(PLOTS_DIR / "sales_by_city.png", dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Visualizations saved to {PLOTS_DIR}")
        
    except Exception as e:
        logger.error(f"Error generating plots: {e}")
        raise

# -------------------------------------------------
# Save Results
# -------------------------------------------------
def save_results(df: pd.DataFrame, kpis: Dict[str, float], 
                monthly_sales: pd.Series, top_products: pd.Series, 
                sales_by_city: pd.Series, metadata: Dict[str, Any]) -> None:
    """
    Save analysis results to CSV files and JSON metadata.
    
    Args:
        df: Merged dataframe
        kpis: Calculated KPIs
        monthly_sales: Monthly sales data
        top_products: Top products data
        sales_by_city: Sales by city data
        metadata: Pipeline execution metadata
    """
    try:
        logger.info("=" * 60)
        logger.info("SAVING RESULTS")
        logger.info("=" * 60)
        
        # Save merged dataset
        df.to_csv(DATA_DIR / "merged_data.csv", index=False)
        logger.info(f"[OK] Merged dataset saved: {DATA_DIR / 'merged_data.csv'}")
        
        # Save KPIs
        kpis_df = pd.DataFrame(list(kpis.items()), columns=['KPI', 'Value'])
        kpis_df.to_csv(OUTPUT_DIR / "kpis.csv", index=False)
        logger.info(f"[OK] KPIs saved: {OUTPUT_DIR / 'kpis.csv'}")
        
        # Save EDA results
        monthly_sales.to_csv(OUTPUT_DIR / "monthly_sales.csv", header=True)
        top_products.to_csv(OUTPUT_DIR / "top_products.csv", header=True)
        sales_by_city.to_csv(OUTPUT_DIR / "sales_by_city.csv", header=True)
        logger.info("[OK] EDA results saved")
        
        # Save metadata report as JSON
        import json
        from datetime import datetime
        metadata['generated_at'] = datetime.utcnow().isoformat()
        with open(OUTPUT_DIR / "eda_report.json", 'w') as f:
            json.dump(metadata, f, indent=2)
        logger.info(f"[OK] Metadata report saved: {OUTPUT_DIR / 'eda_report.json'}")
        
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Error saving results: {e}")
        raise

# -------------------------------------------------
# Main Execution
# -------------------------------------------------
def main() -> None:
    """
    Main execution function for Phase 1: EDA.
    
    Orchestrates the entire EDA pipeline from data loading to result saving.
    MANDATORY: sales.csv
    OPTIONAL: customers.csv, reviews.csv
    """
    try:
        logger.info("=" * 60)
        logger.info("PHASE 1: DATA COLLECTION & EDA STARTED")
        logger.info("=" * 60)
        
        # Track metadata for observability
        metadata = {
            "phase": "01_eda",
            "sales_file_present": False,
            "customers_file_present": False,
            "reviews_file_present": False,
            "pipeline_status": "in_progress"
        }
        
        # Load data (sales is mandatory, others optional)
        sales, customers, reviews = load_data()
        metadata["sales_file_present"] = not sales.empty
        metadata["customers_file_present"] = not customers.empty
        metadata["reviews_file_present"] = not reviews.empty
        metadata["sales_records"] = len(sales)
        metadata["customer_records"] = len(customers) if not customers.empty else 0
        metadata["review_records"] = len(reviews) if not reviews.empty else 0

        # Normalize alias columns to canonical names before validation/cleaning
        customers_normalized, sales_normalized = normalize_datasets(customers, sales)
        
        # Validate data (only mandatory sales columns required)
        validate_data(sales_normalized, customers_normalized)
        
        # Clean data
        customers_clean, sales_clean = clean_data(customers_normalized, sales_normalized)
        
        # Merge datasets (LEFT JOIN to preserve all sales)
        df = merge_data(sales_clean, customers_clean)
        
        # Compute KPIs
        kpis = compute_kpis(df)
        logger.info("\n" + "=" * 60)
        logger.info("KEY PERFORMANCE INDICATORS")
        logger.info("=" * 60)
        for k, v in kpis.items():
            logger.info(f"{k}: {v:,.2f}")
        
        # Perform EDA
        monthly_sales, top_products, sales_by_city = perform_eda(df)
        
        # Generate visualizations
        plot_results(monthly_sales, top_products, sales_by_city)
        
        # Update metadata
        metadata["pipeline_status"] = "success"
        metadata["kpis"] = {k: float(v) for k, v in kpis.items()}
        
        # Save all results
        save_results(df, kpis, monthly_sales, top_products, sales_by_city, metadata)
        
        logger.info("=" * 60)
        logger.info("PHASE 1: EDA COMPLETED SUCCESSFULLY")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        sys.exit(1)

# -------------------------------------------------
if __name__ == "__main__":
    main()
