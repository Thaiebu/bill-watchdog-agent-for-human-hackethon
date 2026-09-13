"""Tool 5: draft_dispute_packet — Generate professional dispute/renegotiation email."""
from strands import tool

VENDOR_CONTEXT = {
    "Jio Fiber": {
        "retention_team": "1800-889-9999 (Jio Care)",
        "known_retention_offers": "often offers 3-month extension of promo rate to loyal customers",
        "cancellation_url": "https://www.jio.com/selfcare/",
    },
    "Figma": {
        "retention_team": "support@figma.com",
        "known_retention_offers": "may offer annual plan discount or education/startup pricing",
        "cancellation_url": "https://www.figma.com/settings",
    },
    "Netflix": {
        "retention_team": "1800-209-0050 or netflix.com/cancelplan",
        "known_retention_offers": "occasionally offers 1-month free or downgrade to Basic",
        "cancellation_url": "https://www.netflix.com/cancelplan",
    },
    "default": {
        "retention_team": "customer service contact listed on your invoice",
        "known_retention_offers": "ask about loyalty discounts or promotional extensions",
        "cancellation_url": "vendor's website account settings page",
    },
}


@tool
def draft_dispute_packet(merchant_name: str, anomaly: dict, account_info: dict) -> dict:
    """
    Generate a professional, courteous dispute or renegotiation email packet
    tailored to the vendor's known retention policy and the specific anomaly type.

    Args:
        merchant_name: The vendor/merchant name.
        anomaly: Anomaly result from detect_bill_anomalies.
        account_info: Dict with optional keys: account_id, months_as_customer, payment_record.

    Returns:
        Dict with email_subject, email_body, suggested_action, alternative_action,
        and cancellation_link.
    """
    vendor = VENDOR_CONTEXT.get(merchant_name, VENDOR_CONTEXT["default"])
    account_id   = account_info.get("account_id", "your account")
    months       = account_info.get("months_as_customer", 12)
    payment_rec  = account_info.get("payment_record", "good standing")
    delta_amt    = abs(anomaly.get("delta_amount", 0))
    delta_pct    = abs(anomaly.get("delta_percentage", 0))
    anomaly_type = anomaly.get("anomaly_type", "STEALTH_PRICE_HIKE")
    explanation  = anomaly.get("root_cause_explanation", "")

    if anomaly_type == "PROMOTION_EXPIRATION":
        subject = f"Request for Promotional Rate Extension — {merchant_name} Account"
        body = f"""Subject: {subject}

Dear {merchant_name} Customer Retention Team,

I am writing regarding a recent change to my monthly bill for account {account_id}.

I have been a loyal {merchant_name} customer for {months} months with a {payment_rec} payment record. My bill has increased by ₹{delta_amt:,.0f} (+{delta_pct:.0f}%) following the expiration of my introductory promotional offer.

I understand promotional pricing has an end date; however, I would greatly appreciate it if your team could:
1. Offer an extended promotional rate or loyalty discount for the next 3–6 months.
2. Or advise on any current retention offers available for long-standing customers.

{vendor['known_retention_offers'].capitalize()}.

I genuinely value {merchant_name}'s service and would prefer to continue as a customer rather than explore alternatives. I am happy to discuss options at your convenience.

Thank you for your time.

Best regards,
[Your Name]
Account: {account_id}
"""
    elif anomaly_type in ("STEALTH_PRICE_HIKE", "HIDDEN_FEE_INJECTION"):
        subject = f"Billing Inquiry — Unexpected Increase on {merchant_name} Account"
        body = f"""Subject: {subject}

Dear {merchant_name} Support Team,

I am contacting you regarding an unexpected increase on my {merchant_name} bill for account {account_id}.

{explanation}

As a customer of {months} months with a {payment_rec} record, I was not notified of this pricing change in advance. I would like to:
1. Understand the specific reason for this ₹{delta_amt:,.0f} increase.
2. Request reinstatement of my previous rate, or be informed of available plan options at the prior price point.

I look forward to a swift resolution and am happy to escalate via {vendor['retention_team']} if needed.

Thank you,
[Your Name]
Account: {account_id}
"""
    else:
        subject = f"General Billing Inquiry — {merchant_name}"
        body = f"""Subject: {subject}

Dear {merchant_name} Team,

I noticed a change on my recent bill for account {account_id} and would appreciate clarification.

{explanation}

Please advise on the next steps or any loyalty options available.

Thank you,
[Your Name]
"""

    return {
        "email_subject":      subject.replace("Subject: ", ""),
        "email_body":         body.strip(),
        "suggested_action":   "Send Email",
        "alternative_action": f"Call Retention: {vendor['retention_team']}",
        "cancellation_link":  vendor["cancellation_url"],
        "vendor_tip":         vendor["known_retention_offers"],
    }
