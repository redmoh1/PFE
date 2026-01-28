"""
Model Explainability Module

Provides human-readable explanations for:
1. Sales Forecasts (trend, seasonality, drivers)
2. RFM Segmentation (why customers are in each segment)
3. Product Recommendations (association rule metrics)

WHY:
- Build trust with stakeholders
- Enable business decisions
- Satisfy regulatory requirements (in some domains)
- Debug model behavior
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# -------------------------------------------------
# Forecast Explainability
# -------------------------------------------------
def explain_forecast(
    forecast_df: pd.DataFrame,
    components: Optional[Dict] = None,
    model_type: str = "Prophet"
) -> Dict:
    """Generate human-readable explanation of sales forecast.
    
    Args:
        forecast_df: DataFrame with forecast results (ds, yhat, yhat_lower, yhat_upper)
        components: Optional trend/seasonality decomposition
        model_type: "Prophet" or "LinearRegression"
        
    Returns:
        Dictionary with explanations and key insights
    """
    explanations = {
        "model_type": model_type,
        "forecast_summary": {},
        "trend_analysis": {},
        "seasonality_insights": {},
        "confidence": {},
        "recommendations": [],
    }
    
    # Summary statistics
    avg_forecast = forecast_df["yhat"].mean()
    min_forecast = forecast_df["yhat"].min()
    max_forecast = forecast_df["yhat"].max()
    total_forecast = forecast_df["yhat"].sum()
    
    explanations["forecast_summary"] = {
        "average_monthly_sales": f"${avg_forecast:,.2f}",
        "minimum_month": f"${min_forecast:,.2f}",
        "maximum_month": f"${max_forecast:,.2f}",
        "total_forecasted": f"${total_forecast:,.2f}",
        "interpretation": f"Over the next {len(forecast_df)} months, we expect average monthly sales of ${avg_forecast:,.2f}, "
                         f"with fluctuations between ${min_forecast:,.2f} and ${max_forecast:,.2f}."
    }
    
    # Trend analysis
    if len(forecast_df) >= 2:
        first_month = forecast_df["yhat"].iloc[0]
        last_month = forecast_df["yhat"].iloc[-1]
        growth_pct = ((last_month - first_month) / first_month) * 100
        
        trend_direction = "upward" if growth_pct > 5 else "downward" if growth_pct < -5 else "stable"
        
        explanations["trend_analysis"] = {
            "direction": trend_direction,
            "growth_rate": f"{growth_pct:+.1f}%",
            "interpretation": f"The forecast shows a {trend_direction} trend with {abs(growth_pct):.1f}% "
                             f"{'growth' if growth_pct > 0 else 'decline'} from first to last month."
        }
        
        # Recommendations based on trend
        if growth_pct > 10:
            explanations["recommendations"].append(
                "Strong growth expected. Consider increasing inventory and marketing budget."
            )
        elif growth_pct < -10:
            explanations["recommendations"].append(
                "Declining trend detected. Review pricing strategy and customer retention efforts."
            )
    
    # Confidence intervals
    if "yhat_lower" in forecast_df.columns and "yhat_upper" in forecast_df.columns:
        avg_uncertainty = (forecast_df["yhat_upper"] - forecast_df["yhat_lower"]).mean()
        uncertainty_pct = (avg_uncertainty / avg_forecast) * 100
        
        confidence_level = "high" if uncertainty_pct < 20 else "medium" if uncertainty_pct < 40 else "low"
        
        explanations["confidence"] = {
            "level": confidence_level,
            "average_range": f"±${avg_uncertainty/2:,.2f}",
            "uncertainty_percent": f"{uncertainty_pct:.1f}%",
            "interpretation": f"Forecast confidence is {confidence_level}. "
                             f"Actual values are likely within ±{uncertainty_pct:.1f}% of predictions."
        }
    
    # Seasonality insights (if Prophet)
    if components and "yearly" in components and components["yearly"]:
        yearly_data = pd.DataFrame(components["yearly"])
        if not yearly_data.empty and "yearly" in yearly_data.columns:
            max_seasonal_idx = yearly_data["yearly"].idxmax()
            min_seasonal_idx = yearly_data["yearly"].idxmin()
            
            explanations["seasonality_insights"] = {
                "present": True,
                "interpretation": f"Sales show seasonal patterns. "
                                 f"Peak periods and slow periods are identified in the forecast.",
                "recommendation": "Plan inventory and marketing campaigns around seasonal peaks."
            }
            explanations["recommendations"].append(
                "Seasonal patterns detected. Align operations with high/low demand periods."
            )
    
    return explanations


# -------------------------------------------------
# RFM Segmentation Explainability
# -------------------------------------------------
def explain_rfm_segment(
    recency: int,
    frequency: int,
    monetary: float,
    r_score: int,
    f_score: int,
    m_score: int,
    segment: str
) -> Dict:
    """Explain why a customer is in a specific RFM segment.
    
    Args:
        recency: Days since last purchase
        frequency: Number of purchases
        monetary: Total spending
        r_score, f_score, m_score: RFM scores (1-5)
        segment: Segment name (e.g., "Champions", "At Risk")
        
    Returns:
        Explanation dictionary
    """
    explanations = {
        "segment": segment,
        "scores": {
            "recency": {"value": recency, "score": r_score, "rating": score_to_rating(r_score)},
            "frequency": {"value": frequency, "score": f_score, "rating": score_to_rating(f_score)},
            "monetary": {"value": f"${monetary:,.2f}", "score": m_score, "rating": score_to_rating(m_score)},
        },
        "interpretation": "",
        "characteristics": [],
        "action_items": [],
    }
    
    # Segment-specific explanations
    segment_explanations = {
        "Champions": {
            "interpretation": "This customer is a Champion - highly valuable with recent, frequent purchases.",
            "characteristics": [
                "Purchased recently (high recency)",
                "Buys frequently (high frequency)",
                "High spending (high monetary value)",
            ],
            "action_items": [
                "Reward loyalty with exclusive offers",
                "Request reviews and testimonials",
                "Upsell premium products",
            ]
        },
        "Loyal Customers": {
            "interpretation": "Loyal customer with consistent purchase behavior.",
            "characteristics": [
                "Regular purchase pattern",
                "Moderate to high spending",
            ],
            "action_items": [
                "Maintain engagement with personalized communication",
                "Introduce loyalty program benefits",
            ]
        },
        "At Risk": {
            "interpretation": "Previously valuable customer now at risk of churning.",
            "characteristics": [
                f"Haven't purchased in {recency} days",
                "Previously active buyer",
            ],
            "action_items": [
                "Send win-back campaigns",
                "Offer special discounts",
                "Survey to understand why they left",
            ]
        },
        "Hibernating": {
            "interpretation": "Customer has gone dormant - urgent re-engagement needed.",
            "characteristics": [
                f"Last purchase was {recency} days ago",
                "Low recent activity",
            ],
            "action_items": [
                "Aggressive reactivation campaign",
                "Deep discounts or freebies",
                "Consider if re-engagement is cost-effective",
            ]
        },
        "Promising": {
            "interpretation": "New customer showing potential for growth.",
            "characteristics": [
                "Recent first purchase",
                "Low frequency so far",
            ],
            "action_items": [
                "Nurture with onboarding campaigns",
                "Encourage second purchase",
                "Provide excellent first experience",
            ]
        },
    }
    
    # Use segment-specific explanation or generic one
    if segment in segment_explanations:
        explanations.update(segment_explanations[segment])
    else:
        explanations["interpretation"] = f"Customer segment: {segment}"
        explanations["characteristics"] = [
            f"Recency score: {r_score}/5 (last purchase: {recency} days ago)",
            f"Frequency score: {f_score}/5 ({frequency} purchases)",
            f"Monetary score: {m_score}/5 (${monetary:,.2f} total)",
        ]
    
    return explanations


def score_to_rating(score: int) -> str:
    """Convert numeric score to qualitative rating."""
    ratings = {5: "Excellent", 4: "Good", 3: "Average", 2: "Below Average", 1: "Poor"}
    return ratings.get(score, "Unknown")


# -------------------------------------------------
# Product Recommendation Explainability
# -------------------------------------------------
def explain_recommendation(
    product_a: str,
    product_b: str,
    support: float,
    confidence: float,
    lift: float
) -> Dict:
    """Explain why Product B is recommended with Product A.
    
    Args:
        product_a: Antecedent product
        product_b: Consequent product (recommended)
        support: Rule support (frequency)
        confidence: Rule confidence
        lift: Rule lift (strength)
        
    Returns:
        Explanation dictionary
    """
    explanations = {
        "recommendation": f"Customers who buy '{product_a}' often buy '{product_b}'",
        "metrics": {
            "support": {
                "value": f"{support*100:.2f}%",
                "interpretation": f"These products appear together in {support*100:.2f}% of all transactions"
            },
            "confidence": {
                "value": f"{confidence*100:.1f}%",
                "interpretation": f"{confidence*100:.1f}% of customers who buy '{product_a}' also buy '{product_b}'"
            },
            "lift": {
                "value": f"{lift:.2f}",
                "interpretation": lift_interpretation(lift)
            }
        },
        "strength": recommendation_strength(confidence, lift),
        "action_items": [],
    }
    
    # Business actions based on strength
    if confidence > 0.5 and lift > 2:
        explanations["action_items"] = [
            f"Create product bundle: '{product_a}' + '{product_b}'",
            "Place these products near each other in store/website",
            "Offer discount when bought together",
        ]
    elif confidence > 0.3 and lift > 1.5:
        explanations["action_items"] = [
            "Suggest as cross-sell during checkout",
            "Include in 'Customers also bought' section",
        ]
    else:
        explanations["action_items"] = [
            "Weak association - monitor for changes",
        ]
    
    return explanations


def lift_interpretation(lift: float) -> str:
    """Interpret lift value in business terms."""
    if lift > 3:
        return f"{lift:.2f}x more likely to buy together than by chance - VERY STRONG relationship"
    elif lift > 2:
        return f"{lift:.2f}x more likely to buy together - STRONG relationship"
    elif lift > 1.5:
        return f"{lift:.2f}x more likely - MODERATE relationship"
    elif lift > 1:
        return f"{lift:.2f}x more likely - WEAK positive relationship"
    else:
        return f"{lift:.2f} - No meaningful relationship"


def recommendation_strength(confidence: float, lift: float) -> str:
    """Overall strength rating."""
    if confidence > 0.5 and lift > 2:
        return "Very Strong"
    elif confidence > 0.3 and lift > 1.5:
        return "Strong"
    elif confidence > 0.2 and lift > 1.2:
        return "Moderate"
    else:
        return "Weak"


# -------------------------------------------------
# Explainability API
# -------------------------------------------------
class ExplainabilityEngine:
    """Unified explainability interface for all models."""
    
    @staticmethod
    def explain_forecast_results(forecast_data: Dict) -> Dict:
        """Wrapper for forecast explanation."""
        forecast_df = pd.DataFrame(forecast_data["forecast"])
        components = forecast_data.get("components")
        model_type = forecast_data.get("metrics", {}).get("model", "Prophet")
        
        return explain_forecast(forecast_df, components, model_type)
    
    @staticmethod
    def explain_customer_segment(customer_data: Dict) -> Dict:
        """Wrapper for RFM explanation."""
        return explain_rfm_segment(
            recency=customer_data["recency"],
            frequency=customer_data["frequency"],
            monetary=customer_data["monetary"],
            r_score=customer_data["r_score"],
            f_score=customer_data["f_score"],
            m_score=customer_data["m_score"],
            segment=customer_data["segment"],
        )
    
    @staticmethod
    def explain_product_recommendation(rule: Dict) -> Dict:
        """Wrapper for recommendation explanation."""
        return explain_recommendation(
            product_a=rule["antecedent"],
            product_b=rule["consequent"],
            support=rule["support"],
            confidence=rule["confidence"],
            lift=rule["lift"],
        )


# -------------------------------------------------
# Example Usage
# -------------------------------------------------
if __name__ == "__main__":
    print("="*70)
    print("MODEL EXPLAINABILITY EXAMPLES")
    print("="*70)
    
    # 1. Forecast Explanation
    print("\n1. FORECAST EXPLANATION:")
    forecast_example = pd.DataFrame({
        "ds": pd.date_range("2026-02", periods=6, freq="MS"),
        "yhat": [15000, 16000, 17500, 16800, 15200, 15800],
        "yhat_lower": [13500, 14400, 15750, 15120, 13680, 14220],
        "yhat_upper": [16500, 17600, 19250, 18480, 16720, 17380],
    })
    
    forecast_explanation = explain_forecast(forecast_example, model_type="Prophet")
    print(f"  Interpretation: {forecast_explanation['forecast_summary']['interpretation']}")
    print(f"  Trend: {forecast_explanation['trend_analysis']['interpretation']}")
    
    # 2. RFM Explanation
    print("\n2. RFM SEGMENT EXPLANATION:")
    rfm_explanation = explain_rfm_segment(
        recency=5, frequency=15, monetary=5000,
        r_score=5, f_score=5, m_score=5,
        segment="Champions"
    )
    print(f"  {rfm_explanation['interpretation']}")
    print(f"  Actions: {', '.join(rfm_explanation['action_items'][:2])}")
    
    # 3. Recommendation Explanation
    print("\n3. PRODUCT RECOMMENDATION EXPLANATION:")
    rec_explanation = explain_recommendation(
        product_a="Laptop",
        product_b="Mouse",
        support=0.15,
        confidence=0.65,
        lift=2.5
    )
    print(f"  {rec_explanation['recommendation']}")
    print(f"  Strength: {rec_explanation['strength']}")
    print(f"  Confidence: {rec_explanation['metrics']['confidence']['interpretation']}")
    
    print("\n" + "="*70)
