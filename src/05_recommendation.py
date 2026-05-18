"""
Phase 5: Market Basket Analysis - Product Recommendation Engine

=============================================================================
PROBLEM #2 FIX: Hard-Coded Column Assumptions
=============================================================================
This module now uses the Schema Resolver (when available) to auto-detect
column names, making it work with different data schemas.

=============================================================================
PROBLEM #4 FIX: Pipeline Rigidity  
=============================================================================
Market Basket Analysis REQUIRES Product column. If the dataset doesn't have 
product identification, this analysis will gracefully skip.
The pipeline controller checks for Product availability before calling
this module.
=============================================================================

Purpose:
    Analyze customer purchase patterns to identify product associations and
    generate data-driven product recommendations using market basket analysis.
    
Why Market Basket Analysis:
    1. Discovers co-purchase patterns in customer transactions
    2. Identifies strong product associations (frequent itemsets)
    3. Generates actionable recommendations with confidence/lift metrics
    4. Optimizes cross-selling and upselling strategies
    5. Improves customer satisfaction through relevant suggestions
    
Business Value:
    - Increase average order value through smart recommendations
    - Improve inventory planning based on association patterns
    - Enhance customer experience with personalized suggestions
    - Identify opportunity markets for bundle pricing
    - Reduce customer churn through targeted offers
"""

import sys
import os
import logging
from pathlib import Path
from typing import Tuple, List, Dict, Any, Optional

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mlxtend.frequent_patterns import apriori, association_rules
from sklearn.preprocessing import MultiLabelBinarizer

# Paths & Logging
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = Path(os.getenv("SI_DATA_DIR", str(BASE_DIR / "data")))
LOGS_DIR = BASE_DIR / "logs"
OUTPUT_DIR = Path(os.getenv("SI_OUTPUT_DIR", str(BASE_DIR / "output")))
PLOTS_DIR = Path(os.getenv("SI_PLOTS_DIR", str(OUTPUT_DIR / "plots")))
RECOMMENDATIONS_DIR = Path(os.getenv("SI_RECOMMENDATIONS_DIR", str(BASE_DIR / "output" / "recommendations")))

LOGS_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
PLOTS_DIR.mkdir(exist_ok=True)
RECOMMENDATIONS_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / 'recommendation.log', encoding='utf-8'),
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


