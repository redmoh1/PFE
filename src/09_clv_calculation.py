"""
Phase 9: Customer Lifetime Value (CLV) Calculation
Strategic Customer Valuation for Business Decisions

=============================================================================
WHY CLV MATTERS (Business Value)
=============================================================================
CLV answers: "How much is this customer worth over their entire relationship?"

Business applications:
1. Marketing Budget: "How much can I spend to acquire a customer?"
2. Segmentation: Beyond RFM - which customers are truly valuable?
3. Prioritization: "Which customers deserve VIP treatment?"
4. Forecasting: "What's the future value of my customer base?"

=============================================================================
CLV CALCULATION METHODS
=============================================================================
This module implements multiple CLV approaches:

1. HISTORICAL CLV (Simple)
   CLV = Total Revenue from Customer
   Pro: Simple, factual
   Con: Backward-looking

2. AVERAGE CLV
   CLV = Avg Order Value × Purchase Frequency × Customer Lifespan
   Pro: Easy to understand
   Con: Assumes uniform behavior

3. PREDICTIVE CLV (Advanced)
   Uses probability models (BG/NBD) to predict future purchases
   Pro: Forward-looking, accounts for churn
   Con: Requires more data

=============================================================================
"""

import logging
import sys
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

import pandas as pd
import numpy as np

# -------------------------------------------------
# Paths & Logging
# -------------------------------------------------
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
LOGS_DIR = BASE_DIR / "logs"

OUTPUT_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "clv_calculation.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


# =============================================================================
# CLV Calculation Functions
# =============================================================================

def calculate_historical_clv(customer_transactions: pd.DataFrame,
                              customer_col: str,
                              revenue_col: str) -> pd.DataFrame:
    """
    Calculate Historical CLV - total revenue per customer.
    
    This is the simplest form: sum of all purchases.
    """
    clv = customer_transactions.groupby(customer_col).agg({
        revenue_col: 'sum'
    }).reset_index()
    
    clv.columns = [customer_col, 'historical_clv']
    return clv


def calculate_average_clv(customer_transactions: pd.DataFrame,
                          customer_col: str,
                          revenue_col: str,
                          date_col: str,
                          avg_lifespan_years: float = 2.0) -> pd.DataFrame:
    """
    Calculate Average CLV using the formula:
    CLV = AOV × Purchase Frequency × Average Lifespan
    
    Args:
        avg_lifespan_years: Expected customer relationship duration
    """
    # Calculate per-customer metrics
    customer_metrics = customer_transactions.groupby(customer_col).agg({
        revenue_col: ['sum', 'mean', 'count'],
        date_col: ['min', 'max']
    }).reset_index()
    
    customer_metrics.columns = [
        customer_col, 'total_revenue', 'avg_order_value', 'purchase_count',
        'first_purchase', 'last_purchase'
    ]
    
    # Calculate customer tenure in days
    customer_metrics['first_purchase'] = pd.to_datetime(customer_metrics['first_purchase'])
    customer_metrics['last_purchase'] = pd.to_datetime(customer_metrics['last_purchase'])
    customer_metrics['tenure_days'] = (
        customer_metrics['last_purchase'] - customer_metrics['first_purchase']
    ).dt.days + 1  # +1 to avoid zero
    
    # Calculate purchase frequency (purchases per year)
    customer_metrics['tenure_years'] = customer_metrics['tenure_days'] / 365.25
    customer_metrics['purchase_frequency'] = (
        customer_metrics['purchase_count'] / 
        customer_metrics['tenure_years'].clip(lower=0.1)  # Avoid division by zero
    )
    
    # Calculate Average CLV
    customer_metrics['average_clv'] = (
        customer_metrics['avg_order_value'] * 
        customer_metrics['purchase_frequency'] * 
        avg_lifespan_years
    )
    
    return customer_metrics


def calculate_predictive_clv(customer_metrics: pd.DataFrame,
                              churn_rate: float = 0.2,
                              discount_rate: float = 0.1,
                              projection_years: int = 3) -> pd.DataFrame:
    """
    Calculate Predictive CLV using a simplified probability model.
    
    CLV = Σ (Expected Revenue × Retention Probability × Discount Factor)
    
    Args:
        churn_rate: Annual probability of customer churning
        discount_rate: Annual discount rate for future value
        projection_years: Years to project forward
    """
    retention_rate = 1 - churn_rate
    
    # Calculate expected future revenue per year
    expected_annual_revenue = (
        customer_metrics['avg_order_value'] * 
        customer_metrics['purchase_frequency']
    )
    
    # Calculate NPV of future cash flows
    predictive_clv = 0
    for year in range(1, projection_years + 1):
        # Probability customer is still active
        survival_prob = retention_rate ** year
        # Discount factor
        discount_factor = 1 / ((1 + discount_rate) ** year)
        # Add discounted expected revenue
        predictive_clv += expected_annual_revenue * survival_prob * discount_factor
    
    customer_metrics['predictive_clv'] = predictive_clv
    
    return customer_metrics


