import json
from typing import Any

from css4007_hw4.domain.errors import error
from css4007_hw4.tools.registry import Tool


def _pairs(pairs: list[tuple[str, Any]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def _constant(_: str) -> None:
    raise ValueError("non-JSON numeric constant")


def dispatch(call: dict, registry: dict[str, Tool]) -> dict:
    try:
        function = call.get("function")
        if call.get("type") != "function" or not isinstance(function, dict):
            return error("INVALID_ARGUMENTS", "Expected a function tool call.")
        name, raw = function.get("name"), function.get("arguments")
        if not isinstance(name, str) or name not in registry:
            return error("UNKNOWN_TOOL", "Tool name is not registered.")
        if not isinstance(raw, str) or len(raw) > 8192:
            return error("INVALID_ARGUMENTS", "arguments must be a JSON object string of at most 8192 characters.")
        try:
            args = json.loads(raw, object_pairs_hook=_pairs, parse_constant=_constant)
        except (ValueError, RecursionError):
            return error("INVALID_ARGUMENTS", "arguments must be valid JSON without duplicate keys or nonfinite constants.")
        if not isinstance(args, dict):
            return error("INVALID_ARGUMENTS", "arguments must decode to an object.")
        result = registry[name](**args)
        json.dumps(result, allow_nan=False)
        return result
    except Exception:
        return error("INTERNAL_ERROR", "Tool execution failed.")
