"""
BillWatchdog — Streamlit Interactive Demo
4-Section Dual-Pane Layout:
  Left:  Budget Overview + Alert Inbox
  Right: Agent Activity Stream + Action Center
"""
import sys
import os
import json
import time
from datetime import datetime

# Ensure project root is importable
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import streamlit as st

from storage.db import init_db, get_budget_limits, get_all_bills_this_month, get_pending_reminders
from storage.seed_data import seed_all, DEMO_BILLS
from tools.extractor_tool import extract_invoice_entities
from tools.baseline_tool import query_billing_baseline
from tools.anomaly_tool import detect_bill_anomalies
from tools.budget_tool import evaluate_budget_impact, get_category
from tools.dispute_tool import draft_dispute_packet
from tools.scheduler_tool import schedule_renewal_deadline
from tools.narrative_tool import explain_spending_narrative


# ──────────────────────────────────────────────────────────────────────────
# Page Config & Styling
# ──────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="BillWatchdog — Silent Bill Sentinel",
    page_icon="💸",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    /* Global */
    .stApp { font-family: 'Inter', sans-serif; }
    [data-testid="stHeader"] { background: transparent; }
    .block-container { padding: 1rem 2rem !important; max-width: 1400px; }

    /* Hero Header */
    .hero-header {
        background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
        padding: 1.5rem 2rem;
        border-radius: 16px;
        margin-bottom: 1.5rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .hero-title {
        color: #fff;
        font-size: 1.8rem;
        font-weight: 800;
        letter-spacing: -0.5px;
    }
    .hero-subtitle {
        color: #b8b5ff;
        font-size: 0.9rem;
        font-weight: 400;
        margin-top: 4px;
    }
    .hero-badge {
        background: rgba(74, 222, 128, 0.15);
        color: #4ade80;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
    }

    /* Cards */
    .metric-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 14px;
        padding: 1.2rem;
        margin-bottom: 0.8rem;
    }
    .metric-label {
        color: #8b8fa3;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 600;
    }
    .metric-value {
        color: #fff;
        font-size: 1.6rem;
        font-weight: 700;
        margin-top: 4px;
    }
    .metric-value.green { color: #4ade80; }
    .metric-value.amber { color: #fbbf24; }
    .metric-value.red { color: #f87171; }

    /* Progress Bar */
    .budget-bar-bg {
        background: rgba(255,255,255,0.05);
        border-radius: 8px;
        height: 12px;
        overflow: hidden;
        margin-top: 6px;
    }
    .budget-bar-fill {
        height: 100%;
        border-radius: 8px;
        transition: width 0.6s ease;
    }

    /* Event Stream */
    .event-stream {
        background: #0d1117;
        border: 1px solid #21262d;
        border-radius: 12px;
        padding: 1rem;
        font-family: 'JetBrains Mono', 'Fira Code', monospace;
        font-size: 0.78rem;
        max-height: 480px;
        overflow-y: auto;
        color: #c9d1d9;
    }
    .event-line {
        padding: 3px 0;
        border-bottom: 1px solid rgba(255,255,255,0.03);
    }
    .event-time { color: #484f58; }
    .event-tool { color: #79c0ff; font-weight: 600; }
    .event-ok { color: #3fb950; }
    .event-warn { color: #d29922; }
    .event-alert { color: #f85149; }

    /* Alert Card */
    .alert-card {
        background: linear-gradient(135deg, #1c1a2e, #2a1f3d);
        border-left: 4px solid #f85149;
        border-radius: 10px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.8rem;
    }
    .alert-card.silent {
        border-left-color: #3fb950;
        background: linear-gradient(135deg, #1a2e1c, #1f3d2a);
    }
    .alert-merchant {
        color: #fff;
        font-weight: 700;
        font-size: 1rem;
    }
    .alert-detail {
        color: #b8b5ff;
        font-size: 0.82rem;
        margin-top: 4px;
    }

    /* Dispute Box */
    .dispute-box {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 1rem;
        margin-top: 0.5rem;
    }
    .dispute-box pre {
        color: #c9d1d9;
        white-space: pre-wrap;
        word-wrap: break-word;
        font-size: 0.78rem;
    }

    /* Hide Streamlit Branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    [data-testid="stToolbar"] {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────
# Session State Init
# ──────────────────────────────────────────────────────────────────────────

if "initialized" not in st.session_state:
    init_db()
    seed_all()
    st.session_state.initialized = True
    st.session_state.event_log = []
    st.session_state.alerts = []
    st.session_state.processed_bills = set()
    st.session_state.disputes = {}
    st.session_state.bill_results = {}


def log_event(icon: str, tool_name: str, message: str, level: str = "ok"):
    ts = datetime.now().strftime("%H:%M:%S")
    st.session_state.event_log.append({
        "time": ts,
        "icon": icon,
        "tool": tool_name,
        "message": message,
        "level": level,  # ok, warn, alert
    })


# ──────────────────────────────────────────────────────────────────────────
# Hero Header
# ──────────────────────────────────────────────────────────────────────────

st.markdown("""
<div class="hero-header">
    <div>
        <div class="hero-title">💸 BillWatchdog</div>
        <div class="hero-subtitle">Watch your bills. Understand your spending. Catch surprises before they cost you.</div>
    </div>
    <div class="hero-badge">🤖 Agent: Active</div>
</div>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────
# Main Layout: Left (Budget + Alerts) | Right (Agent Stream + Actions)
# ──────────────────────────────────────────────────────────────────────────


# ──────────────────────────────────────────────────────────────────────────
# Sidebar: User Account & Quota Simulation (Pre-auth architecture)
# ──────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 👤 User Account")
    st.caption("In production, `user_id` is extracted from AWS Cognito / OAuth JWT. For this demo, switch or reset users here.")
    user_id = st.text_input("Active User ID", value="user_1", key="global_user_id")
    
    from metering.tier_engine import (
        get_user_tier, set_user_tier, check_email_quota, TIERS,
        is_quota_enforcement_enabled, set_quota_enforcement
    )
    enforce_quota = st.toggle(
        "🔒 Enforce Tier Quotas (Prod)",
        value=is_quota_enforcement_enabled(),
        key="prod_quota_enforce_toggle",
        help="OFF by default for demo & testing (unlimited scans). Turn ON when moving to production."
    )
    set_quota_enforcement(enforce_quota)
    current_tier = get_user_tier(user_id)
    selected_tier = st.selectbox(
        "Active Plan",
        options=["free", "pro", "enterprise"],
        index=["free", "pro", "enterprise"].index(current_tier),
        format_func=lambda x: {
            "free": "🆓 Free (10/day)",
            "pro": "⚡ Pro (50/day) — ₹299/mo",
            "enterprise": "🏢 Enterprise (Unlimited)"
        }[x],
        key="sidebar_plan_select"
    )
    if selected_tier != current_tier:
        set_user_tier(user_id, selected_tier)
        st.rerun()
        
    quota_info = check_email_quota(user_id, requested=0)
    st.markdown(f"**Quota Today:** `{quota_info['total_scanned_today']}` / `{quota_info['daily_limit']}` emails")
    
    if st.button("🔄 Reset Today's Quota", use_container_width=True, help="Clear today's scan count for testing"):
        import sqlite3
        from datetime import date
        conn = sqlite3.connect("storage/billwatchdog.db")
        conn.execute("DELETE FROM usage_events WHERE user_id = ? AND timestamp LIKE ?", (user_id, f"{date.today().isoformat()}%"))
        conn.commit()
        conn.close()
        st.success("Quota reset!")
        time.sleep(0.5)
        st.rerun()
        
    st.divider()
    st.markdown("### 🛠️ Architecture Note")
    st.caption("All SQLite tables (`bills`, `baselines`, `usage_events`) filter by `user_id`. Multi-tenancy is fully implemented at the database & tool layer.")

left_col, right_col = st.columns([1, 1], gap="large")


# ═══════════════════════════════════════════════════════════════════════════
# LEFT COLUMN: Budget Overview + Alert Inbox
# ═══════════════════════════════════════════════════════════════════════════

with left_col:
    # ── Section 1: Budget Overview ──
    st.markdown("### 📊 Budget Overview")

    # user_id is provided by sidebar
    limits = get_budget_limits(user_id)
    total_budget = limits.get("total", 50000)
    this_month_bills = get_all_bills_this_month(user_id)
    spent = sum(b["total_amount"] for b in this_month_bills)
    remaining = max(0, total_budget - spent)
    pct = min(100, (spent / total_budget * 100) if total_budget > 0 else 0)

    now = datetime.now()
    days_elapsed = now.day
    import calendar
    days_in_month = calendar.monthrange(now.year, now.month)[1]
    daily_rate = spent / days_elapsed if days_elapsed > 0 else 0
    projected = daily_rate * days_in_month

    # Metric cards row
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Budget</div>
            <div class="metric-value">₹{total_budget:,.0f}</div>
        </div>""", unsafe_allow_html=True)
    with m2:
        color_class = "green" if pct < 75 else ("amber" if pct < 95 else "red")
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Spent</div>
            <div class="metric-value {color_class}">₹{spent:,.0f}</div>
        </div>""", unsafe_allow_html=True)
    with m3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Remaining</div>
            <div class="metric-value green">₹{remaining:,.0f}</div>
        </div>""", unsafe_allow_html=True)
    with m4:
        proj_color = "green" if projected <= total_budget else "red"
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Forecast</div>
            <div class="metric-value {proj_color}">₹{projected:,.0f}</div>
        </div>""", unsafe_allow_html=True)

    # Progress bar
    bar_color = "#4ade80" if pct < 75 else ("#fbbf24" if pct < 95 else "#f85149")
    st.markdown(f"""
    <div class="budget-bar-bg">
        <div class="budget-bar-fill" style="width:{pct:.1f}%; background:{bar_color};"></div>
    </div>
    <p style="color:#8b8fa3; font-size:0.75rem; margin-top:4px; text-align:right;">
        {pct:.1f}% of monthly budget used
    </p>
    """, unsafe_allow_html=True)

    # Category breakdown
    cat_spend = {}
    for b in this_month_bills:
        cat = get_category(b["merchant_name"])
        cat_spend[cat] = cat_spend.get(cat, 0) + b["total_amount"]

    if cat_spend:
        cats_to_show = ["subscriptions", "utilities", "internet", "insurance", "other"]
        for cat in cats_to_show:
            s = cat_spend.get(cat, 0)
            lim = limits.get(cat, 0)
            if lim > 0:
                cpct = min(100, s / lim * 100)
                c_color = "#4ade80" if cpct < 85 else ("#fbbf24" if cpct < 100 else "#f85149")
                status_icon = "✅" if cpct < 85 else ("⚠️" if cpct < 100 else "🔴")
                st.markdown(f"""
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                    <span style="color:#c9d1d9; font-size:0.82rem;">{status_icon} {cat.capitalize()}</span>
                    <span style="color:#8b8fa3; font-size:0.78rem;">₹{s:,.0f} / ₹{lim:,.0f}</span>
                </div>
                <div class="budget-bar-bg" style="height:6px; margin-bottom:8px;">
                    <div class="budget-bar-fill" style="width:{cpct:.1f}%; background:{c_color}; height:100%;"></div>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("---")

    # ── Section 3: Alert Inbox ──
    st.markdown("### 🔔 Alert Inbox")

    if st.session_state.alerts:
        for alert in st.session_state.alerts:
            card_class = "silent" if alert["severity"] == "SILENT" else ""
            icon = "🟢" if alert["severity"] == "SILENT" else "🔴"
            st.markdown(f"""
            <div class="alert-card {card_class}">
                <div class="alert-merchant">{icon} {alert['merchant']}</div>
                <div class="alert-detail">{alert['detail']}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="color:#484f58; text-align:center; padding:2rem; font-style:italic;">
            No alerts yet. Process bills to see the agent in action.
        </div>
        """, unsafe_allow_html=True)

    # ── Explain My Spending ──
    st.markdown("---")
    st.markdown("### 💬 Ask BillWatchdog")
    user_q = st.text_input(
        "Ask about your spending:",
        placeholder="e.g. What changed most this month?",
        key="spending_question",
        label_visibility="collapsed",
    )
    if st.button("🤖 Ask Agent", key="ask_btn", use_container_width=True):
        if user_q:
            with st.spinner("Agent reasoning across all bills..."):
                narrative = explain_spending_narrative(
                    user_id=user_id,
                    user_query=user_q,
                )
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Agent Response</div>
                <div style="color:#c9d1d9; font-size:0.85rem; white-space:pre-wrap; margin-top:8px;">{narrative}</div>
            </div>
            """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# RIGHT COLUMN: Agent Activity Stream + Bill Processing + Action Center
# ═══════════════════════════════════════════════════════════════════════════

with right_col:
    # ── Bill Processing Controls ──
    st.markdown("### 🧾 Process Bills & Statements")
    tab_demo, tab_upload = st.tabs(["⚡ Demo Bills (10)", "📤 Upload Bank PDF"])

    with tab_upload:
        st.markdown("##### 📤 Upload Monthly Bank Statement PDF")
        st.caption("Upload a statement PDF (HDFC, ICICI, SBI, IndusInd, etc.). If password-protected, BillWatchdog decrypts it in-memory with zero-storage privacy.")

        uploaded_pdf = st.file_uploader(
            "Choose Statement PDF",
            type=["pdf"],
            key="statement_pdf_uploader",
            help="Your file is processed 100% locally in volatile RAM"
        )

        if uploaded_pdf is not None:
            pdf_bytes = uploaded_pdf.read()
            from tools.pdf_statement_tool import inspect_pdf_bytes, decrypt_and_extract_statement
            pdf_info = inspect_pdf_bytes(pdf_bytes)

            is_enc = pdf_info.get("is_encrypted", False)
            if is_enc:
                st.warning("🔒 **Password-Protected Statement Detected**")
                st.caption("Common bank formats: PAN (uppercase) or First 4 letters of name + DOB (DDMM)")
                upload_pwd = st.text_input(
                    "Statement Password",
                    type="password",
                    placeholder="e.g. IN1995 or ABCD1234E",
                    key="upload_pdf_pwd_input",
                    help="Never saved to database, logs, or disk."
                )
            else:
                st.info("📄 PDF is unencrypted. Ready to analyze.")
                upload_pwd = ""

            if st.button("🚀 Decrypt & Analyze Statement", type="primary", use_container_width=True, key="analyze_uploaded_pdf_btn"):
                if is_enc and not upload_pwd:
                    st.error("Please enter the statement password to decrypt.")
                else:
                    with st.spinner("Decrypting in-memory & running through 6-tool pipeline..."):
                        dec_result = decrypt_and_extract_statement(pdf_bytes, password=upload_pwd)
                        if not dec_result.get("success"):
                            st.error(f"❌ {dec_result.get('error', 'Failed to extract statement')}")
                        else:
                            up_invoice = dec_result["invoice"]
                            st.success(f"✅ Extracted: **{up_invoice['merchant_name']}** — **₹{up_invoice['total_amount']:,.2f}**")

                            upload_bill_id = f"upload_{int(time.time())}"
                            st.session_state.processed_bills.add(upload_bill_id)

                            log_event("📄", "extract_invoice_entities", f"Uploaded PDF: {up_invoice['merchant_name']} ₹{up_invoice['total_amount']:,.0f}")

                            # Step 2: Baseline
                            baseline = query_billing_baseline(user_id=user_id, merchant_name=up_invoice["merchant_name"])
                            log_event("📊", "query_billing_baseline", f"Baseline ₹{baseline.get('average_monthly_spend', 0):,.0f}")

                            # Step 3: Anomaly
                            anomaly = detect_bill_anomalies(current_invoice=up_invoice, baseline_data=baseline)
                            log_event("🔍", "detect_bill_anomalies", f"{anomaly['anomaly_type']} (Δ ₹{anomaly['delta_amount']:+,.0f})")

                            # Step 4: Budget
                            budget = evaluate_budget_impact(user_id=user_id, current_invoice=up_invoice, anomaly=anomaly)
                            log_event("💰", "evaluate_budget_impact", budget["budget_status"])

                            # Step 5: Dispute / Alert
                            dispute = None
                            if anomaly["is_anomaly"] and anomaly["severity"] == "ACTION_REQUIRED":
                                dispute = draft_dispute_packet(
                                    merchant_name=up_invoice["merchant_name"],
                                    anomaly=anomaly,
                                    account_info={"account_id": "UPLOAD-BANK", "months_as_customer": 12, "payment_record": "good"},
                                )
                                st.session_state.disputes[upload_bill_id] = dispute
                                st.session_state.alerts.append({
                                    "merchant": up_invoice["merchant_name"],
                                    "severity": "ACTION_REQUIRED",
                                    "detail": f"₹{up_invoice['total_amount']:,.0f} — {anomaly['root_cause_explanation']}",
                                })
                            else:
                                st.session_state.alerts.append({
                                    "merchant": up_invoice["merchant_name"],
                                    "severity": "SILENT",
                                    "detail": f"₹{up_invoice['total_amount']:,.0f} — Normal monthly statement. Silently archived.",
                                })

                            # Insert into SQLite so Budget Overview & Safe-to-Spend update
                            insert_bill({
                                "user_id": user_id,
                                "merchant_name": up_invoice["merchant_name"],
                                "invoice_date": up_invoice.get("invoice_date", datetime.now().strftime("%Y-%m-%d")),
                                "total_amount": up_invoice["total_amount"],
                                "currency": up_invoice.get("currency", "INR"),
                                "silent": 0 if (anomaly["is_anomaly"] and anomaly["severity"] == "ACTION_REQUIRED") else 1,
                                "alert_reason": anomaly["root_cause_explanation"] if anomaly["is_anomaly"] else None,
                            })

                            st.session_state.bill_results[upload_bill_id] = {
                                "invoice": up_invoice,
                                "baseline": baseline,
                                "anomaly": anomaly,
                                "budget": budget,
                                "dispute": dispute,
                            }

                            time.sleep(0.5)
                            st.rerun()

    with tab_demo:
        selected = st.selectbox(
            "Select a demo bill to process:",
            [b["label"] for b in DEMO_BILLS],
            key="bill_select",
        )

    if st.button("⚡ Process This Bill", key="process_btn", type="primary", use_container_width=True):
        bill_obj = next(b for b in DEMO_BILLS if b["label"] == selected)
        bill_data = bill_obj["raw"]
        bill_id = bill_obj["id"]

        if bill_id in st.session_state.processed_bills:
            st.warning(f"Bill already processed: {bill_data['merchant_name']}")
        else:
            st.session_state.processed_bills.add(bill_id)
            progress = st.empty()

            # ── Step 1: Extract ──
            progress.markdown("🔄 **Step 1/5**: Extracting invoice entities...")
            log_event("📄", "extract_invoice_entities", f"Parsing {bill_data['merchant_name']}...")
            invoice = extract_invoice_entities(
                raw_content=json.dumps(bill_data),
                source_type="json",
            )
            log_event("✅", "extract_invoice_entities",
                       f"{invoice['merchant_name']} ₹{invoice['total_amount']:,.0f} extracted")
            time.sleep(0.3)

            # ── Step 2: Baseline ──
            progress.markdown("🔄 **Step 2/5**: Querying billing baseline...")
            log_event("📊", "query_billing_baseline", f"Fetching history for {invoice['merchant_name']}...")
            baseline = query_billing_baseline(
                user_id=user_id,
                merchant_name=invoice["merchant_name"],
            )
            if baseline["has_history"]:
                log_event("✅", "query_billing_baseline",
                           f"Baseline ₹{baseline['average_monthly_spend']:,.0f} ({baseline['baseline_months']}mo)")
            else:
                log_event("ℹ️", "query_billing_baseline", "No prior history — new vendor", "warn")
            time.sleep(0.3)

            # ── Step 3: Anomaly Detection ──
            progress.markdown("🔄 **Step 3/5**: Detecting anomalies...")
            log_event("🔍", "detect_bill_anomalies", "Evaluating delta, promos, fees...")
            anomaly = detect_bill_anomalies(
                current_invoice=invoice,
                baseline_data=baseline,
            )
            if anomaly["is_anomaly"]:
                log_event("🔴", "detect_bill_anomalies",
                           f"ANOMALY: {anomaly['anomaly_type']} — {anomaly['root_cause_explanation'][:80]}...",
                           "alert")
            else:
                log_event("🟢", "detect_bill_anomalies",
                           f"NORMAL: {anomaly['root_cause_explanation'][:80]}")
            time.sleep(0.3)

            # ── Step 4: Budget Impact ──
            progress.markdown("🔄 **Step 4/5**: Evaluating budget impact...")
            log_event("💰", "evaluate_budget_impact", "Calculating Safe-to-Spend & projections...")
            budget = evaluate_budget_impact(
                user_id=user_id,
                current_invoice=invoice,
                anomaly=anomaly,
            )
            budget_icon = "🟢" if budget["budget_status"] == "ON_TRACK" else "🔴"
            log_event(budget_icon, "evaluate_budget_impact", budget["impact_statement"][:100])
            time.sleep(0.3)

            # ── Step 5: Dispute / Silent Archive ──
            dispute = None
            if anomaly["is_anomaly"] and anomaly["severity"] == "ACTION_REQUIRED":
                progress.markdown("🔄 **Step 5/5**: Drafting dispute packet...")
                log_event("📝", "draft_dispute_packet", f"Generating dispute email for {invoice['merchant_name']}...")
                dispute = draft_dispute_packet(
                    merchant_name=invoice["merchant_name"],
                    anomaly=anomaly,
                    account_info={"account_id": "ACC-9283", "months_as_customer": 18, "payment_record": "excellent"},
                )
                log_event("✅", "draft_dispute_packet", "Dispute email ready for review")

                st.session_state.disputes[bill_id] = dispute
                st.session_state.alerts.append({
                    "merchant": invoice["merchant_name"],
                    "severity": "ACTION_REQUIRED",
                    "detail": (
                        f"₹{baseline.get('average_monthly_spend', 0):,.0f} → ₹{invoice['total_amount']:,.0f} "
                        f"(+{anomaly['delta_percentage']:.0f}%) — {anomaly['anomaly_type'].replace('_', ' ')}"
                    ),
                })
                progress.markdown(f"🔴 **ACTION REQUIRED** — {invoice['merchant_name']}: {anomaly['root_cause_explanation'][:100]}")
            else:
                log_event("🟢", "DECISION", f"SILENT — {invoice['merchant_name']} archived. 0 notifications.", "ok")
                st.session_state.alerts.append({
                    "merchant": invoice["merchant_name"],
                    "severity": "SILENT",
                    "detail": f"₹{invoice['total_amount']:,.0f} — Normal. Silently archived.",
                })
                progress.markdown(f"🟢 **SILENT** — {invoice['merchant_name']} stored quietly. No notification sent.")

            # Save result
            st.session_state.bill_results[bill_id] = {
                "invoice": invoice,
                "baseline": baseline,
                "anomaly": anomaly,
                "budget": budget,
                "dispute": dispute,
            }

            # Re-run to update budget overview and alerts
            time.sleep(0.5)
            st.rerun()

    # Process All button
    st.markdown("")
    if st.button(f"🚀 Process All {len(DEMO_BILLS)} Bills (Full Demo)", key="process_all_btn", use_container_width=True):
        for bill_obj in DEMO_BILLS:
            bill_data = bill_obj["raw"]
            bill_id = bill_obj["id"]

            if bill_id in st.session_state.processed_bills:
                continue

            st.session_state.processed_bills.add(bill_id)

            # Step 1: Extract
            log_event("📄", "extract_invoice_entities", f"Parsing {bill_data['merchant_name']}...")
            invoice = extract_invoice_entities(raw_content=json.dumps(bill_data), source_type="json")
            log_event("✅", "extract_invoice_entities", f"{invoice['merchant_name']} ₹{invoice['total_amount']:,.0f}")

            # Step 2: Baseline
            log_event("📊", "query_billing_baseline", f"Fetching {invoice['merchant_name']}...")
            baseline = query_billing_baseline(user_id=user_id, merchant_name=invoice["merchant_name"])
            log_event("✅", "query_billing_baseline", f"Baseline: ₹{baseline.get('average_monthly_spend', 'N/A')}")

            # Step 3: Anomaly
            log_event("🔍", "detect_bill_anomalies", "Evaluating...")
            anomaly = detect_bill_anomalies(current_invoice=invoice, baseline_data=baseline)

            # Step 4: Budget
            log_event("💰", "evaluate_budget_impact", "Calculating...")
            budget = evaluate_budget_impact(user_id=user_id, current_invoice=invoice, anomaly=anomaly)

            # Step 5: Decision
            dispute = None
            if anomaly["is_anomaly"] and anomaly["severity"] == "ACTION_REQUIRED":
                log_event("🔴", "detect_bill_anomalies", f"ANOMALY: {anomaly['anomaly_type']}", "alert")
                dispute = draft_dispute_packet(
                    merchant_name=invoice["merchant_name"],
                    anomaly=anomaly,
                    account_info={"account_id": "ACC-9283", "months_as_customer": 18, "payment_record": "excellent"},
                )
                log_event("📝", "draft_dispute_packet", "Dispute ready", "alert")
                st.session_state.disputes[bill_id] = dispute
                st.session_state.alerts.append({
                    "merchant": invoice["merchant_name"],
                    "severity": "ACTION_REQUIRED",
                    "detail": f"₹{baseline.get('average_monthly_spend', 0):,.0f} → ₹{invoice['total_amount']:,.0f} (+{anomaly['delta_percentage']:.0f}%)",
                })
            else:
                log_event("🟢", "DECISION", f"SILENT — {invoice['merchant_name']} archived.", "ok")
                st.session_state.alerts.append({
                    "merchant": invoice["merchant_name"],
                    "severity": "SILENT",
                    "detail": f"₹{invoice['total_amount']:,.0f} — Normal.",
                })

            log_event("─" * 3, "─" * 20, "─" * 30)

            st.session_state.bill_results[bill_id] = {
                "invoice": invoice, "baseline": baseline,
                "anomaly": anomaly, "budget": budget, "dispute": dispute,
            }

        st.rerun()

    st.markdown("---")

    # ── Section 2: Agent Activity Stream ──
    st.markdown("### 🤖 Agent Activity Stream")

    if st.session_state.event_log:
        event_html = ""
        for ev in st.session_state.event_log:
            level_class = f"event-{ev['level']}"
            event_html += (
                f'<div class="event-line">'
                f'<span class="event-time">[{ev["time"]}]</span> '
                f'{ev["icon"]} '
                f'<span class="event-tool">{ev["tool"]}</span> '
                f'<span class="{level_class}">{ev["message"]}</span>'
                f'</div>'
            )
        st.markdown(f'<div class="event-stream">{event_html}</div>', unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="event-stream" style="text-align:center; padding:3rem; color:#484f58;">
            <p style="font-size:1.5rem;">🤖</p>
            <p>Agent waiting for bills to process...</p>
            <p style="font-size:0.7rem;">Select a bill above and click "Process This Bill"</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # ── Section 4: Action Center (Dispute Drafts) ──
    st.markdown("### ⚡ Action Center")

    action_bills = {bid: res for bid, res in st.session_state.bill_results.items()
                    if res.get("dispute")}

    if action_bills:
        for bid, res in action_bills.items():
            inv = res["invoice"]
            ano = res["anomaly"]
            disp = res["dispute"]
            bud = res["budget"]

            st.markdown(f"""
            <div class="alert-card">
                <div class="alert-merchant">🔴 {inv['merchant_name']}</div>
                <div class="alert-detail">
                    ₹{bud.get('category_breakdown', {}).get(get_category(inv['merchant_name']), {}).get('spent', 0):,.0f}
                    / ₹{bud.get('category_breakdown', {}).get(get_category(inv['merchant_name']), {}).get('limit', 0):,.0f}
                    ({get_category(inv['merchant_name']).capitalize()})
                    — {ano['root_cause_explanation'][:120]}
                </div>
            </div>
            """, unsafe_allow_html=True)

            with st.expander(f"📧 View Dispute Draft — {inv['merchant_name']}", expanded=False):
                st.markdown(f"**Subject:** {disp['email_subject']}")
                st.markdown(f"""
                <div class="dispute-box"><pre>{disp['email_body']}</pre></div>
                """, unsafe_allow_html=True)

                c1, c2, c3 = st.columns(3)
                with c1:
                    if st.button("📧 Send Email", key=f"send_{bid}", use_container_width=True):
                        st.success(f"✅ Email sent to {inv['merchant_name']}!")
                with c2:
                    if st.button("📞 Call Script", key=f"call_{bid}", use_container_width=True):
                        st.info(f"📞 {disp['alternative_action']}")
                with c3:
                    if st.button("✅ Accept", key=f"accept_{bid}", use_container_width=True):
                        st.success("Marked as accepted.")
    else:
        st.markdown("""
        <div style="color:#484f58; text-align:center; padding:2rem; font-style:italic;">
            No actions required yet. Process bills to see dispute drafts here.
        </div>
        """, unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────
# Footer
# ──────────────────────────────────────────────────────────────────────────

st.markdown("---")
st.markdown("""
<div style="text-align:center; color:#484f58; font-size:0.75rem; padding:1rem;">
    Built with <strong>AWS Strands Agents SDK</strong> · <strong>Amazon Bedrock AgentCore</strong> · <strong>Streamlit</strong><br>
    BillWatchdog — Agents for Humans Hackathon 2026
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# TAB-BASED SECONDARY SECTION: Email Inbox + Usage Dashboard
# ═══════════════════════════════════════════════════════════════════════════

st.markdown("---")
tab_email, tab_usage = st.tabs(["📧 Email Inbox (Auto-Scan)", "📈 Usage & SaaS Metrics"])


# ──────────────────────────────────────────────────────────────────────────
# TAB: Email Inbox Scanner
# ──────────────────────────────────────────────────────────────────────────

with tab_email:
    from inboxes.base_adapter import get_adapter
    from tools.email_tool import fetch_billing_emails
    from metering.tier_engine import get_user_tier, set_user_tier, TIERS, get_tier_info

    col_cfg, col_results = st.columns([1, 2], gap="large")

    with col_cfg:
        st.markdown("#### ⚙️ Inbox Configuration")

        # Provider selector — the Adapter Pattern in action for judges
        provider = st.selectbox(
            "Email Provider",
            options=["mock", "imap", "oauth2_gmail"],
            format_func=lambda x: {
                "mock":         "🎭 Mock Demo Inbox (20 synthetic bills)",
                "imap":         "📬 Gmail / Outlook (IMAP + App Password)",
                "oauth2_gmail": "🔐 Gmail OAuth2 (Production)",
            }[x],
            key="email_provider",
        )

        max_emails = st.slider("Max emails to scan", min_value=5, max_value=20, value=15, step=5)

        # Tier display & quota status (managed via sidebar)
        current_tier = get_user_tier(user_id)
        quota_check = check_email_quota(user_id, requested=0)
        st.markdown(f"**Plan:** `{current_tier.upper()}` · Scanned today: `{quota_check['total_scanned_today']} / {quota_check['daily_limit']}`")

        # Show IMAP credentials if selected — with persistent keys so text is NEVER cleared on refresh
        imap_creds = {}
        if provider == "imap":
            st.markdown("**IMAP Credentials:**")
            email_val = st.text_input(
                "Email Address",
                placeholder="you@gmail.com",
                key="persistent_imap_email",
                help="Your full email address"
            )
            pwd_val = st.text_input(
                "App Password",
                type="password",
                placeholder="xxxx xxxx xxxx xxxx",
                key="persistent_imap_pwd",
                help="16-character Google App Password from myaccount.google.com/apppasswords"
            )
            host_val = st.text_input(
                "IMAP Host",
                value="imap.gmail.com",
                key="persistent_imap_host"
            )
            imap_creds = {
                "email_address": email_val,
                "app_password": pwd_val,
                "imap_host": host_val,
            }
            st.info("💡 Gmail requires a 16-character **App Password** from [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)")
        elif provider == "oauth2_gmail":
            st.warning("⚠️ OAuth2 requires `gmail_credentials.json`. See `inboxes/oauth2_gmail_adapter.py` for setup. Use Mock for demo.")

        # Bank & Statement Filter
        bank_choice = st.selectbox(
            "Filter Messages By",
            options=["all", "all_banks", "hdfc", "icici", "sbi", "axis", "amex", "custom"],
            format_func=lambda x: {
                "all":        "🌐 All Bills & Invoices (No filter)",
                "all_banks":  "🏦 All Banks & Card Statements Only",
                "hdfc":       "💳 HDFC Bank Statements",
                "icici":      "💳 ICICI Bank Statements",
                "sbi":        "💳 SBI Card e-Statements",
                "axis":       "💳 Axis Bank Alerts",
                "amex":       "💳 American Express Statements",
                "custom":     "🔍 Custom Bank / Keyword...",
            }[x],
            key="bank_filter_select",
            help="Filter specifically for bank e-statements, card bills, and transaction alerts"
        )
        custom_kw = None
        if bank_choice == "custom":
            custom_kw = st.text_input("Enter Bank / Keyword", placeholder="e.g. Kotak, Chase, HSBC", key="custom_bank_kw")

        selected_bank_filter = custom_kw if bank_choice == "custom" and custom_kw else (None if bank_choice == "all" else bank_choice)

        if st.button("🔍 Scan Inbox for Bills", type="primary", use_container_width=True, key="scan_btn"):
            if provider == "imap" and (not imap_creds.get("email_address") or not imap_creds.get("app_password")):
                st.error("⚠️ Please enter both your Email Address and App Password.")
            else:
                with st.spinner(f"Scanning inbox via {provider}..."):
                    try:
                        result = fetch_billing_emails(
                            user_id=user_id,
                            provider=provider,
                            max_count=max_emails,
                            credentials=imap_creds if provider == "imap" else None,
                            bank_filter=selected_bank_filter,
                        )
                        st.session_state["email_scan_result"] = result
                    except Exception as exc:
                        st.error(f"❌ Connection Error: {exc}")
                        if "myaccount.google.com/apppasswords" in str(exc) or "App Password" in str(exc):
                            st.warning(
                                "🔑 **Gmail App Password Setup (1 minute):**\n"
                                "1. Make sure **2-Step Verification** is turned ON in your Google Account.\n"
                                "2. Visit: [https://myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)\n"
                                "3. Type `BillWatchdog` as the app name and click **Create**.\n"
                                "4. Copy the generated 16-character code (e.g. `abcd efgh ijkl mnop`) and paste it into the **App Password** box above."
                            )


    with col_results:
        st.markdown("#### 📨 Scanned Billing Emails")

        scan_result = st.session_state.get("email_scan_result")

        if not scan_result:
            st.markdown("""
            <div style="color:#484f58; text-align:center; padding:3rem; font-style:italic;">
                Click "Scan Inbox for Bills" to fetch emails from your selected provider.
            </div>
            """, unsafe_allow_html=True)
        elif scan_result.get("quota_exceeded"):
            st.error(scan_result["message"])
        else:
            found = scan_result["billing_emails_found"]
            scanned = scan_result["emails_scanned"]
            provider_name = scan_result["provider"]

            # Summary metrics
            m1, m2, m3 = st.columns(3)
            m1.metric("Provider", provider_name)
            m2.metric("Billing Found", found)
            m3.metric("Scanned Today", scanned)

            st.markdown(f"*{scan_result['message']}*")

            # Show each email with its extracted invoice
            for email_data in scan_result["emails"]:
                invoice = email_data.get("invoice")
                has_error = email_data.get("parse_error")
                merchant = invoice.get("merchant_name", "Unknown") if invoice else "Parse Error"
                amount   = invoice.get("total_amount", 0) if invoice else 0

                with st.expander(f"📧 {email_data['subject'][:70]} — ₹{amount:,.0f}", expanded=False):
                    col_a, col_b = st.columns(2)
                    col_a.markdown(f"**From:** {email_data['sender']}")
                    col_b.markdown(f"**Date:** {email_data['date']}")
                    st.markdown(f"**Snippet:** _{email_data['snippet'][:150]}_")

                    # Check if email has password-protected PDF attachment
                    if email_data.get("has_pdf") and email_data.get("is_pdf_encrypted"):
                        pdf_name = email_data.get("pdf_filename") or "statement.pdf"
                        st.warning(f"🔒 **Password-Protected Statement PDF Attached:** `{pdf_name}`")
                        st.caption("🛡️ **Zero-Trust Security:** Passwords are kept in volatile memory only for decryption and are NEVER saved to database, disk, or logs.")

                        c_pwd, c_btn = st.columns([2, 1])
                        with c_pwd:
                            pwd_in = st.text_input(
                                "Statement Password",
                                type="password",
                                placeholder="e.g. IN1995, PAN, or DOB (Demo: IN1995)",
                                key=f"pwd_input_{email_data['email_id']}",
                                help="Most Indian bank statements use PAN or First 4 letters of Name + DOB"
                            )
                        with c_btn:
                            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                            if st.button("🔓 Decrypt & Extract", key=f"btn_dec_{email_data['email_id']}"):
                                if not pwd_in:
                                    st.error("Please enter the password.")
                                else:
                                    from tools.pdf_statement_tool import decrypt_and_extract_statement
                                    dec_res = decrypt_and_extract_statement(email_data.get("pdf_bytes"), password=pwd_in)
                                    if dec_res.get("success"):
                                        st.success(f"✅ Statement Decrypted! {dec_res['invoice']['merchant_name']} — ₹{dec_res['invoice']['total_amount']:,.2f}")
                                        email_data["invoice"] = dec_res["invoice"]
                                        email_data["is_pdf_encrypted"] = False
                                        st.session_state[f"dec_{email_data['email_id']}"] = dec_res["invoice"]
                                        time.sleep(0.5)
                                        st.rerun()
                                    else:
                                        st.error(dec_res.get("error", "Decryption failed"))

                    # Check if session state has decrypted version
                    if f"dec_{email_data['email_id']}" in st.session_state:
                        invoice = st.session_state[f"dec_{email_data['email_id']}"]

                    if has_error:
                        st.warning(f"⚠️ Parse error: {has_error}")
                    elif invoice:
                        st.markdown("**Extracted Invoice / Statement:**")
                        st.json({
                            "merchant_name": invoice.get("merchant_name"),
                            "total_amount":  invoice.get("total_amount"),
                            "currency":      invoice.get("currency"),
                            "invoice_date":  invoice.get("invoice_date"),
                            "line_items":    invoice.get("line_items", []),
                        })

                        # Process this email through the full pipeline
                        if st.button(f"⚡ Run Full Analysis", key=f"analyze_{email_data['email_id']}"):
                            from tools.baseline_tool import query_billing_baseline
                            from tools.anomaly_tool import detect_bill_anomalies
                            from tools.budget_tool import evaluate_budget_impact
                            from tools.dispute_tool import draft_dispute_packet

                            with st.spinner("Running full 7-tool pipeline..."):
                                baseline = query_billing_baseline(user_id=user_id, merchant_name=invoice["merchant_name"])
                                anomaly  = detect_bill_anomalies(current_invoice=invoice, baseline_data=baseline)
                                budget   = evaluate_budget_impact(user_id=user_id, current_invoice=invoice, anomaly=anomaly)

                            if anomaly["is_anomaly"] and anomaly["severity"] == "ACTION_REQUIRED":
                                st.error(f"🔴 **ACTION REQUIRED**: {anomaly['root_cause_explanation']}")
                                st.info(f"💰 Budget Impact: {budget['impact_statement']}")
                                dispute = draft_dispute_packet(
                                    merchant_name=invoice["merchant_name"],
                                    anomaly=anomaly,
                                    account_info={"account_id": "ACC-EMAIL", "months_as_customer": 12, "payment_record": "good"},
                                )
                                st.markdown("**Dispute Draft:**")
                                st.text_area("Email Body", dispute["email_body"], height=200, key=f"disp_{email_data['email_id']}")
                            else:
                                st.success(f"🟢 **SILENT** — {anomaly['root_cause_explanation']}")


# ──────────────────────────────────────────────────────────────────────────
# TAB: Usage Dashboard & SaaS Metering
# ──────────────────────────────────────────────────────────────────────────

with tab_usage:
    from metering.usage_tracker import get_usage_today, get_usage_this_month
    from metering.tier_engine import get_user_tier, get_tier_info, TIERS
    from metering.cost_estimator import estimate_monthly_cost

    st.markdown("#### 📊 Usage Dashboard")

    today_usage = get_usage_today(user_id)
    month_usage = get_usage_this_month(user_id)
    cost_data   = estimate_monthly_cost(user_id)
    user_tier   = get_user_tier(user_id)
    tier_info   = get_tier_info(user_tier)

    # Tier banner
    tier_colors = {"free": "#8b8fa3", "pro": "#fbbf24", "enterprise": "#4ade80"}
    tier_color  = tier_colors.get(user_tier, "#8b8fa3")
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#1a1a2e,#16213e); border:1px solid {tier_color};
                border-radius:12px; padding:1rem 1.5rem; margin-bottom:1rem; display:flex; justify-content:space-between; align-items:center;">
        <div>
            <span style="color:{tier_color}; font-weight:700; font-size:1rem;">
                {tier_info['display_name']} Plan
            </span>
            <div style="color:#8b8fa3; font-size:0.8rem; margin-top:4px;">
                {' · '.join(tier_info['features'])}
            </div>
        </div>
        <div style="color:{tier_color}; font-weight:600;">
            {'Free' if tier_info['price_inr'] == 0 else f"₹{tier_info['price_inr']}/month" if tier_info['price_inr'] else 'Custom'}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Today's usage
    st.markdown("##### Today")
    u1, u2, u3, u4 = st.columns(4)
    u1.metric("Emails Scanned",   today_usage.get("email_scanned", {}).get("count", 0))
    u2.metric("Bills Extracted",  today_usage.get("bill_extracted", {}).get("count", 0))
    u3.metric("Anomalies Found",  today_usage.get("anomaly_detected", {}).get("count", 0))
    u4.metric("Disputes Drafted", today_usage.get("dispute_drafted", {}).get("count", 0))

    # Monthly totals
    st.markdown("##### This Month")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Emails Scanned",   month_usage.get("email_scanned", {}).get("count", 0))
    m2.metric("Bills Extracted",  month_usage.get("bill_extracted", {}).get("count", 0))
    m3.metric("Anomalies Found",  month_usage.get("anomaly_detected", {}).get("count", 0))
    m4.metric("Disputes Drafted", month_usage.get("dispute_drafted", {}).get("count", 0))

    # AWS Cost Estimator
    st.markdown("---")
    st.markdown("##### ☁️ Estimated AWS Cost This Month")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Input Tokens",    f"{cost_data['input_tokens']:,}")
    c2.metric("Output Tokens",   f"{cost_data['output_tokens']:,}")
    c3.metric("Total (USD)",     f"${cost_data['total_cost_usd']:.4f}")
    c4.metric("Total (INR)",     f"₹{cost_data['total_cost_inr']:.2f}")

    st.markdown(f"*{cost_data['note']}*")

    # Tier comparison
    st.markdown("---")
    st.markdown("##### 🏷️ Plan Comparison")
    tier_rows = []
    for t_key, t_info in TIERS.items():
        tier_rows.append({
            "Plan": t_info["display_name"],
            "Daily Emails": str(t_info["daily_email_limit"]) if t_info["daily_email_limit"] else "Unlimited",
            "Alerts/Month": str(t_info["monthly_anomaly_limit"]) if t_info["monthly_anomaly_limit"] else "Unlimited",
            "Disputes/Month": str(t_info["monthly_dispute_limit"]) if t_info["monthly_dispute_limit"] else "Unlimited",
            "Price (INR)": f"₹{t_info['price_inr']}/mo" if t_info["price_inr"] else ("Free" if t_info["price_inr"] == 0 else "Custom"),
        })

    import pandas as pd
    df = pd.DataFrame(tier_rows)
    st.dataframe(df, use_container_width=True, hide_index=True)
