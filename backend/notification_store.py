"""Notification persistence for the dashboard.

Stores notifications as records in SQLite with read/unread state.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Iterable, List, Dict, Any, Set, Optional

from backend.inventory_store import connect, normalize_company_id, normalize_branch_id


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_notifications_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id TEXT NOT NULL,
            branch_id TEXT NOT NULL,
            product_name TEXT,
            message TEXT NOT NULL,
            type TEXT NOT NULL,
            created_at TEXT NOT NULL,
            is_read INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_notifications_company_created
        ON notifications(company_id, branch_id, created_at DESC, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_notifications_company_is_read
        ON notifications(company_id, branch_id, is_read)
        """
    )

    cols = [r["name"] for r in conn.execute("PRAGMA table_info(notifications)").fetchall()]
    if "branch_id" not in cols:
        conn.execute("ALTER TABLE notifications ADD COLUMN branch_id TEXT NOT NULL DEFAULT 'GLOBAL'")

    conn.commit()


def get_read_ids(conn: sqlite3.Connection, ids: Iterable[str], company_id: Optional[str] = None, branch_id: Optional[str] = None) -> Set[str]:
    """Backward-compatible helper for legacy callers."""
    init_notifications_db(conn)
    company = normalize_company_id(company_id)
    branch = normalize_branch_id(branch_id)
    wanted: List[int] = []
    for i in ids:
        try:
            wanted.append(int(i))
        except Exception:
            continue
    if not wanted:
        return set()

    placeholders = ",".join(["?"] * len(wanted))
    rows = conn.execute(
        f"SELECT id FROM notifications WHERE company_id = ? AND branch_id = ? AND is_read = 1 AND id IN ({placeholders})",
        [company, branch, *wanted],
    ).fetchall()
    return {str(r[0]) for r in rows}


def mark_read(conn: sqlite3.Connection, ids: Iterable[str], company_id: Optional[str] = None, branch_id: Optional[str] = None) -> int:
    """Backward-compatible helper for legacy callers."""
    return mark_notifications_read(conn, ids=ids, company_id=company_id, branch_id=branch_id)


def create_notification(
    conn: sqlite3.Connection,
    *,
    product_name: Optional[str],
    message: str,
    type: str,
    company_id: Optional[str] = None,
    branch_id: Optional[str] = None,
) -> Dict[str, Any]:
    init_notifications_db(conn)
    company = normalize_company_id(company_id)
    branch = normalize_branch_id(branch_id)
    created_at = _utc_now_iso()
    ntype = str(type or "INFO").upper().strip()
    if ntype not in {"ALERT", "WARNING", "INFO"}:
        ntype = "INFO"

    cur = conn.execute(
        """
        INSERT INTO notifications (company_id, branch_id, product_name, message, type, created_at, is_read)
        VALUES (?, ?, ?, ?, ?, ?, 0)
        """,
        (
            company,
            branch,
            str(product_name) if product_name else None,
            str(message),
            ntype,
            created_at,
        ),
    )
    conn.commit()
    new_id = int(cur.lastrowid)
    return {
        "id": new_id,
        "product_name": str(product_name) if product_name else None,
        "message": str(message),
        "type": ntype,
        "created_at": created_at,
        "is_read": False,
    }


def list_notifications(
    conn: sqlite3.Connection,
    *,
    company_id: Optional[str] = None,
    branch_id: Optional[str] = None,
    limit: int = 100,
    unread_only: bool = False,
) -> List[Dict[str, Any]]:
    init_notifications_db(conn)
    company = normalize_company_id(company_id)
    branch = normalize_branch_id(branch_id)
    take = max(1, min(int(limit), 500))
    if unread_only:
        rows = conn.execute(
            """
            SELECT id, product_name, message, type, created_at, is_read
            FROM notifications
            WHERE company_id = ? AND branch_id = ? AND is_read = 0
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (company, branch, take),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT id, product_name, message, type, created_at, is_read
            FROM notifications
            WHERE company_id = ? AND branch_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (company, branch, take),
        ).fetchall()

    out: List[Dict[str, Any]] = []
    for r in rows:
        out.append(
            {
                "id": int(r["id"]),
                "product_name": str(r["product_name"]) if r["product_name"] else None,
                "message": str(r["message"]),
                "type": str(r["type"]),
                "created_at": str(r["created_at"]),
                "is_read": bool(int(r["is_read"])),
            }
        )
    return out


def mark_notification_read(
    conn: sqlite3.Connection,
    *,
    notification_id: int,
    company_id: Optional[str] = None,
    branch_id: Optional[str] = None,
) -> bool:
    init_notifications_db(conn)
    company = normalize_company_id(company_id)
    branch = normalize_branch_id(branch_id)
    cur = conn.execute(
        """
        UPDATE notifications
        SET is_read = 1
        WHERE company_id = ? AND branch_id = ? AND id = ?
        """,
        (company, branch, int(notification_id)),
    )
    conn.commit()
    return int(cur.rowcount or 0) > 0


def mark_notifications_read(conn: sqlite3.Connection, ids: Iterable[str], company_id: Optional[str] = None, branch_id: Optional[str] = None) -> int:
    init_notifications_db(conn)
    company = normalize_company_id(company_id)
    branch = normalize_branch_id(branch_id)
    wanted: List[int] = []
    for i in ids:
        try:
            wanted.append(int(i))
        except Exception:
            continue
    if not wanted:
        return 0

    placeholders = ",".join(["?"] * len(wanted))
    cur = conn.execute(
        f"""
        UPDATE notifications
        SET is_read = 1
        WHERE company_id = ? AND branch_id = ? AND id IN ({placeholders})
        """,
        [company, branch, *wanted],
    )
    conn.commit()
    return int(cur.rowcount or 0)


def unread_count(conn: sqlite3.Connection, company_id: Optional[str] = None, branch_id: Optional[str] = None) -> int:
    init_notifications_db(conn)
    company = normalize_company_id(company_id)
    branch = normalize_branch_id(branch_id)
    row = conn.execute(
        """
        SELECT COUNT(1) AS c
        FROM notifications
        WHERE company_id = ? AND branch_id = ? AND is_read = 0
        """,
        (company, branch),
    ).fetchone()
    return int(row["c"] if row else 0)


def with_conn():
    """Convenience contextless connector (keeps parity with inventory_store.connect)."""

    return connect()
