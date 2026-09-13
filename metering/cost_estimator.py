"""
AWS Cost Estimator — estimates monthly Bedrock + AgentCore spend per user.
Prices are approximate public rates as of 2026.
"""
from metering.usage_tracker import get_monthly_token_totals, get_usage_this_month

# Bedrock pricing (Claude 3 Haiku, us-east-1)
HAIKU_INPUT_PRICE_PER_1K  = 0.00025   # USD per 1K input tokens
HAIKU_OUTPUT_PRICE_PER_1K = 0.00125   # USD per 1K output tokens
AGENTCORE_INVOCATION_COST = 0.00001   # USD per invocation

INR_PER_USD = 84.0


def estimate_monthly_cost(user_id: str) -> dict:
    """
    Estimate the user's monthly AWS cost based on actual token usage recorded
    in the usage_events table.
    """
    tokens = get_monthly_token_totals(user_id)
    month_usage = get_usage_this_month(user_id)

    input_tokens  = tokens["input_tokens"]
    output_tokens = tokens["output_tokens"]
    invocations   = sum(
        v.get("count", 0) for k, v in month_usage.items()
        if k == "bedrock_call"
    )

    input_cost  = (input_tokens  / 1000) * HAIKU_INPUT_PRICE_PER_1K
    output_cost = (output_tokens / 1000) * HAIKU_OUTPUT_PRICE_PER_1K
    invoke_cost = invocations * AGENTCORE_INVOCATION_COST
    total_usd   = round(input_cost + output_cost + invoke_cost, 4)
    total_inr   = round(total_usd * INR_PER_USD, 2)

    return {
        "input_tokens":    input_tokens,
        "output_tokens":   output_tokens,
        "invocations":     invocations,
        "bedrock_cost_usd": round(input_cost + output_cost, 4),
        "agentcore_cost_usd": round(invoke_cost, 4),
        "total_cost_usd":  total_usd,
        "total_cost_inr":  total_inr,
        "breakdown": {
            "Input tokens":    f"${input_cost:.4f}",
            "Output tokens":   f"${output_cost:.4f}",
            "AgentCore calls": f"${invoke_cost:.4f}",
        },
        "note": "Estimates based on Claude 3 Haiku pricing in us-east-1 (2026 rates).",
    }
