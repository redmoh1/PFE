from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional, Tuple

import pandas as pd
from pydantic import BaseModel, Field


Severity = Literal["info", "warning", "critical"]


class Insight(BaseModel):
    id: str
    severity: Severity
    title: str
    description: str
    reason: str
    suggested_action: str
    metrics: Dict[str, Any] = Field(default_factory=dict)


class InsightsResponse(BaseModel):
    company_id: str
    generated_at: str
    insights: List[Insight]


def _pct_change(current: float, previous: float) -> Optional[float]:
    if previous == 0:
        return None
    return (current - previous) / previous * 100.0


def _periods_from_sales(sales_df: pd.DataFrame, days: int = 30) -> Tuple[pd.Timestamp, pd.Timestamp, pd.Timestamp, pd.Timestamp]:
    """Return (current_start, current_end, previous_start, previous_end) based on latest date."""
    if sales_df.empty or "__order_date" not in sales_df.columns:
        now = pd.Timestamp.now()
        current_end = now
    else:
        current_end = pd.to_datetime(sales_df["__order_date"].max(), errors="coerce")
        if isinstance(current_end, pd.Timestamp) and current_end.tzinfo is not None:
            current_end = current_end.tz_convert(None)

    current_start = current_end - pd.Timedelta(days=days)
    previous_end = current_start - pd.Timedelta(days=1)
    previous_start = previous_end - pd.Timedelta(days=days)
    return current_start, current_end, previous_start, previous_end


