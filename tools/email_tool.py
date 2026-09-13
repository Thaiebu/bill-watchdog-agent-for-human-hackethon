"""
Tool 8: fetch_billing_emails — Fetch and pre-process billing emails from any inbox provider.
Uses the Adapter Pattern: provider can be swapped without changing agent logic.
"""
import json
from strands import tool
from inboxes.base_adapter import get_adapter
from tools.extractor_tool import extract_invoice_entities
from metering.usage_tracker import track_event


@tool
def fetch_billing_emails(
    user_id: str,
    provider: str = "mock",
    max_count: int = 15,
    credentials: dict = None,
) -> dict:
    """
    Fetch billing-related emails from the user's inbox using the specified
    email provider adapter (Mock, IMAP/Gmail, or OAuth2 Gmail).
    Each billing email is automatically passed through extract_invoice_entities
    so results are ready for the full anomaly detection pipeline.

    Args:
        user_id: The user/account identifier.
        provider: Email provider — "mock" (demo), "imap" (real IMAP), "oauth2_gmail" (production).
        max_count: Max billing emails to fetch per run (daily quota enforced by tier engine).
        credentials: Provider-specific auth dict. For IMAP: {email_address, app_password, imap_host}.
                     Not needed for mock provider.

    Returns:
        Dict with provider name, scan stats, and list of extracted bill payloads.
    """
    from metering.tier_engine import check_email_quota

    # Enforce daily email quota based on user tier
    quota_check = check_email_quota(user_id, requested=max_count)
    if not quota_check["allowed"]:
        return {
            "provider": provider,
            "quota_exceeded": True,
            "message": quota_check["message"],
            "emails_scanned": 0,
            "billing_emails_found": 0,
            "emails": [],
        }

    allowed_count = quota_check["allowed_count"]

    # Get the correct adapter via factory
    adapter = get_adapter(provider, credentials or {})

    # Fetch billing emails (adapter handles auth + filtering)
    raw_emails = adapter.list_billing_emails(max_count=allowed_count)

    # Track usage event
    track_event(user_id, "email_scanned", {
        "provider": provider,
        "count": len(raw_emails),
    })

    # Extract structured invoice data from each email body
    processed = []
    for email in raw_emails:
        try:
            invoice = extract_invoice_entities(
                raw_content=email.body_text,
                source_type="email",
            )
            # Enrich with email metadata
            invoice["email_id"]      = email.id
            invoice["email_subject"] = email.subject
            invoice["email_sender"]  = email.sender
            invoice["email_date"]    = email.date

            # Use email date as invoice date if extractor didn't find one
            if not invoice.get("invoice_date") or invoice["invoice_date"] == "2026-09-01":
                invoice["invoice_date"] = email.date

            track_event(user_id, "bill_extracted", {
                "merchant": invoice.get("merchant_name"),
                "amount":   invoice.get("total_amount"),
            })

            processed.append({
                "email_id":   email.id,
                "subject":    email.subject,
                "sender":     email.sender,
                "date":       email.date,
                "snippet":    email.snippet,
                "invoice":    invoice,
            })
        except Exception as e:
            # Don't fail the whole batch if one email fails to parse
            processed.append({
                "email_id":   email.id,
                "subject":    email.subject,
                "sender":     email.sender,
                "date":       email.date,
                "snippet":    email.snippet,
                "invoice":    None,
                "parse_error": str(e),
            })

    return {
        "provider":              adapter.provider_name(),
        "quota_exceeded":        False,
        "emails_scanned":        quota_check.get("total_scanned_today", 0) + len(raw_emails),
        "billing_emails_found":  len(processed),
        "daily_limit":           quota_check["daily_limit"],
        "emails":                processed,
        "message": (
            f"Fetched {len(processed)} billing emails from {adapter.provider_name()}. "
            f"Ready for anomaly analysis."
        ),
    }
