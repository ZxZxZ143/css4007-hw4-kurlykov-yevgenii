from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from css4007_hw4.config import Config
from css4007_hw4.llm.client import ModelResponse, OpenAIClient
from css4007_hw4.orchestration.agent_loop import run_loop
from css4007_hw4.tools.schemas import tool_definitions
from fakes import FakeClient, final


def test_official_sdk_request_mapping(monkeypatch):
    import openai
    sdk = Mock()
    message = Mock()
    message.model_dump.return_value = final()
    usage = Mock()
    usage.model_dump.return_value = {"prompt_tokens": 7, "completion_tokens": 5}
    sdk.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=message, finish_reason="stop")], usage=usage,
        model=Config().model, _request_id="test-id", service_tier="default")
    constructor = Mock(return_value=sdk)
    monkeypatch.setattr(openai, "OpenAI", constructor)
    monkeypatch.setenv("OPENAI_API_KEY", "dummy-test-key")
    client = OpenAIClient(Config())
    response = client.complete([{"role": "user", "content": "question"}], tool_definitions(), Config())
    assert constructor.call_args.kwargs["max_retries"] == 0
    sent = sdk.chat.completions.create.call_args.kwargs
    assert sent["model"] == "gpt-5.6-luna" and sent["temperature"] == 0.7
    assert sent["tools"] == tool_definitions() and "api_key" not in sent
    assert response.usage["prompt_tokens"] == 7
    assert response.message == final()


def test_substitution_disabled():
    with pytest.raises(ValueError, match="substitution"):
        Config(model="other")
    client = FakeClient([ModelResponse(final(), model="other")])
    result = run_loop(client, [{"role": "user", "content": "question"}], Config())
    assert result["reason"] == "model_mismatch"


def test_none_temperature_omitted():
    assert "temperature" not in Config(temperature=None).request_settings()
