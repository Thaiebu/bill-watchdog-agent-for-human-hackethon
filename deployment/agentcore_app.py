"""
Amazon Bedrock AgentCore Entrypoint for BillWatchdog.
Exposes the Strands Agent as an HTTP handler compatible with AgentCore runtime.

This follows the pattern from the Strands workshop Module 05 (deploy).
"""
import json
import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from strands import Agent
from strands.models import BedrockModel

from tools.extractor_tool import extract_invoice_entities
from tools.baseline_tool import query_billing_baseline
from tools.anomaly_tool import detect_bill_anomalies
from tools.budget_tool import evaluate_budget_impact
from tools.dispute_tool import draft_dispute_packet
from tools.scheduler_tool import schedule_renewal_deadline
from tools.narrative_tool import explain_spending_narrative
from tools.email_tool import fetch_billing_emails
from agent.prompts import SYSTEM_PROMPT
from storage.db import init_db


ALL_TOOLS = [
    extract_invoice_entities,
    query_billing_baseline,
    detect_bill_anomalies,
    evaluate_budget_impact,
    draft_dispute_packet,
    schedule_renewal_deadline,
    explain_spending_narrative,
]


def create_agent() -> Agent:
    """Create the BillWatchdog Strands agent for AgentCore deployment."""
    model = BedrockModel(
        model_id="anthropic.claude-3-haiku-20240307-v1:0",
        region_name="us-east-1",
    )
    return Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=ALL_TOOLS,
    )


# Initialize DB and agent on cold start
init_db()
agent = create_agent()


def handler(event: dict, context=None) -> dict:
    """
    AgentCore HTTP request handler.

    Expected event format:
    {
        "action": "process_bill" | "ask_question",
        "user_id": "user_1",
        "payload": { ... }  // bill data or user question
    }
    """
    action  = event.get("action", "process_bill")
    user_id = event.get("user_id", "user_1")
    payload = event.get("payload", {})

    if action == "process_bill":
        prompt = (
            f"Process this bill for user '{user_id}':\n\n"
            f"{json.dumps(payload, indent=2)}\n\n"
            f"Follow the 6-step decision framework in your system prompt exactly."
        )
    elif action == "ask_question":
        question = payload.get("question", "What changed this month?")
        prompt = (
            f"The user ('{user_id}') is asking: \"{question}\"\n\n"
            f"Use the explain_spending_narrative tool to answer with specific numbers."
        )
    elif action == "scan_inbox":
        provider = payload.get("provider", "mock")
        max_count = payload.get("max_count", 15)
        prompt = (
            f"Scan the inbox for user '{user_id}' using provider '{provider}'. "
            f"Fetch up to {max_count} billing emails with the fetch_billing_emails tool, "
            f"then process each one through the full 5-step anomaly detection pipeline. "
            f"For each bill, decide SILENT or ACTION_REQUIRED. "
            f"Return a summary of: how many emails scanned, how many anomalies found, "
            f"and the list of any ACTION_REQUIRED alerts with dispute drafts."
        )
    else:
        return {"statusCode": 400, "body": f"Unknown action: {action}"}

    # Execute agent
    response_text = ""
    for event_chunk in agent.stream(prompt):
        if hasattr(event_chunk, "text") and event_chunk.text:
            response_text += event_chunk.text

    return {
        "statusCode": 200,
        "body": response_text,
    }


# For local testing
if __name__ == "__main__":
    test_event = {
        "action": "process_bill",
        "user_id": "user_1",
        "payload": {
            "merchant_name": "Netflix",
            "invoice_date": "2026-09-02",
            "total_amount": 649,
            "currency": "INR",
            "line_items": [{"name": "Standard Plan HD", "amount": 649}],
            "detected_terms": [],
        },
    }
    result = handler(test_event)
    print(json.dumps(result, indent=2))
