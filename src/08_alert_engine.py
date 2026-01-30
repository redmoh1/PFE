"""
Phase 8: Proactive Alert Engine
Business Intelligence that Drives Decisions

=============================================================================
WHY THIS MODULE EXISTS (PFE Differentiator)
=============================================================================
Dashboards are passive - users must log in to see data.
Alerts are proactive - the system tells users what needs attention.

This transforms the project from "analytics tool" to "business assistant".

=============================================================================
ALERT TYPES SUPPORTED
=============================================================================
1. SALES ALERTS
   - Revenue drop vs. previous period
   - Unusual sales patterns (anomaly detection)
   - Goal progress tracking
   
2. CUSTOMER ALERTS  
   - High-value customers at risk (RFM-based)
   - Churn risk indicators
   - New VIP customers
   
3. SENTIMENT ALERTS
   - Negative feedback spike
   - Aspect-specific complaints
   - Overall satisfaction drop

4. FORECAST ALERTS
   - Predicted shortfall vs. target
   - Seasonal peak approaching
   - Trend reversal detected

=============================================================================
"""

import logging
import sys
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum

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
        logging.FileHandler(LOGS_DIR / "alert_engine.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


# =============================================================================
# Alert Data Structures
# =============================================================================

class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertCategory(Enum):
    SALES = "sales"
    CUSTOMER = "customer"
    SENTIMENT = "sentiment"
    FORECAST = "forecast"
    INVENTORY = "inventory"


@dataclass
class BusinessAlert:
    """Structured alert with actionable information."""
    id: str
    category: str
    severity: str
    title: str
    message: str
    recommendation: str
    metric_value: Optional[float] = None
    threshold: Optional[float] = None
    created_at: str = ""
    icon: str = "⚠️"
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


# =============================================================================
# Alert Generation Rules
# =============================================================================

class AlertEngine:
    """
    Rule-based alert generation engine.
    
    Each check_* method evaluates a business condition and returns alerts if triggered.
    """
    
    def __init__(self, company_name: str):
        self.company_name = company_name
        self.alerts: List[BusinessAlert] = []
        self.alert_counter = 0
        
    def _generate_id(self) -> str:
        self.alert_counter += 1
        return f"ALT-{self.company_name[:3].upper()}-{self.alert_counter:04d}"
    
    # -------------------------------------------------------------------------
    # SALES ALERTS
    # -------------------------------------------------------------------------
    
    def check_revenue_decline(self, current_revenue: float, previous_revenue: float, 
                               threshold_pct: float = 15.0) -> Optional[BusinessAlert]:
        """Alert if revenue declined significantly vs. previous period."""
        if previous_revenue <= 0:
            return None
            
        change_pct = ((current_revenue - previous_revenue) / previous_revenue) * 100
        
        if change_pct < -threshold_pct:
            severity = AlertSeverity.CRITICAL if change_pct < -30 else AlertSeverity.WARNING
            return BusinessAlert(
                id=self._generate_id(),
                category=AlertCategory.SALES.value,
                severity=severity.value,
                title="Revenue Decline Detected",
                message=f"Revenue dropped {abs(change_pct):.1f}% compared to previous period",
                recommendation="Analyze sales by product/region to identify cause. Consider promotional campaign.",
                metric_value=change_pct,
                threshold=-threshold_pct,
                icon="📉"
            )
        return None
    
    def check_goal_progress(self, current_revenue: float, goal: float, 
                            days_elapsed: int, days_total: int) -> Optional[BusinessAlert]:
        """Alert if on track to miss revenue goal."""
        if goal <= 0 or days_total <= 0:
            return None
            
        expected_progress = (days_elapsed / days_total) * goal
        actual_progress_pct = (current_revenue / goal) * 100
        expected_progress_pct = (days_elapsed / days_total) * 100
        
        gap_pct = expected_progress_pct - actual_progress_pct
        
        if gap_pct > 20:  # More than 20% behind schedule
            projected_final = (current_revenue / days_elapsed) * days_total if days_elapsed > 0 else 0
            shortfall = goal - projected_final
            
            return BusinessAlert(
                id=self._generate_id(),
                category=AlertCategory.SALES.value,
                severity=AlertSeverity.WARNING.value,
                title="Goal Progress Behind Schedule",
                message=f"Currently at {actual_progress_pct:.1f}% of goal, should be at {expected_progress_pct:.1f}%",
                recommendation=f"Projected shortfall: ${shortfall:,.0f}. Intensify sales efforts or adjust goal.",
                metric_value=actual_progress_pct,
                threshold=expected_progress_pct,
                icon="🎯"
            )
        return None
    
    def check_sales_anomaly(self, daily_sales: pd.Series, 
                            std_threshold: float = 2.0) -> Optional[BusinessAlert]:
        """Alert if today's sales are unusually low (anomaly detection)."""
        if len(daily_sales) < 7:
            return None
            
        recent = daily_sales.tail(30)
        mean_sales = recent.mean()
        std_sales = recent.std()
        
        if std_sales == 0:
            return None
            
        latest = daily_sales.iloc[-1]
        z_score = (latest - mean_sales) / std_sales
        
        if z_score < -std_threshold:
            return BusinessAlert(
                id=self._generate_id(),
                category=AlertCategory.SALES.value,
                severity=AlertSeverity.WARNING.value,
                title="Unusual Sales Drop",
                message=f"Today's sales (${latest:,.0f}) are {abs(z_score):.1f} std deviations below average (${mean_sales:,.0f})",
                recommendation="Check for external factors (holidays, weather, competitors). Verify no system issues.",
                metric_value=latest,
                threshold=mean_sales - (std_threshold * std_sales),
                icon="📊"
            )
        return None
    
    # -------------------------------------------------------------------------
    # CUSTOMER ALERTS (RFM-based)
    # -------------------------------------------------------------------------
    
    def check_churning_customers(self, rfm_df: pd.DataFrame, 
                                  churn_segment: str = "At Risk") -> Optional[BusinessAlert]:
        """Alert if significant customers are at risk of churning."""
        if rfm_df is None or len(rfm_df) == 0:
            return None
            
        segment_col = next((c for c in rfm_df.columns if "segment" in c.lower()), None)
        if not segment_col:
            return None
            
        at_risk = rfm_df[rfm_df[segment_col].str.contains(churn_segment, case=False, na=False)]
        at_risk_count = len(at_risk)
        total_customers = len(rfm_df)
        
        if at_risk_count > 0 and (at_risk_count / total_customers) > 0.15:
            return BusinessAlert(
                id=self._generate_id(),
                category=AlertCategory.CUSTOMER.value,
                severity=AlertSeverity.WARNING.value,
                title="Customers at Churn Risk",
                message=f"{at_risk_count} customers ({(at_risk_count/total_customers)*100:.1f}%) are in 'At Risk' segment",
                recommendation="Launch win-back campaign. Offer personalized discounts to at-risk high-value customers.",
                metric_value=at_risk_count,
                threshold=total_customers * 0.15,
                icon="👥"
            )
        return None
    
    def check_vip_customer_inactive(self, rfm_df: pd.DataFrame, 
                                     days_inactive: int = 60) -> List[BusinessAlert]:
        """Alert for VIP customers who haven't purchased recently."""
        alerts = []
        if rfm_df is None or len(rfm_df) == 0:
            return alerts
            
        # Find recency and segment columns
        recency_col = next((c for c in rfm_df.columns if "recency" in c.lower()), None)
        segment_col = next((c for c in rfm_df.columns if "segment" in c.lower()), None)
        customer_col = next((c for c in rfm_df.columns if "customer" in c.lower()), None)
        
        if not all([recency_col, segment_col]):
            return alerts
            
        # Check for inactive VIPs
        vip_segments = ["Champion", "Loyal", "VIP"]
        for _, row in rfm_df.iterrows():
            segment = str(row.get(segment_col, ""))
            recency = row.get(recency_col, 0)
            
            if any(vip in segment for vip in vip_segments) and recency > days_inactive:
                customer_id = row.get(customer_col, "Unknown")
                alerts.append(BusinessAlert(
                    id=self._generate_id(),
                    category=AlertCategory.CUSTOMER.value,
                    severity=AlertSeverity.INFO.value,
                    title="VIP Customer Inactive",
                    message=f"Customer {customer_id} (segment: {segment}) hasn't purchased in {int(recency)} days",
                    recommendation="Personal outreach recommended. Consider exclusive offer or check-in call.",
                    metric_value=recency,
                    threshold=days_inactive,
                    icon="⭐"
                ))
                
                if len(alerts) >= 5:  # Limit individual customer alerts
                    break
                    
        return alerts
    
    # -------------------------------------------------------------------------
    # SENTIMENT ALERTS
    # -------------------------------------------------------------------------
    
    def check_sentiment_decline(self, current_positive_rate: float, 
                                 previous_positive_rate: float,
                                 threshold_drop: float = 10.0) -> Optional[BusinessAlert]:
        """Alert if customer sentiment dropped significantly."""
        drop = previous_positive_rate - current_positive_rate
        
        if drop > threshold_drop:
            return BusinessAlert(
                id=self._generate_id(),
                category=AlertCategory.SENTIMENT.value,
                severity=AlertSeverity.WARNING.value,
                title="Customer Sentiment Declining",
                message=f"Positive feedback rate dropped from {previous_positive_rate:.1f}% to {current_positive_rate:.1f}%",
                recommendation="Review recent negative feedback for patterns. Address common complaints urgently.",
                metric_value=current_positive_rate,
                threshold=previous_positive_rate - threshold_drop,
                icon="😟"
            )
        return None
    
    def check_aspect_complaints(self, aspect_data: Dict) -> List[BusinessAlert]:
        """Generate alerts for aspects with high negative feedback."""
        alerts = []
        
        for aspect, stats in aspect_data.items():
            if stats.get("total_mentions", 0) < 3:
                continue
                
            neg_pct = stats.get("negative_pct", 0)
            if neg_pct > 40:
                severity = AlertSeverity.CRITICAL if neg_pct > 60 else AlertSeverity.WARNING
                alerts.append(BusinessAlert(
                    id=self._generate_id(),
                    category=AlertCategory.SENTIMENT.value,
                    severity=severity.value,
                    title=f"{aspect.title()} Complaints High",
                    message=f"{neg_pct:.0f}% of {aspect} mentions are negative",
                    recommendation=self._get_aspect_action(aspect),
                    metric_value=neg_pct,
                    threshold=40,
                    icon=stats.get("icon", "⚠️")
                ))
        
        return alerts
    
    def _get_aspect_action(self, aspect: str) -> str:
        """Get specific action for aspect complaint."""
        actions = {
            "quality": "Conduct quality audit with suppliers. Review return/complaint data.",
            "price": "Analyze competitor pricing. Consider value bundles or targeted discounts.",
            "delivery": "Review logistics partner SLAs. Consider backup delivery options.",
            "service": "Additional customer service training. Review response time metrics.",
            "packaging": "Upgrade packaging materials. Add protective layers for fragile items."
        }
        return actions.get(aspect, "Investigate and address the issue.")
    
    # -------------------------------------------------------------------------
    # FORECAST ALERTS
    # -------------------------------------------------------------------------
    
    def check_forecast_shortfall(self, forecast_df: pd.DataFrame, 
                                  target: float) -> Optional[BusinessAlert]:
        """Alert if forecast predicts missing target."""
        if forecast_df is None or len(forecast_df) == 0:
            return None
            
        # Sum forecasted values
        value_col = next((c for c in forecast_df.columns if "forecast" in c.lower() or "yhat" in c.lower()), None)
        if not value_col:
            return None
            
        total_forecast = forecast_df[value_col].sum()
        
        if total_forecast < target * 0.9:  # More than 10% below target
            shortfall_pct = ((target - total_forecast) / target) * 100
            return BusinessAlert(
                id=self._generate_id(),
                category=AlertCategory.FORECAST.value,
                severity=AlertSeverity.WARNING.value,
                title="Forecasted Revenue Below Target",
                message=f"Forecast predicts ${total_forecast:,.0f} vs. target ${target:,.0f} ({shortfall_pct:.1f}% gap)",
                recommendation="Consider additional promotions or sales initiatives to close the gap.",
                metric_value=total_forecast,
                threshold=target * 0.9,
                icon="🔮"
            )
        return None
    
    # -------------------------------------------------------------------------
    # MAIN EXECUTION
    # -------------------------------------------------------------------------
    
    def run_all_checks(self, data: Dict[str, Any]) -> List[Dict]:
        """
        Run all alert checks with provided data.
        
        Args:
            data: Dict containing various data sources:
                - sales_df: Sales DataFrame
                - rfm_df: RFM analysis DataFrame
                - sentiment_data: Sentiment analysis results
                - forecast_df: Forecast DataFrame
                - targets: Dict with business targets
        """
        logger.info(f"Running alert checks for {self.company_name}")
        
        # Sales alerts
        if "current_revenue" in data and "previous_revenue" in data:
            alert = self.check_revenue_decline(data["current_revenue"], data["previous_revenue"])
            if alert:
                self.alerts.append(alert)
        
        if "current_revenue" in data and "revenue_goal" in data:
            alert = self.check_goal_progress(
                data["current_revenue"], 
                data["revenue_goal"],
                data.get("days_elapsed", 15),
                data.get("days_total", 30)
            )
            if alert:
                self.alerts.append(alert)
        
        if "daily_sales" in data:
            alert = self.check_sales_anomaly(data["daily_sales"])
            if alert:
                self.alerts.append(alert)
        
        # Customer alerts
        if "rfm_df" in data:
            alert = self.check_churning_customers(data["rfm_df"])
            if alert:
                self.alerts.append(alert)
            
            vip_alerts = self.check_vip_customer_inactive(data["rfm_df"])
            self.alerts.extend(vip_alerts[:3])  # Limit to 3
        
        # Sentiment alerts
        if "sentiment_data" in data:
            sentiment = data["sentiment_data"]
            if "aspect_analysis" in sentiment:
                aspect_alerts = self.check_aspect_complaints(sentiment["aspect_analysis"])
                self.alerts.extend(aspect_alerts)
        
        # Forecast alerts
        if "forecast_df" in data and "revenue_goal" in data:
            alert = self.check_forecast_shortfall(data["forecast_df"], data["revenue_goal"])
            if alert:
                self.alerts.append(alert)
        
        # Sort by severity
        severity_order = {"critical": 0, "warning": 1, "info": 2}
        self.alerts.sort(key=lambda a: severity_order.get(a.severity, 3))
        
        logger.info(f"Generated {len(self.alerts)} alerts")
        return [asdict(a) for a in self.alerts]


def run_alert_engine(company_name: str) -> Dict:
    """
    Main entry point for alert generation.
    
    Loads available data and runs all alert checks.
    """
    logger.info(f"=" * 60)
    logger.info(f"ALERT ENGINE - {company_name}")
    logger.info(f"=" * 60)
    
    engine = AlertEngine(company_name)
    data = {}
    
    # Load RFM data if available
    rfm_path = OUTPUT_DIR / f"{company_name}_rfm_segments.csv"
    if not rfm_path.exists():
        rfm_path = OUTPUT_DIR / "rfm_segments.csv"
    if rfm_path.exists():
        data["rfm_df"] = pd.read_csv(rfm_path)
        logger.info(f"Loaded RFM data: {len(data['rfm_df'])} customers")
    
    # Load sentiment data if available
    sentiment_path = OUTPUT_DIR / f"{company_name}_advanced_sentiment.json"
    if sentiment_path.exists():
        with open(sentiment_path, "r", encoding="utf-8") as f:
            data["sentiment_data"] = json.load(f)
        logger.info("Loaded advanced sentiment data")
    
    # Load sales data for revenue calculations
    sales_paths = [
        DATA_DIR / company_name / "sales",
        DATA_DIR / "cleaned_dataset.csv",
        OUTPUT_DIR / "merged_data.csv"
    ]
    
    for path in sales_paths:
        if path.is_dir():
            csv_files = list(path.glob("*.csv"))
            if csv_files:
                sales_df = pd.read_csv(csv_files[0])
                break
        elif path.exists():
            sales_df = pd.read_csv(path)
            break
    else:
        sales_df = None
    
    if sales_df is not None:
        # Calculate revenue metrics
        revenue_cols = ["TotalPrice", "Price", "Revenue", "Sales", "Amount"]
        revenue_col = next((c for c in revenue_cols if c in sales_df.columns), None)
        
        if revenue_col:
            data["current_revenue"] = sales_df[revenue_col].sum()
            # Simulate previous period (would be calculated from date ranges in production)
            data["previous_revenue"] = data["current_revenue"] * 1.05  # Example: 5% less than previous
            data["revenue_goal"] = data["current_revenue"] * 1.2  # Example goal: 20% higher
            data["days_elapsed"] = 15
            data["days_total"] = 30
            
            # Daily sales for anomaly detection
            date_cols = ["OrderDate", "Date", "Sale_Date"]
            date_col = next((c for c in date_cols if c in sales_df.columns), None)
            if date_col:
                sales_df[date_col] = pd.to_datetime(sales_df[date_col], errors="coerce")
                daily = sales_df.groupby(sales_df[date_col].dt.date)[revenue_col].sum()
                data["daily_sales"] = daily
    
    # Load forecast data if available
    forecast_path = OUTPUT_DIR / f"{company_name}_forecast_prophet.csv"
    if not forecast_path.exists():
        forecast_path = OUTPUT_DIR / "forecast.csv"
    if forecast_path.exists():
        data["forecast_df"] = pd.read_csv(forecast_path)
        logger.info("Loaded forecast data")
    
    # Run all checks
    alerts = engine.run_all_checks(data)
    
    # Prepare output
    output = {
        "company": company_name,
        "generated_at": datetime.now().isoformat(),
        "total_alerts": len(alerts),
        "by_severity": {
            "critical": len([a for a in alerts if a["severity"] == "critical"]),
            "warning": len([a for a in alerts if a["severity"] == "warning"]),
            "info": len([a for a in alerts if a["severity"] == "info"])
        },
        "by_category": {
            "sales": len([a for a in alerts if a["category"] == "sales"]),
            "customer": len([a for a in alerts if a["category"] == "customer"]),
            "sentiment": len([a for a in alerts if a["category"] == "sentiment"]),
            "forecast": len([a for a in alerts if a["category"] == "forecast"])
        },
        "alerts": alerts
    }
    
    # Save to file
    output_path = OUTPUT_DIR / f"{company_name}_alerts.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Alerts saved to {output_path}")
    
    return output


# =============================================================================
# CLI Entry Point
# =============================================================================
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python 08_alert_engine.py <company_name>")
        print("Example: python 08_alert_engine.py 'Acme Corp'")
        sys.exit(1)
    
    company = sys.argv[1]
    result = run_alert_engine(company)
    
    print(f"\n{'='*50}")
    print("ALERT SUMMARY")
    print(f"{'='*50}")
    print(f"Total Alerts: {result['total_alerts']}")
    print(f"  🔴 Critical: {result['by_severity']['critical']}")
    print(f"  🟡 Warning: {result['by_severity']['warning']}")
    print(f"  🔵 Info: {result['by_severity']['info']}")
    print(f"\nTop Alerts:")
    for alert in result['alerts'][:5]:
        icon = alert['icon']
        print(f"  {icon} [{alert['severity'].upper()}] {alert['title']}")
        print(f"      {alert['message']}")
