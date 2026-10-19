from dataclasses import asdict, dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Pricing:
    input_per_million: str = "0.20"
    cached_input_per_million: str = "0.02"
    output_per_million: str = "1.20"
    source: str = "https://developers.openai.com/api/docs/models/gpt-5.6-luna"
    verified_date: str = "2026-10-20"
    model: str = "gpt-5.6-luna"
    currency: str = "USD"
    service_tier: str = "default"
    max_prompt_tokens: int = 272000

    def __post_init__(self) -> None:
        for rate in (self.input_per_million, self.cached_input_per_million, self.output_per_million):
            number = Decimal(rate)
            if not number.is_finite() or number < 0:
                raise ValueError("Prices must be finite nonnegative decimal strings.")
        if not self.source or not self.verified_date:
            raise ValueError("Pricing requires a source and verification date.")

    def to_dict(self) -> dict:
        return asdict(self)


def request_cost(request: dict, pricing: Pricing | None) -> Decimal | None:
    usage = request.get("usage")
    if pricing is None or not isinstance(usage, dict) or request.get("error"):
        return None
    if request.get("service_tier") not in (None, pricing.service_tier):
        return None
    returned = request.get("returned_model")
    if returned and returned != pricing.model and not returned.startswith(pricing.model + "-"):
        return None
    prompt, output = usage.get("prompt_tokens"), usage.get("completion_tokens")
    cached = (usage.get("prompt_tokens_details") or {}).get("cached_tokens")
    if any(type(n) is not int or n < 0 for n in (prompt, output, cached)):
        return None
    if cached > prompt or prompt > pricing.max_prompt_tokens:
        return None
    return (Decimal(prompt - cached) * Decimal(pricing.input_per_million)
            + Decimal(cached) * Decimal(pricing.cached_input_per_million)
            + Decimal(output) * Decimal(pricing.output_per_million)) / Decimal(1_000_000)
