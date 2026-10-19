import os
from dataclasses import dataclass
from typing import Any, Protocol

from css4007_hw4.config import Config


@dataclass
class ModelResponse:
    message: dict[str, Any]
    usage: dict[str, Any] | None = None
    model: str | None = None
    finish_reason: str = "stop"
    request_id: str | None = None
    service_tier: str | None = None


class Client(Protocol):
    def complete(self, messages: list[dict], tools: list[dict] | None, config: Config) -> ModelResponse: ...


def credential_present() -> bool:
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    return bool(key and key != "sk-...")


def safe_api_error(exc: Exception) -> dict:
    """Never persist exception text/HTTP bodies: they can contain credentials."""
    status = getattr(exc, "status_code", None)
    return {"code": "API_ERROR", "type": type(exc).__name__,
            "http_status": status if isinstance(status, int) else None,
            "message": "Model request failed; inspect credentials, model access, network and billing."}


class OpenAIClient:
    def __init__(self, config: Config):
        if not credential_present():
            raise ValueError("OPENAI_API_KEY is missing or still the example placeholder.")
        from openai import OpenAI
        # Disable implicit retries so every actual request is accounted for.
        self.sdk = OpenAI(api_key=os.environ["OPENAI_API_KEY"], max_retries=0,
                          timeout=config.timeout_seconds, base_url="https://api.openai.com/v1")

    def complete(self, messages: list[dict], tools: list[dict] | None, config: Config) -> ModelResponse:
        kwargs = config.request_settings()
        if tools:
            kwargs.update(tools=tools, tool_choice="auto", parallel_tool_calls=True)
        response = self.sdk.chat.completions.create(messages=messages, **kwargs)
        choice = response.choices[0]
        return ModelResponse(message=choice.message.model_dump(exclude_none=True),
                             usage=response.usage.model_dump() if response.usage else None,
                             model=response.model, finish_reason=choice.finish_reason,
                             request_id=getattr(response, "_request_id", None),
                             service_tier=getattr(response, "service_tier", None))
