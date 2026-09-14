"""Tool 1: extract_invoice_entities — Parse raw bill/statement/alert text or JSON into a structured object."""
import json
import re
from strands import tool

KNOWN_BANKS = [
    "IndusInd Bank", "HDFC Bank", "ICICI Bank", "SBI Card", "State Bank of India",
    "Axis Bank", "Kotak Mahindra Bank", "Kotak Bank", "Citibank", "American Express",
    "Amex", "Chase", "Yes Bank", "RBL Bank", "Standard Chartered", "HSBC", "Federal Bank",
    "Bank of Baroda", "Punjab National Bank", "Canara Bank", "IDFC First Bank"
]


@tool
def extract_invoice_entities(raw_content: str, source_type: str = "json") -> dict:
    """
    Parse a raw bill, monthly statement, bank notification, or JSON into a
    normalized invoice entity. Returns a structured dict with merchant_name,
    invoice_date, total_amount, line_items, currency, and detected_terms.

    Handles standard commercial invoices as well as Indian bank e-statements,
    card bills, and debit/credit/UPI transaction alerts.
    """
    # 1. Structured JSON input fast-path
    try:
        data = json.loads(raw_content)
        if isinstance(data, dict) and "merchant_name" in data and "total_amount" in data:
            return _normalize(data)
    except (json.JSONDecodeError, TypeError):
        pass

    # 2. Banking / Financial Alert & Statement Intelligence
    banking_data = _extract_banking_alert(raw_content)
    if banking_data:
        banking_data["source_type"] = source_type
        return _normalize(banking_data)

    # 3. Standard Commercial Invoice fallback (subscriptions, utilities, SaaS)
    merchant = _extract_field(raw_content, r"(?i)(?:merchant|from|biller|vendor)[:\s]+([^\n,]+)")
    amount = _extract_amount(raw_content)
    date = _extract_field(raw_content, r"(\d{4}-\d{2}-\d{2})")
    currency = "INR" if ("₹" in raw_content or "INR" in raw_content or "Rs" in raw_content) else "USD"

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



def parse_bank_statement_transactions(text: str) -> list[dict]:
    """
    Parse tabular bank statement text (such as IndusInd, HDFC, ICICI, SBI e-statements)
    containing DATE, PARTICULARS/MODE, DEPOSITS, WITHDRAWALS, BALANCE.
    Returns structured list of transactions.
    """
    tokens = re.split(r"(?=\b\d{2}[-/]\d{2}[-/]\d{4}\b)", text)
    transactions = []
    current_balance = None

    for block in tokens:
        block = block.strip()
        if not block:
            continue
        m = re.match(r"^(\d{2}[-/]\d{2}[-/]\d{4})\s*(.*)", block, re.DOTALL)
        if not m:
            continue
        date_str, rest = m.group(1), m.group(2).strip()

        # Handle opening balance / B/F
        if re.search(r"\bB/F\b", rest, re.IGNORECASE):
            bf_amt = re.search(r"B/F\s*([\d,]+\.?\d*)", rest, re.IGNORECASE)
            if bf_amt:
                try:
                    current_balance = float(bf_amt.group(1).replace(",", ""))
                except ValueError:
                    pass
            continue

        # Extract all numbers formatted as currency
        amounts = re.findall(r"[\d,]+\.\d{2}", rest)
        if not amounts:
            amounts = re.findall(r"[\d,]+", rest)

        # Particulars
        particulars = rest
        for a in amounts:
            particulars = particulars.replace(a, "")

        lines = [l.strip() for l in particulars.split("\n") if l.strip()]
        vendor = "Unknown"
        if lines:
            first = lines[0]
            if first.startswith("ACH/"):
                parts = first.split("/")
                vendor = parts[1] if len(parts) > 1 else first
            elif "ICICI DIRECT" in first:
                vendor = "ICICI DIRECT"
            elif first.startswith("UPI/"):
                upi_parts = first.split("/")
                vendor = upi_parts[1] if len(upi_parts) > 1 else first
            else:
                vendor = first

        num_vals = []
        for a in amounts:
            try:
                num_vals.append(float(a.replace(",", "")))
            except ValueError:
                pass

        spent = 0.0
        deposit = 0.0

        if len(num_vals) >= 2:
            txn_amt = num_vals[0]
            new_bal = num_vals[1]
            if current_balance is not None and round(current_balance + txn_amt, 2) == round(new_bal, 2):
                deposit = txn_amt
            else:
                spent = txn_amt
            current_balance = new_bal
        elif len(num_vals) == 1:
            txn_amt = num_vals[0]
            if any(x in rest.lower() for x in ["reimb", "salary", "credit", "cr/", "deposit"]):
                deposit = txn_amt
                if current_balance is not None:
                    current_balance += deposit
            else:
                spent = txn_amt
                if current_balance is not None:
                    current_balance -= spent

        transactions.append({
            "date": date_str,
            "vendor": vendor,
            "spent": spent,
            "deposit": deposit,
            "balance": current_balance,
        })

    return transactions


