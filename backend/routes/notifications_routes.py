"""Notifications API."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Header, Query, HTTPException
from pydantic import BaseModel, Field

from backend.notification_store import (
    with_conn,
    list_notifications as store_list_notifications,
    mark_notification_read,
    mark_notifications_read,
    unread_count,
)
from backend.inventory_store import normalize_company_id


router = APIRouter(prefix="/notifications", tags=["Notifications"])


class Notification(BaseModel):
    id: int
    product_name: Optional[str] = None
    message: str
    type: str = Field(..., pattern="^(ALERT|WARNING|INFO)$")
    created_at: str
    is_read: bool


class MarkReadRequest(BaseModel):
    ids: List[int] = Field(default_factory=list)


@router.get("", response_model=Dict[str, Any])
def list_notifications(
    unread_only: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=500),
    company_id: Optional[str] = Header(default=None, alias="X-Company-ID"),
) -> Dict[str, Any]:
    company = normalize_company_id(company_id)
    conn = with_conn()
    try:
        items = store_list_notifications(
            conn,
            company_id=company,
            limit=limit,
            unread_only=unread_only,
        )
        return {
            "ok": True,
            "unread_count": unread_count(conn, company_id=company),
            "count": len(items),
            "items": items,
        }
    finally:
        conn.close()


@router.put("/{notification_id}/read", response_model=Dict[str, Any])
def mark_notification_as_read(
    notification_id: int,
    company_id: Optional[str] = Header(default=None, alias="X-Company-ID"),
) -> Dict[str, Any]:
    company = normalize_company_id(company_id)
    conn = with_conn()
    try:
        updated = mark_notification_read(
            conn,
            notification_id=notification_id,
            company_id=company,
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Notification not found")
    finally:
        conn.close()
    return {"ok": True, "id": int(notification_id), "is_read": True}


@router.post("/mark-read", response_model=Dict[str, Any])
def mark_notifications_read_legacy(
    body: MarkReadRequest,
    company_id: Optional[str] = Header(default=None, alias="X-Company-ID"),
) -> Dict[str, Any]:
    """Backward-compatible bulk mark-as-read endpoint."""
    company = normalize_company_id(company_id)
    conn = with_conn()
    try:
        updated = mark_notifications_read(conn, ids=body.ids, company_id=company)
    finally:
        conn.close()
    return {"ok": True, "updated": int(updated)}
