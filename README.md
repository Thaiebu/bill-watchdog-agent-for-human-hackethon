# 💸 BillWatchdog — Silent Bill Sentinel

> **Everyday Agent | Agents for Humans Hackathon 2026**
> Built with **AWS Strands Agents SDK** · **Amazon Bedrock Claude 3 Haiku** · **Local Ollama Fallback** · **Streamlit**

[![Tests](https://img.shields.io/badge/Tests-56%2F56%20Passing-brightgreen)](tests/)
[![Security](https://img.shields.io/badge/Privacy-Zero--Storage%20In--Memory-blueviolet)](scripts/check_confidential.py)
[![Hackathon](https://img.shields.io/badge/Devpost-Agents%20for%20Humans-orange)](https://agentsforhumans.devpost.com/)

---

## 🧠 What It Does

BillWatchdog is an **autonomous background agent** that silently watches your recurring bills and monthly bank statements. It ingests your bills from email or encrypted bank statements, compares every charge against your historical spending baseline, and only alerts you when a real decision needs to be made — a stealth price hike, an expired promo, a hidden infrastructure surcharge, or a budget breach.

```
95% of bills → 😶 SILENT   (archived quietly into SQLite, zero notification noise)
 5% of bills → 🚨 ACTION   (alert + vendor-specific dispute letter drafted automatically)
```

### The Problem It Solves
The average Indian household loses **₹26,000+/year** to:
- 📈 Silent price hikes buried in billing notifications
- ⏰ Promotional discounts expiring without notice
- 💳 Seat count / usage creeping up unnoticed
- 🔁 Annual auto-renewals for forgotten subscriptions
- 💰 Hidden infrastructure or surcharge fees added quietly
- 📑 Dense, password-protected monthly bank PDF statements that are never audited

---

## ✨ Key Capabilities & Engineering Milestones

### 🛡️ 1. Zero-Trust Privacy & In-Memory Statement Decryption
* **Volatile Memory Only**: Password-protected bank statement PDFs (IndusInd, HDFC, ICICI, SBI, Axis, etc.) are decrypted and parsed strictly in volatile memory using `pypdf` + `fonttools`.
* **Zero Password Retention**: Passwords are wiped from RAM immediately after decryption (`del password`, `gc.collect()`). Passwords and statement bytes are **NEVER** saved to disk, SQLite, or telemetry logs.
* **Confidentiality Git Hooks**: Includes `scripts/check_confidential.py` wired to Git `pre-commit` and `pre-push` hooks. It scans files before push to guarantee that no AWS keys, app passwords, private keys, or PII ever leak to GitHub.
* **PII Masking**: Bank account and card numbers are masked at ingestion (e.g. *ending in 6528*).

### 📑 2. Indian Banking Tabular Statement Intelligence
* **Multi-Transaction Table Parser**: Automatically extracts tabular statements containing `DATE`, `PARTICULARS`, `DEPOSITS`, `WITHDRAWALS`, and `BALANCE`.
* **Debit vs Credit Separation**: Distinguishes expense outflows (UPI, card, mutual fund SIPs) from inflows (salary, employer reimbursements).
* **Running Balance Calculation**: Tracks opening brought forward (B/F) balances and running ledgers with penny accuracy.
* **Executive Agent Audit**: Generates an instant narrative identifying primary burn drivers, systematic investment plans (ICICI Direct, TATA MF), routine transport (Indian Railways), and employer reimbursements.

### 🎨 3. Dynamic Dual Theme Engine (Dark & Light Mode)
* **Instant Mode Switcher**: Header and sidebar toggle switches between **🌙 Obsidian Dark Mode** (`#090d16`) and **☀️ Clean Slate Light Mode** (`#f8fafc`).
* **Responsive 2×2 FinTech KPI Grid**: High-contrast tiles for *Total Debited*, *Total Credited*, *Net Cash Outflow*, and *Transactions Extracted* with zero text wrapping or overlapping.
* **Dedicated Agent Audit Card**: High-contrast card with highlighted pill badges for top outflows and an emerald Sentinel verdict.

---

## 🛠️ Strands Agent Tools (9 Tools)

| # | Tool | File | What it does |
|---|------|------|--------------|
| 1 | `extract_invoice_entities` | `tools/extractor_tool.py` | Parses vendor name, amount, period, line items, and banking tables |
| 2 | `query_billing_baseline` | `tools/baseline_tool.py` | Fetches 6-month historical average for the vendor from SQLite |
| 3 | `detect_bill_anomalies` | `tools/anomaly_tool.py` | Flags price hikes (±5% subscriptions, ±20% utilities), promo expiry, hidden fees |
| 4 | `evaluate_budget_impact` | `tools/budget_tool.py` | Calculates Safe-to-Spend, category limits, monthly forecast |
| 5 | `draft_dispute_packet` | `tools/dispute_tool.py` | Auto-drafts vendor-specific dispute / cancellation email |
| 6 | `schedule_renewal_deadline` | `tools/scheduler_tool.py` | Adds calendar reminders for renewal / review deadlines |
| 7 | `explain_spending_narrative` | `tools/narrative_tool.py` | Answers natural language questions about spending trends |
| 8 | `fetch_billing_emails` | `tools/email_tool.py` | Fetches emails from inbox using the Adapter Pattern + Bank filter |
| 9 | `decrypt_and_extract_statement` | `tools/pdf_statement_tool.py` | In-memory zero-storage decryption of password-protected PDF statements |

---

## 📧 Email & Document Ingestion (Adapter Pattern)

| Adapter | Class | Capabilities |
|---------|-------|--------------|
| **Mock (demo)** | `MockEmailAdapter` | 26 synthetic bills + encrypted PDF statement (`IndusInd_eStatement_Sep2026.pdf`) |
| **IMAP** | `IMAPEmailAdapter` | Gmail / Outlook via App Password + PDF attachment extraction + Bank filter |
| **Direct PDF Upload** | UI Ingestion | Direct upload of password-protected bank statement PDFs with memory-only decryption |
| **Gmail OAuth2** | `OAuth2GmailAdapter` | Production OAuth2 flow for Google Workspace |

---

## 💳 SaaS Tier Metering & Monetization

| Tier | Daily Emails | Monthly Disputes | Monthly Alerts | Price |
|------|--------------|------------------|----------------|-------|
| **Free** | 10 | 1 | 5 | ₹0 |
| **Pro** | 50 | Unlimited | Unlimited | ₹299/mo |
| **Enterprise** | Unlimited | Unlimited | Unlimited | Custom |

> **Developer Control**: Use the sidebar toggle `🔒 Enforce Tier Quotas (Prod)` to test unlimited scans during development or enforce hard limits in production.

---

## 🧪 Test Coverage (56 Unit Tests)

```
tests/test_bank_parser.py       4 passed (UPI alerts, HDFC statement, masked accounts, multi-line tables)
tests/test_pdf_statement.py     5 passed (encrypted PDF, wrong password, missing password, success, invalid)
tests/test_email_adapters.py   16 passed (billing filter, mock inbox, quota enforcement, bank filter)
tests/test_metering.py         15 passed (usage tracker, tiers, Bedrock cost estimator)
tests/test_tools.py            16 passed (extract, baseline, anomaly detection, budget impact, disputes)
======================== 56 passed in ~0.43s ✅ ========================
```

---

## 🚀 Quick Start

### 1. Installation & Environment Setup
```bash
# Clone the repository
git clone https://github.com/Thaiebu/bill-watchdog-agent-for-human-hackethon.git
cd bill-watchdog-agent-for-human-hackethon/BillWatchdog

# Create & activate virtual environment
python3 -m venv ../venv
source ../venv/bin/activate

# Install dependencies (includes strands-agents, pypdf, fonttools)
pip install -r requirements.txt
pip install "strands-agents[ollama]"
```

### 2. Seed Database
```bash
python -c "from storage.seed_data import seed_all; seed_all()"
```

### 3. Run BillWatchdog Dashboard
```bash
# Option A: With local Ollama (zero AWS credentials needed)
USE_OLLAMA=1 streamlit run app.py

# Option B: With Amazon Bedrock Claude 3 Haiku
export AWS_ACCESS_KEY_ID="your_key"
export AWS_SECRET_ACCESS_KEY="your_secret"
export AWS_DEFAULT_REGION="us-east-1"
streamlit run app.py
```
Open your browser at **`http://localhost:8501`**.

---

## 🛡️ Pre-Commit Confidential Scanner
To guarantee no API keys or passwords ever leak to GitHub:
```bash
# Run manual scan across all project files
python scripts/check_confidential.py

# Automatic hooks are pre-installed in .git/hooks/pre-commit and pre-push
```

---

## 🎬 3-Minute Demo Flow

1. **Dashboard & Theme**: Toggle between **🌙 Dark Mode** and **☀️ Light Mode** via the top switch.
2. **Encrypted Bank Statement PDF**:
   - Select **"📤 Upload Bank Statement PDF"**.
   - Upload any statement (or use mock password `IN1995`).
   - Click **"🚀 Decrypt & Analyze Statement PDF"**.
   - See the **2×2 Responsive KPI Grid** (`Total Debited`, `Total Credited`, `Net Cash Outflow`, `Rows`).
   - Review the **🤖 Agent Executive Financial Audit** card and view the full transaction ledger with running balances.
3. **Demo Bills (Silent Sentinel vs Action Required)**:
   - Click **"🚀 Process All 10 Bills"**.
   - Watch the agent silently archive 5 normal bills (zero notifications).
   - Watch the agent flag 5 anomalies and generate vendor-specific dispute drafts in the **⚡ Action Center**.
4. **Conversational Agent Reasoning**:
   - In **💬 Ask BillWatchdog**, ask *"What changed most this month?"* or *"Summarize my bank statement"* for an instant narrative.
5. **Usage & Monetization**:
   - Open **📈 Usage & SaaS Metrics** to view token totals, Claude 3 Haiku AWS costs, and SaaS tier status.
6. **Feature Matrix**:
   - Open **✨ What's Built & Verified** for an interactive overview of all 4 architectural pillars.

---

## 🏆 Hackathon Submission Details

* **Hackathon**: Agents for Humans — [agentsforhumans.devpost.com](https://agentsforhumans.devpost.com)
* **Track**: Everyday Agents
* **Submission Package**: Detailed in `devpost_submission.md`
* **Repository**: [github.com/Thaiebu/bill-watchdog-agent-for-human-hackethon](https://github.com/Thaiebu/bill-watchdog-agent-for-human-hackethon)
* **AWS Services**: Amazon Bedrock Claude 3 Haiku · AWS Strands Agents SDK · Bedrock AgentCore
