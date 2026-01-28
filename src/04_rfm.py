"""
Phase 4: RFM Analysis - Customer Segmentation via Recency, Frequency, Monetary.

=============================================================================
PROBLEM #2 FIX: Hard-Coded Column Assumptions
=============================================================================
This module now uses the Schema Resolver (when available) to auto-detect
column names, making it work with different data schemas.

=============================================================================
PROBLEM #4 FIX: Pipeline Rigidity  
=============================================================================
RFM Analysis REQUIRES CustomerID. If the dataset doesn't have customer 
identification, this analysis will gracefully skip with a clear message.
The pipeline controller checks for CustomerID availability before calling
this module.
=============================================================================
"""

import sys
import logging
from pathlib import Path
from typing import Tuple, Optional, Dict

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

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
        logging.FileHandler(LOGS_DIR / 'rfm.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
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


def resolve_rfm_columns(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    """
    Resolve required columns for RFM analysis.
    
    RFM requires:
    - date column (ORDER_DATE) - for Recency
    - customer column (CUSTOMER_ID) - for grouping
    - value column (TOTAL_PRICE) - for Monetary
    
    Frequency is derived from counting orders per customer.
    
    Returns dict with resolved column names or None if not found.
    """
    if SCHEMA_RESOLVER_AVAILABLE:
        resolver = SchemaResolver()
        result = resolver.resolve(df, "sales")
        
        return {
            "date": result.get_column(SemanticField.ORDER_DATE),
            "customer": result.get_column(SemanticField.CUSTOMER_ID),
            "value": result.get_column(SemanticField.TOTAL_PRICE)
        }
    else:
        # Fallback detection
        date_candidates = ["OrderDate", "Sale_Date", "Order_Date", "Date", "order_date"]
        revenue_candidates = ["TotalPrice", "Price", "Sales_Amount", "Revenue", "Amount"]
        customer_candidates = ["CustomerID", "Customer_ID", "customer_id", "CustomerId"]
        
        date_col = next((c for c in date_candidates if c in df.columns), None)
        revenue_col = next((c for c in revenue_candidates if c in df.columns), None)
        customer_col = next((c for c in customer_candidates if c in df.columns), None)
        
        return {"date": date_col, "customer": customer_col, "value": revenue_col}


def find_data_file() -> Path:
    """Find data file in multiple possible locations.
    
    Search order:
    1. data/cleaned_dataset.csv
    2. data/merged_data.csv
    3. data/sales.csv
    """
    possible_paths = [
        DATA_DIR / "cleaned_dataset.csv",
        DATA_DIR / "merged_data.csv",
        DATA_DIR / "sales.csv",
    ]
    
    for path in possible_paths:
        if path.exists():
            logger.info(f"Found data file at: {path}")
            return path
    
    raise FileNotFoundError(
        f"No data file found. Searched in:\n" + 
        "\n".join(f"  - {p}" for p in possible_paths)
    )


def load_and_validate_data(input_path: Path = None) -> pd.DataFrame:
    """
    Load and validate cleaned dataset for RFM analysis.
    
    Uses Schema Resolver to auto-detect column names.
    
    REQUIRES: CustomerID (for customer grouping)
    REQUIRES: OrderDate, TotalPrice (for RFM metrics)
    
    Args:
        input_path: Path to data file (optional, will auto-detect if None)
        
    Returns:
        Validated dataframe with required columns, or None if CustomerID missing
        
    Raises:
        FileNotFoundError: If input file not found
    """
    logger.info("=" * 60)
    logger.info("RFM ANALYSIS - DATA VALIDATION")
    logger.info("=" * 60)
    
    # Auto-detect file if not provided
    if input_path is None:
        input_path = find_data_file()
    
    if not input_path.exists():
        logger.error(f"✗ Input file not found: {input_path}")
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    df = pd.read_csv(input_path)
    logger.info(f"✓ Loaded {len(df)} records from {input_path}")
    
    # Use Schema Resolver to find columns
    resolved = resolve_rfm_columns(df)
    date_col = resolved.get("date")
    revenue_col = resolved.get("value")
    customer_col = resolved.get("customer")
    
    logger.info(f"Column resolution: date='{date_col}', customer='{customer_col}', value='{revenue_col}'")
    
    # Check for MANDATORY CustomerID (comes from optional customers.csv)
    if not customer_col:
        logger.warning("=" * 60)
        logger.warning("⊘ RFM ANALYSIS SKIPPED")
        logger.warning("⊘ Reason: CustomerID column not available")
        logger.warning(f"⊘ Available columns: {list(df.columns)}")
        logger.warning("⊘ Solution: Upload customers.csv with CustomerID column")
        logger.warning("=" * 60)
        return None
    
    if not date_col or not revenue_col:
        logger.error(f"✗ Missing required columns. Found: date={date_col}, revenue={revenue_col}")
        raise ValueError(f"Missing required columns: date={date_col}, revenue={revenue_col}")
    
    # Rename to standard names
    df = df.rename(columns={
        customer_col: "CustomerID",
        date_col: "OrderDate", 
        revenue_col: "TotalPrice"
    })
    logger.info(f"✓ Using columns: CustomerID={customer_col}, OrderDate={date_col}, TotalPrice={revenue_col}")
    
    # Parse dates
    df["OrderDate"] = pd.to_datetime(df["OrderDate"], errors='coerce')
    invalid_dates = df["OrderDate"].isna().sum()
    if invalid_dates > 0:
        logger.warning(f"⚠ Dropping {invalid_dates} rows with invalid OrderDate")
        df = df.dropna(subset=["OrderDate"])
    
    if len(df) == 0:
        logger.error(f"✗ No valid data after date parsing")
        raise ValueError("No valid data after date parsing")
    
    # Create OrderValue if not present
    if "OrderValue" not in df.columns:
        df["OrderValue"] = df["TotalPrice"]
        logger.info(f"✓ Created OrderValue column from TotalPrice")
    
    logger.info(f"✓ Validated {len(df)} records for RFM analysis")
    logger.info("=" * 60)
    return df


def calculate_rfm(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate Recency, Frequency, and Monetary metrics per customer.
    
    Args:
        df: Dataframe with CustomerID, OrderDate, OrderValue, TotalPrice
        
    Returns:
        RFM dataframe with CustomerID and RFM metrics
    """
    logger.info("Calculating RFM metrics...")
    
    reference_date = df["OrderDate"].max()
    logger.info(f"Reference date: {reference_date.date()}")
    
    # Group by CustomerID and calculate RFM
    rfm = df.groupby("CustomerID").agg({
        "OrderDate": lambda x: (reference_date - x.max()).days,  # Recency
        "OrderValue": "count",  # Frequency
        "TotalPrice": "sum"  # Monetary
    }).reset_index()
    
    rfm.columns = ["CustomerID", "Recency", "Frequency", "Monetary"]
    
    logger.info(f"Calculated RFM for {len(rfm)} unique customers")
    logger.info(f"Recency range: {rfm['Recency'].min()}-{rfm['Recency'].max()} days")
    logger.info(f"Frequency range: {rfm['Frequency'].min()}-{rfm['Frequency'].max()} orders")
    logger.info(f"Monetary range: {rfm['Monetary'].min():,.2f}-{rfm['Monetary'].max():,.2f}")
    
    return rfm


def score_metric(series: pd.Series, lower_is_better: bool = False) -> pd.Series:
    """
    Convert metric values into 1-5 scores based on quantile binning.
    
    Args:
        series: Metric values to score
        lower_is_better: If True, lower values get higher scores (for Recency)
                        If False, higher values get higher scores (for F, M)
        
    Returns:
        Scored series with values 1-5
    """
    try:
        # Use quantile-based binning (qcut) for more even distribution
        # This handles skewed distributions better than rank-based approach
        if lower_is_better:
            # For Recency: lower days = more recent = HIGHER score (5)
            # Invert the series so that qcut gives high scores to low values
            labels = [5, 4, 3, 2, 1]
        else:
            # For Frequency/Monetary: higher values = higher scores
            labels = [1, 2, 3, 4, 5]
        
        scores = pd.qcut(
            series,
            q=5,
            labels=labels,
            duplicates='drop'
        ).astype(int)
        return scores
    except ValueError:
        # Fallback to rank-based if qcut fails (too few unique values)
        ranks = series.rank(method="dense", ascending=not lower_is_better)
        return pd.cut(
            ranks,
            bins=5,
            labels=[1, 2, 3, 4, 5],
            include_lowest=True
        ).astype(int)


def add_rfm_scores(rfm: pd.DataFrame) -> pd.DataFrame:
    """
    Add RFM scores and composite RFM_Score to dataframe.
    
    Args:
        rfm: RFM dataframe
        
    Returns:
        RFM dataframe with R_Score, F_Score, M_Score, and RFM_Score columns
    """
    logger.info("Computing RFM scores (1-5 scale using quantile binning)...")
    
    # Recency: Lower days = more recent = HIGHER score (5)
    # A customer who purchased 1 day ago should score 5, not 1
    rfm["R_Score"] = score_metric(rfm["Recency"], lower_is_better=True)
    
    # Frequency: Higher order count = higher score
    rfm["F_Score"] = score_metric(rfm["Frequency"], lower_is_better=False)
    
    # Monetary: Higher spending = higher score
    rfm["M_Score"] = score_metric(rfm["Monetary"], lower_is_better=False)
    
    # Composite score
    rfm["RFM_Score"] = (
        rfm["R_Score"].astype(str)
        + rfm["F_Score"].astype(str)
        + rfm["M_Score"].astype(str)
    )
    
    logger.info(f"Created {rfm['RFM_Score'].nunique()} unique RFM segments")
    
    return rfm


def classify_customers(rfm: pd.DataFrame) -> pd.DataFrame:
    """
    Classify customers based on RFM scores into business segments.
    
    Args:
        rfm: RFM dataframe with scores
        
    Returns:
        RFM dataframe with customer classification column
    """
    def get_segment(r, f, m):
        """Map RFM scores to customer segment."""
        if r >= 4 and f >= 4 and m >= 4:
            return "Champions"
        elif r >= 4 and f >= 3 and m >= 3:
            return "Loyal Customers"
        elif r >= 3 and f >= 2:
            return "Potential Loyalists"
        elif r >= 4 and f <= 2:
            return "New Customers"
        elif r <= 2 and f >= 3:
            return "At Risk"
        elif r <= 2 and f <= 2:
            return "Lost"
        else:
            return "Need Attention"
    
    rfm["Segment"] = rfm.apply(
        lambda row: get_segment(row["R_Score"], row["F_Score"], row["M_Score"]),
        axis=1
    )
    
    segment_counts = rfm["Segment"].value_counts()
    logger.info("Customer segments:")
    for segment, count in segment_counts.items():
        logger.info(f"  {segment}: {count} customers")
    
    return rfm


def plot_rfm_distribution(rfm: pd.DataFrame, plots_dir: Path) -> None:
    """
    Create visualizations for RFM metrics and segments.
    
    Args:
        rfm: RFM dataframe with scores and segments
        plots_dir: Directory to save plots
    """
    logger.info("Generating RFM visualizations...")
    
    plt.style.use('seaborn-v0_8-darkgrid')
    
    # 1. RFM Score Distribution (Heatmap)
    fig, ax = plt.subplots(figsize=(10, 6))
    rfm_pivot = rfm.pivot_table(
        values="CustomerID",
        index="R_Score",
        columns="F_Score",
        aggfunc="count",
        fill_value=0
    )
    im = ax.imshow(rfm_pivot.values, cmap='YlOrRd', aspect='auto')
    ax.set_xticks(range(len(rfm_pivot.columns)))
    ax.set_yticks(range(len(rfm_pivot.index)))
    ax.set_xticklabels(rfm_pivot.columns)
    ax.set_yticklabels(rfm_pivot.index)
    ax.set_xlabel("Frequency Score", fontsize=11)
    ax.set_ylabel("Recency Score", fontsize=11)
    ax.set_title("RFM Distribution (Recency vs Frequency)", fontsize=12, fontweight='bold', pad=15)
    plt.colorbar(im, ax=ax, label="Customer Count")
    plt.tight_layout()
    plot_path = plots_dir / "rfm_heatmap.png"
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    plt.close()
    logger.info(f"RFM heatmap saved to {plot_path}")
    
    # 2. Segment Distribution
    fig, ax = plt.subplots(figsize=(10, 6))
    segment_counts = rfm["Segment"].value_counts()
    colors = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#6A994E', '#BC4749']
    segment_counts.plot(kind='barh', ax=ax, color=colors[:len(segment_counts)])
    ax.set_xlabel("Number of Customers", fontsize=11)
    ax.set_ylabel("Customer Segment", fontsize=11)
    ax.set_title("Customer Distribution by RFM Segment", fontsize=12, fontweight='bold', pad=15)
    plt.tight_layout()
    plot_path = plots_dir / "rfm_segments.png"
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    plt.close()
    logger.info(f"Segment distribution plot saved to {plot_path}")
    
    # 3. RFM Metrics Distribution
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    
    axes[0].hist(rfm["Recency"], bins=20, color='#2E86AB', edgecolor='black', alpha=0.7)
    axes[0].set_xlabel("Recency (days)", fontsize=10)
    axes[0].set_ylabel("Count", fontsize=10)
    axes[0].set_title("Recency Distribution", fontsize=11, fontweight='bold')
    axes[0].grid(True, alpha=0.3)
    
    axes[1].hist(rfm["Frequency"], bins=20, color='#A23B72', edgecolor='black', alpha=0.7)
    axes[1].set_xlabel("Frequency (orders)", fontsize=10)
    axes[1].set_ylabel("Count", fontsize=10)
    axes[1].set_title("Frequency Distribution", fontsize=11, fontweight='bold')
    axes[1].grid(True, alpha=0.3)
    
    axes[2].hist(rfm["Monetary"], bins=20, color='#F18F01', edgecolor='black', alpha=0.7)
    axes[2].set_xlabel("Monetary Value", fontsize=10)
    axes[2].set_ylabel("Count", fontsize=10)
    axes[2].set_title("Monetary Distribution", fontsize=11, fontweight='bold')
    axes[2].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plot_path = plots_dir / "rfm_metrics_distribution.png"
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    plt.close()
    logger.info(f"Metrics distribution plot saved to {plot_path}")


def save_rfm_results(rfm: pd.DataFrame, output_path: Path) -> None:
    """
    Save RFM analysis results to CSV.
    
    Args:
        rfm: RFM dataframe
        output_path: Output file path
    """
    rfm.to_csv(output_path, index=False)
    logger.info(f"RFM table saved to {output_path} with {len(rfm)} customers")


def main() -> None:
    """
    Main execution for Phase 4: RFM Analysis.
    
    DEPENDENCY: Requires CustomerID (from optional customers.csv)
    If CustomerID not available, gracefully skip RFM and exit with code 0.
    """
    try:
        logger.info("=" * 60)
        logger.info("PHASE 4: RFM ANALYSIS STARTED")
        logger.info("=" * 60)
        
        # Load and validate data (auto-detects file location)
        df = load_and_validate_data()
        
        # If CustomerID not available, skip RFM gracefully
        if df is None:
            logger.info("RFM Analysis skipped - exiting gracefully")
            sys.exit(0)  # Exit with success (not a failure)
        
        # Calculate RFM metrics
        rfm = calculate_rfm(df)
        
        # Add RFM scores
        rfm = add_rfm_scores(rfm)
        
        # Classify customers into segments
        rfm = classify_customers(rfm)
        
        # Generate visualizations
        plot_rfm_distribution(rfm, PLOTS_DIR)
        
        # Save results
        output_path = DATA_DIR / "rfm_table.csv"
        save_rfm_results(rfm, output_path)
        
        logger.info("=" * 60)
        logger.info("PHASE 4: RFM ANALYSIS COMPLETED SUCCESSFULLY")
        logger.info("=" * 60)
        
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        logger.error("Please ensure Phase 2 (cleaning) has completed successfully")
        sys.exit(1)
    except ValueError as e:
        logger.error(f"Data validation error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"RFM analysis failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
