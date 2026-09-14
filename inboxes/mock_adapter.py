
def _generate_mock_statement_pdf(password: str = "IN1995") -> bytes:
    """Generate a realistic in-memory encrypted bank statement PDF for demo."""
    import io
    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, NameObject, DictionaryObject

    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)

    text_stream = b"""BT
/F1 12 Tf
72 712 Td
(INDUSIND BANK MONTHLY E-STATEMENT) Tj
0 -24 Td
(Statement Date: 2026-09-14) Tj
0 -18 Td
(Account No: 15XXXXXX6528) Tj
0 -24 Td
(Total Amount Due: INR 14,250.00) Tj
0 -18 Td
(Payment Due Date: 2026-09-28) Tj
0 -18 Td
(Minimum Amount Due: INR 1,200.00) Tj
0 -24 Td
(Summary of Charges:) Tj
0 -18 Td
(1. Groceries & Dining: INR 6,250.00) Tj
0 -18 Td
(2. Fuel & Commute: INR 8,000.00) Tj
ET"""

    stream_obj = DecodedStreamObject()
    stream_obj.set_data(text_stream)
    page[NameObject('/Contents')] = stream_obj

    font_dict = DictionaryObject({
        NameObject('/Type'): NameObject('/Font'),
        NameObject('/Subtype'): NameObject('/Type1'),
        NameObject('/BaseFont'): NameObject('/Helvetica'),
    })
    page[NameObject('/Resources')] = DictionaryObject({
        NameObject('/Font'): DictionaryObject({NameObject('/F1'): font_dict})
    })

    writer.encrypt(password)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()

"""
MockEmailAdapter — Pre-loaded synthetic billing emails for demo/testing.
No auth required. Covers individuals, startups, and SaaS companies.
"""
from datetime import datetime, timedelta
from typing import List, Optional
from inboxes.base_adapter import EmailInboxAdapter, RawEmail, is_billing_email


def _days_ago(n: int) -> str:
    return (datetime.now() - timedelta(days=n)).strftime("%Y-%m-%d")


