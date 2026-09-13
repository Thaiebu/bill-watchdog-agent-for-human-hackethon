"""Tool 7: explain_spending_narrative — Conversational month-over-month spending analysis."""
from strands import tool
from storage.db import get_all_bills_this_month, get_all_bills_last_month
from tools.budget_tool import get_category


@tool
def explain_spending_narrative(user_id: str, user_query: str) -> str:
    """
    Answer a natural language question about the user's spending patterns by
    reasoning across all current and previous month bills. Identifies the biggest
    changes, root causes, and provides actionable context.

    Args:
        user_id: The user identifier.
        user_query: A free-text question, e.g. 'What changed most this month?'

    Returns:
        A plain-English narrative string explaining spending patterns and changes.
    """
    current_bills = get_all_bills_this_month(user_id)
    last_bills    = get_all_bills_last_month(user_id)

    if not current_bills and not last_bills:
        return "No bill data found for this or last month. Please process some bills first."

    # Aggregate per merchant
    def aggregate(bills: list) -> dict:
        result = {}
        for b in bills:
            m = b["merchant_name"]
            result[m] = result.get(m, 0) + b["total_amount"]
        return result

    curr_by_merchant = aggregate(current_bills)
    prev_by_merchant = aggregate(last_bills)

    total_curr = sum(curr_by_merchant.values())
    total_prev = sum(prev_by_merchant.values())
    total_delta = total_curr - total_prev

    # Build delta table
    all_merchants = set(curr_by_merchant) | set(prev_by_merchant)
    deltas = []
    for m in all_merchants:
        c = curr_by_merchant.get(m, 0)
        p = prev_by_merchant.get(m, 0)
        d = c - p
        if d != 0:
            deltas.append((m, p, c, d))

    deltas.sort(key=lambda x: abs(x[3]), reverse=True)

    # Build narrative
    direction = "higher" if total_delta > 0 else "lower"
    narrative_lines = [
        f"Your total spending this month is ₹{total_curr:,.0f}, "
        f"which is ₹{abs(total_delta):,.0f} {direction} than last month (₹{total_prev:,.0f})."
    ]

    if deltas:
        narrative_lines.append("\nThe main drivers of change:")
        for i, (merchant, prev, curr, delta) in enumerate(deltas[:5], 1):
            sign = "+" if delta > 0 else "-"
            cat = get_category(merchant)
            if prev == 0:
                narrative_lines.append(f"  {i}. {merchant} — New this month: ₹{curr:,.0f} ({cat})")
            elif curr == 0:
                narrative_lines.append(f"  {i}. {merchant} — No bill this month (was ₹{prev:,.0f})")
            else:
                pct = abs(delta / prev * 100)
                narrative_lines.append(
                    f"  {i}. {merchant} — {sign}₹{abs(delta):,.0f} ({sign}{pct:.0f}%) "
                    f"[{prev:,.0f} → {curr:,.0f}] ({cat})"
                )

    # Category summary
    cat_curr: dict = {}
    cat_prev: dict = {}
    for m, a in curr_by_merchant.items():
        cat = get_category(m)
        cat_curr[cat] = cat_curr.get(cat, 0) + a
    for m, a in prev_by_merchant.items():
        cat = get_category(m)
        cat_prev[cat] = cat_prev.get(cat, 0) + a

    cats_changed = [(c, cat_prev.get(c, 0), cat_curr.get(c, 0)) for c in cat_curr
                    if abs(cat_curr.get(c, 0) - cat_prev.get(c, 0)) > 100]
    cats_changed.sort(key=lambda x: abs(x[2] - x[1]), reverse=True)

    if cats_changed:
        narrative_lines.append("\nBy category:")
        for cat, prev_c, curr_c in cats_changed[:4]:
            delta_c = curr_c - prev_c
            sign = "+" if delta_c > 0 else "-"
            narrative_lines.append(
                f"  • {cat.capitalize()}: {sign}₹{abs(delta_c):,.0f} "
                f"(₹{prev_c:,.0f} → ₹{curr_c:,.0f})"
            )

    return "\n".join(narrative_lines)
