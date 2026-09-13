"""
Seed data for BillWatchdog demo.
Loads realistic Indian vendor bills, baselines, and budget limits into SQLite.

Vendors covered (12 baselines):
  Subscriptions : Netflix, Spotify, Amazon Prime, Google One, Hotstar, Notion, Slack
  Internet      : Jio Fiber, Airtel Broadband
  Utilities     : BESCOM Electricity, BWSSB Water
  Insurance     : LIC Insurance
  SaaS/Work     : Figma, GitHub, Zoom

Demo Bills (10 bills — 5 SILENT, 5 ACTION_REQUIRED):
  SILENT  : Netflix (normal), BESCOM (seasonal OK), Spotify (normal),
            Amazon Prime (normal), Google One (normal)
  ACTION  : Figma (price hike +33%), Jio Fiber (promo cliff +50%),
            Hotstar (annual auto-renewal surprise), Airtel (hidden fee added),
            Slack (seat count increase unnoticed)
"""
from datetime import datetime, timedelta
from storage.db import init_db, insert_bill, upsert_baseline, upsert_budget_limit

USER_ID = "user_1"


def seed_all():
    init_db()
    _seed_budget_limits()
    _seed_baselines()
    _seed_historical_bills()
    print("✅ Seed data loaded successfully.")


def _seed_budget_limits():
    limits = {
        "total":          50000,
        "subscriptions":   5000,
        "utilities":       8000,
        "internet":        3000,
        "insurance":      10000,
        "shopping":       10000,
        "saas_work":       8000,
        "other":           5000,
    }
    for category, amount in limits.items():
        upsert_budget_limit(USER_ID, category, amount)


def _seed_baselines():
    baselines = [
        # ── Subscriptions ───────────────────────────────────────────────────
        {
            "merchant_name": "Netflix",
            "average_monthly_spend": 649,
            "last_month_amount": 649,
            "promotions": [],
        },
        {
            "merchant_name": "Spotify",
            "average_monthly_spend": 119,
            "last_month_amount": 119,
            "promotions": [],
        },
        {
            "merchant_name": "Amazon Prime",
            "average_monthly_spend": 179,
            "last_month_amount": 179,
            "promotions": [],
        },
        {
            "merchant_name": "Google One",
            "average_monthly_spend": 130,
            "last_month_amount": 130,
            "promotions": [],
        },
        {
            "merchant_name": "Hotstar",
            "average_monthly_spend": 299,
            "last_month_amount": 0,          # Annual plan — billed yearly
            "promotions": [],
        },
        {
            "merchant_name": "Notion",
            "average_monthly_spend": 400,
            "last_month_amount": 400,
            "promotions": [],
        },
        # ── Internet ────────────────────────────────────────────────────────
        {
            "merchant_name": "Jio Fiber",
            "average_monthly_spend": 999,
            "last_month_amount": 999,
            "promotions": [
                {
                    "name": "6-Month New Customer Offer",
                    "discount": 500,
                    "expiry_date": "2026-09-01",
                }
            ],
        },
        {
            "merchant_name": "Airtel Broadband",
            "average_monthly_spend": 799,
            "last_month_amount": 799,
            "promotions": [],
        },
        # ── Utilities ───────────────────────────────────────────────────────
        {
            "merchant_name": "BESCOM Electricity",
            "average_monthly_spend": 2750,
            "last_month_amount": 2600,
            "promotions": [],
        },
        {
            "merchant_name": "BWSSB Water",
            "average_monthly_spend": 420,
            "last_month_amount": 400,
            "promotions": [],
        },
        # ── Insurance ───────────────────────────────────────────────────────
        {
            "merchant_name": "LIC Insurance",
            "average_monthly_spend": 8500,
            "last_month_amount": 8500,
            "promotions": [],
        },
        # ── SaaS / Work ─────────────────────────────────────────────────────
        {
            "merchant_name": "Figma",
            "average_monthly_spend": 1499,
            "last_month_amount": 1499,
            "promotions": [],
        },
        {
            "merchant_name": "GitHub",
            "average_monthly_spend": 830,
            "last_month_amount": 830,
            "promotions": [],
        },
        {
            "merchant_name": "Slack",
            "average_monthly_spend": 2400,
            "last_month_amount": 2400,
            "promotions": [],
        },
        {
            "merchant_name": "Zoom",
            "average_monthly_spend": 1350,
            "last_month_amount": 1350,
            "promotions": [],
        },
    ]
    for b in baselines:
        b["user_id"] = USER_ID
        b["baseline_months"] = 6
        upsert_baseline(b)


