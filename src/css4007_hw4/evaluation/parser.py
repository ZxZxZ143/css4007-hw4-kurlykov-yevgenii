import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

PATTERN = re.compile(r"ANSWER: ([A-Za-z][A-Za-z '’-]*) \| ([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)")


@dataclass(frozen=True)
class Answer:
    name: str
    value: Decimal

    def to_dict(self) -> dict:
        return {"name": self.name, "value": str(self.value)}


def parse_answer(text: str | None) -> Answer | None:
    if not isinstance(text, str):
        return None
    lines = text.strip().splitlines()
    if not lines or sum(line.lstrip().startswith("ANSWER:") for line in lines) != 1:
        return None
    line = lines[-1].strip()
    if len(line) > 512:
        return None
    match = PATTERN.fullmatch(line)
    if not match:
        return None
    try:
        value = Decimal(match[2])
        if not value.is_finite() or value.copy_abs() > Decimal("1e15") or value.as_tuple().exponent < -100:
            return None
        return Answer(match[1].strip(), value)
    except InvalidOperation:
        return None
