"""Phase 4: RFM Analysis - Customer Segmentation via Recency, Frequency, Monetary."""

import sys
import logging
from pathlib import Path
from typing import Tuple

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


def load_and_validate_data(input_path: Path) -> pd.DataFrame:
    """
    Load and validate cleaned dataset for RFM analysis.
    
    REQUIRES: CustomerID from customers.csv (optional file)
    REQUIRES: OrderDate, TotalPrice from sales.csv (mandatory)
    
    Args:
        input_path: Path to cleaned_dataset.csv
        
    Returns:
        Validated dataframe with required columns, or None if CustomerID missing
        
    Raises:
        FileNotFoundError: If input file not found
    """
    logger.info("=" * 60)
    logger.info("RFM ANALYSIS - DATA VALIDATION")
    logger.info("=" * 60)
    
    if not input_path.exists():
        logger.error(f"✗ Input file not found: {input_path}")
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    df = pd.read_csv(input_path)
    logger.info(f"✓ Loaded {len(df)} records from {input_path}")
    
    # Check for MANDATORY CustomerID (comes from optional customers.csv)
    if "CustomerID" not in df.columns:
        logger.warning("=" * 60)
        logger.warning("⊘ RFM ANALYSIS SKIPPED")
        logger.warning("⊘ Reason: CustomerID column not available")
        logger.warning("⊘ Solution: Upload customers.csv with CustomerID column")
        logger.warning("=" * 60)
        return None
    
    # Validate other required columns (from sales)
    required_cols = ["CustomerID", "OrderDate", "TotalPrice"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        logger.error(f"✗ Missing required columns: {missing}")
        raise ValueError(f"Missing required columns: {missing}")
    
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


def score_metric(series: pd.Series, reverse: bool = False) -> pd.Series:
    """
    Convert metric values into 1-5 scores based on rank.
    
    Args:
        series: Metric values to score
        reverse: If True, higher values get higher scores (for R, F, M)
        
    Returns:
        Scored series with values 1-5
    """
    ranks = series.rank(method="dense")
    if reverse:
        ranks = ranks.max() - ranks + 1
    
    # Bin into 5 scores
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
    logger.info("Computing RFM scores (1-5 scale)...")
    
    # Recency: Lower is better (more recent = higher score)
    rfm["R_Score"] = score_metric(rfm["Recency"], reverse=True)
    
    # Frequency: Higher is better
    rfm["F_Score"] = score_metric(rfm["Frequency"], reverse=False)
    
    # Monetary: Higher is better
    rfm["M_Score"] = score_metric(rfm["Monetary"], reverse=False)
    
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
        
        # Load and validate data
        input_path = DATA_DIR / "cleaned_dataset.csv"
        df = load_and_validate_data(input_path)
        
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
    except Exception as e:
        logger.error(f"RFM analysis failed: {e}")
        sys.exit(1)
        
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
        logger.info("Phase 4: RFM Analysis Completed Successfully")
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