# 20 realistic synthetic billing emails
MOCK_EMAILS = [
    # ── NORMAL bills (should be SILENT) ────────────────────────────────────
    RawEmail(
        id="mock-001",
        subject="Your Netflix subscription receipt - September 2026",
        sender="billing@netflix.com",
        date=_days_ago(1),
        snippet="Amount charged: ₹649.00 to your saved payment method.",
        body_text="""Dear Customer,
Your Netflix subscription has been renewed.
Merchant: Netflix
Invoice Date: {date}
Billing Period: September 1 – September 30, 2026
Plan: Standard HD
Total Amount: ₹649.00
Currency: INR
Payment Method: Credit Card ending in 4242
Thank you for being a Netflix member.""".format(date=_days_ago(1)),
    ),
    RawEmail(
        id="mock-002",
        subject="Spotify Premium - Payment Confirmation",
        sender="no-reply@spotify.com",
        date=_days_ago(2),
        snippet="Your Spotify Premium subscription payment of ₹119 was successful.",
        body_text="""Hi there,
Your Spotify Premium subscription has been renewed.
Merchant: Spotify
Invoice Date: {date}
Billing Period: Sep 2026
Plan: Individual Premium
Total Amount: ₹119.00
Currency: INR
This is an automated message.""".format(date=_days_ago(2)),
    ),
    RawEmail(
        id="mock-003",
        subject="Your BESCOM electricity bill for August 2026",
        sender="billing@bescom.co.in",
        date=_days_ago(3),
        snippet="Electricity bill for consumer 0882345: ₹2,850.00 due by Sep 20.",
        body_text="""BESCOM Monthly Bill
Merchant: BESCOM Electricity
Invoice Date: {date}
Billing Period: August 1 - August 31, 2026
Consumer No: 0882345
Line Items:
  Energy Charges: ₹2600.00
  Fixed Charges: ₹250.00
Total Amount: ₹2850.00
Currency: INR
Due Date: September 20, 2026""".format(date=_days_ago(3)),
    ),
    RawEmail(
        id="mock-004",
        subject="Amazon Prime - Membership renewal confirmed",
        sender="auto-confirm@amazon.in",
        date=_days_ago(4),
        snippet="Your Prime membership has been renewed for ₹179.",
        body_text="""Your Amazon Prime Membership
Merchant: Amazon Prime
Invoice Date: {date}
Plan: Prime Monthly
Total Amount: ₹179.00
Currency: INR
Benefits: Free delivery, Prime Video, Prime Music
Next billing date: {next_date}""".format(date=_days_ago(4), next_date=_days_ago(-30)),
    ),
    RawEmail(
        id="mock-005",
        subject="Google One storage plan - Monthly receipt",
        sender="payments-noreply@google.com",
        date=_days_ago(5),
        snippet="₹130 charged for your Google One 100GB plan.",
        body_text="""Google One Subscription Receipt
Merchant: Google One
Invoice Date: {date}
Plan: 100 GB Storage
Total Amount: ₹130.00
Currency: INR
Billing Period: Sep 1 - Sep 30, 2026""".format(date=_days_ago(5)),
    ),

    # ── ANOMALY bills (should trigger ACTION REQUIRED) ─────────────────────
    RawEmail(
        id="mock-006",
        subject="Your Jio Fiber bill - September 2026 [Action Required]",
        sender="billing@jio.com",
        date=_days_ago(1),
        snippet="Your bill has changed. Total due: ₹1,499.00. Previous: ₹999.00.",
        body_text="""Dear Jio Fiber Customer,
Your September 2026 bill is now available.
Merchant: Jio Fiber
Invoice Date: {date}
Billing Period: September 1 - September 30, 2026
Line Items:
  Gold Plan 150 Mbps: ₹999.00
  OTT Add-on Bundle: ₹300.00
  Router Rental: ₹200.00
Total Amount: ₹1499.00
Currency: INR
Note: Promotional Discount Expired. AutoPay Enrolled.
Detected Terms: Promotional Discount Expired, AutoPay Enrolled
Previous Month: ₹999.00""".format(date=_days_ago(1)),
    ),
    RawEmail(
        id="mock-007",
        subject="Figma Professional - Subscription updated: New pricing",
        sender="billing@figma.com",
        date=_days_ago(2),
        snippet="Your Figma Professional plan has been updated to new pricing: ₹1,999/month.",
        body_text="""Figma Billing Update
Merchant: Figma
Invoice Date: {date}
Plan: Professional
Total Amount: ₹1999.00
Currency: INR
Billing Period: Sep 1 - Sep 30, 2026
Note: New Pricing Effective Sep 2026
Previous amount: ₹1499.00""".format(date=_days_ago(2)),
    ),

    # ── STARTUP / COMPANY bills ────────────────────────────────────────────
    RawEmail(
        id="mock-008",
        subject="AWS Invoice for August 2026 - Account: 123456789012",
        sender="aws-receivables-support@amazon.com",
        date=_days_ago(6),
        snippet="Your AWS invoice for August 2026 totaling $1,247.83 is available.",
        body_text="""Amazon Web Services Invoice
Merchant: Amazon Web Services
Invoice Date: {date}
Account: 123456789012
Billing Period: August 1 - August 31, 2026
Line Items:
  EC2 Instances (t3.medium x 3): $420.00
  RDS Multi-AZ (db.t3.small): $285.00
  S3 Storage (2.1 TB): $48.39
  CloudFront CDN: $124.50
  Lambda Invocations: $12.75
  Data Transfer: $89.19
  Support Plan (Developer): $29.00
  Misc Services: $239.00
Total Amount: $1247.83
Currency: USD""".format(date=_days_ago(6)),
    ),
    RawEmail(
        id="mock-009",
        subject="Slack Business+ Invoice - September 2026",
        sender="billing@slack.com",
        date=_days_ago(5),
        snippet="Invoice for 24 active users. Total: $216.00.",
        body_text="""Slack Invoice
Merchant: Slack
Invoice Date: {date}
Account: Startup Corp Pvt Ltd
Plan: Business+
Active Users: 24
Per User Rate: $9.00/month
Total Amount: $216.00
Currency: USD
Billing Period: Sep 1 - Sep 30, 2026""".format(date=_days_ago(5)),
    ),
    RawEmail(
        id="mock-010",
        subject="GitHub Enterprise - Invoice August 2026",
        sender="support@github.com",
        date=_days_ago(7),
        snippet="Your GitHub Enterprise invoice for 15 seats: $570.00.",
        body_text="""GitHub Enterprise Invoice
Merchant: GitHub
Invoice Date: {date}
Organization: startup-corp
Plan: Enterprise
Seats: 15
Rate: $38.00 per seat/month
Total Amount: $570.00
Currency: USD""".format(date=_days_ago(7)),
    ),

    # ── ANOMALY: SaaS seat price increase ─────────────────────────────────
    RawEmail(
        id="mock-011",
        subject="Notion Team - Price update notice + Invoice",
        sender="billing@notion.so",
        date=_days_ago(1),
        snippet="Notion Team pricing updated. 10 seats × $18/month = $180 (was $10/seat).",
        body_text="""Notion Billing Notice
Merchant: Notion
Invoice Date: {date}
Plan: Team
Seats: 10
New Rate: $18.00 per seat/month (previously $10.00)
Total Amount: $180.00
Currency: USD
Note: Pricing effective September 2026 per updated Terms of Service.
Previous Invoice: $100.00""".format(date=_days_ago(1)),
    ),
    RawEmail(
        id="mock-012",
        subject="LIC Premium payment receipt - Policy 987654321",
        sender="noreply@licindia.in",
        date=_days_ago(3),
        snippet="Premium received for policy 987654321. Amount: ₹8,500. Thank you.",
        body_text="""LIC Premium Receipt
Merchant: LIC Insurance
Invoice Date: {date}
Policy Number: 987654321
Policy Type: Term Life - Smart Tech Plan
Premium Amount: ₹8500.00
Currency: INR
Payment Mode: AutoPay
Next Due Date: {next}""".format(date=_days_ago(3), next=_days_ago(-90)),
    ),
    RawEmail(
        id="mock-013",
        subject="Datadog - Invoice for September 2026",
        sender="billing@datadoghq.com",
        date=_days_ago(2),
        snippet="Your Datadog invoice for 5 hosts + APM: $425.00",
        body_text="""Datadog Invoice
Merchant: Datadog
Invoice Date: {date}
Account: startup-corp
Line Items:
  Infrastructure (5 hosts): $150.00
  APM (5 hosts): $175.00
  Log Management (50GB): $100.00
Total Amount: $425.00
Currency: USD""".format(date=_days_ago(2)),
    ),
    RawEmail(
        id="mock-014",
        subject="Zoom Business - Monthly subscription renewed",
        sender="no-reply@zoom.us",
        date=_days_ago(4),
        snippet="Your Zoom Business plan for 10 hosts has been renewed: $200.00",
        body_text="""Zoom Business Subscription
Merchant: Zoom
Invoice Date: {date}
Plan: Business
Hosts: 10
Rate: $20.00/host/month
Total Amount: $200.00
Currency: USD
Billing Period: Sep 1 - Sep 30, 2026""".format(date=_days_ago(4)),
    ),
    # ANOMALY: Trial expiry
    RawEmail(
        id="mock-015",
        subject="Your Intercom trial has ended - Subscription starts now",
        sender="billing@intercom.io",
        date=_days_ago(0),
        snippet="Your 14-day trial has ended. Your Starter plan at $74/month starts today.",
        body_text="""Intercom Subscription Start
Merchant: Intercom
Invoice Date: {date}
Plan: Starter
Total Amount: $74.00
Currency: USD
Note: Free trial expired. Subscription auto-started.
Detected Terms: Free Trial Expired, AutoPay Enrolled
Previous: $0.00 (trial)""".format(date=_days_ago(0)),
    ),
    RawEmail(
        id="mock-016",
        subject="Airtel Broadband - Bill for September 2026",
        sender="billing@airtel.in",
        date=_days_ago(3),
        snippet="Your Airtel broadband bill of ₹999 for September is now due.",
        body_text="""Airtel Broadband Bill
Merchant: Airtel
Invoice Date: {date}
Plan: Airtel Xstream 200 Mbps
Billing Period: Sep 1 - Sep 30, 2026
Total Amount: ₹999.00
Currency: INR
Due Date: September 25, 2026""".format(date=_days_ago(3)),
    ),
    RawEmail(
        id="mock-017",
        subject="Figma Starter - Downgrade confirmation",
        sender="billing@figma.com",
        date=_days_ago(1),
        snippet="Your Figma plan has been changed to Starter (Free). No charge this month.",
        body_text="""Figma Plan Change
Merchant: Figma
Invoice Date: {date}
Plan: Starter (Free)
Total Amount: ₹0.00
Currency: INR
Note: Downgrade from Professional. Effective Sep 1.""".format(date=_days_ago(1)),
    ),
    RawEmail(
        id="mock-018",
        subject="Razorpay - Monthly platform fee invoice",
        sender="billing@razorpay.com",
        date=_days_ago(2),
        snippet="Platform fee for August 2026. GMV: ₹24,87,500. Fee: ₹5,719.",
        body_text="""Razorpay Platform Fee
Merchant: Razorpay
Invoice Date: {date}
Billing Period: August 2026
GMV Processed: ₹24,87,500.00
Platform Fee (0.23% of GMV): ₹5719.00
GST (18%): ₹1029.42
Total Amount: ₹6748.42
Currency: INR""".format(date=_days_ago(2)),
    ),
    RawEmail(
        id="mock-019",
        subject="Star Health Insurance - Renewal premium due",
        sender="noreply@starhealth.in",
        date=_days_ago(1),
        snippet="Your family floater policy renewal premium of ₹18,400 is due on Sep 15.",
        body_text="""Star Health Insurance Premium
Merchant: Star Health
Invoice Date: {date}
Policy: Family Floater - Smart Health Plus
Sum Assured: ₹10,00,000
Previous Premium: ₹14,800
Current Premium: ₹18400.00
Currency: INR
Increase Note: Annual revision due to medical inflation index.
Due Date: September 15, 2026""".format(date=_days_ago(1)),
    ),

    RawEmail(
        id="mock-021",
        subject="HDFC Bank Credit Card e-Statement for Sep 2026",
        sender="alerts@hdfcbank.net",
        date="2026-09-08",
        snippet="Dear Customer, your HDFC Bank Regalia Credit Card e-Statement for the billing cycle ending 05-Sep-2026 is ready. Total Amount Due: INR 18,450.00. Minimum Amount Due: INR 1,200.00.",
        body_text="""HDFC BANK CREDIT CARD STATEMENT
Card: Regalia Gold ending in 4128
Billing Cycle: 06-Aug-2026 to 05-Sep-2026
Payment Due Date: 25-Sep-2026
Total Amount Due: INR 18,450.00
Minimum Amount Due: INR 1,200.00
Available Credit Limit: INR 3,81,550.00
Payment Options: Pay instantly via HDFC NetBanking or UPI.
""",
    ),
    RawEmail(
        id="mock-022",
        subject="ICICI Bank Credit Card Statement Alert",
        sender="credit_cards@icicibank.com",
        date="2026-09-09",
        snippet="Your ICICI Bank Sapphiro Card statement ending Sep 2026 is generated. Total Due: Rs 12,800.00. Due Date: 28-Sep-2026.",
        body_text="""ICICI BANK CARD STATEMENT
Account: ICICI Sapphiro Credit Card
Statement Date: 08-Sep-2026
Due Date: 28-Sep-2026
Total Amount Due: Rs 12,800.00
Minimum Due: Rs 950.00
Transactions:
1. Swiggy INR 850
2. MakeMyTrip Flights INR 8,950
3. Supermarket INR 3,000
""",
    ),
    RawEmail(
        id="mock-023",
        subject="SBI Card e-Statement - Total Amount Due",
        sender="statements@sbicard.com",
        date="2026-09-07",
        snippet="Dear Cardholder, your monthly SBI Card statement is ready. Total Amount Due is Rs. 7,290.00. Payment Due Date: 26-Sep-2026.",
        body_text="""SBI CARD STATEMENT
Card ending: 8812
Statement Period: 07 Aug 2026 - 06 Sep 2026
Payment Due Date: 26 Sep 2026
Total Amount Due: Rs 7,290.00
Minimum Amount Due: Rs 500.00
Auto-Debit: Not Registered. Please pay before due date.
""",
    ),
    RawEmail(
        id="mock-024",
        subject="Axis Bank Card Bill Due Notification",
        sender="alerts@axisbank.com",
        date="2026-09-06",
        snippet="Axis Bank Credit Card Alert: Bill of INR 4,990.00 is generated for your Magnus card. Due date: 24-Sep-2026.",
        body_text="""AXIS BANK CREDIT CARD BILL
Card: Axis Bank Magnus
Billing Month: September 2026
Total Bill Amount: INR 4,990.00
Due Date: 24-Sep-2026
Pay now to avoid finance charges of 3.6% per month.
""",
    ),
    RawEmail(
        id="mock-025",
        subject="American Express Card Monthly Statement",
        sender="service@americanexpress.com",
        date="2026-09-10",
        snippet="Your American Express Platinum Statement is available online. New Balance: INR 24,500.00. Payment Due: 30 Sep 2026.",
        body_text="""AMERICAN EXPRESS STATEMENT
Account ending in: 31005
Statement Date: 10 Sep 2026
New Balance: INR 24,500.00
Payment Due Date: 30 Sep 2026
AutoPay is scheduled for 28 Sep 2026.
""",
    ),

    RawEmail(
        id="mock-026",
        subject="IndusInd Bank e-Statement for Sep 2026 [Password Protected]",
        sender="IndusInd_Bank@indusind.com",
        date="2026-09-14",
        snippet="Dear Customer, your IndusInd Bank Account e-Statement for September 2026 is attached. This file is password protected for your security.",
        body_text="""Dear Customer,

Please find attached your IndusInd Bank Account e-Statement for the period ending 14-Sep-2026.

Important Security Note:
This PDF attachment is password protected.
Your password is the first 4 letters of your name in CAPITALS followed by your Year of Birth (e.g. IN1995).

Total Amount Due: INR 14,250.00
Payment Due Date: 28-Sep-2026

Assuring you of our best services at all times.
Team IndusInd Bank""",
        has_pdf=True,
        pdf_filename="IndusInd_eStatement_Sep2026.pdf",
        pdf_bytes=_generate_mock_statement_pdf("IN1995"),
        is_pdf_encrypted=True,
    ),
    RawEmail(
        id="mock-020",
        subject="Vercel Pro - Invoice September 2026",
        sender="billing@vercel.com",
        date=_days_ago(3),
        snippet="Vercel Pro plan for 3 members: $60.00 for September 2026.",
        body_text="""Vercel Invoice
Merchant: Vercel
Invoice Date: {date}
Plan: Pro
Members: 3
Rate: $20/member/month
Total Amount: $60.00
Currency: USD
Billing Period: Sep 1 - Sep 30, 2026""".format(date=_days_ago(3)),
    ),
]


class MockEmailAdapter(EmailInboxAdapter):
    """
    Mock email adapter for demo and testing.
    Returns pre-loaded synthetic billing emails.
    No authentication required.
    """

    def __init__(self):
        self._emails = {e.id: e for e in MOCK_EMAILS}

    def provider_name(self) -> str:
        return "Mock Demo Inbox"

    def list_billing_emails(self, max_count: int = 15, bank_filter: str = None) -> List[RawEmail]:
        """Return billing emails from the mock dataset, up to max_count, optionally filtered by bank."""
        billing = [
            email for email in MOCK_EMAILS
            if is_billing_email(email.subject, email.sender, bank_filter=bank_filter)
        ]
        return billing[:max_count]

    def get_email_body(self, email_id: str) -> Optional[str]:
        email = self._emails.get(email_id)
        return email.body_text if email else None
