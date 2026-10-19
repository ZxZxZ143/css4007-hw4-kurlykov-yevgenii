from decimal import Decimal
from statistics import median

from css4007_hw4.evaluation.pricing import Pricing, request_cost


def usage_totals(requests: list[dict], pricing: Pricing | None) -> dict:
    input_tokens = output_tokens = missing = 0
    measured_cost = Decimal(0)
    cost_unknown = 0
    for request in requests:
        usage = request.get("usage") or {}
        prompt, completion = usage.get("prompt_tokens"), usage.get("completion_tokens")
        if type(prompt) is not int or prompt < 0 or type(completion) is not int or completion < 0:
            missing += 1
        else:
            input_tokens += prompt
            output_tokens += completion
        cost = request_cost(request, pricing)
        if cost is None:
            cost_unknown += 1
        else:
            measured_cost += cost
    return {"api_requests": len(requests), "missing_usage_requests": missing,
            "input_tokens": input_tokens if not missing else None,
            "output_tokens": output_tokens if not missing else None,
            "measured_input_tokens": input_tokens, "measured_output_tokens": output_tokens,
            "cost_usd": str(measured_cost) if pricing is not None and not cost_unknown else None,
            "measured_cost_usd": str(measured_cost), "unknown_cost_requests": cost_unknown}


def summarize(records: list[dict], pricing: Pricing | None) -> dict:
    latencies = [r["execution"]["elapsed_seconds"] for r in records]
    requests = [request for r in records for request in r["execution"]["requests"]]
    return {"questions": len(records), "correct": sum(r["score"]["correct"] for r in records),
            "unanswered": sum(r["score"]["unanswered"] for r in records),
            "median_seconds_per_question": median(latencies) if latencies else None,
            "total_seconds": sum(latencies),
            "model_seconds": sum(r["elapsed_seconds"] for r in requests),
            "tool_seconds": sum(t["elapsed_seconds"] for r in records for t in r["execution"]["tool_events"]),
            **usage_totals(requests, pricing)}
