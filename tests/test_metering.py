"""
Tests for the Per-User Usage Tracking and SaaS Tier Engine.
"""
import sys
import os
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from storage.db import init_db


@pytest.fixture(scope="session", autouse=True)
def setup():
    init_db()
    from metering.usage_tracker import init_usage_table
    init_usage_table()


# ── Usage Tracker ────────────────────────────────────────────────────────

class TestUsageTracker:
    def test_track_and_retrieve_event(self):
        from metering.usage_tracker import track_event, get_usage_today

        user = "tracker_test_user_1"
        track_event(user, "bill_extracted", {"merchant": "Netflix", "amount": 649})
        track_event(user, "bill_extracted", {"merchant": "Spotify", "amount": 119})

        today = get_usage_today(user)
        assert "bill_extracted" in today
        assert today["bill_extracted"]["count"] >= 2

    def test_multiple_event_types(self):
        from metering.usage_tracker import track_event, get_usage_today

        user = "tracker_test_user_2"
        track_event(user, "email_scanned",    {"provider": "mock", "count": 5})
        track_event(user, "anomaly_detected", {"anomaly_type": "STEALTH_PRICE_HIKE"})
        track_event(user, "dispute_drafted",  {"merchant": "Figma"})
        track_event(user, "bedrock_call",     {}, input_tokens=500, output_tokens=250)

        today = get_usage_today(user)
        assert "anomaly_detected" in today
        assert "dispute_drafted"  in today
        assert "bedrock_call"     in today

    def test_monthly_totals(self):
        from metering.usage_tracker import track_event, get_usage_this_month

        user = "tracker_test_user_3"
        track_event(user, "bedrock_call", {}, input_tokens=1000, output_tokens=500)

        month = get_usage_this_month(user)
        assert "bedrock_call" in month
        assert month["bedrock_call"]["total_input"] >= 1000

    def test_daily_email_count(self):
        from metering.usage_tracker import track_event, get_daily_email_count

        user = "tracker_email_count_user"
        track_event(user, "email_scanned", {"provider": "mock", "count": 7})
        track_event(user, "email_scanned", {"provider": "mock", "count": 3})

        count = get_daily_email_count(user)
        assert count >= 10

    def test_token_totals(self):
        from metering.usage_tracker import track_event, get_monthly_token_totals

        user = "tracker_token_user"
        track_event(user, "bedrock_call", {}, input_tokens=2000, output_tokens=800)
        track_event(user, "bedrock_call", {}, input_tokens=1500, output_tokens=600)

        totals = get_monthly_token_totals(user)
        assert totals["input_tokens"]  >= 3500
        assert totals["output_tokens"] >= 1400


# ── Tier Engine ──────────────────────────────────────────────────────────

class TestTierEngine:
    def test_default_tier_is_free(self):
        from metering.tier_engine import get_user_tier
        assert get_user_tier("brand_new_user_xyz") == "free"

    def test_set_and_get_tier(self):
        from metering.tier_engine import set_user_tier, get_user_tier
        set_user_tier("tier_test_user", "pro")
        assert get_user_tier("tier_test_user") == "pro"

        set_user_tier("tier_test_user", "enterprise")
        assert get_user_tier("tier_test_user") == "enterprise"

    def test_invalid_tier_raises(self):
        from metering.tier_engine import set_user_tier
        with pytest.raises(ValueError, match="Unknown tier"):
            set_user_tier("user_x", "platinum")

    def test_free_quota_allows_up_to_limit(self):
        from metering.tier_engine import check_email_quota, set_user_tier

        user = "free_quota_fresh_user"
        set_user_tier(user, "free")
        result = check_email_quota(user, requested=5)

        assert result["allowed"] is True
        assert result["allowed_count"] <= 5
        assert result["daily_limit"] == 10

    def test_enterprise_has_no_limit(self):
        from metering.tier_engine import check_email_quota, set_user_tier

        user = "enterprise_test_user"
        set_user_tier(user, "enterprise")
        result = check_email_quota(user, requested=500)

        assert result["allowed"] is True
        assert result["daily_limit"] == "Unlimited"

    def test_pro_tier_limit_is_50(self):
        from metering.tier_engine import get_tier_info
        tier = get_tier_info("pro")
        assert tier["daily_email_limit"] == 50
        assert tier["monthly_anomaly_limit"] is None  # unlimited

    def test_all_tiers_have_required_fields(self):
        from metering.tier_engine import TIERS
        required = ["display_name", "daily_email_limit", "monthly_anomaly_limit",
                    "monthly_dispute_limit", "features"]
        for tier_name, tier_data in TIERS.items():
            for field in required:
                assert field in tier_data, f"Tier '{tier_name}' missing field '{field}'"


# ── Cost Estimator ────────────────────────────────────────────────────────

class TestCostEstimator:
    def test_returns_all_fields(self):
        from metering.cost_estimator import estimate_monthly_cost
        result = estimate_monthly_cost("cost_test_user_1")

        required = ["input_tokens", "output_tokens", "total_cost_usd",
                    "total_cost_inr", "bedrock_cost_usd", "breakdown"]
        for field in required:
            assert field in result, f"Missing field: {field}"

    def test_zero_usage_means_zero_cost(self):
        from metering.cost_estimator import estimate_monthly_cost
        result = estimate_monthly_cost("zero_usage_user_xyz")
        assert result["total_cost_usd"] == 0.0
        assert result["total_cost_inr"] == 0.0

    def test_cost_increases_with_tokens(self):
        from metering.usage_tracker import track_event
        from metering.cost_estimator import estimate_monthly_cost

        user = "cost_increase_user"
        baseline = estimate_monthly_cost(user)

        track_event(user, "bedrock_call", {}, input_tokens=10000, output_tokens=5000)
        after = estimate_monthly_cost(user)

        assert after["total_cost_usd"] > baseline["total_cost_usd"]
        assert after["input_tokens"] >= 10000
