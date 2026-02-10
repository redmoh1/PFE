"""Notifications API.

Notifications are derived from existing inventory status results.
We persist only read/unread state to avoid duplicating business logic.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Literal

from fastapi import APIRouter, Header, Query
from pydantic import BaseModel, Field

from backend.notification_store import with_conn, get_read_ids, mark_read


router = APIRouter(prefix="/notifications", tags=["Notifications"])


NotificationType = Literal["ALERT", "WARNING", "INFO"]


class Notification(BaseModel):
    id: str
    type: NotificationType
    product: Optional[str] = None
    message: str
    severity: int = Field(..., ge=1, le=3)
    created_at: str
    read: bool
    meta: Optional[Dict[str, Any]] = None


class MarkReadRequest(BaseModel):
    ids: List[str] = Field(default_factory=list)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stable_id(company_id: str, ntype: str, product: Optional[str]) -> str:
    base = f"{company_id}|{ntype}|{product or ''}"
    return hashlib.sha1(base.encode("utf-8")).hexdigest()[:16]


def _to_notification(company_id: str, item: Dict[str, Any], include_info: bool, info_scope: str) -> Optional[Dict[str, Any]]:
    status = str(item.get("status") or "").upper()
    product = item.get("product_name")
    days_left = item.get("days_left")
    advice = item.get("advice")
    suggested = item.get("suggested_reorder_qty")
    stock = item.get("current_stock")
    avg = item.get("avg_daily_sales")

    if status == "ALERT":
        ntype: NotificationType = "ALERT"
        severity = 3
        if days_left is None:
            message = f"Critical stock issue for {product}."
        elif float(days_left) <= 0:
            message = f"Out of stock: {product}."
        else:
            message = f"Stock alert: {product} has ~{days_left} days left."
    elif status == "WARNING":
        ntype = "WARNING"
        severity = 2
        if days_left is None:
            message = f"Low stock warning for {product}."
        else:
            message = f"Stock warning: {product} has ~{days_left} days left."
    else:
        if not include_info:
            return None
        # INFO scope controls what non-risk statuses become notifications.
        # - UNKNOWN: useful prompt to set stock.
        # - DORMANT: can be noisy; only include when requested.
        if status == "UNKNOWN":
            ntype = "INFO"
            severity = 1
            message = f"Stock not set for {product}. Add current stock to enable alerts."
        elif status == "DORMANT" and (info_scope or "UNKNOWN").upper() == "ALL":
            ntype = "INFO"
            severity = 1
            message = f"No meaningful demand detected for {product}. Consider promotion."
        else:
            return None

    nid = _stable_id(company_id, ntype, str(product) if product else None)

    meta = {
        "status": status,
        "product_name": product,
        "days_left": days_left,
        "current_stock": stock,
        "avg_daily_sales": avg,
        "advice": advice,
        "suggested_reorder_qty": suggested,
    }

    return {
        "id": nid,
        "type": ntype,
        "product": product,
        "message": message,
        "severity": severity,
        "created_at": _utc_now_iso(),
        "meta": meta,
    }


def _list_notifications_impl(
    *,
    source: Optional[str],
    warning_days: int,
    alert_days: int,
    lead_time_days: int,
    safety_days: int,
    include_info: bool,
    info_scope: str,
    unread_only: bool,
    limit: int,
    company_id: Optional[str],
) -> Dict[str, Any]:
    """Implementation with plain defaults (safe to call from Python code too)."""

    # SINGLE SOURCE OF TRUTH: derive notifications from the active alerts list,
    # plus optional INFO notifications from inventory status.
    from backend.inventory_store import normalize_company_id
    from backend.routes.alerts_routes import _active_alerts_impl
    from backend.routes.inventory_routes import get_inventory_status

    company = normalize_company_id(company_id)

    alerts_payload = _active_alerts_impl(
        source=source,
        warning_days=warning_days,
        alert_days=alert_days,
        lead_time_days=lead_time_days,
        safety_days=safety_days,
        company_id=company,
    )

    notifications: List[Dict[str, Any]] = []

    # Convert alerts -> notifications (ALERT/WARNING only).
    for a in (alerts_payload.get("items") or []):
        ntype = str(a.get("status") or "").upper()
        product = a.get("product")
        nid = _stable_id(company, ntype, str(product) if product else None)
        message = (
            f"Stock alert: {product}." if ntype == "ALERT" else f"Stock warning: {product}."
        )
        # Prefer a message if we can include days_left.
        days_left = a.get("days_left")
        if days_left is not None:
            message = f"{ntype.title()}: {product} has ~{days_left} days left."

        notifications.append(
            {
                "id": nid,
                "type": "ALERT" if ntype == "ALERT" else "WARNING",
                "product": product,
                "message": message,
                "severity": 3 if ntype == "ALERT" else 2,
                "created_at": a.get("created_at") or _utc_now_iso(),
                "meta": a.get("meta") or {},
            }
        )

    # Optional INFO notifications from inventory status (no new business rules).
    if include_info:
        inv_payload = get_inventory_status(
            source=source,
            warning_days=warning_days,
            alert_days=alert_days,
            lead_time_days=lead_time_days,
            safety_days=safety_days,
            company_id=company,
        )
        inv_items: List[Dict[str, Any]] = inv_payload.get("items") or []
        for it in inv_items:
            n = _to_notification(company, it, include_info=True, info_scope=info_scope)
            if n and n.get("type") == "INFO":
                notifications.append(n)

    # Stable sort: severity desc, then product for predictability.
    notifications.sort(key=lambda x: (-int(x.get("severity") or 1), str(x.get("product") or "")))
    notifications = notifications[: int(limit)]

    conn = with_conn()
    try:
        read_ids = get_read_ids(conn, [n["id"] for n in notifications], company_id=company)
    finally:
        conn.close()

    result_items: List[Dict[str, Any]] = []
    unread_count = 0
    for n in notifications:
        is_read = n["id"] in read_ids
        if unread_only and is_read:
            continue
        if not is_read:
            unread_count += 1
        result_items.append({**n, "read": bool(is_read)})

    if unread_only:
        unread_count = sum(1 for n in result_items if not n.get("read"))

    unread_risk_count = sum(1 for n in result_items if (not n.get("read")) and (n.get("type") in {"ALERT", "WARNING"}))

    # source_file comes from alerts payload (which comes from inventory status)
    return {
        "ok": True,
        "source_file": alerts_payload.get("source_file"),
        "badge_count": unread_risk_count,
        "unread_risk_count": unread_risk_count,
        "unread_count": unread_count,
        "count": len(result_items),
        "items": result_items,
    }


@router.get("", response_model=Dict[str, Any])
def list_notifications(
    source: Optional[str] = Query(default=None, description="Optional: cleaned|merged|raw."),
    warning_days: int = Query(default=7, ge=0, le=365),
    alert_days: int = Query(default=3, ge=0, le=365),
    lead_time_days: int = Query(default=7, ge=0, le=365),
    safety_days: int = Query(default=0, ge=0, le=365),
    include_info: bool = Query(default=True, description="Include INFO notifications"),
    info_scope: str = Query(default="UNKNOWN", description="UNKNOWN | ALL"),
    unread_only: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=500),
    company_id: Optional[str] = Header(default=None, alias="X-Company-ID"),
) -> Dict[str, Any]:
    """Return notifications derived from inventory status.

    This endpoint intentionally reuses the inventory status calculation to avoid
    duplicating business logic.
    """

    return _list_notifications_impl(
        source=source,
        warning_days=warning_days,
        alert_days=alert_days,
        lead_time_days=lead_time_days,
        safety_days=safety_days,
        include_info=include_info,
        info_scope=info_scope,
        unread_only=unread_only,
        limit=limit,
        company_id=company_id,
    )


@router.post("/mark-read", response_model=Dict[str, Any])
def mark_notifications_read(
    body: MarkReadRequest,
    company_id: Optional[str] = Header(default=None, alias="X-Company-ID"),
) -> Dict[str, Any]:
    from backend.inventory_store import normalize_company_id

    company = normalize_company_id(company_id)
    conn = with_conn()
    try:
        updated = mark_read(conn, body.ids, company_id=company)
    finally:
        conn.close()
    return {"ok": True, "updated": updated}
