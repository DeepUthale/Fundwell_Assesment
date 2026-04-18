"""Validate node — checks for missing or incomplete fields."""

from __future__ import annotations

from src.models import LoanApplicationState


# Fields that are critical for triage decisions
CRITICAL_FIELDS = [
    ("business_name", "Business name"),
    ("loan_amount_requested", "Loan amount"),
    ("monthly_revenue", "Revenue"),
]

IMPORTANT_FIELDS = [
    ("owner_name", "Owner name"),
    ("location", "Location"),
    ("years_in_business", "Years in business"),
    ("loan_purpose", "Loan purpose"),
]


def validate_node(state: LoanApplicationState) -> LoanApplicationState:
    """Check extracted fields for completeness and flag missing data."""

    missing_critical: list[str] = []
    missing_important: list[str] = []

    for field_key, field_label in CRITICAL_FIELDS:
        if not state.get(field_key):
            missing_critical.append(field_label)

    for field_key, field_label in IMPORTANT_FIELDS:
        if not state.get(field_key):
            missing_important.append(field_label)

    state["missing_fields"] = missing_critical + missing_important

    risk_flags = list(state.get("risk_flags", []))

    # If all critical fields are missing, reject outright
    if len(missing_critical) == len(CRITICAL_FIELDS):
        state["triage_decision"] = "rejected"
        state["confidence_score"] = 0.1
        risk_flags.append(
            f"Missing all critical fields: {', '.join(missing_critical)}"
        )
    elif len(missing_critical) >= 2:
        state["triage_decision"] = "needs_review"
        state["confidence_score"] = 0.3
        risk_flags.append(
            f"Missing critical fields: {', '.join(missing_critical)}"
        )

    if missing_important:
        risk_flags.append(
            f"Missing fields: {', '.join(missing_important)}"
        )

    state["risk_flags"] = risk_flags
    return state


def should_continue_after_validation(state: LoanApplicationState) -> str:
    """Conditional edge: skip scoring if already flagged for review."""
    decision = state.get("triage_decision")
    if decision in ("needs_review", "rejected"):
        return "route"
    return "enrich"