def generate_insights(
    *,
    company_id: str,
    sales_df: pd.DataFrame,
    forecast_df: Optional[pd.DataFrame] = None,
    rfm_df: Optional[pd.DataFrame] = None,
    sentiment_df: Optional[pd.DataFrame] = None,
    recommendations_df: Optional[pd.DataFrame] = None,
    limit: int = 8,
) -> InsightsResponse:
    """Generate deterministic, rule-based business insights.

    This is intentionally non-ML and deterministic.
    It uses already-produced metrics/outputs (sales, forecast, RFM, sentiment, recommendations).
    """

    insights: List[Insight] = []

    # ---------------------------------------------------------------------
    # Sales-based insights (revenue/orders/AOV trend)
    # ---------------------------------------------------------------------
    if not sales_df.empty and "__order_date" in sales_df.columns and "__total_price" in sales_df.columns:
        # Normalize datetime to tz-naive for safe comparisons
        try:
            sales_df = sales_df.copy()
            sales_df["__order_date"] = pd.to_datetime(sales_df["__order_date"], errors="coerce", utc=True).dt.tz_convert(None)
        except Exception:
            # Fall back to whatever dtype exists; downstream will handle empty/NaT
            pass

        current_start, current_end, prev_start, prev_end = _periods_from_sales(sales_df, days=30)
        current_df = sales_df[(sales_df["__order_date"] >= current_start) & (sales_df["__order_date"] <= current_end)]
        prev_df = sales_df[(sales_df["__order_date"] >= prev_start) & (sales_df["__order_date"] <= prev_end)]

        current_revenue = float(current_df["__total_price"].sum())
        prev_revenue = float(prev_df["__total_price"].sum()) if not prev_df.empty else 0.0
        current_orders = int(len(current_df))
        prev_orders = int(len(prev_df)) if not prev_df.empty else 0
        current_aov = current_revenue / current_orders if current_orders else 0.0
        prev_aov = prev_revenue / prev_orders if prev_orders else 0.0

        revenue_change = _pct_change(current_revenue, prev_revenue) if prev_revenue > 0 else None
        aov_change = _pct_change(current_aov, prev_aov) if prev_aov > 0 else None
        orders_change = _pct_change(float(current_orders), float(prev_orders)) if prev_orders > 0 else None

        # Revenue change insight
        if revenue_change is not None:
            if revenue_change <= -10:
                insights.append(
                    Insight(
                        id="revenue_drop_30d",
                        severity="critical" if revenue_change <= -20 else "warning",
                        title="Revenue is down vs the previous period",
                        description=f"Revenue changed by {revenue_change:.1f}% over the last 30 days.",
                        reason="Lower sales volume, weaker demand, or pricing/discount changes can drive this.",
                        suggested_action="Review top cities/products for declines, validate promotions/discounts, and check stock-outs.",
                        metrics={"revenue_change_pct": round(revenue_change, 2)},
                    )
                )
            elif revenue_change >= 10:
                insights.append(
                    Insight(
                        id="revenue_growth_30d",
                        severity="info",
                        title="Revenue is growing",
                        description=f"Revenue increased by {revenue_change:.1f}% over the last 30 days.",
                        reason="Higher demand, stronger conversion, or improved average order value can drive this.",
                        suggested_action="Identify the top drivers (products/cities) and consider scaling inventory and marketing.",
                        metrics={"revenue_change_pct": round(revenue_change, 2)},
                    )
                )

        # AOV change insight
        if aov_change is not None and abs(aov_change) >= 10:
            insights.append(
                Insight(
                    id="aov_change_30d",
                    severity="warning" if aov_change < 0 else "info",
                    title="Average order value shifted materially",
                    description=f"AOV changed by {aov_change:.1f}% over the last 30 days.",
                    reason="Basket size changes, product mix shifts, or discounting often affects AOV.",
                    suggested_action="Compare product mix and discount rates; test bundles or minimum-order incentives.",
                    metrics={"aov_change_pct": round(aov_change, 2)},
                )
            )

        # Concentration risk (top city share)
        if "__city" in sales_df.columns and sales_df["__city"].notna().any():
            city_rev = (
                current_df.dropna(subset=["__city"]).groupby("__city")["__total_price"].sum().sort_values(ascending=False)
            )
            if not city_rev.empty and city_rev.sum() > 0:
                top_city = str(city_rev.index[0])
                share = float(city_rev.iloc[0] / city_rev.sum())
                if share >= 0.55:
                    insights.append(
                        Insight(
                            id="city_concentration",
                            severity="warning",
                            title="Revenue is concentrated in one city",
                            description=f"{top_city} represents {share*100:.1f}% of revenue in the last 30 days.",
                            reason="Over-reliance on a single region increases risk from local demand changes.",
                            suggested_action="Diversify acquisition/retention campaigns to other cities and monitor city-level trends weekly.",
                            metrics={"top_city": top_city, "top_city_share": round(share, 4)},
                        )
                    )

        # Orders volume insight (optional)
        if orders_change is not None and orders_change <= -15:
            insights.append(
                Insight(
                    id="orders_drop_30d",
                    severity="warning",
                    title="Order volume is declining",
                    description=f"Orders changed by {orders_change:.1f}% vs the previous 30 days.",
                    reason="Traffic, conversion, or availability issues can reduce order count.",
                    suggested_action="Check top products for availability issues and review recent channel performance.",
                    metrics={"orders_change_pct": round(orders_change, 2)},
                )
            )

    # ---------------------------------------------------------------------
    # Forecast deviation insight (if forecast available)
    # ---------------------------------------------------------------------
    if forecast_df is not None and not forecast_df.empty:
        # Expect MonthStart + ForecastedSales or yhat
        if "MonthStart" in forecast_df.columns:
            f = forecast_df.copy()
            f["MonthStart"] = pd.to_datetime(f["MonthStart"], errors="coerce")
            f = f.dropna(subset=["MonthStart"])
            if not f.empty:
                f = f.sort_values("MonthStart")
                last_forecast_row = f.iloc[-1]
                forecast_val = float(last_forecast_row.get("ForecastedSales", last_forecast_row.get("yhat", 0.0)) or 0.0)
                # Compare with last actual month if possible
                if not sales_df.empty and "__order_date" in sales_df.columns and "__total_price" in sales_df.columns:
                    last_month = pd.to_datetime(last_forecast_row["MonthStart"]).strftime("%Y-%m")
                    actual_monthly = (
                        sales_df.groupby(pd.Grouper(key="__order_date", freq="MS"))["__total_price"].sum().reset_index()
                    )
                    actual_monthly["month_key"] = actual_monthly["__order_date"].dt.strftime("%Y-%m")
                    match = actual_monthly[actual_monthly["month_key"] == last_month]
                    if not match.empty and forecast_val > 0:
                        actual_val = float(match.iloc[0]["__total_price"])
                        gap = _pct_change(actual_val, forecast_val)
                        # gap is vs forecast; negative means below forecast
                        if gap is not None and gap <= -20:
                            insights.append(
                                Insight(
                                    id="actual_below_forecast",
                                    severity="warning",
                                    title="Actual revenue is materially below forecast",
                                    description=f"Last month actuals are {abs(gap):.1f}% below the forecast.",
                                    reason="Demand may have softened or the model is reacting to a new trend.",
                                    suggested_action="Validate recent drivers (price/discounts/stock) and consider re-running the pipeline after fresh data upload.",
                                    metrics={"month": last_month, "actual": round(actual_val, 2), "forecast": round(forecast_val, 2), "gap_pct": round(gap, 2)},
                                )
                            )

    # ---------------------------------------------------------------------
    # RFM distribution insight
    # ---------------------------------------------------------------------
    if rfm_df is not None and not rfm_df.empty and "Segment" in rfm_df.columns:
        seg_counts = rfm_df["Segment"].value_counts(dropna=False)
        total = int(seg_counts.sum())
        at_risk = int(seg_counts.get("At Risk", 0) + seg_counts.get("Hibernating", 0) + seg_counts.get("Lost", 0))
        if total > 0:
            ratio = at_risk / total
            if ratio >= 0.25:
                insights.append(
                    Insight(
                        id="high_at_risk_customers",
                        severity="warning" if ratio < 0.4 else "critical",
                        title="A large share of customers are at risk",
                        description=f"{ratio*100:.1f}% of customers are in At Risk / Hibernating / Lost segments.",
                        reason="Customers may be churning due to reduced engagement or satisfaction.",
                        suggested_action="Launch win-back campaigns, personalize offers for at-risk segments, and monitor retention weekly.",
                        metrics={"at_risk_ratio": round(ratio, 4), "at_risk_customers": at_risk, "total_customers": total},
                    )
                )

    # ---------------------------------------------------------------------
    # Sentiment insight
    # ---------------------------------------------------------------------
    if sentiment_df is not None and not sentiment_df.empty:
        # common columns: SentimentLabel / Sentiment
        label_col = None
        for c in ["SentimentLabel", "Sentiment", "Label", "sentiment_label"]:
            if c in sentiment_df.columns:
                label_col = c
                break
        if label_col:
            counts = sentiment_df[label_col].value_counts().to_dict()
            total = sum(int(v) for v in counts.values())
            neg = int(counts.get("Negative", 0))
            if total > 0:
                neg_pct = neg / total * 100.0
                if neg_pct >= 30:
                    insights.append(
                        Insight(
                            id="negative_sentiment_high",
                            severity="warning" if neg_pct < 45 else "critical",
                            title="Customer sentiment is trending negative",
                            description=f"Negative reviews represent {neg_pct:.1f}% of analyzed feedback.",
                            reason="Service issues, delays, or product quality problems often drive negative sentiment.",
                            suggested_action="Review negative feedback themes, prioritize operational fixes, and follow up with affected customers.",
                            metrics={"negative_pct": round(neg_pct, 2), "total_reviews": total},
                        )
                    )

    # ---------------------------------------------------------------------
    # Recommendations availability insight
    # ---------------------------------------------------------------------
    if recommendations_df is None or recommendations_df.empty:
        insights.append(
            Insight(
                id="recommendations_unavailable",
                severity="info",
                title="Product recommendations are not available yet",
                description="No recommendation rules were found for the current dataset.",
                reason="Association-rule recommendations require enough multi-product orders.",
                suggested_action="Upload more transaction history with multi-item orders, then re-run the pipeline to generate rules.",
                metrics={},
            )
        )

    # Deterministic ordering: critical -> warning -> info, then stable by id
    severity_rank = {"critical": 0, "warning": 1, "info": 2}
    insights = sorted(insights, key=lambda x: (severity_rank[x.severity], x.id))
    insights = insights[: max(1, min(limit, 20))]

    return InsightsResponse(
        company_id=company_id,
        generated_at=datetime.now(timezone.utc).isoformat(),
        insights=insights,
    )
