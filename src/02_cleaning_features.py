"""
Phase 2: Data Cleaning & Feature Engineering

Enhancements:
- Path management via pathlib
- Logging with row-count tracking
- Validation of required columns
- Safer missing-value fills (mode with fallback, median for numeric)
- Restrict non-negative enforcement to relevant columns
- Cap outliers (IQR winsorization) instead of dropping rows
"""

import logging
import sys
from pathlib import Path

import pandas as pd
import numpy as np


# -------------------------------------------------
# Paths & Logging
# -------------------------------------------------
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"

LOGS_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / 'cleaning_features.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def safe_mode(series: pd.Series):
    """Return first mode value if available; otherwise fallback to empty string."""
    modes = series.mode(dropna=True)
    if len(modes) > 0:
        return modes.iloc[0]
    return ""  # fallback for all-NaN categorical


def winsorize_iqr(series: pd.Series) -> pd.Series:
    """Cap values to IQR bounds (Q1-1.5*IQR, Q3+1.5*IQR). Handles zero-IQR gracefully."""
    if series.empty:
        return series
    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    iqr = q3 - q1
    if pd.isna(iqr) or iqr == 0:
        return series
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    return series.clip(lower, upper)


def main():
    """
    Phase 2: Data Cleaning & Feature Engineering
    
    MANDATORY inputs: OrderID, OrderDate, TotalPrice from sales
    OPTIONAL inputs: CustomerID, City (from customers if available)
    
    Never fails due to missing optional columns - adapts to available data.
    """
    logger.info("=" * 60)
    logger.info("PHASE 2: DATA CLEANING & FEATURE ENGINEERING")
    logger.info("=" * 60)
    
    # Load the dataset
    data_path = DATA_DIR / 'merged_data.csv'
    if not data_path.exists():
        logger.error(f"CRITICAL: Missing input file: {data_path}")
        logger.error(f"Phase 1 (EDA) must run first to generate merged_data.csv")
        sys.exit(1)

    df = pd.read_csv(data_path)
    logger.info(f"✓ Loaded {len(df)} rows from {data_path}")

    # Validate MANDATORY columns only (from sales)
    required_cols = ['OrderID', 'OrderDate', 'TotalPrice']
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        logger.error(f"✗ Missing MANDATORY columns: {missing}")
        sys.exit(1)
    logger.info(f"✓ Mandatory columns validated")
    
    # Check for OPTIONAL columns and log availability
    optional_cols = {'CustomerID': False, 'City': False, 'Product': False}
    for col in optional_cols.keys():
        if col in df.columns:
            optional_cols[col] = True
            logger.info(f"✓ Optional column '{col}' available")
        else:
            logger.warning(f"⊘ Optional column '{col}' not available")

    # Remove duplicate rows
    before = len(df)
    df = df.drop_duplicates()
    logger.info(f"✓ Dropped {before - len(df)} duplicate rows")

    # Remove invalid numeric negatives (only for TotalPrice - mandatory)
    if 'TotalPrice' in df.columns:
        before_negatives = len(df)
        df = df[df['TotalPrice'] >= 0]
        removed = before_negatives - len(df)
        if removed > 0:
            logger.info(f"✓ Removed {removed} rows with negative TotalPrice")

    # Handle missing values
    for col in df.columns:
        if df[col].dtype == 'object':
            fill_val = safe_mode(df[col])
            df[col] = df[col].fillna(fill_val)
        elif pd.api.types.is_numeric_dtype(df[col]):
            # median is more robust to outliers than mean
            fill_val = df[col].median()
            if pd.isna(fill_val):
                fill_val = 0
            df[col] = df[col].fillna(fill_val)
    logger.info(f"✓ Handled missing values")

    # Convert OrderDate to datetime and drop invalid
    df['OrderDate'] = pd.to_datetime(df['OrderDate'], errors='coerce')
    invalid_dates = df['OrderDate'].isna().sum()
    if invalid_dates:
        logger.warning(f"⚠ Dropping {invalid_dates} rows with invalid OrderDate")
        df = df.dropna(subset=['OrderDate'])

    # Handle outliers: cap numeric values (excluding IDs)
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    id_like = {'OrderID', 'CustomerID'}
    numeric_target = [c for c in numeric_cols if c not in id_like]
    for col in numeric_target:
        df[col] = winsorize_iqr(df[col])
    logger.info(f"✓ Outliers handled via IQR winsorization")

    # Feature Engineering - ALWAYS possible (based on mandatory sales columns)
    df['OrderMonth'] = df['OrderDate'].dt.month
    df['OrderYear'] = df['OrderDate'].dt.year
    df['OrderValue'] = df['TotalPrice']
    df['OrderQuarter'] = df['OrderDate'].dt.quarter
    df['OrderWeek'] = df['OrderDate'].dt.isocalendar().week.astype(int)
    logger.info(f"✓ Core time-based features created")
    
    # CONDITIONAL Feature Engineering - only if CustomerID exists
    if optional_cols['CustomerID']:
        df['CustomerLifetimeValue'] = df.groupby('CustomerID')['OrderValue'].transform('sum')
        logger.info(f"✓ Customer-based features created (CustomerLifetimeValue)")
    else:
        logger.info(f"⊘ Skipped customer-based features (CustomerID not available)")

    # Reset index
    df = df.reset_index(drop=True)

    # Save the cleaned dataset
    output_path = DATA_DIR / 'cleaned_dataset.csv'
    df.to_csv(output_path, index=False)
    logger.info(f"✓ Saved cleaned dataset to {output_path} with {len(df)} rows")
    
    logger.info("=" * 60)
    logger.info("PHASE 2: CLEANING COMPLETED SUCCESSFULLY")
    logger.info("=" * 60)


if __name__ == '__main__':
    main()