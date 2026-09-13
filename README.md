# 💸 BillWatchdog — Silent Bill Sentinel

> **Everyday Agent | Agents for Humans Hackathon 2026**
> Built with **AWS Strands Agents SDK** · **Local Ollama** (no AWS creds needed) · **Streamlit**

---

## 🧠 What It Does

BillWatchdog is an **autonomous background agent** that silently watches your bills. It reads your inbox, compares every bill against your personal spending history, and only alerts you when a real decision needs to be made — a stealth price hike, an expired promo, a hidden fee, or a budget breach.

```
95% of bills → 😶 SILENT   (archived quietly, zero noise)
 5% of bills → 🚨 ACTION   (alert + dispute email drafted automatically)
```

### The Problem It Solves
The average Indian household loses **₹26,000+/year** to:
- 📈 Silent price hikes buried in billing emails
- ⏰ Promotional discounts expiring without notice
- 💳 Seat count / usage creeping up unnoticed
- 🔁 Annual auto-renewals for forgotten subscriptions
- 💰 Hidden infrastructure or surcharge fees added quietly

---

## ✅ What's Implemented

### 8 Strands Agent Tools

| # | Tool | File | What it does |
|---|------|------|--------------|
| 1 | `extract_invoice_entities` | `tools/extractor_tool.py` | Parses vendor name, amount, period, line items from any bill |
| 2 | `query_billing_baseline` | `tools/baseline_tool.py` | Fetches 6-month historical average for the vendor from SQLite |
| 3 | `detect_bill_anomalies` | `tools/anomaly_tool.py` | Flags price hikes (±5% subscriptions, ±20% utilities), promo expiry, hidden fees |
| 4 | `evaluate_budget_impact` | `tools/budget_tool.py` | Calculates Safe-to-Spend, category limits, monthly forecast |
| 5 | `draft_dispute_packet` | `tools/dispute_tool.py` | Auto-drafts vendor-specific dispute / cancellation email |
| 6 | `schedule_renewal_deadline` | `tools/scheduler_tool.py` | Adds calendar reminders for renewal / review deadlines |
| 7 | `explain_spending_narrative` | `tools/narrative_tool.py` | Answers natural language questions about spending trends |
| 8 | `fetch_billing_emails` | `tools/email_tool.py` | Fetches emails from inbox using the Adapter Pattern |

### Email Adapter Pattern (swap providers in one line)

| Adapter | Class | Use Case |
|---------|-------|----------|
| Mock (demo) | `MockEmailAdapter` | 20 synthetic bills — no auth needed |
| IMAP | `IMAPEmailAdapter` | Gmail / Outlook / Yahoo via App Password |
| Gmail OAuth2 | `OAuth2GmailAdapter` | Production — full OAuth2 flow |

### SaaS Tier Metering

| Tier | Emails/day | Disputes | Price |
|------|-----------|----------|-------|
| Free | 10 | 1/month | ₹0 |
| Pro | 50 | Unlimited | ₹299/mo |
| Enterprise | Unlimited | Unlimited | Custom |

### Test Coverage

| Test file | Tests | What's tested |
|-----------|-------|---------------|
| `tests/test_tools.py` | 13 | All 7 processing tools |
| `tests/test_email_adapters.py` | 16 | Adapters, billing filter, quota |
| `tests/test_metering.py` | 15 | Usage tracking, tiers, cost estimation |
| **Total** | **44** | All passing ✅ |

---

## 🚀 How to Run

### Option A — Local with Ollama (Recommended — No AWS needed)

**Step 1: Install & start Ollama**
```bash
# Download from https://ollama.com/download (macOS app)
ollama pull llama3.1        # or gemma4:e4b if already installed
```

**Step 2: Set up the project**
```bash
cd BillWatchdog
source ../venv/bin/activate
pip install -r requirements.txt
pip install "strands-agents[ollama]"
```

**Step 3: Seed the database**
```bash
python -c "from storage.seed_data import seed_all; seed_all()"
```

