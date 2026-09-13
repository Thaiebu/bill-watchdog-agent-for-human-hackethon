"""Tool 4: evaluate_budget_impact — Budget Intelligence Engine."""
from datetime import datetime
from strands import tool
from storage.db import get_budget_limits, get_all_bills_this_month

# Vendor → budget category mapping
CATEGORY_MAP = {
    "Netflix":           "subscriptions",
    "Spotify":           "subscriptions",
    "Amazon Prime":      "subscriptions",
    "Figma":             "subscriptions",
    "Google One":        "subscriptions",
    "GitHub":            "subscriptions",
    "Slack":             "subscriptions",
    "Jio Fiber":         "internet",
    "Airtel":            "internet",
    "BSNL":              "internet",
    "BESCOM Electricity":"utilities",
    "MSEB Electricity":  "utilities",
    "Tata Power":        "utilities",
    "LIC Insurance":     "insurance",
    "HDFC Life":         "insurance",
    "Star Health":       "insurance",
}


def get_category(merchant_name: str) -> str:
    return CATEGORY_MAP.get(merchant_name, "other")


@tool
def evaluate_budget_impact(user_id: str, current_invoice: dict, anomaly: dict) -> dict:
    """
    Calculate the budget impact of a bill: monthly budget health, Safe-to-Spend,
    projected month-end spend, and per-category budget status.

    Args:
        user_id: The user identifier.
        current_invoice: The structured invoice being evaluated.
        anomaly: The anomaly result from detect_bill_anomalies.

    Returns:
        Budget impact dict with spending pace, safe-to-spend, category status,
        and a plain-English impact statement.
    """
    now = datetime.now()
    days_elapsed = now.day
    days_in_month = _days_in_month(now.year, now.month)
    days_remaining = days_in_month - days_elapsed

    limits = get_budget_limits(user_id)
    total_budget = limits.get("total", 50000)

    # Get all bills processed so far this month from the DB
    this_month_bills = get_all_bills_this_month(user_id)
    spent_so_far = sum(b["total_amount"] for b in this_month_bills)

    # Add the current bill being evaluated
    current_amount = float(current_invoice.get("total_amount", 0))
    spent_so_far += current_amount

    # Spending pace and projections
    daily_rate = spent_so_far / days_elapsed if days_elapsed > 0 else 0
    projected_month_end = round(daily_rate * days_in_month, 2)
    expected_pace_spend = round(total_budget / days_in_month * days_elapsed, 2)
    safe_to_spend = max(0, round(total_budget - spent_so_far, 2))

    # Overall budget status
    if projected_month_end <= total_budget * 0.9:
        budget_status = "ON_TRACK"
        pace_narrative = f"You are ₹{expected_pace_spend - spent_so_far:,.0f} below expected spending pace."
    elif projected_month_end <= total_budget:
        budget_status = "ON_TRACK"
        pace_narrative = "You are on track to finish within budget."
    else:
        overshoot = projected_month_end - total_budget
        budget_status = "AT_RISK"
        pace_narrative = f"At current pace, you may exceed budget by ₹{overshoot:,.0f}."

    # Per-category breakdown for this month
    category_breakdown = {}
    for b in this_month_bills + [current_invoice]:
        cat = get_category(b.get("merchant_name", ""))
        cat_limit = limits.get(cat, 0)
        if cat not in category_breakdown:
            category_breakdown[cat] = {"spent": 0.0, "limit": cat_limit}
        category_breakdown[cat]["spent"] += float(b.get("total_amount", 0))

    for cat, data in category_breakdown.items():
        pct = (data["spent"] / data["limit"] * 100) if data["limit"] > 0 else 0
        data["percentage"] = round(pct, 1)
        data["status"] = "OVER_BUDGET" if pct > 100 else ("WARNING" if pct > 85 else "OK")

    # This bill's category impact
    this_category = get_category(current_invoice.get("merchant_name", ""))
    cat_data = category_breakdown.get(this_category, {})
    cat_pct = cat_data.get("percentage", 0)
    cat_status = cat_data.get("status", "OK")

    if anomaly.get("is_anomaly") and cat_status in ("OVER_BUDGET", "WARNING"):
        impact_statement = (
            f"This {anomaly['anomaly_type'].replace('_', ' ').lower()} pushes "
            f"'{this_category}' to {cat_pct:.0f}% of monthly limit "
            f"(₹{cat_data.get('spent', 0):,.0f} / ₹{cat_data.get('limit', 0):,.0f}). "
            f"{pace_narrative}"
        )
    elif anomaly.get("is_anomaly"):
        impact_statement = (
            f"This bill increase is notable, but '{this_category}' budget "
            f"({cat_pct:.0f}%) is still within safe range. {pace_narrative}"
        )
    else:
        impact_statement = f"No budget concern. {pace_narrative}"

    return {
        "monthly_budget":        total_budget,
        "total_spent_so_far":    round(spent_so_far, 2),
        "days_elapsed":          days_elapsed,
        "days_in_month":         days_in_month,
        "days_remaining":        days_remaining,
        "daily_rate":            round(daily_rate, 2),
        "expected_pace_spend":   expected_pace_spend,
        "projected_month_end":   projected_month_end,
        "safe_to_spend":         safe_to_spend,
        "budget_status":         budget_status,
        "category":              this_category,
        "category_breakdown":    category_breakdown,
        "impact_statement":      impact_statement,
    }


def _days_in_month(year: int, month: int) -> int:
    import calendar
    return calendar.monthrange(year, month)[1]
