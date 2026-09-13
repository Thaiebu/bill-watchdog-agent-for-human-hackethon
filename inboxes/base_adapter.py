"""
Abstract Base Adapter for Email Inbox providers.

Design: Adapter Pattern
- EmailInboxAdapter defines the contract (interface)
- Concrete adapters (Mock, IMAP, OAuth2Gmail) implement it
- Tools and agent code depend ONLY on this abstract interface
- Swapping Gmail → Outlook → SAP/ERP requires zero changes to agent logic

Usage:
    adapter = MockEmailAdapter()           # Demo
    adapter = IMAPEmailAdapter(...)        # Real Gmail/any IMAP
    adapter = OAuth2GmailAdapter(...)      # Production OAuth2

    emails = adapter.list_billing_emails(max_count=15)
    body   = adapter.get_email_body(email_id)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class RawEmail:
    """Normalized email structure returned by all adapters."""
    id:        str
    subject:   str
    sender:    str
    date:      str          # ISO: YYYY-MM-DD
    snippet:   str          # First ~200 chars
    body_text: str          # Full plain-text body
    is_html:   bool = False


# Billing keyword filters applied by all adapters
BILLING_SUBJECT_KEYWORDS = [
    "invoice", "bill", "receipt", "statement", "payment due",
    "payment confirmation", "subscription", "renewal", "auto-renew",
    "charge", "debit", "your order", "purchase confirmation",
    "plan", "monthly summary", "account summary",
]

BILLING_SENDER_KEYWORDS = [
    "billing", "invoice", "noreply", "no-reply", "payments",
    "accounts", "finance", "support", "subscription",
]

EXCLUDE_KEYWORDS = [
    "unsubscribe", "newsletter", "promotional", "offer of the week",
    "marketing", "sale ends", "limited time",
]

# Bank-specific identifiers (domains, abbreviations, and keywords)
BANK_IDENTIFIERS = {
    "all_banks": [
        "bank", "card", "statement", "credit card", "debit card",
        "hdfc", "icici", "sbi", "axis", "kotak", "rbl", "indusind",
        "citi", "amex", "american express", "chase", "hsbc", "barclays"
    ],
    "hdfc": ["hdfc", "hdfcbank", "hdfc bank"],
    "icici": ["icici", "icicibank", "icici bank"],
    "sbi": ["sbi", "sbicard", "sbi card", "state bank of india"],
    "axis": ["axis", "axisbank", "axis bank"],
    "kotak": ["kotak", "kotakbank", "kotak mahindra"],
    "amex": ["amex", "american express", "americanexpress"],
    "chase": ["chase", "jpmorgan"],
}



def matches_bank_filter(subject: str, sender: str, bank_filter: str) -> bool:
    """Check if an email matches a bank/financial institution filter."""
    if not bank_filter or bank_filter == "all":
        return True
    
    text = f"{subject} {sender}".lower()
    filter_key = bank_filter.lower().strip()
    
    # Predefined bank list check
    if filter_key in BANK_IDENTIFIERS:
        return any(term in text for term in BANK_IDENTIFIERS[filter_key])
    
    # Custom bank name check
    return filter_key in text


def is_billing_email(subject: str, sender: str, bank_filter: str = None) -> bool:
    """
    Return True if an email is a billing notification, optionally filtered
    by a specific bank or all banks.
    """
    subject_lower = subject.lower()
    sender_lower  = sender.lower()

    # Exclude marketing noise first
    if any(kw in subject_lower for kw in EXCLUDE_KEYWORDS):
        return False

    # Check bank filter if requested
    if bank_filter and not matches_bank_filter(subject, sender, bank_filter):
        return False

    # Check subject keywords
    if any(kw in subject_lower for kw in BILLING_SUBJECT_KEYWORDS):
        return True

    # Check sender patterns
    if any(kw in sender_lower for kw in BILLING_SENDER_KEYWORDS):
        return True

    # Also detect bank statements directly as billing
    if any(term in subject_lower or term in sender_lower for term in BANK_IDENTIFIERS["all_banks"]):
        if any(term in subject_lower for term in ["statement", "due", "bill", "alert", "debit", "spent", "e-statement"]):
            return True

    return False


class EmailInboxAdapter(ABC):
    """
    Abstract base class for all email inbox providers.
    All concrete adapters MUST implement these two methods.
    """

    @abstractmethod
    def list_billing_emails(self, max_count: int = 15, bank_filter: str = None) -> List[RawEmail]:
        """
        Fetch and filter billing-related emails from the inbox.

        Args:
            max_count: Maximum number of billing emails to return (daily quota).

        Returns:
            List of RawEmail objects filtered to billing/financial emails only.
        """
        raise NotImplementedError

    @abstractmethod
    def get_email_body(self, email_id: str) -> Optional[str]:
        """
        Retrieve the full body text of a specific email by ID.

        Args:
            email_id: The unique identifier for the email.

        Returns:
            Full plain-text body of the email, or None if not found.
        """
        raise NotImplementedError

    def provider_name(self) -> str:
        """Human-readable name of this provider."""
        return self.__class__.__name__.replace("Adapter", "").replace("Email", "")


def get_adapter(provider: str, credentials: dict = None) -> EmailInboxAdapter:
    """
    Factory function: returns the correct adapter for a given provider string.
    This is the single point of change when adding new providers.

    Args:
        provider: One of "mock", "imap", "oauth2_gmail"
        credentials: Provider-specific auth dict (optional for mock)
    """
    from inboxes.mock_adapter import MockEmailAdapter
    from inboxes.imap_adapter import IMAPEmailAdapter
    from inboxes.oauth2_gmail_adapter import OAuth2GmailAdapter

    providers = {
        "mock":         lambda: MockEmailAdapter(),
        "imap":         lambda: IMAPEmailAdapter(**(credentials or {})),
        "oauth2_gmail": lambda: OAuth2GmailAdapter(**(credentials or {})),
    }

    if provider not in providers:
        raise ValueError(
            f"Unknown provider '{provider}'. Available: {list(providers.keys())}"
        )

    return providers[provider]()
