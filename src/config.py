import os
from dotenv import load_dotenv

load_dotenv()


def _get_secret(key: str, default: str = "") -> str:
    """Read from Streamlit secrets first, then fall back to env vars."""
    try:
        import streamlit as st
        val = st.secrets.get(key, None)
        if val:
            return val
    except Exception:
        pass
    return os.getenv(key, default)


ANTHROPIC_API_KEY = _get_secret("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = _get_secret("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

GMAIL_CREDENTIALS_PATH = os.getenv("GMAIL_CREDENTIALS_PATH", "credentials.json")
GMAIL_INBOX_LABEL = os.getenv("GMAIL_INBOX_LABEL", "INBOX")

CRM_API_URL = os.getenv("CRM_API_URL", "")
CRM_API_KEY = os.getenv("CRM_API_KEY", "")

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")

EXPORT_DIR = os.getenv("EXPORT_DIR", "./exports")

# Scoring thresholds
QUALIFIED_THRESHOLD = 0.7
REJECTION_THRESHOLD = 0.4
MIN_YEARS_IN_BUSINESS = 2
MIN_REVENUE_TO_LOAN_RATIO = 2.0
