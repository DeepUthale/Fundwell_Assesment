"""Route node -takes action based on triage decision."""

from __future__ import annotations

from src.models import LoanApplicationState, TriageDecision


def _generate_summary(state: LoanApplicationState) -> str:
    """Generate a one-line human-readable summary of the application."""
    parts = []

    name = state.get("business_name") or "Unknown Business"
    parts.append(name)

    years = state.get("years_in_business")
    if years:
        parts.append(f"{years} yrs")

    ratio = state.get("revenue_to_loan_ratio")
    if ratio:
        parts.append(f"rev/loan {ratio}x")

    flags = state.get("risk_flags", [])
    flag_count = len(flags)
    if flag_count:
        parts.append(f"{flag_count} risk flag{'s' if flag_count != 1 else ''}")

    decision = state.get("triage_decision", "unknown")
    parts.append(f"-> {decision.upper()}")

    return " | ".join(parts)


def _assign_underwriter(state: LoanApplicationState) -> str:
    """Assign an underwriter team based on loan size and type."""
    amount = state.get("loan_amount_requested", 0) or 0

    if amount > 500_000:
        return "senior_underwriting"
    elif amount > 250_000:
        return "mid_market_underwriting"
    else:
        return "standard_underwriting"


def route_node(state: LoanApplicationState) -> LoanApplicationState:
    """Route the application based on its triage decision."""

    decision = state.get("triage_decision", TriageDecision.NEEDS_REVIEW.value)
    state["summary"] = _generate_summary(state)

    if decision == TriageDecision.QUALIFIED.value:
        state["assigned_underwriter"] = _assign_underwriter(state)
        print(f"[route] QUALIFIED -{state['summary']}")

    elif decision == TriageDecision.NEEDS_REVIEW.value:
        state["assigned_underwriter"] = None
        print(f"[route] NEEDS REVIEW -{state['summary']}")

    elif decision == TriageDecision.REJECTED.value:
        state["assigned_underwriter"] = None
        print(f"[route] REJECTED -{state['summary']}")

    return state
