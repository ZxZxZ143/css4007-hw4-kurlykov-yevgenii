import math
from typing import Any

from css4007_hw4.domain.errors import ToolError

NUMERIC_LIMIT = 1e15


def checked_number(value: Any) -> float:
    if type(value) not in (int, float):
        raise ToolError("INVALID_ARGUMENTS", "A real numeric value is required; booleans are invalid.")
    if abs(value) > NUMERIC_LIMIT or not math.isfinite(value):
        raise ToolError("LIMIT_EXCEEDED", "Numeric values must be finite and have absolute value <= 1e15.")
    return float(value)


def fields(arguments: dict[str, Any], required: set[str], optional: set[str]) -> None:
    if required - arguments.keys() or arguments.keys() - required - optional:
        raise ToolError("INVALID_ARGUMENTS", "Missing required fields or unexpected/wrong-mode fields.")