def _extract_banking_alert(text: str) -> dict | None:
    """
    Detect and extract entities from Indian bank transaction alerts,
    UPI debits, and monthly e-statement notifications.
    """
    text_lower = text.lower()
    is_banking = any(w in text_lower for w in [
        "debited", "credited", "statement", "bank account", "account no",
        "upi/", "total amount due", "minimum amount due", "card bill",
        "payment due", "e-statement", "transaction alert", "card ending"
    ])
    if not is_banking:
        return None

    # Detect Bank
    bank_name = None
    for b in KNOWN_BANKS:
        if b.lower() in text_lower:
            bank_name = b
            break
    if not bank_name:
        b_match = re.search(r"([A-Za-z0-9]+ Bank)", text)
        bank_name = b_match.group(1) if b_match else "Bank Alert"

    # Check for multi-transaction statement table
    multi_txns = parse_bank_statement_transactions(text)
    if len(multi_txns) > 1:
        total_spent = sum(t["spent"] for t in multi_txns)
        total_deposits = sum(t["deposit"] for t in multi_txns)
        latest_date = multi_txns[-1]["date"]
        if "-" in latest_date and len(latest_date.split("-")[0]) == 2:
            d_parts = latest_date.split("-")
            date_val = f"{d_parts[2]}-{d_parts[1]}-{d_parts[0]}"
        else:
            date_val = latest_date

        line_items = [
            {
                "name": f"{t['vendor']} ({t['date']})",
                "amount": t["spent"],
                "date": t["date"],
                "vendor": t["vendor"],
                "spent": t["spent"],
                "deposit": t["deposit"],
                "balance": t["balance"],
            }
            for t in multi_txns
        ]
        return {
            "merchant_name": f"{bank_name} Monthly Statement ({len(multi_txns)} Txns)",
            "invoice_date": date_val,
            "billing_period": f"{multi_txns[0]['date']} to {multi_txns[-1]['date']}",
            "total_amount": round(total_spent, 2),
            "currency": "INR",
            "line_items": line_items,
            "detected_terms": [
                f"{len(multi_txns)} Transactions Extracted",
                f"Total Debits: ₹{total_spent:,.2f}",
                f"Total Credits: ₹{total_deposits:,.2f}",
                "Confidential PII Masked",
            ],
        }


    # Detect Amount
    amt = None
    patterns = [
        r"(?i)(?:total amount due|total due|new balance|bill amount)[:\s]*(?:INR|Rs\.?|₹)?\s*([\d,]+\.?\d*)",
        r"(?i)(?:debited for|credited for|payment of|spent)[:\s]*(?:INR|Rs\.?|₹)?\s*([\d,]+\.?\d*)",
        r"(?i)(?:INR|Rs\.?|₹)\s*([\d,]+\.?\d*)\s*(?:has been debited|towards|debited|spent)",
        r"(?i)(?:INR|Rs\.?|₹)\s*([\d,]+\.?\d*)",
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            try:
                amt = float(m.group(1).replace(",", ""))
                break
            except ValueError:
                continue

    # Detect Payee / Beneficiary for UPI or Card transactions
    payee = None
    payee_m = re.search(r'(?i)towards\s+([^\n\r]+?)(?:\s+\.|\s*$)', text)
    if payee_m:
        raw_payee = payee_m.group(1).strip()
        if "upi/" in raw_payee.lower():
            parts = raw_payee.split("/")
            payee = parts[-1].strip() if len(parts) > 1 else raw_payee
        else:
            payee = raw_payee[:40]

    # Detect Date
    date_m = re.search(r"(\d{4}-\d{2}-\d{2})", text)
    date_val = date_m.group(1) if date_m else "2026-09-14"

    # Mask sensitive account numbers for zero-trust compliance
    acct_m = re.search(r"(?i)(?:account(?:\s+no\.?)?|card(?:\s+ending)?)\s*[:\s]*([0-9X\*]{4,20})", text)
    masked_acct = ""
    if acct_m:
        raw_num = acct_m.group(1)
        last4 = re.findall(r"\d", raw_num)
        masked_acct = f" ending in {"".join(last4[-4:])}" if len(last4) >= 4 else ""

    # Build merchant title
    if "statement" in text_lower or "due" in text_lower:
        merchant_label = f"{bank_name} Credit Card / Statement{masked_acct}"
    elif payee:
        merchant_label = f"{bank_name} — {payee}"
    else:
        merchant_label = f"{bank_name}{masked_acct}"

    line_items = []
    if payee and amt:
        line_items.append({"name": f"Payment to {payee}", "amount": amt})

    return {
        "merchant_name": merchant_label,
        "invoice_date": date_val,
        "billing_period": "",
        "total_amount": amt or 0.0,
        "currency": "INR",
        "line_items": line_items,
        "detected_terms": ["Banking Transaction / Statement", "Confidential PII Masked"],
    }


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
        try:
            return float(m.group(1).replace(",", ""))
        except ValueError:
            return None
    return None
