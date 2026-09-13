# 🏆 Devpost Hackathon Submission Package

**Project Name:** BillWatchdog — The Silent Bill Sentinel  
**Hackathon:** AWS Agents for Humans Hackathon 2026  
**Track:** Everyday Agents  
**GitHub Repository:** https://github.com/Thaiebu/bill-watchdog-agent-for-human-hackethon  

---

## 📌 Tagline (1 sentence)
> An autonomous background agent built on AWS Strands SDK that silently audits your bills, catches stealth price hikes and promo cliffs, and auto-drafts dispute emails before you lose money.

---

## 💡 Inspiration
Every month, ordinary consumers and startup founders bleed money to subscription creep:
- A ₹999/month broadband plan silently doubles to ₹1,499 after a "introductory discount" expires without notice.
- A design tool bumps pricing from ₹1,499 to ₹1,999 with an obscure footnote in an email receipt.
- A forgotten OTT service automatically renews for ₹1,499/year.
- Cloud SaaS services creep up seat counts unnoticed.

In India alone, the average household loses **₹26,000+ every year** simply because people don't have time to audit 20+ receipts every month. 

Traditional finance apps fail because they are passive dashboards: they wait for you to open the app, categorize transactions manually, and look at pie charts *after* the money is already gone. 

We asked: **What if an agent lived in your inbox, audited every invoice against your personal 6-month spending baseline, filed 95% of normal bills silently without nagging you, and only interrupted you when real action or money was on the line?**

That became **BillWatchdog**.

---

## ⚙️ What It Does

BillWatchdog follows a radical UX principle: **The best agent is the one you rarely see.**

1. **Inbox Autonomy (Adapter Pattern):** Connects to your email via Gmail OAuth2, standard IMAP (Outlook, Yahoo), or a synthetic Mock adapter. It continuously monitors for new billing receipts.
2. **Entity Extraction:** When an invoice arrives, the agent parses vendor, invoice date, line items, and terms.
3. **Baseline Comparison:** Looks up your historical spend for that merchant over the past 6 months from a local SQLite database.
4. **Autonomous Anomaly Detection:** 
   - Knows that utilities (electricity, water) vary seasonally by ±20% and stays silent.
   - Knows that subscriptions should never change and flags even a 5% increase.
   - Catches promotional discounts ending, hidden surcharge fees, and seat creep.
5. **Safe-to-Spend & Budget Impact:** Calculates how the bill impacts your monthly category limit and safe-to-spend balance.
6. **Auto-Drafted Dispute Packet:** If an unfair charge is detected, it doesn't just send an alert — it pre-drafts a professional, vendor-tailored dispute or cancellation email citing account numbers and policy clauses.
7. **Conversational Financial Narrative:** Ask natural language questions like *"What changed most in my spending this month?"* and get clear answers grounded in your actual bills.
8. **SaaS Metering & Cost Tracking:** Includes production-grade Free, Pro, and Enterprise tiers with quota limits and real-time AWS Bedrock token cost tracking.

---

## 🛠️ How We Built It

BillWatchdog was built from the ground up using modern agentic software patterns:

- **AWS Strands Agents SDK:** Built with genuine multi-tool agentic orchestration using 8 modular `@tool` decorators (`extractor_tool`, `baseline_tool`, `anomaly_tool`, `budget_tool`, `dispute_tool`, `scheduler_tool`, `narrative_tool`, `email_tool`).
- **Amazon Bedrock & Claude 3 Haiku:** Powers the agent reasoning loop, entity extraction from ambiguous email bodies, and dispute generation.
- **Local Ollama Support (`gemma4:e4b` / `llama3.1`):** Seamless local fallback when AWS credentials are not set, ensuring 100% offline development and zero API cost testing.
- **Adapter Design Pattern:** Abstract `EmailInboxAdapter` interface with 3 swappable implementations (`MockEmailAdapter`, `IMAPEmailAdapter`, `OAuth2GmailAdapter`).
- **Amazon Bedrock AgentCore & Guardrails:** Production deployment configuration with financial content policies in `deployment/agentcore.yaml` and `deployment/agentcore_app.py`.
- **Database & Storage:** SQLite schema with 5 relational tables (`bills`, `vendor_baselines`, `budget_limits`, `reminders`, `usage_events`).
- **Streamlit Interactive UI:** High-density command center with live streaming agent reasoning traces, category spending progress bars, dispute action center, and SaaS usage dashboard.

---

## 🧗 Challenges We Ran Into

1. **Avoiding Notification Fatigue (The "Silent Agent" Challenge):** Most agents over-alert. Teaching the agent that a ₹2,850 summer electricity bill is normal (seasonal heat wave) while a ₹1,999 Figma bill is an anomaly required fine-tuning tolerance bands per category (±20% for utilities vs ±5% for fixed SaaS).
2. **Handling Both Local Ollama & Cloud Bedrock:** Ensuring the Strands agent could effortlessly switch between local Ollama (`gemma4:e4b`) and AWS Bedrock (`anthropic.claude-3-haiku`) without breaking tool invocation syntax.
3. **Inbox Security & Privacy:** Users shouldn't have to give full inbox access to an AI agent. We implemented strict regex and sender-domain pre-filtering so only billing-related emails are ever ingested by the agent.

---

## 🌟 Accomplishments That We're Proud Of

- **8 Specialized Strands Agent Tools** working in harmony.
- **44 Unit Tests passing 100%** across tool extraction, adapters, quota enforcement, and Bedrock cost estimation.
- **True "Silent Background" Pattern:** 5 out of 10 demo bills are processed silently with zero interruption; 5 anomalies are caught with precision.
- **Production-Ready Metering:** Real-time token tracking and AWS cost calculation ($0.00025/1k input, $0.00125/1k output tokens) proving commercial viability.

---

## 📚 What We Learned

- Building agents for human daily life requires prioritizing restraint over chattiness. Agents that notify users only when action is required build immense trust.
- The Adapter Pattern is essential for enterprise agent architectures to prevent tight coupling with third-party email or communication APIs.
- AWS Strands Agents SDK provides an elegant, clean way to structure tool-calling loops without messy manual JSON schema boilerplate.

---

## 🔮 What's Next for BillWatchdog

- **Automated Dispute Dispatch via Amazon SES:** Allowing users to click one button to have the agent send the dispute email directly to vendor billing departments.
- **Bank & UPI SMS Ingestion:** Expanding beyond email to parse Indian UPI (GPay, PhonePe) debit notifications.
- **DynamoDB & Bedrock AgentCore Production Deployment:** Migrating SQLite state to DynamoDB and running as an always-on serverless Bedrock Agent.

---

## 🏷️ Built With Tags
`aws` `amazon-bedrock` `strands-agents-sdk` `python` `streamlit` `claude-3-haiku` `ollama` `sqlite` `email-automation`