def _seed_historical_bills():
    """Insert 3 months of realistic historical bills for 12 vendors."""
    now = datetime.now()

    def months_ago(n):
        d = now - timedelta(days=30 * n)
        return d.strftime("%Y-%m-05")

    # (merchant_name, amount_3mo_ago, amount_2mo_ago, amount_1mo_ago)
    history = [
        # Subscriptions
        ("Netflix",            649,   649,   649),
        ("Spotify",            119,   119,   119),
        ("Amazon Prime",       179,   179,   179),
        ("Google One",         130,   130,   130),
        ("Notion",             400,   400,   400),
        # Internet
        ("Jio Fiber",          999,   999,   999),
        ("Airtel Broadband",   799,   799,   799),
        # Utilities  (seasonal variation is normal — ±20%)
        ("BESCOM Electricity", 2400,  2600,  2750),
        ("BWSSB Water",        390,   400,   420),
        # Insurance
        ("LIC Insurance",      8500,  8500,  8500),
        # SaaS
        ("Figma",              1499,  1499,  1499),
        ("GitHub",             830,   830,   830),
        ("Slack",              2400,  2400,  2400),
        ("Zoom",               1350,  1350,  1350),
    ]

    for merchant, amt3, amt2, amt1 in history:
        for n, amount in [(3, amt3), (2, amt2), (1, amt1)]:
            insert_bill({
                "user_id":       USER_ID,
                "merchant_name": merchant,
                "invoice_date":  months_ago(n),
                "total_amount":  amount,
                "currency":      "INR",
                "silent":        1,
            })


# ── Demo bill payloads (used by Streamlit UI and smoke tests) ──────────────
# 5 SILENT + 5 ACTION_REQUIRED = 10 bills total

