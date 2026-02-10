"""Active alerts API.

SINGLE SOURCE OF TRUTH:
- Alerts are derived ONLY from inventory status.
- No additional business rules.

This module exposes:
- GET /alerts/active

Other modules (e.g. notifications) should reuse the implementation helper in this file
instead of re-filtering inventory status again.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Header, Query


router = APIRouter(prefix="/alerts", tags=["Alerts"])


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _active_alerts_impl(
    *,
    source: Optional[str],
    warning_days: int,
    alert_days: int,
    lead_time_days: int,
    safety_days: int,
    company_id: Optional[str],
) -> Dict[str, Any]:
    # Lazy import avoids circulars.
    from backend.inventory_store import normalize_company_id
    from backend.routes.inventory_routes import get_inventory_status

    company = normalize_company_id(company_id)

    payload = get_inventory_status(
        source=source,
        warning_days=warning_days,
        alert_days=alert_days,
        lead_time_days=lead_time_days,
        safety_days=safety_days,
        company_id=company,
    )

    items: List[Dict[str, Any]] = payload.get("items") or []

    alerts: List[Dict[str, Any]] = []
    for it in items:
        status = str(it.get("status") or "").upper()
        if status not in {"ALERT", "WARNING"}:
            continue

        product = it.get("product_name")
        days_left = it.get("days_left")
        avg = it.get("avg_daily_sales")
        stock = it.get("current_stock")
        advice = it.get("advice")
        suggested = it.get("suggested_reorder_qty")

        # Reason is explanation-only (not a new business rule): just restates existing fields.
        if days_left is None:
            reason = "Low stock threshold reached based on current settings."
        else:
            reason = f"Estimated days left is {days_left} (based on avg daily sales)."

        alerts.append(
            {
                "product": product,
                "status": status,
                "days_left": days_left,
                "reason": reason,
                "seller_advice": advice,
                "created_at": _utc_now_iso(),
                "meta": {
                    "current_stock": stock,
                    "avg_daily_sales": avg,
                    "suggested_reorder_qty": suggested,
                },
            }
        )

    # Sort most severe first.
    alerts.sort(key=lambda x: (0 if x.get("status") == "ALERT" else 1, str(x.get("product") or "")))

    return {
        "ok": True,
        "source_file": payload.get("source_file"),
        "count": len(alerts),
        "items": alerts,
    }


@router.get("/active", response_model=Dict[str, Any])
def get_active_alerts(
    source: Optional[str] = Query(default=None, description="Optional: cleaned|merged|raw."),
    warning_days: int = Query(default=7, ge=0, le=365),
    alert_days: int = Query(default=3, ge=0, le=365),
    lead_time_days: int = Query(default=7, ge=0, le=365),
    safety_days: int = Query(default=0, ge=0, le=365),
    company_id: Optional[str] = Header(default=None, alias="X-Company-ID"),
) -> Dict[str, Any]:
    return _active_alerts_impl(
        source=source,
        warning_days=warning_days,
        alert_days=alert_days,
        lead_time_days=lead_time_days,
        safety_days=safety_days,
        company_id=company_id,
    )
