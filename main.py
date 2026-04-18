"""
Fundwell AI Loan Triage Agent
-----------------------------------
CLI entry point for processing loan inquiry emails and generating reports.

Usage:
    # Process sample emails (demo mode — no Gmail required)
    python main.py demo

    # Process emails from Gmail inbox
    python main.py process

    # Export today's processed applications to Excel
    python main.py export --range today

    # Export last 7 days
    python main.py export --range week

    # Export all
    python main.py export --range all
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone

from src.graph import triage_app
from src.models import LoanApplicationState
from src.nodes.ingest import fetch_unread_emails
from src.utils.excel_export import export_applications, generate_report

# In-memory store for processed applications
processed_applications: list[LoanApplicationState] = []

# Sample emails for demo mode

SAMPLE_EMAILS = [
    LoanApplicationState(
        raw_email=(
            "Hi, I own Brightside Bakery in Austin, TX. We've been in business "
            "since 2019 and bring in about $45K/month in revenue. I'm looking for "
            "$120,000 to open a second location and buy new equipment. We do have "
            "an existing SBA loan with about $30K remaining. Happy to provide "
            "whatever documentation you need. Thanks, Maria."
        ),
        sender="maria.santos@brightsidebakery.com",
        subject="Financing for second location",
        date_received=datetime.now(timezone.utc).isoformat(),
        missing_fields=[],
        risk_flags=[],
        is_duplicate=False,
        confidence_score=1.0,
    ),
    LoanApplicationState(
        raw_email=(
            "Hello, I need a loan. Can you help? My business does okay and "
            "I need some money to expand. Let me know what you need from me."
        ),
        sender="vague.applicant@gmail.com",
        subject="Loan inquiry",
        date_received=datetime.now(timezone.utc).isoformat(),
        missing_fields=[],
        risk_flags=[],
        is_duplicate=False,
        confidence_score=1.0,
    ),
    LoanApplicationState(
        raw_email=(
            "Hi Fundwell team,\n\n"
            "I'm the founder of GreenLeaf Landscaping, based in Denver, CO. "
            "We started in 2015 and currently have 12 employees. Our annual "
            "revenue is around $1.2M. We're looking to borrow $350,000 for a "
            "fleet of electric trucks and new mowing equipment.\n\n"
            "We have a $50K line of credit with Chase that's about half drawn. "
            "Credit score is 720. Happy to share financials.\n\n"
            "Best,\nJames Park"
        ),
        sender="james@greenleaflandscaping.com",
        subject="Equipment financing for landscaping fleet",
        date_received=datetime.now(timezone.utc).isoformat(),
        missing_fields=[],
        risk_flags=[],
        is_duplicate=False,
        confidence_score=1.0,
    ),
    LoanApplicationState(
        raw_email=(
            "yo i need like 500k for my new restaurant idea. just started "
            "planning it last month. no revenue yet but trust me its gonna be "
            "huge. my uncle will co-sign if needed lol"
        ),
        sender="newbiz2026@hotmail.com",
        subject="need money ASAP",
        date_received=datetime.now(timezone.utc).isoformat(),
        missing_fields=[],
        risk_flags=[],
        is_duplicate=False,
        confidence_score=1.0,
    ),
]


def process_email(state: LoanApplicationState) -> LoanApplicationState:
    """Run a single email through the triage pipeline."""
    result = triage_app.invoke(state)
    processed_applications.append(result)
    return result


def run_demo():
    """Process sample emails to demonstrate the pipeline."""
    print("=" * 70)
    print("  FUNDWELL AI LOAN TRIAGE AGENT - DEMO MODE")
    print("=" * 70)
    print(f"\nProcessing {len(SAMPLE_EMAILS)} sample emails...\n")

    for i, email in enumerate(SAMPLE_EMAILS, 1):
        print(f"\n{'-' * 60}")
        print(f"  Email {i}/{len(SAMPLE_EMAILS)}: {email['subject']}")
        print(f"  From: {email['sender']}")
        print(f"{'-' * 60}")

        result = process_email(email)

        # Print result summary
        print(f"\n  Business:    {result.get('business_name', 'N/A')}")
        print(f"  Owner:       {result.get('owner_name', 'N/A')}")
        print(f"  Revenue:     ${result.get('monthly_revenue', 0) or 0:,.0f}/mo")
        print(f"  Loan Ask:    ${result.get('loan_amount_requested', 0) or 0:,.0f}")
        print(f"  Ratio:       {result.get('revenue_to_loan_ratio', 'N/A')}x")
        print(f"  Risk Flags:  {result.get('risk_flags', [])}")
        print(f"  Confidence:  {result.get('confidence_score', 0):.2f}")
        print(f"  Decision:    {result.get('triage_decision', 'N/A')}")
        print(f"  Underwriter: {result.get('assigned_underwriter', 'N/A')}")
        print(f"  Summary:     {result.get('summary', '')}")

    # Generate Excel report
    print(f"\n{'=' * 70}")
    print("  GENERATING EXCEL REPORT")
    print(f"{'=' * 70}\n")

    filepath = generate_report(processed_applications)
    print(f"\nDone! Report saved to: {filepath}")

    # Also print JSON output for the first email (bonus deliverable)
    print(f"\n{'=' * 70}")
    print("  MOCK JSON OUTPUT (Email #1)")
    print(f"{'=' * 70}\n")

    first = processed_applications[0]
    json_output = {
        "business_name": first.get("business_name"),
        "owner_name": first.get("owner_name"),
        "location": first.get("location"),
        "years_in_business": first.get("years_in_business"),
        "monthly_revenue": first.get("monthly_revenue"),
        "loan_amount_requested": first.get("loan_amount_requested"),
        "loan_purpose": first.get("loan_purpose"),
        "existing_debt": first.get("existing_debt"),
        "is_duplicate": first.get("is_duplicate"),
        "risk_flags": first.get("risk_flags"),
        "confidence_score": first.get("confidence_score"),
        "revenue_to_loan_ratio": first.get("revenue_to_loan_ratio"),
        "triage_decision": first.get("triage_decision"),
        "assigned_underwriter": first.get("assigned_underwriter"),
        "summary": first.get("summary"),
    }
    print(json.dumps(json_output, indent=2))


def run_process():
    """Fetch and process real emails from Gmail."""
    print("Fetching unread emails from Gmail...")
    emails = fetch_unread_emails()

    if not emails:
        print("No unread emails found.")
        return

    print(f"Found {len(emails)} unread emails. Processing...\n")

    for i, email in enumerate(emails, 1):
        print(f"[{i}/{len(emails)}] Processing: {email['subject']} from {email['sender']}")
        result = process_email(email)
        print(f"  → {result.get('triage_decision', 'N/A')} | {result.get('summary', '')}\n")

    filepath = generate_report(processed_applications)
    print(f"\nReport saved to: {filepath}")


def run_export(date_range: str):
    """Export processed applications to Excel."""
    if not processed_applications:
        print("No processed applications in memory. Run 'demo' or 'process' first.")
        return

    filepath = export_applications(processed_applications, date_range=date_range)
    if filepath:
        print(f"Report saved to: {filepath}")


def main():
    parser = argparse.ArgumentParser(
        description="Fundwell AI Loan Triage Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # demo_command
    subparsers.add_parser("demo", help="Process sample emails (no Gmail required)")

    # process_command
    subparsers.add_parser("process", help="Fetch and process emails from Gmail")

    # export_command
    export_parser = subparsers.add_parser("export", help="Export applications to Excel")
    export_parser.add_argument(
        "--range",
        choices=["today", "week", "all"],
        default="today",
        help="Date range for export (default: today)",
    )

    args = parser.parse_args()

    if args.command == "demo":
        run_demo()
    elif args.command == "process":
        run_process()
    elif args.command == "export":
        run_export(args.range)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