def resolve_recommendation_columns(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    """
    Resolve required columns for market basket analysis.
    
    Market Basket requires:
    - order column (ORDER_ID) - for grouping transactions
    - product column (PRODUCT) - for item associations
    
    Returns dict with resolved column names or None if not found.
    """
    if SCHEMA_RESOLVER_AVAILABLE:
        resolver = SchemaResolver()
        result = resolver.resolve(df, "sales")
        
        return {
            "order": result.get_column(SemanticField.ORDER_ID),
            "product": result.get_column(SemanticField.PRODUCT)
        }
    else:
        # Fallback detection
        order_candidates = ["OrderID", "Order_ID", "order_id", "TransactionID", "InvoiceNo"]
        product_candidates = ["Product", "ProductID", "Product_ID", "product", "Item", "Description"]
        
        order_col = next((c for c in order_candidates if c in df.columns), None)
        product_col = next((c for c in product_candidates if c in df.columns), None)
        
        return {"order": order_col, "product": product_col}


def find_data_file() -> Path:
    """Find data file in multiple possible locations."""
    possible_paths = [
        OUTPUT_DIR / "cleaned_dataset.csv",
        OUTPUT_DIR / "merged_data.csv",
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
    Load and validate cleaned dataset for market basket analysis.
    
    Uses Schema Resolver to auto-detect column names.
    
    Args:
        input_path: Path to data file (optional, will auto-detect if None)
        
    Returns:
        Validated dataframe with required columns
        
    Raises:
        FileNotFoundError: If input file not found
        ValueError: If required columns missing or dataset empty
    """
    # Auto-detect file if not provided
    if input_path is None:
        input_path = find_data_file()
        
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    try:
        df = pd.read_csv(input_path)
    except Exception as e:
        raise ValueError(f"Failed to read CSV file: {str(e)[:100]}")
    
    logger.info(f"Loaded {len(df)} records from {input_path}")
    
    # Use Schema Resolver to find columns
    resolved = resolve_recommendation_columns(df)
    order_col = resolved.get("order")
    product_col = resolved.get("product")
    
    logger.info(f"Column resolution: order='{order_col}', product='{product_col}'")
    
    if not order_col or not product_col:
        logger.warning(f"Missing columns. Available: {list(df.columns)}")
        logger.warning("Market basket analysis requires OrderID and Product columns")
        raise ValueError(
            f"Missing required columns for market basket analysis.\n"
            f"  - OrderID: {order_col or 'NOT FOUND'}\n"
            f"  - Product: {product_col or 'NOT FOUND'}\n"
            f"  Available columns: {list(df.columns)}"
        )
    
    # Rename to standard names for processing
    df = df.rename(columns={order_col: "OrderID", product_col: "Product"})
    logger.info(f"Using columns: OrderID='{order_col}', Product='{product_col}'")
    
    # Validate required columns
    required_cols = ["OrderID", "Product"]
    
    if len(df) == 0:
        raise ValueError("Dataset is empty")
    
    # Check for nulls in critical columns
    null_count = df[required_cols].isnull().sum().sum()
    if null_count > 0:
        logger.warning(f"Found {null_count} null values in required columns")
        df = df.dropna(subset=required_cols)
        logger.info(f"Removed null records, now {len(df)} valid records remaining")
    
    logger.info(f"Validated {len(df)} records for market basket analysis")
    return df


def analyze_basket_composition(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Analyze and log basket composition statistics with quality metrics.
    
    Args:
        df: Transaction dataframe with OrderID and Product
        
    Returns:
        Dictionary with basket composition metrics
        
    Raises:
        ValueError: If analysis fails
    """
    logger.info("Analyzing basket composition...")
    
    try:
        total_orders = df["OrderID"].nunique()
        unique_products = df["Product"].nunique()
        total_items = len(df)
        
        basket_sizes = df.groupby("OrderID").size()
        avg_basket_size = float(basket_sizes.mean())
        max_basket_size = int(basket_sizes.max())
        min_basket_size = int(basket_sizes.min())
        
        multi_product_orders = int((basket_sizes > 1).sum())
        multi_product_pct = (multi_product_orders / total_orders) * 100
        
        metrics = {
            "total_orders": total_orders,
            "unique_products": unique_products,
            "total_items": total_items,
            "avg_basket_size": avg_basket_size,
            "max_basket_size": max_basket_size,
            "min_basket_size": min_basket_size,
            "multi_product_orders": multi_product_orders,
            "multi_product_pct": multi_product_pct
        }
        
        logger.info("--- BASKET COMPOSITION STATISTICS ---")
        logger.info(f"Total Orders: {total_orders}")
        logger.info(f"Unique Products: {unique_products}")
        logger.info(f"Average Basket Size: {avg_basket_size:.2f} items")
        logger.info(f"Basket Size Range: {min_basket_size}-{max_basket_size} items")
        logger.info(f"Multi-product Orders: {multi_product_orders} ({multi_product_pct:.1f}%)")
        
        if multi_product_pct < 1:
            logger.warning("Very few multi-product orders detected. Association rules may not be meaningful.")
        
        return metrics
        
    except Exception as e:
        raise ValueError(f"Error analyzing basket composition: {str(e)[:100]}")


def encode_baskets(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """
    Create one-hot encoded basket matrix for market basket analysis.
    
    Args:
        df: Transaction dataframe with OrderID and Product
        
    Returns:
        Tuple of (encoded_dataframe, product_list)
        
    Raises:
        ValueError: If encoding fails
    """
    logger.info("Encoding baskets for analysis...")
    
    try:
        # Group products by order
        baskets = df.groupby("OrderID")["Product"].apply(list)
        
        if len(baskets) == 0:
            raise ValueError("No valid orders found for encoding")
        
        # One-hot encode
        mlb = MultiLabelBinarizer()
        basket_encoded = pd.DataFrame(
            mlb.fit_transform(baskets),
            columns=mlb.classes_,
            index=baskets.index
        )
        
        # CRITICAL: Convert to boolean dtype for mlxtend compatibility
        # Prevents warning about non-bool DataFrame and ensures stable behavior
        basket_encoded = basket_encoded.astype(bool)
        
        logger.info(f"Created basket matrix: {basket_encoded.shape[0]} orders x {basket_encoded.shape[1]} products")
        
        # Sparsity analysis
        sparsity = 1 - (basket_encoded.sum().sum() / (basket_encoded.shape[0] * basket_encoded.shape[1]))
        logger.info(f"Matrix sparsity: {sparsity*100:.1f}%")
        
        return basket_encoded, list(mlb.classes_)
        
    except Exception as e:
        raise ValueError(f"Error encoding baskets: {str(e)[:100]}")


def mine_association_rules(basket_encoded: pd.DataFrame, 
                          min_support: float = 0.01,
                          min_confidence: float = 0.1) -> pd.DataFrame:
    """
    Mine association rules using Apriori algorithm.
    
    Args:
        basket_encoded: One-hot encoded basket matrix
        min_support: Minimum support threshold (0.0-1.0)
            - 0.01 (1%) is the default, suitable for exploratory analysis
            - For production, consider 0.02-0.05 to reduce false positives
            - Lower values generate more rules but may include spurious patterns
            - Rule of thumb: min_support >= 1 / (number of orders * 2)
        min_confidence: Minimum confidence threshold (0.0-1.0)
            - 0.1 (10%) is the default
            - Higher values (0.3-0.5) ensure more reliable recommendations
            - Lower values may include coincidental associations
        
    Returns:
        Dataframe with association rules sorted by confidence and lift
        
    Raises:
        ValueError: If no frequent itemsets/rules found or invalid parameters
        
    Note:
        Always validate rules with domain knowledge. High support/confidence
        doesn't guarantee business relevance. Consider:
        - Lift > 1.0 indicates positive correlation (required for useful rules)
        - Lift > 2.0 suggests strong association
        - High conviction (>1) means the rule is reliable
    """
    # Validate parameters
    if not (0 < min_support < 1):
        raise ValueError(f"min_support must be between 0 and 1, got {min_support}")
    if not (0 < min_confidence < 1):
        raise ValueError(f"min_confidence must be between 0 and 1, got {min_confidence}")
    
    logger.info(f"Mining frequent itemsets (min_support={min_support})...")
    
    try:
        # Find frequent itemsets
        frequent_itemsets = apriori(
            basket_encoded,
            min_support=min_support,
            use_colnames=True,
            verbose=0
        )
        
        if len(frequent_itemsets) == 0:
            raise ValueError(
                f"No frequent itemsets found with min_support={min_support}. "
                f"Try lowering min_support (e.g., 0.005) or check basket data quality."
            )
        
        logger.info(f"Frequent itemsets found: {len(frequent_itemsets)}")
        logger.info(f"Support range: {frequent_itemsets['support'].min():.4f}-{frequent_itemsets['support'].max():.4f}")
        
    except Exception as e:
        raise ValueError(f"Error finding frequent itemsets: {str(e)[:100]}")
    
    # Generate association rules
    logger.info(f"Generating association rules (min_confidence={min_confidence})...")
    
    try:
        # Use standard association_rules signature for mlxtend compatibility
        # Do NOT use num_itemsets or other non-standard parameters
        rules = association_rules(
            frequent_itemsets,
            metric="confidence",
            min_threshold=min_confidence
        )
        
        if len(rules) == 0:
            raise ValueError(
                f"No rules found with min_confidence={min_confidence}. "
                f"Try lowering min_confidence or improving data quality."
            )
    except TypeError as e:
        # Handle any remaining parameter issues gracefully
        logger.error(f"association_rules parameter error: {e}")
        raise ValueError(f"Error generating association rules: {str(e)[:100]}")
    except Exception as e:
        raise ValueError(f"Error generating association rules: {str(e)[:100]}")
    
    # CRITICAL: Filter by lift > 1.0 (positive association)
    # Lift < 1 means negative correlation (buying A makes buying B LESS likely)
    # Lift = 1 means no correlation (random chance)
    # Lift > 1 means positive correlation (useful for recommendations)
    initial_count = len(rules)
    rules = rules[rules["lift"] > 1.0]
    filtered_count = initial_count - len(rules)
    if filtered_count > 0:
        logger.info(f"Filtered out {filtered_count} rules with lift <= 1.0 (no positive correlation)")
    
    if len(rules) == 0:
        raise ValueError(
            "No rules with lift > 1.0 found. "
            "This means no meaningful positive associations exist in the data."
        )
    
    # Sort by metrics
    rules = rules.sort_values(
        by=["confidence", "lift"],
        ascending=[False, False]
    ).reset_index(drop=True)
    
    # Add rule ID
    rules["RuleID"] = range(1, len(rules) + 1)
    
    logger.info(f"Generated {len(rules)} association rules")
    logger.info(f"Confidence range: {rules['confidence'].min():.4f}-{rules['confidence'].max():.4f}")
    logger.info(f"Lift range: {rules['lift'].min():.4f}-{rules['lift'].max():.4f}")
    logger.info(f"Average confidence: {rules['confidence'].mean():.4f}")
    logger.info(f"Average lift: {rules['lift'].mean():.4f}")
    
    return rules


def format_rules_for_display(rules: pd.DataFrame) -> pd.DataFrame:
    """
    Format rules for human-readable display and CSV output.
    
    Args:
        rules: Association rules dataframe
        
    Returns:
        Formatted rules dataframe with readable strings
        
    Raises:
        ValueError: If formatting fails
    """
    try:
        # Convert frozensets to strings
        rules_display = rules.copy()
        rules_display["Antecedents"] = rules_display["antecedents"].apply(
            lambda x: ", ".join(sorted(list(x)))
        )
        rules_display["Consequents"] = rules_display["consequents"].apply(
            lambda x: ", ".join(sorted(list(x)))
        )
    except Exception as e:
        raise ValueError(f"Error formatting rules: {str(e)[:100]}")
    
    # Select columns for output
    cols_to_select = ["RuleID", "Antecedents", "Consequents",
                      "support", "confidence", "lift",
                      "leverage", "conviction"]
    
    # Check which columns exist
    cols_to_select = [c for c in cols_to_select if c in rules_display.columns]
    rules_display = rules_display[cols_to_select]
    
    # Rename for readability
    rename_map = {
        "Antecedents": "IF (Buy)",
        "Consequents": "THEN (Recommend)",
        "support": "Support",
        "confidence": "Confidence",
        "lift": "Lift",
        "leverage": "Leverage",
        "conviction": "Conviction"
    }
    rules_display.columns = [rename_map.get(c, c) for c in rules_display.columns]
    
    return rules_display


def plot_association_rules(rules: pd.DataFrame, plots_dir: Path) -> None:
    """
    Create professional visualizations for association rules analysis.
    
    Args:
        rules: Association rules dataframe
        plots_dir: Directory to save plots
        
    Raises:
        ValueError: If rules dataframe is invalid or visualization fails
    """
    logger.info("Generating rule visualizations...")
    
    if len(rules) == 0 or "confidence" not in rules.columns:
        raise ValueError("Invalid rules dataframe for visualization")
    
    plt.style.use('seaborn-v0_8-darkgrid')
    
    # 1. Confidence vs Lift scatter plot
    fig, ax = plt.subplots(figsize=(10, 6))
    scatter = ax.scatter(
        rules["confidence"],
        rules["lift"],
        s=rules["support"] * 1000,  # Size by support
        c=rules["leverage"],  # Color by leverage
        cmap="YlOrRd",
        alpha=0.6,
        edgecolors="black",
        linewidth=0.5
    )
    ax.set_xlabel("Confidence", fontsize=11, fontweight='bold')
    ax.set_ylabel("Lift", fontsize=11, fontweight='bold')
    ax.set_title("Association Rules: Confidence vs Lift\n(Bubble size = Support, Color = Leverage)", 
                 fontsize=12, fontweight='bold', pad=15)
    ax.grid(True, alpha=0.3)
    plt.colorbar(scatter, ax=ax, label="Leverage")
    plt.tight_layout()
    plot_path = plots_dir / "rules_confidence_lift.png"
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    plt.close()
    logger.info(f"Confidence-Lift plot saved to {plot_path}")
    
    # 2. Top Rules by Lift
    top_n = min(10, len(rules))
    top_rules = rules.nlargest(top_n, "lift")
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    rule_labels = [
        f"{' + '.join(list(x))} -> {' + '.join(list(y))}"
        for x, y in zip(top_rules["antecedents"], top_rules["consequents"])
    ]
    
    y_pos = np.arange(len(rule_labels))
    bars = ax.barh(y_pos, top_rules["lift"].values, color='#2E86AB', alpha=0.8, edgecolor='black')
    
    # Add value labels on bars
    for i, (bar, val) in enumerate(zip(bars, top_rules["lift"].values)):
        ax.text(val + 0.05, i, f'{val:.2f}', va='center', fontsize=9)
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels(rule_labels, fontsize=9)
    ax.set_xlabel("Lift Score", fontsize=11, fontweight='bold')
    ax.set_title(f"Top {top_n} Association Rules by Lift", fontsize=12, fontweight='bold', pad=15)
    ax.grid(True, alpha=0.3, axis='x')
    plt.tight_layout()
    plot_path = plots_dir / "top_rules_by_lift.png"
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    plt.close()
    logger.info(f"Top rules plot saved to {plot_path}")
    
    # 3. Metrics Distribution
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    
    axes[0].hist(rules["support"], bins=20, color='#A23B72', edgecolor='black', alpha=0.7)
    axes[0].set_xlabel("Support", fontsize=10, fontweight='bold')
    axes[0].set_ylabel("Frequency", fontsize=10)
    axes[0].set_title("Support Distribution", fontsize=11, fontweight='bold')
    axes[0].grid(True, alpha=0.3)
    
    axes[1].hist(rules["confidence"], bins=20, color='#F18F01', edgecolor='black', alpha=0.7)
    axes[1].set_xlabel("Confidence", fontsize=10, fontweight='bold')
    axes[1].set_ylabel("Frequency", fontsize=10)
    axes[1].set_title("Confidence Distribution", fontsize=11, fontweight='bold')
    axes[1].grid(True, alpha=0.3)
    
    axes[2].hist(rules["lift"], bins=20, color='#6A994E', edgecolor='black', alpha=0.7)
    axes[2].set_xlabel("Lift", fontsize=10, fontweight='bold')
    axes[2].set_ylabel("Frequency", fontsize=10)
    axes[2].set_title("Lift Distribution", fontsize=11, fontweight='bold')
    axes[2].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plot_path = plots_dir / "rules_metrics_distribution.png"
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    plt.close()
    logger.info(f"Metrics distribution plot saved to {plot_path}")


def save_recommendation_results(rules: pd.DataFrame, output_path: Path) -> None:
    """
    Save recommendation rules to CSV with proper formatting.
    
    Args:
        rules: Association rules dataframe (formatted for display)
        output_path: Output file path
        
    Raises:
        IOError: If file write fails
    """
    try:
        rules.to_csv(output_path, index=False, encoding='utf-8')
        logger.info(f"Recommendation rules saved to {output_path} ({len(rules)} rules, {len(rules.columns)} columns)")
    except IOError as e:
        logger.error(f"Failed to save recommendation results: {e}")
        raise


def main() -> None:
    """
    Main execution pipeline for Phase 5: Market Basket Analysis.
    
    Pipeline:
        1. Load and validate transaction data
        2. Analyze basket composition and data quality
        3. Encode baskets for Apriori algorithm
        4. Mine association rules
        5. Format and display top recommendations
        6. Generate professional visualizations
        7. Save results to CSV
    """
    try:
        logger.info("" + "=" * 70)
        logger.info("Phase 5: Market Basket Analysis & Product Recommendations")
        logger.info("=" * 70)
        
        # Step 1: Load and validate data (auto-detects file)
        logger.info("\n[STEP 1/6] Loading and validating transaction data...")
        df = load_and_validate_data()
        logger.info(f"  Status: Loaded {len(df)} transaction records")
        
        # Step 2: Analyze basket composition
        logger.info("\n[STEP 2/6] Analyzing basket composition...")
        basket_metrics = analyze_basket_composition(df)
        
        # Check data quality for association rules
        if basket_metrics["multi_product_pct"] < 1:
            logger.warning("\n  WARNING: Very few multi-product baskets detected!")
            logger.warning("  Association rules may be sparse or unreliable.")
            logger.warning("  Consider collecting more data or adjusting parameters.")
        
        # Step 3: Encode baskets
        logger.info("\n[STEP 3/6] Encoding baskets for Apriori...")
        basket_encoded, products = encode_baskets(df)
        logger.info(f"  Status: Encoded {basket_encoded.shape[0]} orders with {basket_encoded.shape[1]} products")
        
        # Step 4: Mine association rules
        logger.info("\n[STEP 4/6] Mining association rules...")
        try:
            rules = mine_association_rules(
                basket_encoded,
                min_support=0.01,
                min_confidence=0.1
            )
            logger.info(f"  Status: Generated {len(rules)} rules")
        except ValueError as e:
            logger.warning(f"  Apriori mining failed: {e}")
            logger.warning("  *** Dataset may be too small for meaningful recommendations ***")
            
            # CRITICAL: Delete old product_recommendations.csv to ensure no stale data
            output_path = RECOMMENDATIONS_DIR / "product_recommendations.csv"
            if output_path.exists():
                try:
                    output_path.unlink()
                    logger.info(f"  ✓ Deleted old product_recommendations.csv (no new rules generated)")
                except Exception as del_e:
                    logger.error(f"  ✗ Failed to delete old recommendations: {del_e}")
            
            logger.info("\n" + "=" * 70)
            logger.info("Phase 5: Completed (status: no_recommendations)")
            logger.info("=" * 70)
            return
        
        # Step 5: Format and display recommendations
        logger.info("\n[STEP 5/6] Formatting recommendations...")
        rules_display = format_rules_for_display(rules)
        logger.info(f"  Status: Formatted {len(rules_display)} rules for output")
        
        logger.info("\n--- TOP 5 RECOMMENDATIONS ---")
        for idx, row in rules_display.head(5).iterrows():
            logger.info(
                f"  Rule {row['RuleID']}: {row['IF (Buy)']} -> {row['THEN (Recommend)']} "
                f"(Conf: {row['Confidence']:.1%}, Lift: {row['Lift']:.2f})"
            )
        
        # Step 6: Generate visualizations and save
        logger.info("\n[STEP 6/6] Generating visualizations and saving results...")
        plot_association_rules(rules, PLOTS_DIR)
        logger.info(f"  Status: Generated 3 visualizations")
        
        output_path = RECOMMENDATIONS_DIR / "product_recommendations.csv"
        save_recommendation_results(rules_display, output_path)
        
        logger.info("\n" + "=" * 70)
        logger.info("SUCCESS: Phase 5: Market Basket Analysis Completed")
        logger.info("=" * 70)
        logger.info(f"\nOutputs:")
        logger.info(f"  - Results: {output_path}")
        logger.info(f"  - Logs:    {LOGS_DIR / 'recommendation.log'}")
        logger.info(f"  - Plots:   {PLOTS_DIR}/")
        
    except FileNotFoundError as e:
        logger.error(f"File error: {e}")
        logger.info("Expected file: data/cleaned_dataset.csv")
        logger.info("Ensure data preprocessing (Phase 2) has been completed first")
        sys.exit(1)
        
    except ValueError as e:
        logger.error(f"Data validation error: {e}")
        sys.exit(1)
        
    except Exception as e:
        logger.error(f"Unexpected error during execution: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
