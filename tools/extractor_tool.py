"""Tool 1: extract_invoice_entities — Parse raw bill text/JSON into a structured object."""
import json
import re
from strands import tool


@tool
def extract_invoice_entities(raw_content: str, source_type: str = "json") -> dict:
    """
    Parse a raw bill (JSON string, email text, or structured dict) into a
    normalized invoice entity. Returns a structured dict with merchant_name,
    invoice_date, total_amount, line_items, currency, and detected_terms.

    Args:
        raw_content: The raw bill content as a JSON string or plain text.
        source_type: One of 'json', 'email', or 'text'.

    Returns:
        A structured invoice dict ready for downstream analysis.
    """
    # If raw_content is already a JSON string, parse it directly
    try:
        data = json.loads(raw_content)
        if isinstance(data, dict) and "merchant_name" in data and "total_amount" in data:
            # Already structured — normalize and return
            return _normalize(data)
    except (json.JSONDecodeError, TypeError):
        pass

    # Fallback: extract key fields from plain text using patterns
    merchant = _extract_field(raw_content, r"(?i)(merchant|from|biller)[:\s]+([^\n,]+)")
    amount = _extract_amount(raw_content)
    date = _extract_field(raw_content, r"(\d{4}-\d{2}-\d{2})")
    currency = "INR" if "₹" in raw_content or "INR" in raw_content else "USD"

    return _normalize({
        "merchant_name": merchant or "Unknown Merchant",
        "invoice_date": date or "2026-09-01",
        "billing_period": "",
        "total_amount": amount or 0.0,
        "currency": currency,
        "line_items": [],
        "detected_terms": [],
        "source_type": source_type,
    })


def _normalize(data: dict) -> dict:
    """Ensure all required fields exist and types are correct."""
    return {
        "merchant_name":  str(data.get("merchant_name", "Unknown")),
        "invoice_date":   str(data.get("invoice_date", "2026-09-01")),
        "billing_period": str(data.get("billing_period", "")),
        "total_amount":   float(data.get("total_amount", 0)),
        "currency":       str(data.get("currency", "INR")),
        "line_items":     list(data.get("line_items", [])),
        "detected_terms": list(data.get("detected_terms", [])),
        "source_type":    str(data.get("source_type", "json")),
    }


def _extract_field(text: str, pattern: str) -> str | None:
    m = re.search(pattern, text)
    if m:
        return m.group(len(m.groups()))
    return None


def _extract_amount(text: str) -> float | None:
    m = re.search(r"[₹$]?\s*([\d,]+\.?\d*)", text)
    if m:
        return float(m.group(1).replace(",", ""))
    return None
