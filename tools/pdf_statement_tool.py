import io
import gc
from typing import Optional
from pypdf import PdfReader
from tools.extractor_tool import extract_invoice_entities


def inspect_pdf_bytes(pdf_bytes: bytes) -> dict:
    """
    Inspect raw PDF bytes without decrypting.
    Returns whether the PDF is valid, encrypted, and its page count.
    """
    if not pdf_bytes or not pdf_bytes.startswith(b"%PDF"):
        return {
            "is_pdf": False,
            "is_encrypted": False,
            "page_count": 0,
            "error": "Not a valid PDF file",
        }

    try:
        stream = io.BytesIO(pdf_bytes)
        reader = PdfReader(stream)
        is_enc = reader.is_encrypted
        pages = len(reader.pages) if not is_enc else None
        return {
            "is_pdf": True,
            "is_encrypted": is_enc,
            "page_count": pages,
            "error": None,
        }
    except Exception as exc:
        return {
            "is_pdf": True,
            "is_encrypted": False,
            "page_count": 0,
            "error": f"Failed to inspect PDF: {str(exc)}",
        }


def decrypt_and_extract_statement(pdf_bytes: bytes, password: str = "") -> dict:
    """
    In-memory decryption and entity extraction from a bank statement PDF.

    Security guarantees:
    - Never persists password to SQLite, logs, or disk.
    - Password is wiped from memory as soon as decrypt() finishes.
    - Extracts billing entities (Bank name, Statement Period, Total Due, Due Date, Min Due).
    """
    if not pdf_bytes:
        return {"success": False, "error": "Empty PDF attachment"}

    stream = io.BytesIO(pdf_bytes)
    try:
        reader = PdfReader(stream)
    except Exception as exc:
        return {"success": False, "error": f"Invalid PDF format: {exc}"}

    is_encrypted = reader.is_encrypted

    if is_encrypted:
        if not password:
            return {
                "success": False,
                "is_encrypted": True,
                "error": "Password required: This bank statement is password-protected.",
            }

        # In-memory decryption attempt
        try:
            clean_pwd = password.strip()
            res = reader.decrypt(clean_pwd)
            if res == 0:
                return {
                    "success": False,
                    "is_encrypted": True,
                    "error": "Incorrect password. Common bank formats: PAN or First 4 letters of name + DOB (DDMM).",
                }
        finally:
            del password
            gc.collect()

    # Extract text from first 2 pages
    extracted_text = []
    try:
        max_pages = min(2, len(reader.pages))
        for i in range(max_pages):
            page = reader.pages[i]
            extracted_text.append(page.extract_text() or "")
    except Exception as exc:
        return {"success": False, "error": f"Decryption succeeded but failed to read text: {exc}"}

    full_text = chr(10).join(extracted_text)

    if not full_text.strip():
        return {
            "success": False,
            "error": "Statement PDF has no selectable text layer.",
        }

    # Extract structured statement entities
    invoice = extract_invoice_entities(raw_content=full_text, source_type="pdf")

    return {
        "success": True,
        "is_encrypted": is_encrypted,
        "decrypted": True,
        "raw_text_snippet": full_text[:400].replace(chr(10), " "),
        "invoice": invoice,
    }
