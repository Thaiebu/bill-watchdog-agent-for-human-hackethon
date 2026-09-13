"""
IMAPEmailAdapter — Real inbox connection via IMAP + App Password.
Works with Gmail, Outlook, Yahoo, or any IMAP-enabled inbox.

Gmail setup:
  1. Enable 2FA on your Google account
  2. Go to: myaccount.google.com/apppasswords
  3. Create an App Password for "Mail"
  4. Use that 16-character password here (not your real password)

Outlook setup:
  imap_host = "imap-mail.outlook.com", imap_port = 993
"""
import imaplib
import email as email_lib
import re
from email.header import decode_header
from typing import List, Optional
from inboxes.base_adapter import EmailInboxAdapter, RawEmail, is_billing_email


class IMAPEmailAdapter(EmailInboxAdapter):
    """
    Connects to any IMAP mailbox (Gmail, Outlook, etc.) using
    host/port + app password credentials.
    """

    PROVIDER_DEFAULTS = {
        "gmail":   {"host": "imap.gmail.com",           "port": 993},
        "outlook": {"host": "imap-mail.outlook.com",    "port": 993},
        "yahoo":   {"host": "imap.mail.yahoo.com",      "port": 993},
        "icloud":  {"host": "imap.mail.me.com",         "port": 993},
    }

    def __init__(
        self,
        email_address: str = "",
        app_password: str = "",
        imap_host: str = "imap.gmail.com",
        imap_port: int = 993,
        provider_preset: str = None,  # "gmail" | "outlook" | "yahoo"
    ):
        if provider_preset and provider_preset in self.PROVIDER_DEFAULTS:
            defaults = self.PROVIDER_DEFAULTS[provider_preset]
            imap_host = defaults["host"]
            imap_port = defaults["port"]

        self.email_address = email_address
        self.app_password  = app_password
        self.imap_host     = imap_host
        self.imap_port     = imap_port
        self._email_cache: dict[str, RawEmail] = {}

    def provider_name(self) -> str:
        if "gmail" in self.imap_host:
            return "Gmail (IMAP)"
        if "outlook" in self.imap_host:
            return "Outlook (IMAP)"
        return f"IMAP ({self.imap_host})"

    def _connect(self) -> imaplib.IMAP4_SSL:
        try:
            mail = imaplib.IMAP4_SSL(self.imap_host, self.imap_port)
            # Remove any spaces that user might have copied from Google UI (e.g. "abcd efgh ijkl mnop")
            clean_password = self.app_password.replace(" ", "").strip()
            mail.login(self.email_address.strip(), clean_password)
            return mail
        except imaplib.IMAP4.error as e:
            err_msg = str(e)
            if "Application-specific password required" in err_msg or "support.google.com/accounts/answer/185833" in err_msg:
                raise PermissionError(
                    "Google requires a 16-character App Password (not your normal Gmail password). "
                    "Generate one in 30 seconds at: https://myaccount.google.com/apppasswords"
                ) from e
            elif "authentication failed" in err_msg.lower() or "invalid credentials" in err_msg.lower():
                raise PermissionError(
                    "Invalid email or App Password. Check that 2FA is enabled and your 16-character App Password is correct."
                ) from e
            raise

    def list_billing_emails(self, max_count: int = 15, bank_filter: str = None) -> List[RawEmail]:
        """
        Fetch recent emails from INBOX, filter for billing/bank-related ones,
        and return up to max_count.
        """
        if not self.email_address or not self.app_password:
            raise ValueError(
                "IMAP adapter requires email_address and app_password. "
                "See docstring for Gmail App Password setup instructions."
            )

        mail = self._connect()
        mail.select("INBOX")

        # Search recent emails (fetch last 100 to ensure monthly statements are caught)
        status, messages = mail.search(None, "ALL")
        all_ids = messages[0].split() if messages and messages[0] else []
        recent_ids = all_ids[-100:] if len(all_ids) > 100 else all_ids
        recent_ids = list(reversed(recent_ids))  # Newest first

        billing_emails: List[RawEmail] = []

        for msg_id in recent_ids:
            if len(billing_emails) >= max_count:
                break

            status, data = mail.fetch(msg_id, "(RFC822)")
            if not data or not data[0] or not isinstance(data[0], tuple):
                continue
            raw_email = data[0][1]
            msg = email_lib.message_from_bytes(raw_email)

            subject = _decode_header_value(msg.get("Subject", ""))
            sender  = _decode_header_value(msg.get("From", ""))
            date    = _parse_date(msg.get("Date", ""))

            if not is_billing_email(subject, sender, bank_filter=bank_filter):
                continue

            body = _extract_body(msg)
            snippet = body[:200].replace("\n", " ") if body else ""

            raw = RawEmail(
                id=f"imap-{msg_id.decode()}",
                subject=subject,
                sender=sender,
                date=date,
                snippet=snippet,
                body_text=body or "",
            )
            self._email_cache[raw.id] = raw
            billing_emails.append(raw)

        mail.logout()
        return billing_emails

    def get_email_body(self, email_id: str) -> Optional[str]:
        """Return cached email body or None."""
        email = self._email_cache.get(email_id)
        return email.body_text if email else None


# ── Helpers ───────────────────────────────────────────────────────────────

def _decode_header_value(value: str) -> str:
    parts = decode_header(value)
    result = []
    for text, charset in parts:
        if isinstance(text, bytes):
            result.append(text.decode(charset or "utf-8", errors="replace"))
        else:
            result.append(text)
    return " ".join(result)


def _parse_date(date_str: str) -> str:
    """Extract YYYY-MM-DD from email Date header."""
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(date_str)
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return date_str[:10] if len(date_str) >= 10 else "2026-09-01"


def _extract_body(msg) -> str:
    """Extract plain-text body from email message object."""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition  = str(part.get("Content-Disposition", ""))
            if content_type == "text/plain" and "attachment" not in disposition:
                try:
                    body = part.get_payload(decode=True).decode(
                        part.get_content_charset() or "utf-8", errors="replace"
                    )
                    break
                except Exception:
                    continue
    else:
        try:
            body = msg.get_payload(decode=True).decode(
                msg.get_content_charset() or "utf-8", errors="replace"
            )
        except Exception:
            body = str(msg.get_payload())

    # Strip HTML tags if needed
    body = re.sub(r"<[^>]+>", " ", body)
    body = re.sub(r"\s+", " ", body).strip()
    return body
