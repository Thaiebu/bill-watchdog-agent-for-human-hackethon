"""Tool 3: detect_bill_anomalies — Multi-factor anomaly evaluation."""
from datetime import datetime
from strands import tool


SEASONAL_MERCHANTS = {"BESCOM Electricity", "MSEB Electricity", "Tata Power"}
SEASONAL_VARIANCE_PCT = 20.0   # ±20% is acceptable for utilities
DEFAULT_VARIANCE_PCT  = 5.0    # ±5% acceptable for regular subscriptions


@tool
def detect_bill_anomalies(current_invoice: dict, baseline_data: dict) -> dict:
    """
    Compare a current invoice against its historical baseline to detect
    anomalies: price hikes, promotional expirations, hidden fee injections,
    and seasonal deviations.

    Args:
        current_invoice: Structured invoice from extract_invoice_entities.
        baseline_data: Baseline dict from query_billing_baseline.

    Returns:
        Anomaly result with is_anomaly, delta_amount, delta_percentage,
        anomaly_type, root_cause_explanation, and severity.
    """
    current_amount = float(current_invoice.get("total_amount", 0))
    merchant = current_invoice.get("merchant_name", "Unknown")
    detected_terms = current_invoice.get("detected_terms", [])

    # No baseline history — first time seeing this vendor
    if not baseline_data.get("has_history") or baseline_data.get("average_monthly_spend") is None:
        return _build_result(
            is_anomaly=False,
            delta_amount=0,
            delta_pct=0,
            anomaly_type="NEW_VENDOR",
            explanation=f"First bill from {merchant}. Baseline established at ₹{current_amount:,.0f}.",
            severity="SILENT",
        )

    baseline_amount = float(baseline_data["average_monthly_spend"])
    delta_amount = current_amount - baseline_amount
    delta_pct = (delta_amount / baseline_amount * 100) if baseline_amount > 0 else 0

    # Allow for seasonal variance on utility bills
    threshold = SEASONAL_VARIANCE_PCT if merchant in SEASONAL_MERCHANTS else DEFAULT_VARIANCE_PCT

    # Check for promotional expiration in detected terms
    promo_expired = any(
        kw in term.lower()
        for term in detected_terms
        for kw in ["promo", "promotional", "discount expired", "offer expired"]
    )
    promos = baseline_data.get("promotions", [])
    active_promo_expired = _check_promo_expiry(promos)

    # ── Decision Logic ─────────────────────────────────────────────────────

    if promo_expired or active_promo_expired:
        promo_name = promos[0]["name"] if promos else "Promotional discount"
        return _build_result(
            is_anomaly=True,
            delta_amount=round(delta_amount, 2),
            delta_pct=round(delta_pct, 1),
            anomaly_type="PROMOTION_EXPIRATION",
            explanation=(
                f"{promo_name} has expired. Bill increased from ₹{baseline_amount:,.0f} "
                f"to ₹{current_amount:,.0f} (+₹{delta_amount:,.0f}, +{delta_pct:.1f}%)."
            ),
            severity="ACTION_REQUIRED",
        )

    if delta_pct > threshold and delta_amount > 50:
        # Determine if this is a stealth hike or new fee injection
        anomaly_type = "STEALTH_PRICE_HIKE"
        explanation = (
            f"Unannounced price increase detected on {merchant}. "
            f"Bill rose from ₹{baseline_amount:,.0f} to ₹{current_amount:,.0f} "
            f"(+₹{delta_amount:,.0f}, +{delta_pct:.1f}%). "
            f"No promotional change noted."
        )
        if _has_new_line_item(current_invoice):
            anomaly_type = "HIDDEN_FEE_INJECTION"
            explanation = (
                f"New line item detected on {merchant} bill. "
                f"Total increased from ₹{baseline_amount:,.0f} to ₹{current_amount:,.0f}."
            )
        severity = "ACTION_REQUIRED" if delta_pct > 15 else "INFORMATIONAL"
        return _build_result(
            is_anomaly=True,
            delta_amount=round(delta_amount, 2),
            delta_pct=round(delta_pct, 1),
            anomaly_type=anomaly_type,
            explanation=explanation,
            severity=severity,
        )

    if delta_pct < -threshold and abs(delta_amount) > 50:
        return _build_result(
            is_anomaly=False,
            delta_amount=round(delta_amount, 2),
            delta_pct=round(delta_pct, 1),
            anomaly_type="CREDIT_OR_DISCOUNT",
            explanation=f"{merchant} bill decreased by ₹{abs(delta_amount):,.0f}. Possible credit or discount applied.",
            severity="SILENT",
        )

    # Normal — within expected variance
    return _build_result(
        is_anomaly=False,
        delta_amount=round(delta_amount, 2),
        delta_pct=round(delta_pct, 1),
        anomaly_type="NORMAL",
        explanation=f"{merchant} bill ₹{current_amount:,.0f} is within expected range (±{threshold:.0f}% of ₹{baseline_amount:,.0f} baseline).",
        severity="SILENT",
    )


def _build_result(is_anomaly, delta_amount, delta_pct, anomaly_type, explanation, severity) -> dict:
    return {
        "is_anomaly":           is_anomaly,
        "delta_amount":         delta_amount,
        "delta_percentage":     delta_pct,
        "anomaly_type":         anomaly_type,
        "root_cause_explanation": explanation,
        "severity":             severity,
    }


def _check_promo_expiry(promotions: list) -> bool:
    today = datetime.now().date()
    for promo in promotions:
        expiry_str = promo.get("expiry_date", "")
        if expiry_str:
            try:
                expiry = datetime.strptime(expiry_str, "%Y-%m-%d").date()
                if expiry <= today:
                    return True
            except ValueError:
                pass
    return False


def _has_new_line_item(invoice: dict) -> bool:
    """Heuristic: if line items contain known add-on keywords, flag as new fee."""
    add_on_keywords = ["fee", "surcharge", "add-on", "rental", "tax", "levy"]
    for item in invoice.get("line_items", []):
        name = item.get("name", "").lower()
        if any(kw in name for kw in add_on_keywords):
            return True
    return False