def assign_clv_segments(customer_metrics: pd.DataFrame,
                        clv_column: str = 'average_clv') -> pd.DataFrame:
    """
    Assign customer segments based on CLV quartiles.
    
    Segments:
    - Platinum: Top 10% 
    - Gold: 70-90 percentile
    - Silver: 40-70 percentile
    - Bronze: Bottom 40%
    """
    clv_values = customer_metrics[clv_column]
    
    # Calculate percentiles
    p40 = clv_values.quantile(0.40)
    p70 = clv_values.quantile(0.70)
    p90 = clv_values.quantile(0.90)
    
    def get_segment(clv):
        if clv >= p90:
            return 'Platinum'
        elif clv >= p70:
            return 'Gold'
        elif clv >= p40:
            return 'Silver'
        else:
            return 'Bronze'
    
    customer_metrics['clv_segment'] = clv_values.apply(get_segment)
    
    return customer_metrics


def generate_clv_insights(customer_metrics: pd.DataFrame) -> Dict:
    """
    Generate actionable insights from CLV analysis.
    """
    insights = {
        "summary": {},
        "segments": {},
        "recommendations": []
    }
    
    # Overall statistics
    insights["summary"] = {
        "total_customers": len(customer_metrics),
        "total_clv": round(customer_metrics['average_clv'].sum(), 2),
        "average_clv": round(customer_metrics['average_clv'].mean(), 2),
        "median_clv": round(customer_metrics['average_clv'].median(), 2),
        "clv_std": round(customer_metrics['average_clv'].std(), 2)
    }
    
    # Segment breakdown
    if 'clv_segment' in customer_metrics.columns:
        segment_stats = customer_metrics.groupby('clv_segment').agg({
            'average_clv': ['count', 'sum', 'mean']
        }).round(2)
        
        segment_stats.columns = ['customer_count', 'total_clv', 'avg_clv']
        
        for segment in ['Platinum', 'Gold', 'Silver', 'Bronze']:
            if segment in segment_stats.index:
                stats = segment_stats.loc[segment]
                insights["segments"][segment] = {
                    "count": int(stats['customer_count']),
                    "total_clv": float(stats['total_clv']),
                    "avg_clv": float(stats['avg_clv']),
                    "pct_of_total": round(
                        stats['total_clv'] / insights["summary"]["total_clv"] * 100, 1
                    )
                }
    
    # Generate recommendations
    if insights["segments"].get("Platinum"):
        platinum_pct = insights["segments"]["Platinum"]["pct_of_total"]
        insights["recommendations"].append({
            "type": "retention",
            "priority": "high",
            "message": f"Platinum customers ({insights['segments']['Platinum']['count']}) generate {platinum_pct}% of CLV",
            "action": "Implement VIP loyalty program with exclusive benefits for top customers"
        })
    
    if insights["segments"].get("Bronze"):
        bronze_count = insights["segments"]["Bronze"]["count"]
        insights["recommendations"].append({
            "type": "growth",
            "priority": "medium",
            "message": f"{bronze_count} Bronze customers have growth potential",
            "action": "Create upgrade path with targeted promotions to increase purchase frequency"
        })
    
    # Acquisition cost recommendation
    avg_clv = insights["summary"]["average_clv"]
    recommended_cac = avg_clv * 0.3  # Rule of thumb: CAC should be < 30% of CLV
    insights["recommendations"].append({
        "type": "acquisition",
        "priority": "info",
        "message": f"Based on average CLV of ${avg_clv:.2f}",
        "action": f"Customer Acquisition Cost should not exceed ${recommended_cac:.2f} (30% of CLV)"
    })
    
    return insights


