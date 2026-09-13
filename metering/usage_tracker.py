"""
Per-user usage event tracking for BillWatchdog.
Records every agent action to the usage_events table for metering,
SaaS tier enforcement, and AWS cost estimation.
"""
import sqlite3
import json
from datetime import datetime, date
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "storage" / "billwatchdog.db"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_usage_table():
    """Create usage_events table if not exists."""
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS usage_events (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      TEXT    NOT NULL,
            event_type   TEXT    NOT NULL,
            payload      TEXT,           -- JSON metadata
            input_tokens  INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0,
            timestamp    TEXT    NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    conn.close()


def track_event(user_id: str, event_type: str, payload: dict = None,
                input_tokens: int = 0, output_tokens: int = 0):
    """
    Record a usage event.

    Event types:
      email_scanned      — inbox fetch run
      bill_extracted     — invoice successfully parsed
      anomaly_detected   — anomaly flagged (not silent)
      dispute_drafted    — dispute email generated
      bedrock_call       — LLM API invocation with token count
    """
    init_usage_table()
    conn = get_conn()
    conn.execute("""
        INSERT INTO usage_events (user_id, event_type, payload, input_tokens, output_tokens)
        VALUES (?, ?, ?, ?, ?)
    """, (
        user_id,
        event_type,
        json.dumps(payload or {}),
        input_tokens,
        output_tokens,
    ))
    conn.commit()
    conn.close()


def get_usage_today(user_id: str) -> dict:
    """Get per-event-type counts for today."""
    init_usage_table()
    today = date.today().isoformat()
    conn = get_conn()
    cur = conn.execute("""
        SELECT event_type, COUNT(*) as count,
               SUM(input_tokens) as total_input,
               SUM(output_tokens) as total_output
        FROM usage_events
        WHERE user_id = ? AND timestamp LIKE ?
        GROUP BY event_type
    """, (user_id, f"{today}%"))
    rows = {r["event_type"]: dict(r) for r in cur.fetchall()}
    conn.close()
    return rows


def get_usage_this_month(user_id: str) -> dict:
    """Get per-event-type counts for the current calendar month."""
    init_usage_table()
    month_prefix = datetime.now().strftime("%Y-%m")
    conn = get_conn()
    cur = conn.execute("""
        SELECT event_type, COUNT(*) as count,
               SUM(input_tokens) as total_input,
               SUM(output_tokens) as total_output
        FROM usage_events
        WHERE user_id = ? AND timestamp LIKE ?
        GROUP BY event_type
    """, (user_id, f"{month_prefix}%"))
    rows = {r["event_type"]: dict(r) for r in cur.fetchall()}
    conn.close()
    return rows


def get_daily_email_count(user_id: str) -> int:
    """How many emails has this user scanned today?"""
    today_usage = get_usage_today(user_id)
    email_event = today_usage.get("email_scanned", {})
    payload_sum = 0
    conn = get_conn()
    today = date.today().isoformat()
    cur = conn.execute("""
        SELECT payload FROM usage_events
        WHERE user_id = ? AND event_type = 'email_scanned' AND timestamp LIKE ?
    """, (user_id, f"{today}%"))
    for row in cur.fetchall():
        try:
            payload_sum += json.loads(row["payload"] or "{}").get("count", 0)
        except Exception:
            pass
    conn.close()
    return payload_sum


def get_monthly_token_totals(user_id: str) -> dict:
    """Total input/output tokens used this month for cost estimation."""
    month_usage = get_usage_this_month(user_id)
    bedrock = month_usage.get("bedrock_call", {})
    return {
        "input_tokens":  bedrock.get("total_input", 0) or 0,
        "output_tokens": bedrock.get("total_output", 0) or 0,
    }
