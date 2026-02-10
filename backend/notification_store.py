"""Notification persistence (read/unread) for the dashboard.

We intentionally keep this *minimal*:
- Notifications themselves are derived from existing inventory status calculations.
- This module only persists read-state in SQLite.

Tables:
- notifications_read: one row per (company_id, notification_id) that was marked read.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Iterable, Set, Optional

from backend.inventory_store import connect, normalize_company_id


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_notifications_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS notifications_read (
            company_id TEXT NOT NULL,
            notification_id TEXT NOT NULL,
            read_at TEXT NOT NULL,
            PRIMARY KEY(company_id, notification_id)
        )
        """
    )
    conn.commit()


def get_read_ids(conn: sqlite3.Connection, ids: Iterable[str], company_id: Optional[str] = None) -> Set[str]:
    init_notifications_db(conn)
    company = normalize_company_id(company_id)
    id_list = [str(i) for i in ids if i]
    if not id_list:
        return set()

    placeholders = ",".join(["?"] * len(id_list))
    rows = conn.execute(
        f"SELECT notification_id FROM notifications_read WHERE company_id = ? AND notification_id IN ({placeholders})",
        [company, *id_list],
    ).fetchall()
    return {str(r[0]) for r in rows}


def mark_read(conn: sqlite3.Connection, ids: Iterable[str], company_id: Optional[str] = None) -> int:
    init_notifications_db(conn)
    company = normalize_company_id(company_id)
    now = _utc_now_iso()
    id_list = [str(i) for i in ids if i]
    if not id_list:
        return 0

    updated = 0
    for nid in id_list:
        conn.execute(
            """
            INSERT OR REPLACE INTO notifications_read (company_id, notification_id, read_at)
            VALUES (?, ?, ?)
            """,
            (company, nid, now),
        )
        updated += 1
    conn.commit()
    return updated


def with_conn():
    """Convenience contextless connector (keeps parity with inventory_store.connect)."""

    return connect()
