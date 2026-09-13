"""
Core BillWatchdog Strands Agent.
Wires all 8 tools into a single Agent instance and exposes
process_bill() and ask_spending_question() entry points.

Model selection (checked in order):
  1. USE_OLLAMA=1 env var  → local Ollama (no AWS creds needed)
  2. AWS credentials present → Amazon Bedrock Claude 3 Haiku
  3. fallback               → Ollama (graceful degradation)
"""
import json
import sys
import os

# Ensure BillWatchdog root is on the path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from strands import Agent

from tools.extractor_tool  import extract_invoice_entities
from tools.baseline_tool   import query_billing_baseline
from tools.anomaly_tool    import detect_bill_anomalies
from tools.budget_tool     import evaluate_budget_impact
from tools.dispute_tool    import draft_dispute_packet
from tools.scheduler_tool  import schedule_renewal_deadline
from tools.narrative_tool  import explain_spending_narrative
from tools.email_tool      import fetch_billing_emails
from agent.prompts         import SYSTEM_PROMPT
from storage.db            import init_db, insert_bill


ALL_TOOLS = [
    fetch_billing_emails,
    extract_invoice_entities,
    query_billing_baseline,
    detect_bill_anomalies,
    evaluate_budget_impact,
    draft_dispute_packet,
    schedule_renewal_deadline,
    explain_spending_narrative,
]

# ---------------------------------------------------------------------------
# Model factory — Ollama first (no creds needed), Bedrock if creds present
# ---------------------------------------------------------------------------

def _build_model():
    """
    Return the best available model:
      - Ollama (gemma4:e4b)  if USE_OLLAMA=1 or AWS creds are missing
      - Bedrock Claude Haiku if AWS creds are fully configured
    """
    force_ollama = os.environ.get("USE_OLLAMA", "").strip() in ("1", "true", "yes")
    has_aws = bool(
        os.environ.get("AWS_ACCESS_KEY_ID") and os.environ.get("AWS_SECRET_ACCESS_KEY")
    )

    if force_ollama or not has_aws:
        from strands.models.ollama import OllamaModel
        model_id = os.environ.get("OLLAMA_MODEL", "gemma4:e4b")
        print(f"🦙 Using Ollama model: {model_id} (local, no AWS creds needed)")
        return OllamaModel(
            host=os.environ.get("OLLAMA_HOST", "http://localhost:11434"),
            model_id=model_id,
        )
    else:
        from strands.models import BedrockModel
        model_id = os.environ.get("BEDROCK_MODEL", "anthropic.claude-3-haiku-20240307-v1:0")
        region   = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
        print(f"☁️  Using Bedrock model: {model_id} in {region}")
        return BedrockModel(model_id=model_id, region_name=region)


def get_agent() -> Agent:
    """Create and return a configured BillWatchdog Strands Agent."""
    return Agent(
        model=_build_model(),
        system_prompt=SYSTEM_PROMPT,
        tools=ALL_TOOLS,
    )


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------

def process_bill(bill_data: dict, user_id: str = "user_1") -> dict:
    """
    Process a single bill through the full Strands agent pipeline.

    Returns a result dict with:
      - silent: bool
      - severity: SILENT | INFORMATIONAL | ACTION_REQUIRED
      - agent_response: str
    """
    init_db()
    agent = get_agent()

    prompt = (
        f"Process this bill for user '{user_id}':\n\n"
        f"{json.dumps(bill_data, indent=2)}\n\n"
        f"Follow the 6-step decision framework in your system prompt exactly."
    )

    # agent(prompt) is the standard Strands sync call — returns AgentResult
    result = agent(prompt)
    response_text = str(result)

    is_silent = "ACTION_REQUIRED" not in response_text.upper()

    # Normalise: DEMO_BILLS wrap fields under "raw"; Streamlit passes flat dicts.
    db_record = bill_data.get("raw", bill_data).copy()
    db_record["user_id"]      = user_id
    db_record["silent"]       = is_silent
    db_record["alert_reason"] = None if is_silent else response_text[:300]
    insert_bill(db_record)

    return {
        "silent":         is_silent,
        "severity":       "SILENT" if is_silent else "ACTION_REQUIRED",
        "agent_response": response_text,
        "events":         [],   # streaming not used in sync mode
    }


def ask_spending_question(user_query: str, user_id: str = "user_1") -> str:
    """
    Route a natural-language spending question to the explain_spending_narrative
    tool via the Strands agent.
    """
    init_db()
    agent = get_agent()

    prompt = (
        f"The user ('{user_id}') is asking: \"{user_query}\"\n\n"
        f"Use the explain_spending_narrative tool to answer this question "
        f"with specific numbers from their actual bill history."
    )

    result = agent(prompt)
    response_text = str(result)

    return response_text or "Unable to generate spending narrative. Please ensure bills have been processed first."


# ---------------------------------------------------------------------------
# Quick smoke test — run with: USE_OLLAMA=1 python agent/strands_agent.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    from storage.seed_data import DEMO_BILLS
    print("=== BillWatchdog Agent Smoke Test ===\n")
    result = process_bill(DEMO_BILLS[0])
    print(f"\n{'='*50}")
    print(f"Severity : {result['severity']}")
    print(f"Silent   : {result['silent']}")
    print(f"Response :\n{result['agent_response'][:600]}")
