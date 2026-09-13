"""
Unit tests for BillWatchdog Strands tools.
Tests each @tool function independently with mock/synthetic data.
"""
import sys
import os
import json
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from storage.db import init_db
from storage.seed_data import seed_all


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    """Initialize and seed DB once for all tests."""
    init_db()
    seed_all()


# ── Tool 1: extract_invoice_entities ────────────────────────────────────

class TestExtractInvoice:
    def test_json_input(self):
        from tools.extractor_tool import extract_invoice_entities

        raw = json.dumps({
            "merchant_name": "Netflix",
            "invoice_date": "2026-09-02",
            "total_amount": 649,
            "currency": "INR",
            "line_items": [{"name": "Standard Plan", "amount": 649}],
            "detected_terms": [],
        })
        result = extract_invoice_entities(raw_content=raw, source_type="json")

        assert result["merchant_name"] == "Netflix"
        assert result["total_amount"] == 649.0
        assert result["currency"] == "INR"
        assert isinstance(result["line_items"], list)

    def test_missing_fields(self):
        from tools.extractor_tool import extract_invoice_entities

        raw = json.dumps({"merchant_name": "Test", "total_amount": 100})
        result = extract_invoice_entities(raw_content=raw, source_type="json")

        assert result["merchant_name"] == "Test"
        assert result["total_amount"] == 100.0
        assert result["currency"] == "INR"  # default


# ── Tool 2: query_billing_baseline ──────────────────────────────────────

class TestBillingBaseline:
    def test_known_vendor(self):
        from tools.baseline_tool import query_billing_baseline

        result = query_billing_baseline(user_id="user_1", merchant_name="Netflix")
        assert result["has_history"] is True
        assert result["average_monthly_spend"] == 649
        assert result["merchant_name"] == "Netflix"

    def test_unknown_vendor(self):
        from tools.baseline_tool import query_billing_baseline

        result = query_billing_baseline(user_id="user_1", merchant_name="NonExistentCorp")
        assert result["has_history"] is False
        assert result["average_monthly_spend"] is None


# ── Tool 3: detect_bill_anomalies ───────────────────────────────────────

class TestDetectAnomalies:
    def test_normal_bill(self):
        from tools.anomaly_tool import detect_bill_anomalies

        invoice = {"merchant_name": "Netflix", "total_amount": 649, "detected_terms": []}
        baseline = {"merchant_name": "Netflix", "average_monthly_spend": 649,
                     "has_history": True, "promotions": []}

        result = detect_bill_anomalies(current_invoice=invoice, baseline_data=baseline)
        assert result["is_anomaly"] is False
        assert result["severity"] == "SILENT"

    def test_price_hike(self):
        from tools.anomaly_tool import detect_bill_anomalies

        invoice = {"merchant_name": "Figma", "total_amount": 1999,
                    "detected_terms": ["New Pricing"]}
        baseline = {"merchant_name": "Figma", "average_monthly_spend": 1499,
                     "has_history": True, "promotions": []}

        result = detect_bill_anomalies(current_invoice=invoice, baseline_data=baseline)
        assert result["is_anomaly"] is True
        assert result["delta_amount"] == 500
        assert result["severity"] == "ACTION_REQUIRED"

    def test_promo_expiry(self):
        from tools.anomaly_tool import detect_bill_anomalies

        invoice = {"merchant_name": "Jio Fiber", "total_amount": 1499,
                    "detected_terms": ["Promotional Discount Expired"]}
        baseline = {"merchant_name": "Jio Fiber", "average_monthly_spend": 999,
                     "has_history": True,
                     "promotions": [{"name": "6-Month Offer", "discount": 500,
                                     "expiry_date": "2026-09-01"}]}

        result = detect_bill_anomalies(current_invoice=invoice, baseline_data=baseline)
        assert result["is_anomaly"] is True
        assert result["anomaly_type"] == "PROMOTION_EXPIRATION"
        assert result["severity"] == "ACTION_REQUIRED"

    def test_seasonal_utility_within_range(self):
        from tools.anomaly_tool import detect_bill_anomalies

        invoice = {"merchant_name": "BESCOM Electricity", "total_amount": 2850,
                    "detected_terms": []}
        baseline = {"merchant_name": "BESCOM Electricity", "average_monthly_spend": 2750,
                     "has_history": True, "promotions": []}

        result = detect_bill_anomalies(current_invoice=invoice, baseline_data=baseline)
        assert result["is_anomaly"] is False
        assert result["severity"] == "SILENT"


# ── Tool 4: evaluate_budget_impact ──────────────────────────────────────

class TestBudgetImpact:
    def test_budget_calculation(self):
        from tools.budget_tool import evaluate_budget_impact

        invoice = {"merchant_name": "Netflix", "total_amount": 649}
        anomaly = {"is_anomaly": False, "anomaly_type": "NORMAL"}

        result = evaluate_budget_impact(user_id="user_1", current_invoice=invoice, anomaly=anomaly)
        assert "monthly_budget" in result
        assert "safe_to_spend" in result
        assert "budget_status" in result
        assert result["monthly_budget"] == 50000


# ── Tool 5: draft_dispute_packet ────────────────────────────────────────

class TestDisputeDraft:
    def test_promo_dispute(self):
        from tools.dispute_tool import draft_dispute_packet

        anomaly = {
            "delta_amount": 500,
            "delta_percentage": 50,
            "anomaly_type": "PROMOTION_EXPIRATION",
            "root_cause_explanation": "6-month promo expired",
        }
        result = draft_dispute_packet(
            merchant_name="Jio Fiber",
            anomaly=anomaly,
            account_info={"account_id": "JF-9283", "months_as_customer": 18,
                          "payment_record": "excellent"},
        )

        assert "email_subject" in result
        assert "email_body" in result
        assert "Jio Fiber" in result["email_body"]
        assert "18 months" in result["email_body"]
        assert result["suggested_action"] == "Send Email"

    def test_stealth_hike_dispute(self):
        from tools.dispute_tool import draft_dispute_packet

        anomaly = {
            "delta_amount": 500,
            "delta_percentage": 33.3,
            "anomaly_type": "STEALTH_PRICE_HIKE",
            "root_cause_explanation": "Unannounced pricing change",
        }
        result = draft_dispute_packet(
            merchant_name="Figma",
            anomaly=anomaly,
            account_info={"account_id": "FIG-001"},
        )

        assert "Unexpected Increase" in result["email_subject"]
        assert "email_body" in result


# ── Tool 6: schedule_renewal_deadline ───────────────────────────────────

class TestScheduler:
    def test_schedule_reminder(self):
        from tools.scheduler_tool import schedule_renewal_deadline

        result = schedule_renewal_deadline(
            user_id="user_1",
            merchant_name="Netflix",
            alert_date="2026-10-15",
            action_type="REVIEW",
            notes="Check if price reverted",
        )

        assert result["status"] == "scheduled"
        assert result["trigger_date"] == "2026-10-15"
        assert "rem-" in result["reminder_id"]


# ── Tool 7: explain_spending_narrative ──────────────────────────────────

class TestNarrative:
    def test_narrative_returns_text(self):
        from tools.narrative_tool import explain_spending_narrative

        result = explain_spending_narrative(
            user_id="user_1",
            user_query="What changed most this month?",
        )
        assert isinstance(result, str)
        assert len(result) > 10
