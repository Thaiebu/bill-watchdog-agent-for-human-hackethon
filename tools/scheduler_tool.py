"""Tool 6: schedule_renewal_deadline — Register follow-up reminders."""
from strands import tool
from storage.db import insert_reminder


@tool
def schedule_renewal_deadline(
    user_id: str,
    merchant_name: str,
    alert_date: str,
    action_type: str = "REVIEW",
    notes: str = "",
) -> dict:
    """
    Register a background calendar reminder for a subscription renewal,
    trial expiration, or contract renegotiation window.

    Args:
        user_id: The user identifier.
        merchant_name: Vendor to watch.
        alert_date: ISO date string (YYYY-MM-DD) when to trigger the reminder.
        action_type: One of REVIEW, CANCEL, RENEGOTIATE, RETEST.
        notes: Optional additional context for the reminder.

    Returns:
        Confirmation dict with reminder_id and trigger_date.
    """
    reminder_id = insert_reminder({
        "user_id":       user_id,
        "merchant_name": merchant_name,
        "alert_date":    alert_date,
        "action_type":   action_type,
        "notes":         notes,
    })

    return {
        "status":        "scheduled",
        "reminder_id":   f"rem-{reminder_id:04d}",
        "merchant_name": merchant_name,
        "trigger_date":  alert_date,
        "action_type":   action_type,
        "message":       f"Reminder set: Review {merchant_name} on {alert_date}. Action: {action_type}.",
    }
