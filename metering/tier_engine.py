"""
SaaS Tier Engine — Enforces Free / Pro / Enterprise usage limits.
In production, tier is read from a user profile DB or Stripe subscription.
For demo, tier is set per session.
"""
from metering.usage_tracker import get_daily_email_count, init_usage_table

# Tier definitions
TIERS = {
    "free": {
        "display_name":       "Free",
        "daily_email_limit":  10,
        "monthly_anomaly_limit": 3,
        "monthly_dispute_limit": 1,
        "price_inr":          0,
        "price_usd":          0,
        "features": [
            "10 emails/day",
            "3 anomaly alerts/month",
            "1 dispute draft/month",
            "Mock inbox only",
        ],
    },
    "pro": {
        "display_name":       "Pro",
        "daily_email_limit":  50,
        "monthly_anomaly_limit": None,   # unlimited
        "monthly_dispute_limit": None,   # unlimited
        "price_inr":          299,
        "price_usd":          4,
        "features": [
            "50 emails/day",
            "Unlimited anomaly alerts",
            "Unlimited dispute drafts",
            "Gmail IMAP + OAuth2",
            "Budget intelligence",
            "Spending narratives",
        ],
    },
    "enterprise": {
        "display_name":       "Enterprise",
        "daily_email_limit":  None,      # unlimited
        "monthly_anomaly_limit": None,
        "monthly_dispute_limit": None,
        "price_inr":          None,
        "price_usd":          None,
        "features": [
            "Unlimited emails",
            "Unlimited alerts + disputes",
            "Multi-inbox support",
            "CRM integration",
            "Custom vendor rules",
            "Dedicated support",
        ],
    },
}

# In-memory user tier store (production: read from DB or Stripe)
_user_tiers: dict[str, str] = {}


def get_user_tier(user_id: str) -> str:
    """Return user's current tier. Defaults to 'free'."""
    return _user_tiers.get(user_id, "free")


def set_user_tier(user_id: str, tier: str):
    """Set user tier (called during onboarding or upgrade)."""
    if tier not in TIERS:
        raise ValueError(f"Unknown tier: {tier}. Valid: {list(TIERS.keys())}")
    _user_tiers[user_id] = tier


def get_tier_info(tier: str) -> dict:
    return TIERS.get(tier, TIERS["free"])


def check_email_quota(user_id: str, requested: int = 15) -> dict:
    """
    Check if user has email scan quota remaining today.
    Returns allowed count and a message if limit is hit.
    """
    init_usage_table()
    tier = get_user_tier(user_id)
    tier_info = TIERS[tier]
    daily_limit = tier_info["daily_email_limit"]

    # Enterprise: no limit
    if daily_limit is None:
        return {
            "allowed": True,
            "allowed_count": requested,
            "daily_limit": "Unlimited",
            "total_scanned_today": 0,
            "message": f"Enterprise: unlimited emails.",
        }

    scanned_today = get_daily_email_count(user_id)
    remaining = max(0, daily_limit - scanned_today)

    if remaining == 0:
        return {
            "allowed": False,
            "allowed_count": 0,
            "daily_limit": daily_limit,
            "total_scanned_today": scanned_today,
            "message": (
                f"Daily email limit reached ({daily_limit}/day on {tier_info['display_name']} tier). "
                f"Upgrade to Pro for 50 emails/day."
            ),
        }

    allowed = min(requested, remaining)
    return {
        "allowed": True,
        "allowed_count": allowed,
        "daily_limit": daily_limit,
        "total_scanned_today": scanned_today,
        "message": f"Quota OK: {remaining} emails remaining today ({tier_info['display_name']} tier).",
    }
