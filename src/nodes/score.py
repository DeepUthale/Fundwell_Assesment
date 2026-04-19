"""Score node — evaluates risk and assigns a triage decision."""

from __future__ import annotations

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate

from src.config import (
    MIN_REVENUE_TO_LOAN_RATIO,
    MIN_YEARS_IN_BUSINESS,
    QUALIFIED_THRESHOLD,
    REJECTION_THRESHOLD,
)
from src.models import LoanApplicationState, TriageDecision


def _get_llm():
    from src.config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL
    return ChatAnthropic(
        model=ANTHROPIC_MODEL,
        api_key=ANTHROPIC_API_KEY,
        temperature=0,
        max_tokens=512,
    )

RISK_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a risk analyst at a business lending company. "
            "Given the loan application details below, identify 0-3 specific "
            "risk factors that would NOT be caught by standard financial ratios. "
            "Focus on industry risk, stated purpose red flags, or inconsistencies. "
            "Return ONLY a JSON array of short risk strings. "
            'Example: ["Seasonal business may have inconsistent cash flow", '
            '"Equipment purchase with no asset backing detail"]. '
            "If there are no notable risks, return an empty array: []",
        ),
        (
            "human",
            "Business: {business_name}\n"
            "Location: {location}\n"
            "Years in business: {years_in_business}\n"
            "Monthly revenue: ${monthly_revenue}\n"
            "Loan requested: ${loan_amount}\n"
            "Purpose: {loan_purpose}\n"
            "Existing debt: {existing_debt}",
        ),
    ]
)


def score_node(state: LoanApplicationState) -> LoanApplicationState:
    """Apply rule-based and LLM-based scoring to determine triage decision."""

    risk_flags = list(state.get("risk_flags", []))

    # --- Rule-based checks ---
    monthly_revenue = state.get("monthly_revenue")
    loan_amount = state.get("loan_amount_requested")
    years = state.get("years_in_business")

    ratio = None
    if monthly_revenue and loan_amount and loan_amount > 0:
        ratio = (monthly_revenue * 12) / loan_amount
        state["revenue_to_loan_ratio"] = round(ratio, 2)
        if ratio < MIN_REVENUE_TO_LOAN_RATIO:
            risk_flags.append(
                f"Low revenue-to-loan ratio ({ratio:.1f}x - minimum {MIN_REVENUE_TO_LOAN_RATIO}x)"
            )
    else:
        state["revenue_to_loan_ratio"] = None

    if years is not None and years < MIN_YEARS_IN_BUSINESS:
        risk_flags.append(
            f"Business under {MIN_YEARS_IN_BUSINESS} years old ({years} yr)"
        )

    # --- LLM-based nuanced risk assessment ---
    try:
        chain = RISK_PROMPT | _get_llm()
        response = chain.invoke(
            {
                "business_name": state.get("business_name", "Unknown"),
                "location": state.get("location", "Unknown"),
                "years_in_business": years or "Unknown",
                "monthly_revenue": f"{monthly_revenue:,.0f}" if monthly_revenue else "Unknown",
                "loan_amount": f"{loan_amount:,.0f}" if loan_amount else "Unknown",
                "loan_purpose": state.get("loan_purpose", "Not stated"),
                "existing_debt": state.get("existing_debt", "None mentioned"),
            }
        )
        content = response.content.strip()
        # Parse JSON array from response
        import json

        if content.startswith("```"):
            content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        start = content.find("[")
        end = content.rfind("]") + 1
        if start != -1 and end > start:
            llm_risks = json.loads(content[start:end])
            risk_flags.extend(llm_risks)
    except Exception as e:
        risk_flags.append(f"LLM risk analysis unavailable: {e}")

    state["risk_flags"] = risk_flags

    # --- Compute confidence score ---
    flag_count = len(risk_flags)
    confidence = max(0.0, 1.0 - (flag_count * 0.15))
    state["confidence_score"] = round(confidence, 2)

    # --- Triage decision ---
    if confidence >= QUALIFIED_THRESHOLD and flag_count <= 1:
        state["triage_decision"] = TriageDecision.QUALIFIED.value
    elif confidence < REJECTION_THRESHOLD:
        state["triage_decision"] = TriageDecision.REJECTED.value
    else:
        state["triage_decision"] = TriageDecision.NEEDS_REVIEW.value

    return state
