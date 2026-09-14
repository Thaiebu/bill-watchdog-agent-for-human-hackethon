"""Unit tests for PDF statement inspector and zero-trust decryptor."""
from inboxes.mock_adapter import _generate_mock_statement_pdf
from tools.pdf_statement_tool import inspect_pdf_bytes, decrypt_and_extract_statement


class TestPDFStatementTool:
    def test_inspect_encrypted_pdf(self):
        pdf_bytes = _generate_mock_statement_pdf(password="TEST1234")
        info = inspect_pdf_bytes(pdf_bytes)

        assert info["is_pdf"] is True
        assert info["is_encrypted"] is True
        assert info["error"] is None

    def test_decrypt_with_wrong_password_fails(self):
        pdf_bytes = _generate_mock_statement_pdf(password="CORRECT_PWD")
        res = decrypt_and_extract_statement(pdf_bytes, password="WRONG_PASSWORD")

        assert res["success"] is False
        assert res["is_encrypted"] is True
        assert "Incorrect password" in res["error"]

    def test_decrypt_with_missing_password_prompts(self):
        pdf_bytes = _generate_mock_statement_pdf(password="CORRECT_PWD")
        res = decrypt_and_extract_statement(pdf_bytes, password="")

        assert res["success"] is False
        assert res["is_encrypted"] is True
        assert "Password required" in res["error"]

    def test_decrypt_with_correct_password_succeeds(self):
        pdf_bytes = _generate_mock_statement_pdf(password="IN1995")
        res = decrypt_and_extract_statement(pdf_bytes, password="IN1995")

        assert res["success"] is True
        assert res["is_encrypted"] is True
        assert res["decrypted"] is True
        assert "invoice" in res
        invoice = res["invoice"]
        assert "IndusInd Bank" in invoice["merchant_name"]
        assert invoice["total_amount"] == 14250.0
        assert invoice["currency"] == "INR"

    def test_invalid_bytes_returns_error(self):
        info = inspect_pdf_bytes(b"not a pdf")
        assert info["is_pdf"] is False
        assert info["error"] is not None

        res = decrypt_and_extract_statement(b"not a pdf", password="test")
        assert res["success"] is False
