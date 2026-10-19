from dataclasses import asdict, dataclass
import math

MODEL = "gpt-5.6-luna"


@dataclass(frozen=True)
class Config:
    model: str = MODEL
    temperature: float | None = 0.7
    reasoning_effort: str = "none"
    max_completion_tokens: int = 4096
    max_rounds: int = 8
    samples: int = 5
    timeout_seconds: float = 90.0

    def __post_init__(self) -> None:
        if self.model != MODEL:
            raise ValueError("The assignment requires gpt-5.6-luna; substitution is disabled.")
        if type(self.max_rounds) is not int or not 1 <= self.max_rounds <= 32:
            raise ValueError("max_rounds must be an integer from 1 to 32.")
        if self.samples != 5:
            raise ValueError("S2 requires exactly five samples.")
        if self.temperature is not None and (type(self.temperature) not in (int, float)
                or not math.isfinite(self.temperature) or not 0 <= self.temperature <= 2):
            raise ValueError("temperature must be null or a number in [0,2].")
        if self.reasoning_effort not in {"none", "low", "medium", "high", "xhigh", "max"}:
            raise ValueError("Unsupported reasoning_effort.")
        if type(self.max_completion_tokens) is not int or self.max_completion_tokens < 64:
            raise ValueError("max_completion_tokens must be >=64.")
        if not math.isfinite(self.timeout_seconds) or self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be finite and positive.")

    def request_settings(self) -> dict:
        result = {"model": self.model, "reasoning_effort": self.reasoning_effort,
                  "max_completion_tokens": self.max_completion_tokens, "service_tier": "default"}
        if self.temperature is not None:
            result["temperature"] = self.temperature
        return result

    def to_dict(self) -> dict:
        return asdict(self)
