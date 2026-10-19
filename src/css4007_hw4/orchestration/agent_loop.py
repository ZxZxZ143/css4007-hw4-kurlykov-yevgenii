from copy import deepcopy
from datetime import datetime, timezone
import json
from time import perf_counter
from collections.abc import Callable

from css4007_hw4.config import Config
from css4007_hw4.domain.errors import error
from css4007_hw4.evaluation.parser import parse_answer
from css4007_hw4.llm.client import Client, safe_api_error
from css4007_hw4.orchestration.dispatcher import dispatch
from css4007_hw4.tools.registry import Tool

EventSink = Callable[[dict], None]


def run_loop(client: Client, initial_messages: list[dict], config: Config,
             definitions: list[dict] | None = None, registry: dict[str, Tool] | None = None,
             *, max_calls: int | None = None, sink: EventSink | None = None) -> dict:
    started = perf_counter()
    history, requests, tool_events = deepcopy(initial_messages), [], []
    status, reason, final = "unanswered", "round_limit", None
    limit = config.max_rounds if max_calls is None else max_calls
    if (type(limit) is not int or limit < 1 or not history
            or not isinstance(history[-1].get("content"), str) or not history[-1]["content"].strip()):
        return {"status": "unanswered", "reason": "invalid_input", "answer": None, "final_text": None,
                "messages": history, "requests": [], "tool_events": [], "elapsed_seconds": 0.0}
    for round_number in range(1, limit + 1):
        record = {"round": round_number, "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                  "config": config.request_settings(), "messages": deepcopy(history),
                  "tools": deepcopy(definitions), "usage": None}
        call_start = perf_counter()
        try:
            response = client.complete(deepcopy(history), deepcopy(definitions), config)
            record.update(elapsed_seconds=perf_counter() - call_start,
                          assistant=deepcopy(response.message), usage=response.usage,
                          returned_model=response.model, finish_reason=response.finish_reason,
                          request_id=response.request_id, service_tier=response.service_tier, error=None)
        except Exception as exc:
            record.update(elapsed_seconds=perf_counter() - call_start, error=safe_api_error(exc))
            requests.append(record)
            if sink:
                sink({"type": "request", "data": record})
            reason = "api_error"
            break
        requests.append(record)
        if sink:
            sink({"type": "request", "data": record})
        if response.model and response.model != config.model and not response.model.startswith(config.model + "-"):
            reason = "model_mismatch"
            break
        message = response.message
        if not isinstance(message, dict) or message.get("role") != "assistant":
            reason = "protocol_error"
            break
        history.append(deepcopy(message))  # Preserve the original assistant message.
        calls = message.get("tool_calls")
        if calls:
            if not isinstance(calls, list):
                reason = "protocol_error"
                break
            ids_seen: set[str] = set()
            malformed = False
            for index, call in enumerate(calls):
                call_id = call.get("id") if isinstance(call, dict) else None
                if not isinstance(call_id, str) or not call_id or call_id in ids_seen:
                    malformed = True
                    continue
                ids_seen.add(call_id)
                tool_start = perf_counter()
                result = (dispatch(call, registry or {}) if index < 32
                          else error("LIMIT_EXCEEDED", "At most 32 tool executions per model response."))
                event = {"round": round_number, "tool_call_id": call_id, "call": deepcopy(call),
                         "result": result, "elapsed_seconds": perf_counter() - tool_start}
                tool_events.append(event)
                history.append({"role": "tool", "tool_call_id": call_id,
                                "content": json.dumps(result, ensure_ascii=False, allow_nan=False)})
                if sink:
                    sink({"type": "tool", "data": event})
            if malformed or not definitions:
                reason = "protocol_error"
                break
            continue
        final = message.get("content")
        answer = parse_answer(final)
        if response.finish_reason != "stop":
            reason = "incomplete_completion"
        elif answer is None:
            reason = "format_error"
        else:
            status, reason = "completed", None
        break
    parsed = parse_answer(final) if status == "completed" else None
    return {"status": status, "reason": reason, "answer": parsed.to_dict() if parsed else None,
            "final_text": final, "messages": history, "requests": requests,
            "tool_events": tool_events, "elapsed_seconds": perf_counter() - started}
