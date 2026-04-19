"""Fetch emails via IMAP — works on Streamlit Cloud with Gmail App Passwords."""

from __future__ import annotations

import email
import imaplib
from datetime import datetime, timezone
from email.header import decode_header
from email.utils import parseaddr

from src.models import LoanApplicationState


def _decode_header_value(value: str) -> str:
    """Decode an email header value that may be encoded."""
    parts = decode_header(value)
    decoded = []
    for part, charset in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(part)
    return "".join(decoded)


def _extract_body(msg: email.message.Message) -> str:
    """Extract plain-text body from an email message."""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="replace")
        # Fallback: try HTML if no plain text
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="replace")
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            return payload.decode(charset, errors="replace")
    return ""


def fetch_emails_imap(
    email_address: str,
    app_password: str,
    max_results: int = 5,
    imap_server: str = "imap.gmail.com",
) -> list[LoanApplicationState]:
    """Fetch recent emails via IMAP and return them as LoanApplicationStates."""
    mail = imaplib.IMAP4_SSL(imap_server)
    mail.login(email_address, app_password)
    mail.select("INBOX", readonly=True)

    # Search for all emails, get the latest ones
    _, data = mail.search(None, "ALL")
    email_ids = data[0].split()

    # Get the last N emails (most recent)
    selected_ids = email_ids[-max_results:] if len(email_ids) >= max_results else email_ids
    selected_ids = list(reversed(selected_ids))  # newest first

    states: list[LoanApplicationState] = []
    for eid in selected_ids:
        _, msg_data = mail.fetch(eid, "(RFC822)")
        raw_email = msg_data[0][1]
        msg = email.message_from_bytes(raw_email)

        _, sender_email = parseaddr(msg.get("From", ""))
        subject = _decode_header_value(msg.get("Subject", "(no subject)"))
        body = _extract_body(msg)

        states.append(
            LoanApplicationState(
                raw_email=body,
                sender=sender_email,
                subject=subject,
                date_received=datetime.now(timezone.utc).isoformat(),
                missing_fields=[],
                risk_flags=[],
                is_duplicate=False,
                confidence_score=1.0,
            )
        )

    mail.logout()
    return states
