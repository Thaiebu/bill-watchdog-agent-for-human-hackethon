"""
SQLite storage layer for BillWatchdog.
Manages bill history, vendor baselines, budget limits, and scheduled reminders.
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "billwatchdog.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create all tables if they don't exist."""
    conn = get_connection()
    cur = conn.cursor()

    # --- Bills table: one row per bill processed ---
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bills (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         TEXT NOT NULL DEFAULT 'user_1',
            merchant_name   TEXT NOT NULL,
            invoice_date    TEXT NOT NULL,
            billing_period  TEXT,
            total_amount    REAL NOT NULL,
            currency        TEXT DEFAULT 'INR',
            line_items      TEXT,          -- JSON array
            detected_terms  TEXT,          -- JSON array
            source_type     TEXT DEFAULT 'manual',
            processed_at    TEXT NOT NULL DEFAULT (datetime('now')),
            silent          INTEGER DEFAULT 1,  -- 1=silent, 0=alerted
            alert_reason    TEXT
        )
    """)

    # --- Vendor baselines: rolling average per merchant ---
    cur.execute("""
        CREATE TABLE IF NOT EXISTS vendor_baselines (
            id                      INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id                 TEXT NOT NULL DEFAULT 'user_1',
            merchant_name           TEXT NOT NULL,
            average_monthly_spend   REAL NOT NULL,
            baseline_months         INTEGER DEFAULT 6,
            last_month_amount       REAL,
            promotions              TEXT,  -- JSON array of promo objects
            updated_at              TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(user_id, merchant_name)
        )
    """)

    # --- Budget limits: monthly per-category limits ---
    cur.execute("""
        CREATE TABLE IF NOT EXISTS budget_limits (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     TEXT NOT NULL DEFAULT 'user_1',
            category    TEXT NOT NULL,
            monthly_limit REAL NOT NULL,
            UNIQUE(user_id, category)
        )
    """)

    # --- Scheduled reminders ---
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         TEXT NOT NULL DEFAULT 'user_1',
            merchant_name   TEXT NOT NULL,
            alert_date      TEXT NOT NULL,
            action_type     TEXT,
            notes           TEXT,
            triggered       INTEGER DEFAULT 0,
            created_at      TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)

    conn.commit()
    conn.close()


# ── Bills ──────────────────────────────────────────────────────────────────

def insert_bill(data: dict) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO bills
            (user_id, merchant_name, invoice_date, billing_period,
             total_amount, currency, line_items, detected_terms,
             source_type, silent, alert_reason)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """, (
        data.get("user_id", "user_1"),
        data["merchant_name"],
        data["invoice_date"],
        data.get("billing_period", ""),
        data["total_amount"],
        data.get("currency", "INR"),
        json.dumps(data.get("line_items", [])),
        json.dumps(data.get("detected_terms", [])),
        data.get("source_type", "manual"),
        1 if data.get("silent", True) else 0,
        data.get("alert_reason"),
    ))
    conn.commit()
    row_id = cur.lastrowid
    conn.close()
    return row_id


def get_bill_history(user_id: str, merchant_name: str, months: int = 12) -> list[dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM bills
        WHERE user_id = ? AND merchant_name = ?
        ORDER BY invoice_date DESC
        LIMIT ?
    """, (user_id, merchant_name, months))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    for r in rows:
        r["line_items"] = json.loads(r["line_items"] or "[]")
        r["detected_terms"] = json.loads(r["detected_terms"] or "[]")
    return rows


def get_all_bills_this_month(user_id: str) -> list[dict]:
    now = datetime.now()
    month_prefix = now.strftime("%Y-%m")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM bills
        WHERE user_id = ? AND invoice_date LIKE ?
        ORDER BY invoice_date DESC
    """, (user_id, f"{month_prefix}%"))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    for r in rows:
        r["line_items"] = json.loads(r["line_items"] or "[]")
        r["detected_terms"] = json.loads(r["detected_terms"] or "[]")
    return rows


def get_all_bills_last_month(user_id: str) -> list[dict]:
    now = datetime.now()
    if now.month == 1:
        month_prefix = f"{now.year - 1}-12"
    else:
        month_prefix = f"{now.year}-{now.month - 1:02d}"
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM bills
        WHERE user_id = ? AND invoice_date LIKE ?
        ORDER BY invoice_date DESC
    """, (user_id, f"{month_prefix}%"))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    for r in rows:
        r["line_items"] = json.loads(r["line_items"] or "[]")
        r["detected_terms"] = json.loads(r["detected_terms"] or "[]")
    return rows


# ── Baselines ──────────────────────────────────────────────────────────────

def upsert_baseline(data: dict):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO vendor_baselines
            (user_id, merchant_name, average_monthly_spend,
             baseline_months, last_month_amount, promotions)
        VALUES (?,?,?,?,?,?)
        ON CONFLICT(user_id, merchant_name) DO UPDATE SET
            average_monthly_spend = excluded.average_monthly_spend,
            last_month_amount     = excluded.last_month_amount,
            promotions            = excluded.promotions,
            updated_at            = datetime('now')
    """, (
        data.get("user_id", "user_1"),
        data["merchant_name"],
        data["average_monthly_spend"],
        data.get("baseline_months", 6),
        data.get("last_month_amount"),
        json.dumps(data.get("promotions", [])),
    ))
    conn.commit()
    conn.close()


def get_baseline(user_id: str, merchant_name: str) -> dict | None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM vendor_baselines
        WHERE user_id = ? AND merchant_name = ?
    """, (user_id, merchant_name))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    result = dict(row)
    result["promotions"] = json.loads(result.get("promotions") or "[]")
    return result


# ── Budget Limits ──────────────────────────────────────────────────────────

def get_budget_limits(user_id: str) -> dict:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT category, monthly_limit FROM budget_limits WHERE user_id = ?", (user_id,))
    rows = cur.fetchall()
    conn.close()
    return {r["category"]: r["monthly_limit"] for r in rows}


def upsert_budget_limit(user_id: str, category: str, monthly_limit: float):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO budget_limits (user_id, category, monthly_limit)
        VALUES (?,?,?)
        ON CONFLICT(user_id, category) DO UPDATE SET monthly_limit = excluded.monthly_limit
    """, (user_id, category, monthly_limit))
    conn.commit()
    conn.close()


# ── Reminders ─────────────────────────────────────────────────────────────

def insert_reminder(data: dict) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO reminders (user_id, merchant_name, alert_date, action_type, notes)
        VALUES (?,?,?,?,?)
    """, (
        data.get("user_id", "user_1"),
        data["merchant_name"],
        data["alert_date"],
        data.get("action_type", "REVIEW"),
        data.get("notes", ""),
    ))
    conn.commit()
    row_id = cur.lastrowid
    conn.close()
    return row_id


def get_pending_reminders(user_id: str) -> list[dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM reminders WHERE user_id = ? AND triggered = 0
        ORDER BY alert_date ASC
    """, (user_id,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows
