"""Inventory routes (Gestion de Stock).

Step 1: Product detection.

This module is designed to EXTEND the existing FastAPI backend without
breaking existing analytics endpoints.

Endpoints in this file are mounted under /inventory.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional, Dict, Any

import pandas as pd
from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Header
from fastapi.responses import Response
from pydantic import BaseModel, Field

from backend.inventory_store import (
    connect,
    normalize_company_id,
    normalize_product_name,
    upsert_stock,
    increment_stock,
    get_stock_map,
    list_manual_products,
    parse_invoice_lines,
    compute_avg_daily_sales,
    classify_status,
    compute_reorder_suggestion,
    advice_for,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/inventory", tags=["Inventory"])


class StockUpdateItem(BaseModel):
    product_name: str = Field(..., min_length=1, description="Product name")
    current_stock: int = Field(..., ge=0, description="Current stock (>=0)")


class StockUpdateRequest(BaseModel):
    items: List[StockUpdateItem]


class AddProductRequest(BaseModel):
    product_name: str = Field(..., min_length=1, description="Product name")
    initial_stock: int = Field(0, ge=0, description="Initial stock (>=0)")


def _project_base_dir() -> Path:
    # .../Sales_Intelligence_Project/backend/routes/inventory_routes.py
    # parents[0]=routes, [1]=backend, [2]=Sales_Intelligence_Project
    return Path(__file__).resolve().parents[2]


def _data_dir() -> Path:
    return _project_base_dir() / "data"


def _company_data_dir(company_id: Optional[str]) -> Path:
    """Resolve the correct data directory for a company.

    The existing backend stores company datasets under data/<company_id>/.
    For backward compatibility, if the company folder doesn't exist, fall back
    to the root data directory.
    """

    base = _data_dir()
    company = normalize_company_id(company_id)
    candidate = base / company
    return candidate if candidate.exists() else base


def _pick_sales_data_file(source: Optional[str] = None, company_id: Optional[str] = None) -> Path:
    """Pick the best available sales dataset.

    Preference order is:
    - cleaned_dataset.csv (preferred for consistent schema)
    - merged_data.csv
    - sales.csv (raw upload)

    Args:
        source: optional override: "cleaned" | "merged" | "raw"

    Returns:
        Path to an existing CSV.
    """

    # This project currently stores canonical pipeline outputs in data/ (shared),
    # while uploaded raw datasets may exist under data/<company_id>/<dataset_type>/.
    # We therefore try the shared folder first, then fall back to the company folder.
    base_dir = _data_dir()
    company_dir = _company_data_dir(company_id)
    candidate_dirs = [base_dir]
    if company_dir != base_dir:
        candidate_dirs.append(company_dir)

    if source:
        source = source.lower().strip()
        mapping = {
            "cleaned": "cleaned_dataset.csv",
            "merged": "merged_data.csv",
            "raw": "sales.csv",
        }
        picked_name = mapping.get(source)
        if not picked_name:
            raise HTTPException(status_code=400, detail="Invalid source. Use cleaned|merged|raw")
        for d in candidate_dirs:
            picked = d / picked_name
            if picked.exists():
                return picked
        raise HTTPException(status_code=404, detail=f"Requested source file not found: {picked_name}")

    for d in candidate_dirs:
        for candidate in [
            d / "cleaned_dataset.csv",
            d / "merged_data.csv",
            d / "sales.csv",
        ]:
            if candidate.exists():
                return candidate

    raise HTTPException(
        status_code=404,
        detail="No sales dataset found. Upload sales data first (sales.csv / cleaned_dataset.csv).",
    )


def _normalize_product_value(value: object) -> Optional[str]:
    if value is None:
        return None
    # Preserve codes (e.g. StockCode) but normalize whitespace/case for UI consistency.
    text = str(value).strip()
    if not text:
        return None
    # Remove accidental double spaces; keep it simple and explainable.
    text = " ".join(text.split())
    return text.upper()


@router.get("/products", response_model=List[str])
def get_inventory_products(
    source: Optional[str] = Query(
        default=None,
        description="Optional: cleaned|merged|raw. Defaults to best available.",
    ),
    company_id: Optional[str] = Header(default=None, alias="X-Company-ID"),
) -> List[str]:
    """Extract unique product names from the current sales data.

    Uses the existing Schema Resolver to detect the product column even when
    datasets use different column names (Product, Description, SKU, StockCode...).

    Returns:
        A sorted list of unique product names.
    """

    csv_path = _pick_sales_data_file(source, company_id=company_id)

    try:
        df = pd.read_csv(csv_path)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to read sales CSV for inventory product detection: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to read dataset: {csv_path.name}")

    if df.empty:
        return []

    # Reuse the existing semantic schema resolver.
    product_col: Optional[str] = None
    try:
        from src.schema_resolver import SchemaResolver, SemanticField

        resolver = SchemaResolver()
        resolution = resolver.resolve(df, dataset_type="sales")
        product_col = resolution.get_column(SemanticField.PRODUCT)
    except Exception as exc:  # noqa: BLE001
        # Resolver is optional; do not break the API if import fails.
        logger.warning("SchemaResolver not available or failed (%s). Falling back.", exc)

    # Fallback: common product-ish columns.
    if not product_col:
        fallback_candidates = [
            "ProductID",
            "Product_ID",
            "Product",
            "product",
            "ProductName",
            "product_name",
            "Description",
            "description",
            "SKU",
            "sku",
            "StockCode",
            "stock_code",
        ]
        for c in fallback_candidates:
            if c in df.columns:
                product_col = c
                break

    if not product_col:
        raise HTTPException(
            status_code=422,
            detail="Could not detect product column in sales data.",
        )

    series = df[product_col]
    products = {p for p in (normalize_product_name(str(v)) for v in series.dropna().tolist()) if p}

    return sorted(products)


@router.post("/update")
def update_inventory_stock(
    payload: StockUpdateRequest,
    company_id: Optional[str] = Header(default=None, alias="X-Company-ID"),
) -> Dict[str, Any]:
    """Persist seller-provided stock values.

    Body:
        {"items": [{"product_name": "LAPTOP", "current_stock": 10}, ...]}
    """

    if not payload.items:
        return {"ok": True, "updated": 0}

    conn = connect()
    try:
        for item in payload.items:
            upsert_stock(conn, item.product_name, item.current_stock, company_id=company_id)
        return {"ok": True, "updated": len(payload.items)}
    finally:
        conn.close()


@router.post("/add-product")
def add_inventory_product(
    payload: AddProductRequest,
    company_id: Optional[str] = Header(default=None, alias="X-Company-ID"),
) -> Dict[str, Any]:
    """Manually add a new product with initial stock."""

    conn = connect()
    try:
        upsert_stock(conn, payload.product_name, payload.initial_stock, company_id=company_id)
        return {"ok": True, "product_name": normalize_product_name(payload.product_name)}
    finally:
        conn.close()


@router.post("/upload-invoice")
async def upload_purchase_invoice(
    file: UploadFile = File(...),
    company_id: Optional[str] = Header(default=None, alias="X-Company-ID"),
) -> Dict[str, Any]:
    """Upload a purchase invoice CSV and automatically increase stock.

    Expected columns (flexible):
    - Product (or aliases)
    - QuantityPurchased (or Quantity/Qty/Units...)

    New products are created automatically with their purchased quantity.
    """

    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    try:
        raw = await file.read()
        df = pd.read_csv(pd.io.common.BytesIO(raw))
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to read invoice CSV: %s", exc)
        raise HTTPException(status_code=400, detail="Invalid CSV file")

    try:
        lines = parse_invoice_lines(df)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=str(exc))

    conn = connect()
    try:
        for line in lines:
            increment_stock(conn, line.product_name, line.quantity_purchased, company_id=company_id)
        return {"ok": True, "lines_applied": len(lines)}
    finally:
        conn.close()


@router.get("/status")
def get_inventory_status(
    source: Optional[str] = Query(
        default=None,
        description="Optional: cleaned|merged|raw. Defaults to best available.",
    ),
    warning_days: int = Query(default=7, ge=0, le=365, description="Days-left threshold for WARNING"),
    alert_days: int = Query(default=3, ge=0, le=365, description="Days-left threshold for ALERT"),
    lead_time_days: int = Query(default=7, ge=0, le=365, description="Lead time in days for reorder suggestion"),
    safety_days: int = Query(default=0, ge=0, le=365, description="Extra safety days for reorder suggestion"),
    company_id: Optional[str] = Header(default=None, alias="X-Company-ID"),
) -> Dict[str, Any]:
    """Return inventory status per product (stock + sales velocity + advice)."""

    csv_path = _pick_sales_data_file(source, company_id=company_id)

    try:
        df = pd.read_csv(csv_path)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to read sales CSV for inventory status: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to read dataset: {csv_path.name}")

    detected_products: List[str] = []
    if not df.empty:
        # Try to reuse the same detection logic as /products.
        try:
            detected_products = get_inventory_products(source=source, company_id=company_id)
        except Exception:
            detected_products = []

    avg_daily = compute_avg_daily_sales(df)

    conn = connect()
    try:
        stock_map = get_stock_map(conn, company_id=company_id)
        manual_products = list_manual_products(conn, company_id=company_id)
    finally:
        conn.close()

    # FULL OUTER JOIN semantics: sales-detected products ∪ any product already in stock table
    all_products = sorted(set(detected_products).union(manual_products).union(stock_map.keys()))

    items: List[Dict[str, Any]] = []
    for product in all_products:
        stock = stock_map.get(product)
        avg = float(avg_daily.get(product, 0.0))
        status, days_left = classify_status(stock, avg, warning_days=warning_days, alert_days=alert_days)
        advice = advice_for(status)
        suggested_reorder_qty = compute_reorder_suggestion(
            stock,
            avg,
            lead_time_days=lead_time_days,
            safety_days=safety_days,
        )
        items.append(
            {
                "product_name": product,
                "current_stock": stock,
                "avg_daily_sales": round(avg, 4),
                "days_left": None if days_left is None else round(float(days_left), 2),
                "status": status,
                "advice": advice,
                "suggested_reorder_qty": suggested_reorder_qty,
            }
        )

    return {
        "ok": True,
        "source_file": csv_path.name,
        "thresholds": {
            "warning_days": warning_days,
            "alert_days": alert_days,
            "lead_time_days": lead_time_days,
            "safety_days": safety_days,
        },
        "count": len(items),
        "items": items,
    }


@router.get("/alerts-summary")
def get_inventory_alerts_summary(
    source: Optional[str] = Query(
        default=None,
        description="Optional: cleaned|merged|raw. Defaults to best available.",
    ),
    warning_days: int = Query(default=7, ge=0, le=365, description="Days-left threshold for WARNING"),
    alert_days: int = Query(default=3, ge=0, le=365, description="Days-left threshold for ALERT"),
    lead_time_days: int = Query(default=7, ge=0, le=365, description="Lead time in days for reorder suggestion"),
    safety_days: int = Query(default=0, ge=0, le=365, description="Extra safety days for reorder suggestion"),
    company_id: Optional[str] = Header(default=None, alias="X-Company-ID"),
) -> Dict[str, Any]:
    """Return a compact alert summary for header widgets/badges.

    This avoids downloading the full status table when the UI only needs counts.
    """

    payload = get_inventory_status(
        source=source,
        warning_days=warning_days,
        alert_days=alert_days,
        lead_time_days=lead_time_days,
        safety_days=safety_days,
        company_id=company_id,
    )
    items = payload.get("items") or []

    counts = {
        "ALERT": 0,
        "WARNING": 0,
        "OK": 0,
        "DORMANT": 0,
        "UNKNOWN": 0,
    }
    for it in items:
        s = str(it.get("status") or "UNKNOWN").upper()
        counts[s] = counts.get(s, 0) + 1

    alert_count = int(counts.get("ALERT", 0))
    warning_count = int(counts.get("WARNING", 0))
    badge_count = alert_count + warning_count

    return {
        "ok": True,
        "source_file": payload.get("source_file"),
        "total": len(items),
        "badge_count": badge_count,
        "alert_count": alert_count,
        "warning_count": warning_count,
        "counts": counts,
    }


@router.get("/reorder-export")
def export_reorder_csv(
    source: Optional[str] = Query(default=None, description="Optional: cleaned|merged|raw."),
    scope: str = Query(
        default="RISK",
        description="Rows to export: RISK (ALERT+WARNING) | ALERT | WARNING | ALL",
    ),
    warning_days: int = Query(default=7, ge=0, le=365),
    alert_days: int = Query(default=3, ge=0, le=365),
    lead_time_days: int = Query(default=7, ge=0, le=365),
    safety_days: int = Query(default=0, ge=0, le=365),
    company_id: Optional[str] = Header(default=None, alias="X-Company-ID"),
) -> Response:
    """Export reorder suggestions as a CSV file.

    This is intentionally lightweight: it reuses /inventory/status calculations
    and outputs only the actionable rows (by default ALERT+WARNING).
    """

    payload = get_inventory_status(
        source=source,
        warning_days=warning_days,
        alert_days=alert_days,
        lead_time_days=lead_time_days,
        safety_days=safety_days,
        company_id=company_id,
    )

    items: List[Dict[str, Any]] = payload.get("items") or []
    scope_norm = (scope or "RISK").strip().upper()

    def in_scope(status: str) -> bool:
        s = (status or "").upper()
        if scope_norm == "ALL":
            return True
        if scope_norm == "ALERT":
            return s == "ALERT"
        if scope_norm == "WARNING":
            return s == "WARNING"
        # Default: RISK
        return s in {"ALERT", "WARNING"}

    export_rows: List[Dict[str, Any]] = []
    for it in items:
        status = str(it.get("status") or "")
        if not in_scope(status):
            continue
        qty = it.get("suggested_reorder_qty")
        # Export only actionable quantities when possible
        if qty is None:
            continue
        try:
            if int(qty) <= 0:
                continue
        except Exception:
            continue

        export_rows.append(
            {
                "Product": it.get("product_name"),
                "SuggestedReorderQty": qty,
                "Status": it.get("status"),
                "CurrentStock": it.get("current_stock"),
                "AvgDailySales": it.get("avg_daily_sales"),
                "DaysLeft": it.get("days_left"),
                "Advice": it.get("advice"),
            }
        )

    df = pd.DataFrame(export_rows)
    csv_bytes = df.to_csv(index=False).encode("utf-8")

    filename = "reorder_suggestions.csv"
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"'
    }
    return Response(content=csv_bytes, media_type="text/csv", headers=headers)


@router.get("/purchase-order-template")
def export_purchase_order_template_csv(
    source: Optional[str] = Query(default=None, description="Optional: cleaned|merged|raw."),
    scope: str = Query(
        default="RISK",
        description="Rows to export: RISK (ALERT+WARNING) | ALERT | WARNING | ALL",
    ),
    warning_days: int = Query(default=7, ge=0, le=365),
    alert_days: int = Query(default=3, ge=0, le=365),
    lead_time_days: int = Query(default=7, ge=0, le=365),
    safety_days: int = Query(default=0, ge=0, le=365),
    company_id: Optional[str] = Header(default=None, alias="X-Company-ID"),
) -> Response:
    """Export a Purchase Order CSV template.

    هدفه يكون ملف جاهز للمشتريات: نفس اقتراحات إعادة الطلب، لكن مع أعمدة
    إضافية لتعبئتها يدويًا (المورّد، سعر الوحدة...) حتى يصبح عمليًا كـ PO.
    """

    payload = get_inventory_status(
        source=source,
        warning_days=warning_days,
        alert_days=alert_days,
        lead_time_days=lead_time_days,
        safety_days=safety_days,
        company_id=company_id,
    )

    items: List[Dict[str, Any]] = payload.get("items") or []
    scope_norm = (scope or "RISK").strip().upper()

    def in_scope(status: str) -> bool:
        s = (status or "").upper()
        if scope_norm == "ALL":
            return True
        if scope_norm == "ALERT":
            return s == "ALERT"
        if scope_norm == "WARNING":
            return s == "WARNING"
        return s in {"ALERT", "WARNING"}

    rows: List[Dict[str, Any]] = []
    for it in items:
        status = str(it.get("status") or "")
        if not in_scope(status):
            continue

        qty = it.get("suggested_reorder_qty")
        try:
            qty_int = int(qty) if qty is not None else 0
        except Exception:
            qty_int = 0
        if qty_int <= 0:
            continue

        rows.append(
            {
                "Product": it.get("product_name"),
                "QuantityToOrder": qty_int,
                "Supplier": "",
                "UnitCost": "",
                "Currency": "",
                "TotalCost": "",  # optional: fill in Excel (=UnitCost*QuantityToOrder)
                "Status": it.get("status"),
                "DaysLeft": it.get("days_left"),
                "AvgDailySales": it.get("avg_daily_sales"),
                "Notes": it.get("advice"),
            }
        )

    df = pd.DataFrame(rows)
    csv_bytes = df.to_csv(index=False).encode("utf-8")

    filename = "purchase_order_template.csv"
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"'
    }
    return Response(content=csv_bytes, media_type="text/csv", headers=headers)
