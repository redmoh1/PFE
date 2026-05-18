"""Notifications API."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query, HTTPException, Depends
from pydantic import BaseModel, Field

from backend.notification_store import (
    with_conn,
    list_notifications as store_list_notifications,
    mark_notification_read,
    mark_notifications_read,
    unread_count,
)
from backend.auth import get_tenant_scope, TenantScope


router = APIRouter(prefix="/notifications", tags=["Notifications"])


def _company_key_from_tenant(tenant: TenantScope) -> str:
    if getattr(tenant, "company_name", None):
        return str(tenant.company_name)
    if int(getattr(tenant, "company_id", 0) or 0) == 1:
        return "Acme Corp"
    return str(tenant.company_id)


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
    tenant: TenantScope = Depends(get_tenant_scope),
) -> Dict[str, Any]:
    company = _company_key_from_tenant(tenant)
    branch_id = str(tenant.branch_id) if tenant.branch_id is not None else None
    conn = with_conn()
    try:
        items = store_list_notifications(
            conn,
            company_id=company,
            branch_id=branch_id,
            limit=limit,
            unread_only=unread_only,
        )
        return {
            "ok": True,
            "unread_count": unread_count(conn, company_id=company, branch_id=branch_id),
            "count": len(items),
            "items": items,
        }
    finally:
        conn.close()


@router.put("/{notification_id}/read", response_model=Dict[str, Any])
def mark_notification_as_read(
    notification_id: int,
    tenant: TenantScope = Depends(get_tenant_scope),
) -> Dict[str, Any]:
    company = _company_key_from_tenant(tenant)
    branch_id = str(tenant.branch_id) if tenant.branch_id is not None else None
    conn = with_conn()
    try:
        updated = mark_notification_read(
            conn,
            notification_id=notification_id,
            company_id=company,
            branch_id=branch_id,
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Notification not found")
    finally:
        conn.close()
    return {"ok": True, "id": int(notification_id), "is_read": True}


@router.post("/mark-read", response_model=Dict[str, Any])
def mark_notifications_read_legacy(
    body: MarkReadRequest,
    tenant: TenantScope = Depends(get_tenant_scope),
) -> Dict[str, Any]:
    """Backward-compatible bulk mark-as-read endpoint."""
    company = _company_key_from_tenant(tenant)
    branch_id = str(tenant.branch_id) if tenant.branch_id is not None else None
    conn = with_conn()
    try:
        updated = mark_notifications_read(conn, ids=body.ids, company_id=company, branch_id=branch_id)
    finally:
        conn.close()
    return {"ok": True, "updated": int(updated)}
