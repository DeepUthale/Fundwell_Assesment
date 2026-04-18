"""Enrich node — checks CRM for duplicates and adds contextual data."""

from __future__ import annotations

from src.models import LoanApplicationState

# Stub CRM client - replace with real CRM integration (HubSpot, Salesforce…)

class CRMClient:
    """Placeholder CRM client for demonstration purposes."""

    def __init__(self):
        self._known_applicants: dict[str, str] = {}  # email -> opportunity_id

    def search_by_email(self, email: str) -> dict | None:
        """Search the CRM for an existing contact by email address."""
        if email in self._known_applicants:
            return {"id": self._known_applicants[email], "email": email}
        return None

    def search_by_business(self, business_name: str) -> dict | None:
        """Search the CRM for an existing contact by business name."""
        # Stub - always returns None
        return None


crm_client = CRMClient()


def enrich_node(state: LoanApplicationState) -> LoanApplicationState:
    """Check CRM for duplicates and enrich the application state."""

    risk_flags = list(state.get("risk_flags", []))
    sender = state.get("sender", "")
    business_name = state.get("business_name", "")

    # Check for existing applicant by email
    match = crm_client.search_by_email(sender)

    # Fallback: check by business name
    if not match and business_name:
        match = crm_client.search_by_business(business_name)

    if match:
        state["is_duplicate"] = True
        state["crm_match_id"] = match["id"]
        risk_flags.append(
            f"Returning applicant - existing CRM record {match['id']}"
        )
    else:
        state["is_duplicate"] = False
        state["crm_match_id"] = None

    state["risk_flags"] = risk_flags
    return state
