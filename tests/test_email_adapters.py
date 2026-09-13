"""
Tests for Email Adapter Layer (Adapter Pattern) and Tool 8.
Covers: MockAdapter, base adapter filter, factory, and fetch_billing_emails tool.
"""
import sys
import os
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from storage.db import init_db
from storage.seed_data import seed_all


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    init_db()
    seed_all()


# ── Base Adapter: Billing Filter ────────────────────────────────────────

class TestBillingFilter:
    def test_billing_subject_detected(self):
        from inboxes.base_adapter import is_billing_email
        assert is_billing_email("Your Netflix invoice for September", "billing@netflix.com") is True
        assert is_billing_email("Monthly payment receipt", "no-reply@jio.com") is True
        assert is_billing_email("Subscription renewal confirmation", "support@figma.com") is True

    def test_marketing_excluded(self):
        from inboxes.base_adapter import is_billing_email
        assert is_billing_email("Unsubscribe from our newsletter", "news@company.com") is False
        assert is_billing_email("This week's promotional offers", "deals@shop.com") is False

    def test_billing_sender_detected(self):
        from inboxes.base_adapter import is_billing_email
        assert is_billing_email("Your account summary", "billing@service.com") is True
        assert is_billing_email("Payment processed", "payments@vendor.io") is True


# ── MockEmailAdapter ────────────────────────────────────────────────────

class TestMockAdapter:
    def test_returns_billing_emails(self):
        from inboxes.mock_adapter import MockEmailAdapter
        adapter = MockEmailAdapter()
        emails = adapter.list_billing_emails(max_count=10)

        assert isinstance(emails, list)
        assert len(emails) > 0
        assert len(emails) <= 10

    def test_email_fields_present(self):
        from inboxes.mock_adapter import MockEmailAdapter
        adapter = MockEmailAdapter()
        emails = adapter.list_billing_emails(max_count=5)

        for email in emails:
            assert email.id
            assert email.subject
            assert email.sender
            assert email.date
            assert email.body_text

    def test_max_count_respected(self):
        from inboxes.mock_adapter import MockEmailAdapter
        adapter = MockEmailAdapter()
        emails_5  = adapter.list_billing_emails(max_count=5)
        emails_15 = adapter.list_billing_emails(max_count=15)

        assert len(emails_5) <= 5
        assert len(emails_15) <= 15
        assert len(emails_15) >= len(emails_5)

    def test_get_email_body(self):
        from inboxes.mock_adapter import MockEmailAdapter
        adapter = MockEmailAdapter()
        emails = adapter.list_billing_emails(max_count=3)
        email_id = emails[0].id

        body = adapter.get_email_body(email_id)
        assert body is not None
        assert len(body) > 10

    def test_unknown_email_id_returns_none(self):
        from inboxes.mock_adapter import MockEmailAdapter
        adapter = MockEmailAdapter()
        result = adapter.get_email_body("nonexistent-id-000")
        assert result is None

    def test_provider_name(self):
        from inboxes.mock_adapter import MockEmailAdapter
        adapter = MockEmailAdapter()
        assert "Mock" in adapter.provider_name()

    def test_includes_anomaly_emails(self):
        """Ensure mock data includes known anomaly bills (Jio + Figma)."""
        from inboxes.mock_adapter import MockEmailAdapter
        adapter = MockEmailAdapter()
        emails = adapter.list_billing_emails(max_count=20)
        subjects = " ".join(e.subject for e in emails)
        # At least one of the anomaly vendors should appear
        assert any(vendor in subjects for vendor in ["Jio", "Figma", "Notion", "Intercom"])


# ── Adapter Factory ─────────────────────────────────────────────────────

class TestAdapterFactory:
    def test_mock_factory(self):
        from inboxes.base_adapter import get_adapter
        adapter = get_adapter("mock")
        assert adapter is not None
        emails = adapter.list_billing_emails(max_count=3)
        assert len(emails) > 0

    def test_unknown_provider_raises(self):
        from inboxes.base_adapter import get_adapter
        with pytest.raises(ValueError, match="Unknown provider"):
            get_adapter("nonexistent_provider")

    def test_interface_compliance(self):
        """All adapters returned by factory must implement the ABC."""
        from inboxes.base_adapter import get_adapter, EmailInboxAdapter
        mock = get_adapter("mock")
        assert isinstance(mock, EmailInboxAdapter)
        assert hasattr(mock, "list_billing_emails")
        assert hasattr(mock, "get_email_body")
        assert hasattr(mock, "provider_name")


# ── Tool 8: fetch_billing_emails ────────────────────────────────────────

class TestEmailTool:
    def test_mock_provider_returns_results(self):
        from tools.email_tool import fetch_billing_emails
        from metering.tier_engine import set_user_tier
        set_user_tier("user_test_email", "enterprise")  # Use pro to avoid quota issues in test

        result = fetch_billing_emails(
            user_id="user_test_email",
            provider="mock",
            max_count=10,
        )

        assert "provider" in result
        assert "billing_emails_found" in result
        assert "emails" in result
        assert result["billing_emails_found"] > 0
        assert isinstance(result["emails"], list)

    def test_each_email_has_invoice(self):
        from tools.email_tool import fetch_billing_emails
        from metering.tier_engine import set_user_tier
        set_user_tier("user_test_inv", "enterprise")

        result = fetch_billing_emails(
            user_id="user_test_inv",
            provider="mock",
            max_count=5,
        )

        for email in result["emails"]:
            assert "email_id"   in email
            assert "subject"    in email
            assert "invoice"    in email or "parse_error" in email

    def test_free_tier_quota_enforcement(self):
        from tools.email_tool import fetch_billing_emails
        from metering.usage_tracker import track_event
        from metering.tier_engine import set_user_tier

        # Simulate user who already hit their daily quota
        test_user = "quota_test_user"
        set_user_tier(test_user, "free")

        # Pre-fill their daily usage to exceed the limit
        for _ in range(15):
            track_event(test_user, "email_scanned", {"provider": "mock", "count": 1})

        result = fetch_billing_emails(
            user_id=test_user,
            provider="mock",
            max_count=10,
        )

        # Should be blocked
        assert result["quota_exceeded"] is True
        assert result["billing_emails_found"] == 0
        assert "Upgrade" in result["message"]
