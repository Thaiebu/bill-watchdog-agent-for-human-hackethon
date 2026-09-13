"""Tool 2: query_billing_baseline — Fetch vendor history and promotional terms."""
from strands import tool
from storage.db import get_baseline, get_bill_history


@tool
def query_billing_baseline(user_id: str, merchant_name: str) -> dict:
    """
    Retrieve the historical billing baseline and any known promotional terms
    for a given merchant. Returns average monthly spend, last month amount,
    and any expiring promotions.

    Args:
        user_id: The user identifier.
        merchant_name: The merchant/vendor name to look up.

    Returns:
        Baseline dict with average_monthly_spend, last_month_amount, promotions.
        Returns a 'no_history' baseline if the vendor has never been seen before.
    """
    baseline = get_baseline(user_id, merchant_name)

    if baseline:
        return {
            "merchant_name":          baseline["merchant_name"],
            "average_monthly_spend":  baseline["average_monthly_spend"],
            "baseline_months":        baseline["baseline_months"],
            "last_month_amount":      baseline["last_month_amount"],
            "promotions":             baseline["promotions"],
            "has_history":            True,
        }

    # Try to compute baseline from raw bill history
    history = get_bill_history(user_id, merchant_name, months=12)
    if history:
        amounts = [b["total_amount"] for b in history]
        avg = sum(amounts) / len(amounts)
        return {
            "merchant_name":         merchant_name,
            "average_monthly_spend": round(avg, 2),
            "baseline_months":       len(history),
            "last_month_amount":     history[0]["total_amount"],
            "promotions":            [],
            "has_history":           True,
        }

    # First-time vendor — no history
    return {
        "merchant_name":         merchant_name,
        "average_monthly_spend": None,
        "baseline_months":       0,
        "last_month_amount":     None,
        "promotions":            [],
        "has_history":           False,
    }
