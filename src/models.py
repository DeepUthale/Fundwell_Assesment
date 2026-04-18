from __future__ import annotations

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
from typing_extensions import TypedDict


# Enums

class TriageDecision(str, Enum):
    QUALIFIED = "qualified"
    NEEDS_REVIEW = "needs_review"
    REJECTED = "rejected"


class RevenuePeriod(str, Enum):
    MONTHLY = "monthly"
    ANNUAL = "annual"
    UNKNOWN = "unknown"


# Pydantic model used for LLM structured extraction

class ExtractedFields(BaseModel):
    """Fields extracted from a loan inquiry email by the LLM."""

    business_name: Optional[str] = Field(
        None, description="Name of the business applying for the loan"
    )
    owner_name: Optional[str] = Field(
        None, description="Name of the business owner / applicant"
    )
    location: Optional[str] = Field(
        None, description="City and state of the business"
    )
    years_in_business: Optional[int] = Field(
        None, description="How many years the business has been operating"
    )
    revenue_amount: Optional[float] = Field(
        None, description="Revenue amount as a number (e.g. 45000)"
    )
    revenue_period: Optional[RevenuePeriod] = Field(
        None, description="Whether the revenue figure is monthly or annual"
    )
    loan_amount_requested: Optional[float] = Field(
        None, description="Total loan amount requested in USD"
    )
    loan_purpose: Optional[str] = Field(
        None, description="What the funds will be used for"
    )
    existing_debt: Optional[str] = Field(
        None, description="Any existing loans or debts mentioned"
    )
    additional_notes: Optional[str] = Field(
        None, description="Any other relevant details from the email"
    )

# Graph state — shared across all nodes
class LoanApplicationState(TypedDict, total=False):
    # Raw input
    raw_email: str
    sender: str
    subject: str
    date_received: str

    # Extracted fields
    business_name: Optional[str]
    owner_name: Optional[str]
    location: Optional[str]
    years_in_business: Optional[int]
    monthly_revenue: Optional[float]
    loan_amount_requested: Optional[float]
    loan_purpose: Optional[str]
    existing_debt: Optional[str]
    additional_notes: Optional[str]

    # Validation
    missing_fields: list[str]

    # Enrichment
    is_duplicate: bool
    crm_match_id: Optional[str]

    # Scoring
    risk_flags: list[str]
    confidence_score: float
    revenue_to_loan_ratio: Optional[float]

    # Decision
    triage_decision: Optional[str]
    assigned_underwriter: Optional[str]
    summary: Optional[str]
