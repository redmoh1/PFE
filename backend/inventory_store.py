"""Inventory persistence + analysis helpers.

This module implements a minimal Inventory Management storage layer.

Design choices:
- Uses SQLite (same data directory as the rest of the backend) for persistence.
- Keeps schema intentionally small and explainable.
- Avoids importing backend.main to prevent circular imports.

Tables:
- inventory_stock: one row per product with current stock.

NOTE: Multi-tenant (per-company) support can be added later by introducing
      a company_id column and using (company_id, product_name) as the PK.
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple, Literal
import math

import pandas as pd

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Paths / DB
# ---------------------------------------------------------------------------

def _project_base_dir() -> Path:
    # .../Sales_Intelligence_Project/backend/inventory_store.py
    return Path(__file__).resolve().parents[1]


def data_dir() -> Path:
    d = _project_base_dir() / "data"
    d.mkdir(exist_ok=True)
    return d


def db_path() -> Path:
    # Keep using the project's datasets.db file for simplicity.
    return data_dir() / "datasets.db"


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(db_path(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Create inventory tables if they do not exist."""

    # New schema (multi-tenant): (company_id, product_name) composite PK
    # Migration: if an old single-tenant table exists, move rows to the new schema.
    existing_cols = []
    try:
        existing_cols = [r["name"] for r in conn.execute("PRAGMA table_info(inventory_stock)").fetchall()]
    except Exception:
        existing_cols = []

    if existing_cols and "company_id" not in existing_cols:
        logger.info("[INVENTORY] Migrating inventory_stock to multi-tenant schema")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS inventory_stock_v2 (
                company_id TEXT NOT NULL,
                product_name TEXT NOT NULL,
                current_stock INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY(company_id, product_name)
            )
            """
        )
        conn.execute(
            """
            INSERT OR IGNORE INTO inventory_stock_v2 (company_id, product_name, current_stock, created_at, updated_at)
            SELECT ?, product_name, current_stock, created_at, updated_at
            FROM inventory_stock
            """,
            ("Acme Corp",),
        )
        conn.execute("DROP TABLE inventory_stock")
        conn.execute("ALTER TABLE inventory_stock_v2 RENAME TO inventory_stock")
        conn.commit()
        return

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS inventory_stock (
            company_id TEXT NOT NULL,
            product_name TEXT NOT NULL,
            current_stock INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY(company_id, product_name)
        )
        """
    )
    conn.commit()


def init_deleted_products_db(conn: sqlite3.Connection) -> None:
    """Create deleted-products table if it does not exist.

    This enables soft-delete of products from the Inventory module without
    modifying raw sales data.
    """

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS inventory_deleted_products (
            company_id TEXT NOT NULL,
            product_name TEXT NOT NULL,
            deleted_at TEXT NOT NULL,
            PRIMARY KEY(company_id, product_name)
        )
        """
    )
    conn.commit()


def init_product_costs_db(conn: sqlite3.Connection) -> None:
    """Create product-cost table if it does not exist.

    Stores a seller-maintained Cost Per Unit for each product.
    This is intentionally kept separate from stock so we don't alter any
    existing stock/business logic.
    """

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS inventory_product_costs (
            company_id TEXT NOT NULL,
            product_name TEXT NOT NULL,
            cost_per_unit REAL NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY(company_id, product_name)
        )
        """
    )
    conn.commit()


