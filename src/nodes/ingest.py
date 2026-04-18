"""Ingest node — fetches unread emails from a Gmail inbox."""

from __future__ import annotations

import base64
import os
from datetime import datetime, timezone
from email.utils import parseaddr
from typing import Optional

from src.models import LoanApplicationState


def _decode_body(payload: dict) -> str:
    """Recursively extract plain-text body from Gmail message payload."""
    if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")

    for part in payload.get("parts", []):
        text = _decode_body(part)
        if text:
            return text
    return ""


def fetch_unread_emails(max_results: int = 20) -> list[LoanApplicationState]:
    """Fetch unread emails from Gmail and return them as initial states.

    Requires a valid OAuth credentials file (see .env.example).
    Returns an empty list if credentials are missing.
    """
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
    except ImportError:
        print("[ingest] google-api-python-client not installed - skipping Gmail fetch.")
        return []

    from src.config import GMAIL_CREDENTIALS_PATH

    SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
    creds: Optional[Credentials] = None
    token_path = "token.json"

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        elif os.path.exists(GMAIL_CREDENTIALS_PATH):
            flow = InstalledAppFlow.from_client_secrets_file(GMAIL_CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        else:
            print(f"[ingest] Credentials file not found at {GMAIL_CREDENTIALS_PATH}")
            return []

        with open(token_path, "w") as f:
            f.write(creds.to_json())

    service = build("gmail", "v1", credentials=creds)
    results = (
        service.users()
        .messages()
        .list(userId="me", labelIds=["INBOX", "UNREAD"], maxResults=max_results)
        .execute()
    )
    messages = results.get("messages", [])

    states: list[LoanApplicationState] = []
    for msg_meta in messages:
        msg = service.users().messages().get(userId="me", id=msg_meta["id"], format="full").execute()
        headers = {h["name"].lower(): h["value"] for h in msg["payload"].get("headers", [])}

        _, sender_email = parseaddr(headers.get("from", ""))
        subject = headers.get("subject", "(no subject)")
        body = _decode_body(msg["payload"])

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

    return states


def ingest_node(state: LoanApplicationState) -> LoanApplicationState:
    """Pass-through node for emails already loaded into state."""
    if "date_received" not in state or not state["date_received"]:
        state["date_received"] = datetime.now(timezone.utc).isoformat()
    if "missing_fields" not in state:
        state["missing_fields"] = []
    if "risk_flags" not in state:
        state["risk_flags"] = []
    if "is_duplicate" not in state:
        state["is_duplicate"] = False
    if "confidence_score" not in state:
        state["confidence_score"] = 1.0
    return state