def run_clv_analysis(company_name: str) -> Dict:
    """
    Main entry point for CLV analysis.
    
    Args:
        company_name: Company identifier for multi-tenant data isolation
    """
    logger.info(f"=" * 60)
    logger.info(f"CLV ANALYSIS - {company_name}")
    logger.info(f"=" * 60)
    
    # Find sales data
    sales_paths = [
        DATA_DIR / company_name / "sales",
        OUTPUT_DIR / f"{company_name}_merged_data.csv",
        OUTPUT_DIR / "merged_data.csv",
        DATA_DIR / "cleaned_dataset.csv"
    ]
    
    sales_df = None
    for path in sales_paths:
        if path.is_dir():
            csv_files = list(path.glob("*.csv"))
            if csv_files:
                sales_df = pd.read_csv(csv_files[0])
                logger.info(f"Loaded sales data from {csv_files[0]}")
                break
        elif path.exists():
            sales_df = pd.read_csv(path)
            logger.info(f"Loaded sales data from {path}")
            break
    
    if sales_df is None:
        logger.error("No sales data found")
        return {"error": "No sales data found", "company": company_name}
    
    # Resolve columns
    customer_candidates = ["CustomerID", "Customer_ID", "customer_id", "CustomerId", "customer"]
    revenue_candidates = ["TotalPrice", "Price", "Revenue", "Sales", "Amount", "Total"]
    date_candidates = ["OrderDate", "Date", "Sale_Date", "Order_Date", "TransactionDate"]
    
    customer_col = next((c for c in customer_candidates if c in sales_df.columns), None)
    revenue_col = next((c for c in revenue_candidates if c in sales_df.columns), None)
    date_col = next((c for c in date_candidates if c in sales_df.columns), None)
    
    if not customer_col:
        logger.error("No customer ID column found - CLV requires customer identification")
        return {"error": "No customer ID column found", "company": company_name}
    
    if not revenue_col:
        logger.error("No revenue column found")
        return {"error": "No revenue column found", "company": company_name}
    
    logger.info(f"Using columns: Customer={customer_col}, Revenue={revenue_col}, Date={date_col}")
    
    # Prepare data
    if date_col:
        sales_df[date_col] = pd.to_datetime(sales_df[date_col], errors='coerce')
    
    # Remove invalid data
    sales_df = sales_df.dropna(subset=[customer_col, revenue_col])
    sales_df = sales_df[sales_df[revenue_col] > 0]
    
    logger.info(f"Processing {len(sales_df)} transactions for {sales_df[customer_col].nunique()} customers")
    
    # Calculate CLV
    if date_col:
        customer_metrics = calculate_average_clv(
            sales_df, customer_col, revenue_col, date_col
        )
        customer_metrics = calculate_predictive_clv(customer_metrics)
    else:
        # If no date column, use historical CLV only
        customer_metrics = calculate_historical_clv(sales_df, customer_col, revenue_col)
        customer_metrics['average_clv'] = customer_metrics['historical_clv']
    
    # Assign segments
    customer_metrics = assign_clv_segments(customer_metrics)
    
    # Generate insights
    insights = generate_clv_insights(customer_metrics)
    
    # Merge with RFM if available
    rfm_path = OUTPUT_DIR / f"{company_name}_rfm_segments.csv"
    if not rfm_path.exists():
        rfm_path = OUTPUT_DIR / "rfm_segments.csv"
    
    if rfm_path.exists():
        logger.info("Merging with RFM segments for enhanced analysis")
        rfm_df = pd.read_csv(rfm_path)
        rfm_customer_col = next((c for c in rfm_df.columns if "customer" in c.lower()), None)
        
        if rfm_customer_col:
            # Rename for merge
            rfm_df = rfm_df.rename(columns={rfm_customer_col: customer_col})
            # Select relevant RFM columns
            rfm_cols = [customer_col] + [c for c in rfm_df.columns if 'rfm' in c.lower() or 'segment' in c.lower()]
            rfm_subset = rfm_df[[c for c in rfm_cols if c in rfm_df.columns]]
            
            customer_metrics = customer_metrics.merge(rfm_subset, on=customer_col, how='left')
            logger.info("RFM data merged successfully")
    
    # Save results
    output_csv = OUTPUT_DIR / f"{company_name}_clv_analysis.csv"
    customer_metrics.to_csv(output_csv, index=False)
    logger.info(f"CLV data saved to {output_csv}")
    
    output_json = OUTPUT_DIR / f"{company_name}_clv_insights.json"
    output = {
        "company": company_name,
        "analysis_date": datetime.now().isoformat(),
        "insights": insights,
        "top_customers": customer_metrics.nlargest(10, 'average_clv')[
            [customer_col, 'average_clv', 'clv_segment']
        ].to_dict('records')
    }
    
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2, default=str)
    logger.info(f"CLV insights saved to {output_json}")
    
    return output


# =============================================================================
# CLI Entry Point
# =============================================================================
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python 09_clv_calculation.py <company_name>")
        print("Example: python 09_clv_calculation.py 'Acme Corp'")
        sys.exit(1)
    
    company = sys.argv[1]
    result = run_clv_analysis(company)
    
    if "error" not in result:
        print(f"\n{'='*50}")
        print("CLV ANALYSIS COMPLETE")
        print(f"{'='*50}")
        
        summary = result["insights"]["summary"]
        print(f"Total Customers: {summary['total_customers']}")
        print(f"Average CLV: ${summary['average_clv']:,.2f}")
        print(f"Total CLV: ${summary['total_clv']:,.2f}")
        
        print(f"\nSegment Breakdown:")
        for segment, data in result["insights"]["segments"].items():
            print(f"  {segment}: {data['count']} customers ({data['pct_of_total']}% of value)")
        
        print(f"\nTop 5 Customers by CLV:")
        for i, customer in enumerate(result["top_customers"][:5], 1):
            print(f"  {i}. Customer {customer[list(customer.keys())[0]]}: ${customer['average_clv']:,.2f}")