DEMO_BILLS = [
    # ── SILENT bills (normal / within baseline) ───────────────────────────
    {
        "id": 1,
        "label": "🟢 Bill 1: Netflix (Normal — ₹649)",
        "raw": {
            "merchant_name": "Netflix",
            "invoice_date":  datetime.now().strftime("%Y-%m-02"),
            "billing_period": "Sep 1 – Sep 30, 2026",
            "total_amount":  649,
            "currency":      "INR",
            "line_items":    [{"name": "Standard Plan HD", "amount": 649}],
            "detected_terms": [],
        },
        "expected": "SILENT",
    },
    {
        "id": 2,
        "label": "🟢 Bill 2: BESCOM Electricity (Seasonal OK — ₹2,850)",
        "raw": {
            "merchant_name": "BESCOM Electricity",
            "invoice_date":  datetime.now().strftime("%Y-%m-03"),
            "billing_period": "Aug 1 – Aug 31, 2026",
            "total_amount":  2850,
            "currency":      "INR",
            "line_items":    [
                {"name": "Energy Charges", "amount": 2600},
                {"name": "Fixed Charges",  "amount": 250},
            ],
            "detected_terms": [],
        },
        "expected": "SILENT",
    },
    {
        "id": 3,
        "label": "🟢 Bill 3: Spotify (Normal — ₹119)",
        "raw": {
            "merchant_name": "Spotify",
            "invoice_date":  datetime.now().strftime("%Y-%m-04"),
            "billing_period": "Sep 1 – Sep 30, 2026",
            "total_amount":  119,
            "currency":      "INR",
            "line_items":    [{"name": "Individual Plan", "amount": 119}],
            "detected_terms": [],
        },
        "expected": "SILENT",
    },
    {
        "id": 4,
        "label": "🟢 Bill 4: Airtel Broadband (Normal — ₹799)",
        "raw": {
            "merchant_name": "Airtel Broadband",
            "invoice_date":  datetime.now().strftime("%Y-%m-05"),
            "billing_period": "Sep 1 – Sep 30, 2026",
            "total_amount":  799,
            "currency":      "INR",
            "line_items":    [{"name": "Home 100 Mbps Plan", "amount": 799}],
            "detected_terms": [],
        },
        "expected": "SILENT",
    },
    {
        "id": 5,
        "label": "🟢 Bill 5: GitHub (Normal — ₹830)",
        "raw": {
            "merchant_name": "GitHub",
            "invoice_date":  datetime.now().strftime("%Y-%m-05"),
            "billing_period": "Sep 1 – Sep 30, 2026",
            "total_amount":  830,
            "currency":      "INR",
            "line_items":    [{"name": "GitHub Team Plan (1 seat)", "amount": 830}],
            "detected_terms": [],
        },
        "expected": "SILENT",
    },
    # ── ACTION_REQUIRED bills (anomalies / traps) ─────────────────────────
    {
        "id": 6,
        "label": "🔴 Bill 6: Figma (Stealth Price Hike +33% — ₹1,999)",
        "raw": {
            "merchant_name": "Figma",
            "invoice_date":  datetime.now().strftime("%Y-%m-06"),
            "billing_period": "Sep 1 – Sep 30, 2026",
            "total_amount":  1999,
            "currency":      "INR",
            "line_items":    [{"name": "Figma Professional Plan", "amount": 1999}],
            "detected_terms": ["New Pricing Effective Sep 2026"],
        },
        "expected": "ACTION_REQUIRED",
    },
    {
        "id": 7,
        "label": "🔴 Bill 7: Jio Fiber (Promo Expired — ₹1,499 was ₹999)",
        "raw": {
            "merchant_name": "Jio Fiber",
            "invoice_date":  datetime.now().strftime("%Y-%m-07"),
            "billing_period": "Sep 1 – Sep 30, 2026",
            "total_amount":  1499,
            "currency":      "INR",
            "line_items":    [
                {"name": "Gold Plan 150 Mbps",  "amount": 999},
                {"name": "OTT Add-on Bundle",   "amount": 300},
                {"name": "Router Rental",        "amount": 200},
            ],
            "detected_terms": ["Promotional Discount Expired", "AutoPay Enrolled"],
        },
        "expected": "ACTION_REQUIRED",
    },
    {
        "id": 8,
        "label": "🔴 Bill 8: Hotstar (Annual Auto-Renewal Surprise — ₹1,499)",
        "raw": {
            "merchant_name": "Hotstar",
            "invoice_date":  datetime.now().strftime("%Y-%m-08"),
            "billing_period": "Sep 2026 – Sep 2027 (Annual)",
            "total_amount":  1499,
            "currency":      "INR",
            "line_items":    [{"name": "Disney+ Hotstar Super Annual", "amount": 1499}],
            "detected_terms": ["Annual Auto-Renewal", "Non-Refundable"],
        },
        "expected": "ACTION_REQUIRED",
    },
    {
        "id": 9,
        "label": "🔴 Bill 9: Airtel (Hidden Fee Added — ₹1,099 was ₹799)",
        "raw": {
            "merchant_name": "Airtel Broadband",
            "invoice_date":  datetime.now().strftime("%Y-%m-09"),
            "billing_period": "Sep 1 – Sep 30, 2026",
            "total_amount":  1099,
            "currency":      "INR",
            "line_items":    [
                {"name": "Home 100 Mbps Plan",       "amount": 799},
                {"name": "Static IP Add-on",          "amount": 200},
                {"name": "Infrastructure Surcharge",  "amount": 100},
            ],
            "detected_terms": ["Infrastructure Surcharge — New Fee", "Static IP Added"],
        },
        "expected": "ACTION_REQUIRED",
    },
    {
        "id": 10,
        "label": "🔴 Bill 10: Slack (Seat Count Crept Up — ₹3,600 was ₹2,400)",
        "raw": {
            "merchant_name": "Slack",
            "invoice_date":  datetime.now().strftime("%Y-%m-10"),
            "billing_period": "Sep 1 – Sep 30, 2026",
            "total_amount":  3600,
            "currency":      "INR",
            "line_items":    [
                {"name": "Slack Pro — 12 seats × ₹300", "amount": 3600},
            ],
            "detected_terms": ["Seat count increased from 8 to 12"],
        },
        "expected": "ACTION_REQUIRED",
    },
]
