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

    def test_multiline_bank_statement_table(self):
        sample = """DATE MODE PARTICULARS DEPOSITS WITHDRAWALS BALANCE
01-08-2026 B/F 49,049.67
01-08-2026

Indian Railways
UPI/Indian Rai/bdpg2.ir@sbi/train/State
Bank/657960975710/ICIc6df7676e6e74153b47c8dc05739b0f
7/

411.80 48,637.87

01-08-2026

Mr Mohaideen Bava
UPI/Mr Mohaide/bavaalim1972@o/saving/INDIAN
BAN/657984981067/ICI045c8f4ad9ff4c83b9675a0955783c1e/

25,000.00 23,637.87

02-08-2026

MASJID ALLAH
UPI/MASJID ALL/22646487602644/sadaka/CANARA
BAN/658026316139/AXI3a2ac4075f174a1db6d118db15b9cf2
e/

500.00 23,137.87

03-08-2026 ICICI DIRECT EBA/EQ Trade 03AUG/20260803171103 737.60 21,860.27
06-08-2026 ACH/THWORKSTECHINDPVTLTD/Empreimb04Aug239 794.00 21,149.26
"""
        result = extract_invoice_entities(sample, source_type="pdf")
        assert len(result["line_items"]) >= 5
        assert result["total_amount"] > 25000.0
        # Check Indian Railways spent
        railway_item = next(i for i in result["line_items"] if "Indian Railways" in i["name"])
        assert railway_item["spent"] == 411.80
        # Check Mr Mohaideen Bava spent
        bava_item = next(i for i in result["line_items"] if "Mohaideen Bava" in i["name"])
        assert bava_item["spent"] == 25000.0