**Step 4: Launch the UI**
```bash
USE_OLLAMA=1 streamlit run app.py
```

Open **http://localhost:8501** 🎉

---

### Option B — With AWS Bedrock (Claude 3 Haiku)

**Step 1: Get AWS credentials**
1. Go to [console.aws.amazon.com](https://console.aws.amazon.com) → **IAM** → **Security credentials**
2. Click **Create access key** → copy `Access Key ID` and `Secret Access Key`
3. In **Amazon Bedrock** → **Model access** → enable **Claude 3 Haiku** (instant, free tier)

**Step 2: Set credentials**
```bash
export AWS_ACCESS_KEY_ID="AKIA..."
export AWS_SECRET_ACCESS_KEY="..."
export AWS_DEFAULT_REGION="us-east-1"
```

**Step 3: Run**
```bash
cd BillWatchdog
source ../venv/bin/activate
streamlit run app.py
```

---

### Option C — Agent-only smoke test (no UI)

```bash
cd BillWatchdog
source ../venv/bin/activate

# With Ollama
USE_OLLAMA=1 python agent/strands_agent.py

# With Bedrock (if creds set)
python agent/strands_agent.py
```

---

## 🧪 Run Tests

```bash
cd BillWatchdog
source ../venv/bin/activate
python -m pytest tests/ -v
# Expected: 44 passed in < 2s
```

---

## 🗂️ Project Structure

```
BillWatchdog/
│
├── app.py                      # Streamlit UI — 4 tabs: Budget / Bills / Email / Usage
│
├── agent/
│   ├── strands_agent.py        # Core Strands Agent — auto-selects Ollama or Bedrock
│   └── prompts.py              # System prompt with 6-step decision framework
│
├── tools/                      # 8 Strands @tool functions (pure, independently testable)
│   ├── extractor_tool.py       # Tool 1: extract_invoice_entities
│   ├── baseline_tool.py        # Tool 2: query_billing_baseline
│   ├── anomaly_tool.py         # Tool 3: detect_bill_anomalies
│   ├── budget_tool.py          # Tool 4: evaluate_budget_impact
│   ├── dispute_tool.py         # Tool 5: draft_dispute_packet
│   ├── scheduler_tool.py       # Tool 6: schedule_renewal_deadline
│   ├── narrative_tool.py       # Tool 7: explain_spending_narrative
│   └── email_tool.py           # Tool 8: fetch_billing_emails
│
├── inboxes/                    # Email Adapter Pattern
│   ├── base_adapter.py         # Abstract EmailInboxAdapter ABC + get_adapter() factory
│   ├── mock_adapter.py         # 20 synthetic billing emails (demo, no auth)
│   ├── imap_adapter.py         # Real IMAP — Gmail/Outlook via App Password
│   └── oauth2_gmail_adapter.py # Gmail API with OAuth2 (production ready)
│
├── metering/                   # Per-user SaaS usage tracking
│   ├── usage_tracker.py        # SQLite event recording (email_scanned, bedrock_call …)
│   ├── tier_engine.py          # Free / Pro / Enterprise quota enforcement
│   └── cost_estimator.py       # AWS Bedrock cost per user (Claude 3 Haiku rates)
│
├── storage/
│   ├── db.py                   # SQLite schema + CRUD (5 tables)
│   └── seed_data.py            # 15 vendor baselines + 42 historical bills + 10 demo bills
│
├── deployment/
│   ├── agentcore_app.py        # AgentCore HTTP handler (process_bill / scan_inbox / ask)
│   └── agentcore.yaml          # Deployment config + Bedrock Guardrails
│
├── tests/
│   ├── test_tools.py           # 13 tests — all 7 processing tools
│   ├── test_email_adapters.py  # 16 tests — adapters, quota enforcement
│   └── test_metering.py        # 15 tests — tiers, cost estimation
│
├── requirements.txt
└── README.md
```

---

## 📊 Demo Test Data (10 Bills)

### Silent Bills (no action needed)
| # | Vendor | Amount | Why Silent |
|---|--------|--------|-----------|
| 1 | Netflix | ₹649 | Matches 6-month baseline exactly |
| 2 | BESCOM Electricity | ₹2,850 | Within ±20% seasonal tolerance |
| 3 | Spotify | ₹119 | Normal |
| 4 | Airtel Broadband | ₹799 | Normal |
| 5 | GitHub | ₹830 | Normal |

### Action Required Bills (anomaly detected)
| # | Vendor | Amount | Anomaly |
|---|--------|--------|---------|
| 6 | Figma | ₹1,999 | 🔺 +33% price hike (was ₹1,499) |
| 7 | Jio Fiber | ₹1,499 | 🔺 +50% promo cliff (was ₹999) |
| 8 | Hotstar | ₹1,499 | ⚠️ Annual auto-renewal surprise |
| 9 | Airtel Broadband | ₹1,099 | 💰 Hidden infrastructure fee added |
| 10 | Slack | ₹3,600 | 📈 Seat count crept up 8→12 |

---

## 🏗️ Architecture

```
Email Inbox (Gmail / Outlook / Mock)
        │  Adapter Pattern — swap providers without changing agent
        ▼
fetch_billing_emails()           ← Tool 8

extract_invoice_entities()       ← Tool 1
        │
query_billing_baseline()         ← Tool 2  (reads SQLite history)
        │
detect_bill_anomalies()          ← Tool 3
        │
        ├── SILENT → archived to DB, user never notified
        │
        └── ACTION REQUIRED
                ├── evaluate_budget_impact()     ← Tool 4
                ├── draft_dispute_packet()        ← Tool 5
                └── schedule_renewal_deadline()  ← Tool 6

User query → explain_spending_narrative()        ← Tool 7
```

### Model Selection (auto-detected)

```python
# In agent/strands_agent.py — no code change needed:
# Set USE_OLLAMA=1  → runs on local Ollama (gemma4:e4b or llama3.1)
# Set AWS creds    → runs on Amazon Bedrock Claude 3 Haiku
# Nothing set      → auto-falls back to Ollama
```

---

## 🔧 Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `USE_OLLAMA` | `""` | Set to `1` to force Ollama (skip Bedrock) |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `gemma4:e4b` | Model ID for Ollama |
| `BEDROCK_MODEL` | `anthropic.claude-3-haiku-20240307-v1:0` | Bedrock model ID |
| `AWS_DEFAULT_REGION` | `us-east-1` | AWS region for Bedrock |
| `AWS_ACCESS_KEY_ID` | — | AWS credential |
| `AWS_SECRET_ACCESS_KEY` | — | AWS credential |

---

## 🎬 Demo Walkthrough (3 minutes)

1. **Dashboard tab** — See budget overview: categories, spend vs. limit, Safe-to-Spend
2. **Process All 10 Bills** → Watch: 5 silent, 5 action alerts with full reasoning
3. **Action Center** → Open Slack dispute draft → review vendor-specific email → "Send"
4. **Email Inbox tab** → Select "Mock Demo Inbox" → "Scan Inbox" → 20 emails auto-processed
5. **Ask Agent** → Type `"What changed most this month?"` → spending narrative with real ₹ numbers
6. **Usage tab** → SaaS tier, email quota remaining, estimated AWS cost per run

---

## 🏆 Hackathon

**Track**: Everyday Agents
**Hackathon**: Agents for Humans — [agentsforhumans.devpost.com](https://agentsforhumans.devpost.com)
**Deadline**: September 14, 2026 at 8:00 PM EDT (Sep 15 at 5:30 AM IST)

**AWS Services Used**:
- Amazon Bedrock — Claude 3 Haiku (LLM reasoning + tool calling)
- Amazon Bedrock AgentCore — Agent hosting runtime
- Amazon Bedrock Guardrails — Financial content policy enforcement
- SQLite (local) — Bill history, usage metering (DynamoDB-ready for production)