def init_stock_movements_db(conn: sqlite3.Connection) -> None:
    """Create stock_movements table if it does not exist."""

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS stock_movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id TEXT NOT NULL,
            product_name TEXT NOT NULL,
            date TEXT NOT NULL,
            type TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            reason TEXT NOT NULL,
            balance_after INTEGER
        )
        """
    )

    # Lightweight migration for existing DBs (SQLite supports ADD COLUMN).
    try:
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(stock_movements)").fetchall()]
        if "balance_after" not in cols:
            conn.execute("ALTER TABLE stock_movements ADD COLUMN balance_after INTEGER")
    except Exception:
        # Non-blocking; table still works without the column for reads.
        pass

    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_stock_movements_lookup ON stock_movements(company_id, product_name, date)"
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Stock CRUD
# ---------------------------------------------------------------------------

def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_product_name(name: str) -> str:
    """Normalize product name for stable matching.

    - Trims whitespace
    - Collapses internal whitespace
    - Uppercases for case-insensitive matching

    This matches the product detection endpoint behavior.
    """

    text = (name or "").strip()
    text = " ".join(text.split())
    return text.upper()


def normalize_company_id(company_id: Optional[str]) -> str:
    text = (company_id or "").strip()
    # Keep the original company name (can contain spaces) but avoid empty.
    return text or "Acme Corp"


def upsert_stock(
    conn: sqlite3.Connection,
    product_name: str,
    current_stock: int,
    company_id: Optional[str] = None,
    movement_reason: str = "Manual Adjustment",
) -> None:
    init_db(conn)
    now = _utc_now_iso()
    product = normalize_product_name(product_name)
    company = normalize_company_id(company_id)

    # Track previous stock so we can record a movement without changing the core stock behavior.
    prev_row = conn.execute(
        "SELECT current_stock FROM inventory_stock WHERE company_id = ? AND product_name = ?",
        (company, product),
    ).fetchone()
    prev_stock = int(prev_row["current_stock"]) if prev_row else 0
    next_stock = int(current_stock)

    conn.execute(
        """
        INSERT INTO inventory_stock (company_id, product_name, current_stock, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(company_id, product_name) DO UPDATE SET
            current_stock = excluded.current_stock,
            updated_at = excluded.updated_at
        """,
        (company, product, next_stock, now, now),
    )
    conn.commit()

    # Record movement if stock actually changed.
    delta = next_stock - prev_stock
    if delta != 0:
        record_stock_movement(
            conn,
            product_name=product,
            movement_type="IN" if delta > 0 else "OUT",
            quantity=abs(int(delta)),
            reason=movement_reason,
            balance_after=next_stock,
            company_id=company,
            date=now,
        )


def increment_stock(
    conn: sqlite3.Connection,
    product_name: str,
    delta: int,
    company_id: Optional[str] = None,
    movement_reason: str = "Manual Adjustment",
) -> None:
    """Increase stock by delta; creates the row if missing."""

    init_db(conn)
    product = normalize_product_name(product_name)
    company = normalize_company_id(company_id)

    row = conn.execute(
        "SELECT current_stock FROM inventory_stock WHERE company_id = ? AND product_name = ?",
        (company, product),
    ).fetchone()

    current = int(row["current_stock"]) if row else 0
    new_value = current + int(delta)
    if new_value < 0:
        new_value = 0
    # upsert_stock will record the movement (IN/OUT) based on the resulting delta.
    upsert_stock(conn, product, new_value, company_id=company, movement_reason=movement_reason)


def get_stock_map(conn: sqlite3.Connection, company_id: Optional[str] = None) -> Dict[str, int]:
    init_db(conn)
    company = normalize_company_id(company_id)
    rows = conn.execute(
        "SELECT product_name, current_stock FROM inventory_stock WHERE company_id = ?",
        (company,),
    ).fetchall()
    return {str(r["product_name"]): int(r["current_stock"]) for r in rows}


def list_manual_products(conn: sqlite3.Connection, company_id: Optional[str] = None) -> List[str]:
    init_db(conn)
    company = normalize_company_id(company_id)
    rows = conn.execute(
        "SELECT product_name FROM inventory_stock WHERE company_id = ? ORDER BY product_name",
        (company,),
    ).fetchall()
    return [str(r["product_name"]) for r in rows]


def get_deleted_products_set(conn: sqlite3.Connection, company_id: Optional[str] = None) -> set[str]:
    init_deleted_products_db(conn)
    company = normalize_company_id(company_id)
    rows = conn.execute(
        "SELECT product_name FROM inventory_deleted_products WHERE company_id = ?",
        (company,),
    ).fetchall()
    return {str(r["product_name"]) for r in rows}


def mark_product_deleted(conn: sqlite3.Connection, product_name: str, company_id: Optional[str] = None) -> None:
    init_deleted_products_db(conn)
    company = normalize_company_id(company_id)
    product = normalize_product_name(product_name)
    conn.execute(
        """
        INSERT OR REPLACE INTO inventory_deleted_products (company_id, product_name, deleted_at)
        VALUES (?, ?, ?)
        """,
        (company, product, _utc_now_iso()),
    )
    conn.commit()


def delete_stock_row(conn: sqlite3.Connection, product_name: str, company_id: Optional[str] = None) -> int:
    """Remove product from stock tracking table.

    This does not touch any sales datasets. Soft-delete is tracked separately in
    inventory_deleted_products.
    """

    init_db(conn)
    company = normalize_company_id(company_id)
    product = normalize_product_name(product_name)
    cur = conn.execute(
        "DELETE FROM inventory_stock WHERE company_id = ? AND product_name = ?",
        (company, product),
    )
    conn.commit()
    try:
        return int(cur.rowcount or 0)
    except Exception:
        return 0


def record_stock_movement(
    conn: sqlite3.Connection,
    product_name: str,
    movement_type: Literal["IN", "OUT"],
    quantity: int,
    reason: str,
    balance_after: Optional[int] = None,
    company_id: Optional[str] = None,
    date: Optional[str] = None,
) -> None:
    """Insert a movement record.

    This is additive-only telemetry for stock changes.
    """

    init_stock_movements_db(conn)
    company = normalize_company_id(company_id)
    product = normalize_product_name(product_name)
    when = date or _utc_now_iso()

    qty = int(quantity)
    if qty <= 0:
        return

    t = (movement_type or "").upper().strip()
    if t not in {"IN", "OUT"}:
        raise ValueError("movement_type must be IN or OUT")

    r = (reason or "").strip() or "Manual Adjustment"

    bal = None
    if balance_after is not None:
        try:
            bal = int(balance_after)
        except Exception:
            bal = None

    try:
        conn.execute(
            """
            INSERT INTO stock_movements (company_id, product_name, date, type, quantity, reason, balance_after)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (company, product, when, t, qty, r, bal),
        )
        conn.commit()
        return
    except sqlite3.OperationalError:
        # Backward compatibility: DB might not have balance_after yet.
        conn.execute(
            """
            INSERT INTO stock_movements (company_id, product_name, date, type, quantity, reason)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (company, product, when, t, qty, r),
        )
        conn.commit()


def list_stock_movements(
    conn: sqlite3.Connection,
    product_name: str,
    company_id: Optional[str] = None,
    limit: int = 500,
) -> List[Dict[str, object]]:
    init_stock_movements_db(conn)
    company = normalize_company_id(company_id)
    product = normalize_product_name(product_name)
    take = max(1, min(int(limit), 2000))

    try:
        rows = conn.execute(
            """
            SELECT id, product_name, date, type, quantity, reason, balance_after
            FROM stock_movements
            WHERE company_id = ? AND product_name = ?
            ORDER BY date DESC, id DESC
            LIMIT ?
            """,
            (company, product, take),
        ).fetchall()
        has_balance = True
    except sqlite3.OperationalError:
        rows = conn.execute(
            """
            SELECT id, product_name, date, type, quantity, reason
            FROM stock_movements
            WHERE company_id = ? AND product_name = ?
            ORDER BY date DESC, id DESC
            LIMIT ?
            """,
            (company, product, take),
        ).fetchall()
        has_balance = False

    return [
        {
            "id": int(r["id"]),
            "product_name": str(r["product_name"]),
            "date": str(r["date"]),
            "type": str(r["type"]),
            "quantity": int(r["quantity"]),
            "reason": str(r["reason"]),
            "balance_after": None
            if not has_balance
            else (None if r["balance_after"] is None else int(r["balance_after"])),
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Product costs (Cost Per Unit)
# ---------------------------------------------------------------------------


def upsert_cost_per_unit(
    conn: sqlite3.Connection,
    product_name: str,
    cost_per_unit: float,
    company_id: Optional[str] = None,
) -> None:
    init_product_costs_db(conn)
    company = normalize_company_id(company_id)
    product = normalize_product_name(product_name)

    try:
        value = float(cost_per_unit)
    except Exception as exc:  # noqa: BLE001
        raise ValueError("cost_per_unit must be a number") from exc

    if not math.isfinite(value) or value < 0:
        raise ValueError("cost_per_unit must be a non-negative finite number")

    now = _utc_now_iso()
    conn.execute(
        """
        INSERT INTO inventory_product_costs (company_id, product_name, cost_per_unit, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(company_id, product_name) DO UPDATE SET
            cost_per_unit = excluded.cost_per_unit,
            updated_at = excluded.updated_at
        """,
        (company, product, value, now, now),
    )
    conn.commit()


def get_cost_per_unit_map(conn: sqlite3.Connection, company_id: Optional[str] = None) -> Dict[str, float]:
    init_product_costs_db(conn)
    company = normalize_company_id(company_id)
    rows = conn.execute(
        "SELECT product_name, cost_per_unit FROM inventory_product_costs WHERE company_id = ?",
        (company,),
    ).fetchall()
    return {str(r["product_name"]): float(r["cost_per_unit"]) for r in rows}


def delete_cost_row(conn: sqlite3.Connection, product_name: str, company_id: Optional[str] = None) -> int:
    init_product_costs_db(conn)
    company = normalize_company_id(company_id)
    product = normalize_product_name(product_name)
    cur = conn.execute(
        "DELETE FROM inventory_product_costs WHERE company_id = ? AND product_name = ?",
        (company, product),
    )
    conn.commit()
    try:
        return int(cur.rowcount or 0)
    except Exception:
        return 0


# ---------------------------------------------------------------------------
# Invoice parsing
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class InvoiceLine:
    product_name: str
    quantity_purchased: int


def _detect_column_by_aliases(df: pd.DataFrame, aliases: Iterable[str]) -> Optional[str]:
    cols = set(df.columns)
    for a in aliases:
        if a in cols:
            return a
    # Try case-insensitive match for common invoice columns
    lowered = {c.lower(): c for c in df.columns}
    for a in aliases:
        key = a.lower()
        if key in lowered:
            return lowered[key]
    return None


def detect_invoice_columns(df: pd.DataFrame) -> Tuple[Optional[str], Optional[str]]:
    """Detect product + quantity columns in an invoice CSV.

    We intentionally do NOT call SchemaResolver.resolve(dataset_type='sales')
    because invoice files are not sales datasets and would fail validations.
    """

    product_aliases: List[str] = [
        "Product",
        "product",
        "ProductName",
        "product_name",
        "Item",
        "item",
        "Description",
        "description",
        "SKU",
        "sku",
        "StockCode",
        "stock_code",
    ]
    qty_aliases: List[str] = [
        "QuantityPurchased",
        "quantity_purchased",
        "QtyPurchased",
        "qty_purchased",
        "Quantity",
        "quantity",
        "Qty",
        "qty",
        "Units",
        "units",
    ]

    # If schema_resolver exists, enrich aliases from its registry.
    try:
        from src.schema_resolver import COLUMN_ALIASES, SemanticField

        product_aliases = list(dict.fromkeys(product_aliases + COLUMN_ALIASES.get(SemanticField.PRODUCT, [])))
        qty_aliases = list(dict.fromkeys(qty_aliases + COLUMN_ALIASES.get(SemanticField.QUANTITY, [])))
    except Exception as exc:  # noqa: BLE001
        logger.debug("Could not import schema_resolver aliases for invoice detection: %s", exc)

    product_col = _detect_column_by_aliases(df, product_aliases)
    qty_col = _detect_column_by_aliases(df, qty_aliases)
    return product_col, qty_col


def parse_invoice_lines(df: pd.DataFrame) -> List[InvoiceLine]:
    product_col, qty_col = detect_invoice_columns(df)
    if not product_col or not qty_col:
        raise ValueError("Invoice must contain product and quantity columns")

    lines: List[InvoiceLine] = []
    for _, row in df.iterrows():
        product_raw = row.get(product_col)
        qty_raw = row.get(qty_col)
        if pd.isna(product_raw) or str(product_raw).strip() == "":
            continue

        product = normalize_product_name(str(product_raw))
        try:
            qty = int(float(qty_raw)) if qty_raw is not None and not pd.isna(qty_raw) else 0
        except Exception:
            qty = 0

        if qty <= 0:
            continue

        lines.append(InvoiceLine(product_name=product, quantity_purchased=qty))

    return lines


# ---------------------------------------------------------------------------
# Inventory status analysis
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class InventoryStatus:
    product_name: str
    current_stock: Optional[int]
    avg_daily_sales: float
    days_left: Optional[float]
    status: str
    advice: str


def compute_avg_daily_sales(df: pd.DataFrame) -> Dict[str, float]:
    """Compute average daily unit sales per product.

    Logic:
    - Uses SchemaResolver to find date/product/quantity columns.
    - Aggregates units per (date, product).
    - avg_daily_sales = mean(daily_units) across ACTIVE days for that product.

    If quantity column is missing, each row counts as 1 unit.
    """

    if df is None or df.empty:
        return {}

    product_col = None
    date_col = None
    qty_col = None

    try:
        from src.schema_resolver import SchemaResolver, SemanticField

        resolver = SchemaResolver()
        res = resolver.resolve(df, dataset_type="sales")
        product_col = res.get_column(SemanticField.PRODUCT)
        date_col = res.get_column(SemanticField.ORDER_DATE)
        qty_col = res.get_column(SemanticField.QUANTITY)
    except Exception as exc:  # noqa: BLE001
        logger.warning("SchemaResolver failed for avg_daily_sales (%s). Falling back.", exc)

    # Fallbacks
    if not product_col:
        for c in ["ProductID", "Product_ID", "Product", "product", "Description", "description", "SKU", "StockCode"]:
            if c in df.columns:
                product_col = c
                break

    if not date_col:
        for c in ["OrderDate", "order_date", "Date", "date", "Sale_Date", "InvoiceDate", "invoice_date"]:
            if c in df.columns:
                date_col = c
                break

    if not product_col or not date_col:
        return {}

    working = df[[product_col, date_col] + ([qty_col] if qty_col and qty_col in df.columns else [])].copy()
    working[product_col] = working[product_col].apply(lambda v: normalize_product_name(str(v)) if pd.notna(v) else None)
    working = working.dropna(subset=[product_col])

    working[date_col] = pd.to_datetime(working[date_col], errors="coerce")
    working = working.dropna(subset=[date_col])
    working["__day"] = working[date_col].dt.date

    if qty_col and qty_col in working.columns:
        working["__qty"] = pd.to_numeric(working[qty_col], errors="coerce").fillna(0)
    else:
        working["__qty"] = 1.0

    # Aggregate per active day
    daily = (
        working.groupby([product_col, "__day"], dropna=True)["__qty"]
        .sum()
        .reset_index()
    )

    # Mean daily units across active days
    avg = daily.groupby(product_col)["__qty"].mean()

    result: Dict[str, float] = {}
    for product, value in avg.items():
        try:
            result[str(product)] = float(value)
        except Exception:
            continue
    return result


def classify_status(
    current_stock: Optional[int],
    avg_daily_sales: float,
    warning_days: int = 7,
    alert_days: int = 3,
    lead_days: Optional[int] = None,
) -> Tuple[str, Optional[float]]:
    """Return (status, days_left).

    Thresholds:
    - ALERT if days_left <= alert_days
    - WARNING if days_left <= warning_days
    - OK otherwise
    """

    if avg_daily_sales <= 0.01:
        # No meaningful demand detected
        return "DORMANT", None

    if current_stock is None:
        return "UNKNOWN", None

    days_left = current_stock / avg_daily_sales if avg_daily_sales > 0 else None

    if current_stock <= 0:
        return "ALERT", 0.0

    # Ensure sensible ordering
    alert_days = max(int(alert_days), 0)
    warning_days = max(int(warning_days), alert_days)

    if days_left is not None and days_left <= alert_days:
        return "ALERT", float(days_left)

    if days_left is not None and days_left <= warning_days:
        return "WARNING", float(days_left)

    return "OK", float(days_left) if days_left is not None else None


def compute_reorder_suggestion(
    current_stock: Optional[int],
    avg_daily_sales: float,
    lead_time_days: int = 7,
    safety_days: int = 0,
) -> Optional[int]:
    """Compute a simple reorder quantity suggestion.

    target_units = avg_daily_sales * (lead_time_days + safety_days)
    suggested = ceil(max(0, target_units - current_stock))

    Returns None when stock is unknown or demand is dormant.
    """

    if current_stock is None:
        return None
    if avg_daily_sales <= 0.01:
        return None

    lead_time_days = max(int(lead_time_days), 0)
    safety_days = max(int(safety_days), 0)
    target = float(avg_daily_sales) * float(lead_time_days + safety_days)
    needed = max(0.0, target - float(current_stock))
    return int(math.ceil(needed))


def advice_for(status: str) -> str:
    mapping = {
        "ALERT": "Reorder immediately. High demand detected.",
        "WARNING": "Stock running low. Monitor closely.",
        "DORMANT": "Apply promotion or discount.",
        "OK": "Stock level is healthy.",
        "UNKNOWN": "Set current stock to enable inventory analysis.",
    }
    return mapping.get(status, "Review stock levels.")
