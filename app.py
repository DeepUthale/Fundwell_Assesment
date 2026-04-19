"""
Fundwell AI Loan Triage Agent - Streamlit Dashboard
"""

import json
import os
from datetime import datetime, timezone

import streamlit as st

from src.graph import triage_app
from src.models import LoanApplicationState
from src.utils.email_fetcher import fetch_emails_imap
from src.utils.excel_export import generate_report

# Page config

st.set_page_config(
    page_title="Fundwell Loan Triage Agent",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Session state

if "processed" not in st.session_state:
    st.session_state.processed = []

# Helpers

DECISION_COLORS = {
    "qualified": "#d4edda",
    "needs_review": "#fff3cd",
    "rejected": "#f8d7da",
}

DECISION_EMOJI = {
    "qualified": "✅",
    "needs_review": "⚠️",
    "rejected": "❌",
}

SAMPLE_EMAILS = [
    {
        "sender": "maria.santos@brightsidebakery.com",
        "subject": "Financing for second location",
        "body": (
            "Hi, I own Brightside Bakery in Austin, TX. We've been in business "
            "since 2019 and bring in about $45K/month in revenue. I'm looking for "
            "$120,000 to open a second location and buy new equipment. We do have "
            "an existing SBA loan with about $30K remaining. Happy to provide "
            "whatever documentation you need. Thanks, Maria."
        ),
    },
    {
        "sender": "james@greenleaflandscaping.com",
        "subject": "Equipment financing for landscaping fleet",
        "body": (
            "Hi Fundwell team,\n\n"
            "I'm the founder of GreenLeaf Landscaping, based in Denver, CO. "
            "We started in 2015 and currently have 12 employees. Our annual "
            "revenue is around $1.2M. We're looking to borrow $350,000 for a "
            "fleet of electric trucks and new mowing equipment.\n\n"
            "We have a $50K line of credit with Chase that's about half drawn. "
            "Credit score is 720. Happy to share financials.\n\n"
            "Best,\nJames Park"
        ),
    },
    {
        "sender": "vague.applicant@gmail.com",
        "subject": "Loan inquiry",
        "body": (
            "Hello, I need a loan. Can you help? My business does okay and "
            "I need some money to expand. Let me know what you need from me."
        ),
    },
    {
        "sender": "newbiz2026@hotmail.com",
        "subject": "need money ASAP",
        "body": (
            "yo i need like 500k for my new restaurant idea. just started "
            "planning it last month. no revenue yet but trust me its gonna be "
            "huge. my uncle will co-sign if needed lol"
        ),
    },
]


def process_email(sender: str, subject: str, body: str) -> LoanApplicationState:
    """Run a single email through the triage pipeline."""
    state = LoanApplicationState(
        raw_email=body,
        sender=sender,
        subject=subject,
        date_received=datetime.now(timezone.utc).isoformat(),
        missing_fields=[],
        risk_flags=[],
        is_duplicate=False,
        confidence_score=1.0,
    )
    result = triage_app.invoke(state)
    st.session_state.processed.append(result)
    return result


def render_result_card(result: LoanApplicationState):
    """Render a single triage result as a styled card."""
    decision = result.get("triage_decision", "needs_review")
    color = DECISION_COLORS.get(decision, "#000000")
    emoji = DECISION_EMOJI.get(decision, "")

    st.markdown(
        f"""
        <div style="
            background-color: {color};
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 10px;
            border-left: 5px solid {'#28a745' if decision == 'qualified' else '#ffc107' if decision == 'needs_review' else '#dc3545'};
        ">
            <h3 style="margin:0; color:#000;">{emoji} {result.get('business_name') or 'Unknown Business'}</h3>
            <p style="margin:5px 0; color:#555;">
                {result.get('owner_name') or 'Unknown'} | {result.get('location') or 'Unknown location'} | {result.get('sender', '')}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        revenue = result.get("monthly_revenue", 0) or 0
        st.metric("Monthly Revenue", f"${revenue:,.0f}")
    with col2:
        loan = result.get("loan_amount_requested", 0) or 0
        st.metric("Loan Amount", f"${loan:,.0f}")
    with col3:
        ratio = result.get("revenue_to_loan_ratio")
        st.metric("Revenue/Loan Ratio", f"{ratio}x" if ratio else "N/A")
    with col4:
        conf = result.get("confidence_score", 0)
        st.metric("Confidence", f"{conf:.0%}")

    # Risk flags
    flags = result.get("risk_flags", [])
    if flags:
        with st.expander(f"Risk Flags ({len(flags)})"):
            for flag in flags:
                st.warning(flag)

    # Underwriter
    underwriter = result.get("assigned_underwriter")
    if underwriter:
        st.info(f"Assigned to: **{underwriter}**")

    # JSON view
    with st.expander("Raw JSON Output"):
        display = {
            "business_name": result.get("business_name"),
            "owner_name": result.get("owner_name"),
            "location": result.get("location"),
            "years_in_business": result.get("years_in_business"),
            "monthly_revenue": result.get("monthly_revenue"),
            "loan_amount_requested": result.get("loan_amount_requested"),
            "loan_purpose": result.get("loan_purpose"),
            "existing_debt": result.get("existing_debt"),
            "is_duplicate": result.get("is_duplicate"),
            "risk_flags": result.get("risk_flags"),
            "confidence_score": result.get("confidence_score"),
            "revenue_to_loan_ratio": result.get("revenue_to_loan_ratio"),
            "triage_decision": result.get("triage_decision"),
            "assigned_underwriter": result.get("assigned_underwriter"),
            "summary": result.get("summary"),
        }
        st.json(display)


# Sidebar

with st.sidebar:
    st.title("🏦 Fundwell")
    st.caption("AI Loan Triage Agent")
    st.divider()

    page = st.radio(
        "Navigation",
        ["📩 Triage Email", "📊 Dashboard", "📥 Export Report"],
        label_visibility="collapsed",
    )

    st.divider()
    st.markdown(f"**Processed:** {len(st.session_state.processed)} applications")

    if st.session_state.processed:
        qualified = sum(
            1 for a in st.session_state.processed if a.get("triage_decision") == "qualified"
        )
        review = sum(
            1 for a in st.session_state.processed if a.get("triage_decision") == "needs_review"
        )
        rejected = sum(
            1 for a in st.session_state.processed if a.get("triage_decision") == "rejected"
        )
        st.markdown(f"✅ Qualified: {qualified}")
        st.markdown(f"⚠️ Needs Review: {review}")
        st.markdown(f"❌ Rejected: {rejected}")

    st.divider()
    if st.button("Clear All Data", type="secondary"):
        st.session_state.processed = []
        st.rerun()


# Page: Triage Email

if page == "📩 Triage Email":
    st.header("📩 Triage a Loan Inquiry Email")

    tab1, tab2, tab3 = st.tabs(["Paste Email", "Fetch from Email", "Use Sample"])

    with tab1:
        with st.form("email_form"):
            sender = st.text_input("From (email)", placeholder="applicant@business.com")
            subject = st.text_input("Subject", placeholder="Loan inquiry")
            body = st.text_area(
                "Email Body",
                height=200,
                placeholder="Paste the loan inquiry email here...",
            )
            submitted = st.form_submit_button("Triage This Email", type="primary")

        if submitted:
            if not body.strip():
                st.error("Please paste an email body to triage.")
            else:
                with st.spinner("Processing email through triage pipeline..."):
                    result = process_email(sender, subject, body)
                st.success("Triage complete!")
                st.divider()
                render_result_card(result)

    with tab2:
        st.markdown("Fetch recent emails from your Gmail inbox and triage them.")
        st.info(
            "**Setup:** You need a Gmail App Password. "
            "Go to [Google Account > Security > App Passwords](https://myaccount.google.com/apppasswords) "
            "to generate one. (Requires 2-Step Verification to be enabled.)"
        )

        with st.form("fetch_email_form"):
            fetch_email = st.text_input(
                "Gmail Address",
                placeholder="you@gmail.com",
            )
            fetch_password = st.text_input(
                "App Password",
                type="password",
                placeholder="xxxx xxxx xxxx xxxx",
            )
            fetch_count = st.selectbox(
                "Number of emails to fetch",
                options=[5, 10, 15, 20],
                index=0,
            )
            fetch_submitted = st.form_submit_button("Fetch Emails", type="primary")

        if fetch_submitted:
            if not fetch_email.strip() or not fetch_password.strip():
                st.error("Please enter both your Gmail address and App Password.")
            else:
                with st.spinner(f"Fetching last {fetch_count} emails..."):
                    try:
                        fetched = fetch_emails_imap(
                            fetch_email.strip(),
                            fetch_password.strip(),
                            max_results=fetch_count,
                        )
                    except Exception as e:
                        st.error(f"Failed to fetch emails: {e}")
                        fetched = []

                if fetched:
                    st.success(f"Fetched {len(fetched)} emails.")
                    st.session_state["fetched_emails"] = fetched

        # Display fetched emails for triaging
        if "fetched_emails" in st.session_state and st.session_state["fetched_emails"]:
            st.divider()
            st.subheader(f"Fetched Emails ({len(st.session_state['fetched_emails'])})")

            for i, email_state in enumerate(st.session_state["fetched_emails"]):
                with st.expander(
                    f"{email_state.get('subject', '(no subject)')} — {email_state.get('sender', 'Unknown')}"
                ):
                    st.text(email_state.get("raw_email", "")[:500])
                    if st.button("Triage This Email", key=f"fetched_{i}"):
                        with st.spinner("Processing..."):
                            result = process_email(
                                email_state.get("sender", ""),
                                email_state.get("subject", ""),
                                email_state.get("raw_email", ""),
                            )
                        st.success("Done!")
                        render_result_card(result)

            if st.button("Triage All Fetched Emails", type="primary"):
                progress = st.progress(0)
                total = len(st.session_state["fetched_emails"])
                for i, email_state in enumerate(st.session_state["fetched_emails"]):
                    with st.spinner(f"Processing email {i + 1}/{total}..."):
                        result = process_email(
                            email_state.get("sender", ""),
                            email_state.get("subject", ""),
                            email_state.get("raw_email", ""),
                        )
                    progress.progress((i + 1) / total)
                st.success(f"All {total} emails triaged!")
                st.session_state["fetched_emails"] = []
                st.rerun()

    with tab3:
        st.markdown("Select a sample email to test the pipeline:")

        for i, sample in enumerate(SAMPLE_EMAILS):
            with st.expander(f"{sample['subject']} — {sample['sender']}"):
                st.text(sample["body"])
                if st.button(f"Triage This Email", key=f"sample_{i}"):
                    with st.spinner("Processing..."):
                        result = process_email(
                            sample["sender"], sample["subject"], sample["body"]
                        )
                    st.success("Done!")
                    render_result_card(result)


# Page: Dashboard

elif page == "📊 Dashboard":
    st.header("📊 Triage Dashboard")

    if not st.session_state.processed:
        st.info("No applications processed yet. Go to **Triage Email** to get started.")
    else:
        apps = st.session_state.processed

        # Summary metrics
        total = len(apps)
        qualified = sum(1 for a in apps if a.get("triage_decision") == "qualified")
        review = sum(1 for a in apps if a.get("triage_decision") == "needs_review")
        rejected = sum(1 for a in apps if a.get("triage_decision") == "rejected")
        total_loan = sum(a.get("loan_amount_requested", 0) or 0 for a in apps)

        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Total", total)
        col2.metric("Qualified", qualified)
        col3.metric("Needs Review", review)
        col4.metric("Rejected", rejected)
        col5.metric("Total Loan Volume", f"${total_loan:,.0f}")

        st.divider()

        # Filter
        filter_decision = st.selectbox(
            "Filter by decision",
            ["All", "qualified", "needs_review", "rejected"],
        )

        filtered = apps
        if filter_decision != "All":
            filtered = [a for a in apps if a.get("triage_decision") == filter_decision]

        # Display each application
        for i, result in enumerate(filtered):
            st.divider()
            render_result_card(result)


# Page: Export Report

elif page == "📥 Export Report":
    st.header("📥 Export to Excel")

    if not st.session_state.processed:
        st.info("No applications to export. Process some emails first.")
    else:
        st.markdown(
            f"**{len(st.session_state.processed)}** applications ready for export."
        )

        col1, col2 = st.columns(2)
        with col1:
            filename = st.text_input(
                "Filename (optional)",
                placeholder="loan_triage_report.xlsx",
            )

        if st.button("📥 Generate Excel Report", type="primary"):
            with st.spinner("Generating report..."):
                filepath = generate_report(
                    st.session_state.processed,
                    filename=filename if filename.strip() else None,
                )

            st.success(f"Report saved to `{filepath}`")

            # Provide download button
            with open(filepath, "rb") as f:
                st.download_button(
                    label="⬇️ Download Report",
                    data=f.read(),
                    file_name=os.path.basename(filepath),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )

        # Preview table
        st.divider()
        st.subheader("Preview")
        table_data = []
        for app in st.session_state.processed:
            table_data.append(
                {
                    "Business": app.get("business_name") or "N/A",
                    "Owner": app.get("owner_name") or "N/A",
                    "Revenue/mo": f"${(app.get('monthly_revenue') or 0):,.0f}",
                    "Loan Ask": f"${(app.get('loan_amount_requested') or 0):,.0f}",
                    "Ratio": f"{app.get('revenue_to_loan_ratio', 'N/A')}x",
                    "Decision": app.get("triage_decision", "N/A"),
                    "Confidence": f"{(app.get('confidence_score') or 0):.0%}",
                }
            )
        st.dataframe(table_data, use_container_width=True)
