"""Extract node — uses LLM to pull structured fields from raw email text."""

from __future__ import annotations

import json

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate

from src.models import ExtractedFields, LoanApplicationState

SYSTEM_PROMPT = """\
You are a loan application data extractor at Fundwell, a business financing company.

Your job is to extract structured information from incoming inquiry emails.
Follow these rules strictly:

1. Only extract information that is **explicitly stated** in the email.
2. If a field is not mentioned, return null — do NOT guess or infer.
3. For monetary values, normalize to plain numbers in USD:
   - "$45K/month" → revenue_amount: 45000, revenue_period: "monthly"
   - "$500,000 annual revenue" → revenue_amount: 500000, revenue_period: "annual"
   - If the period is unclear, set revenue_period to "unknown".
4. For years in business, calculate from the founding year if given:
   - "in business since 2019" with current year 2026 → years_in_business: 7
5. Extract only the PRIMARY applicant / business. If multiple entities are
   mentioned, focus on the one requesting the loan.

Return a valid JSON object matching this schema:

{schema}
"""

HUMAN_TEMPLATE = """\
Email from: {sender}
Subject: {subject}

{raw_email}
"""

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        ("human", HUMAN_TEMPLATE),
    ]
)

_SCHEMA_STR = json.dumps(ExtractedFields.model_json_schema(), indent=2)


def _get_llm():
    from src.config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL
    return ChatAnthropic(
        model=ANTHROPIC_MODEL,
        api_key=ANTHROPIC_API_KEY,
        temperature=0,
        max_tokens=1024,
    )


def extract_node(state: LoanApplicationState) -> LoanApplicationState:
    """Call the LLM to extract structured fields from the email body."""

    chain = prompt | _get_llm()
    response = chain.invoke(
        {
            "schema": _SCHEMA_STR,
            "sender": state.get("sender", ""),
            "subject": state.get("subject", ""),
            "raw_email": state.get("raw_email", ""),
        }
    )

    # Parse the LLM response - strip markdown fences if present
    content = response.content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

    try:
        extracted = ExtractedFields.model_validate_json(content)
    except Exception:
        # Fallback: try to find JSON object in the response
        start = content.find("{")
        end = content.rfind("}") + 1
        if start != -1 and end > start:
            extracted = ExtractedFields.model_validate_json(content[start:end])
        else:
            # If all parsing fails, return state with a risk flag
            state["risk_flags"] = state.get("risk_flags", []) + [
                "LLM extraction failed - could not parse response"
            ]
            return state

    # Normalize revenue to monthly
    monthly_revenue = None
    if extracted.revenue_amount is not None:
        if extracted.revenue_period == "annual":
            monthly_revenue = extracted.revenue_amount / 12
        elif extracted.revenue_period == "monthly":
            monthly_revenue = extracted.revenue_amount
        else:
            # Unknown period — assume monthly, flag for review
            monthly_revenue = extracted.revenue_amount
            state["risk_flags"] = state.get("risk_flags", []) + [
                "Revenue period unclear - assumed monthly"
            ]

    # Write extracted fields into state
    state["business_name"] = extracted.business_name
    state["owner_name"] = extracted.owner_name
    state["location"] = extracted.location
    state["years_in_business"] = extracted.years_in_business
    state["monthly_revenue"] = monthly_revenue
    state["loan_amount_requested"] = extracted.loan_amount_requested
    state["loan_purpose"] = extracted.loan_purpose
    state["existing_debt"] = extracted.existing_debt
    state["additional_notes"] = extracted.additional_notes

    return state
