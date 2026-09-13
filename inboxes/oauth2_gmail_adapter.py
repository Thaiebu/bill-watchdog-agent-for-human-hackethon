"""
OAuth2GmailAdapter — Production-grade Gmail integration via Gmail API + OAuth2.

This adapter reads emails using the official Gmail API with OAuth2 authentication.
It is the recommended production path for a deployed SaaS product.

Setup Instructions (do this once before deployment):
  1. Go to console.cloud.google.com → Create project → Enable "Gmail API"
  2. Create OAuth 2.0 credentials (Desktop app or Web app)
  3. Download credentials.json
  4. Run the auth flow once: python inboxes/oauth2_gmail_adapter.py --auth
  5. This stores token.json for future use

For the hackathon demo, use MockEmailAdapter instead.
For real Gmail testing, use IMAPEmailAdapter with an App Password.
"""
import json
import os
from typing import List, Optional
from inboxes.base_adapter import EmailInboxAdapter, RawEmail, is_billing_email

TOKEN_FILE       = "gmail_token.json"
CREDENTIALS_FILE = "gmail_credentials.json"
SCOPES           = ["https://www.googleapis.com/auth/gmail.readonly"]


class OAuth2GmailAdapter(EmailInboxAdapter):
    """
    Gmail API adapter using OAuth2.
    Requires google-auth-oauthlib and google-api-python-client packages.

    For hackathon demo: raises a clear error directing to MockEmailAdapter.
    For production: performs full OAuth2 flow with token refresh.
    """

    def __init__(
        self,
        credentials_file: str = CREDENTIALS_FILE,
        token_file: str = TOKEN_FILE,
    ):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self._service = None

    def provider_name(self) -> str:
        return "Gmail (OAuth2)"

    def _get_service(self):
        if self._service:
            return self._service

        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
        except ImportError:
            raise ImportError(
                "OAuth2GmailAdapter requires extra packages. Install with:\n"
                "  pip install google-auth-oauthlib google-api-python-client\n\n"
                "For the hackathon demo, use provider='mock' instead."
            )

        creds = None
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_file):
                    raise FileNotFoundError(
                        f"OAuth2 credentials file not found: {self.credentials_file}\n\n"
                        f"Setup: Download credentials.json from Google Cloud Console\n"
                        f"and place it in the BillWatchdog root directory.\n\n"
                        f"For demo, use: provider='mock'"
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, SCOPES
                )
                creds = flow.run_local_server(port=0)
            with open(self.token_file, "w") as token:
                token.write(creds.to_json())

        self._service = build("gmail", "v1", credentials=creds)
        return self._service

    def list_billing_emails(self, max_count: int = 15, bank_filter: str = None) -> List[RawEmail]:
        """Fetch billing emails via Gmail API with billing keyword query."""
        service = self._get_service()

        # Build Gmail search query — much more precise than IMAP
        query = (
            "subject:(invoice OR bill OR receipt OR statement OR "
            "'payment due' OR subscription OR renewal) "
            "newer_than:7d -label:promotions -label:social"
        )

        result = service.users().messages().list(
            userId="me", q=query, maxResults=max_count * 2
        ).execute()

        messages = result.get("messages", [])
        billing_emails: List[RawEmail] = []

        for msg_ref in messages[:max_count * 2]:
            if len(billing_emails) >= max_count:
                break

            msg = service.users().messages().get(
                userId="me", id=msg_ref["id"], format="full"
            ).execute()

            subject = _get_header(msg, "Subject")
            sender  = _get_header(msg, "From")
            date    = _get_header(msg, "Date")[:10] if _get_header(msg, "Date") else "2026-09-01"

            if not is_billing_email(subject, sender):
                continue

            body = _extract_gmail_body(msg)
            snippet = msg.get("snippet", "")[:200]

            email = RawEmail(
                id=f"gmail-{msg_ref['id']}",
                subject=subject,
                sender=sender,
                date=date,
                snippet=snippet,
                body_text=body,
            )
            billing_emails.append(email)

        return billing_emails

    def get_email_body(self, email_id: str) -> Optional[str]:
        """Fetch email body directly from Gmail API by message ID."""
        try:
            msg_id = email_id.replace("gmail-", "")
            service = self._get_service()
            msg = service.users().messages().get(
                userId="me", id=msg_id, format="full"
            ).execute()
            return _extract_gmail_body(msg)
        except Exception:
            return None


def _get_header(msg: dict, name: str) -> str:
    headers = msg.get("payload", {}).get("headers", [])
    for h in headers:
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


def _extract_gmail_body(msg: dict) -> str:
    """Recursively extract text/plain from Gmail API message parts."""
    import base64
    import re

    def _get_parts(payload):
        if payload.get("mimeType") == "text/plain":
            data = payload.get("body", {}).get("data", "")
            if data:
                return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
        for part in payload.get("parts", []):
            result = _get_parts(part)
            if result:
                return result
        return ""

    body = _get_parts(msg.get("payload", {}))
    body = re.sub(r"<[^>]+>", " ", body)
    body = re.sub(r"\s+", " ", body).strip()
    return body


if __name__ == "__main__":
    import sys
    if "--auth" in sys.argv:
        adapter = OAuth2GmailAdapter()
        adapter._get_service()
        print("✅ Gmail OAuth2 authentication successful. token.json saved.")
