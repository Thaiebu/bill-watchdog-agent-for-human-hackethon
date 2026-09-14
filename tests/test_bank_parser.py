"""Unit tests for Indian banking alert & statement parsing."""
from tools.extractor_tool import extract_invoice_entities


class TestBankParser:
    def test_indusind_upi_debit_alert(self):
        sample = '''Dear Customer,

Thank you for banking with us.

Your IndusInd Bank Account No. 15XXXXXX6528 has been Debited for INR 30.00 towards UPI/662389768014/DR/O Sa/YESB/ytm.s20t6wy@pty .

The balance available in your Account is INR 86.53.
'''
        result = extract_invoice_entities(sample, source_type="email")
        assert "IndusInd Bank" in result["merchant_name"]
        assert result["total_amount"] == 30.0
        assert result["currency"] == "INR"
        assert len(result["line_items"]) > 0
        assert "ytm.s20t6wy@pty" in result["merchant_name"] or "ytm.s20t6wy@pty" in result["line_items"][0]["name"]

    def test_hdfc_card_statement_alert(self):
        sample = '''HDFC Bank Credit Card e-Statement for Regalia Gold ending in 4128.
Total Amount Due: INR 18,450.00.
Minimum Amount Due: INR 1,200.00.
Payment Due Date: 2026-09-25.
'''
        result = extract_invoice_entities(sample, source_type="email")
        assert "HDFC Bank" in result["merchant_name"]
        assert result["total_amount"] == 18450.0
        assert result["currency"] == "INR"

    def test_account_number_is_masked(self):
        sample = '''Your IndusInd Bank Account No. 151234566528 has been Debited for INR 500.00 towards Grocery.'''
        result = extract_invoice_entities(sample, source_type="email")
        # Full raw account number must not appear in merchant_name
        assert "151234566528" not in result["merchant_name"]
