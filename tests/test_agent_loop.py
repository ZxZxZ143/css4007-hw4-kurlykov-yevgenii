import json

import pytest

from css4007_hw4.config import Config
from css4007_hw4.llm.client import ModelResponse
from css4007_hw4.orchestration.agent_loop import run_loop
from css4007_hw4.tools.calculate import calculate
from css4007_hw4.tools.schemas import tool_definitions
from fakes import FakeClient, assistant, final, tool_call

INITIAL = [{"role": "system", "content": "test"}, {"role": "user", "content": "Compute"}]


def run(client, **kwargs):
    return run_loop(client, INITIAL, Config(), tool_definitions(), {"calculate": calculate}, **kwargs)


def test_original_message_and_one_tool_reply():
    message = assistant(tool_call())
    message["content"] = "Checking arithmetic."
    client = FakeClient([message, final()])
    result = run(client)
    assert result["status"] == "completed" and len(result["requests"]) == 2
    assert client.calls[1]["messages"][2] == message
    assert result["messages"][2] == message
    replies = [m for m in result["messages"] if m["role"] == "tool"]
    assert len(replies) == 1 and replies[0]["tool_call_id"] == "c1"
    assert json.loads(replies[0]["content"])["value"] == 5
    assert result["requests"][0]["usage"]["prompt_tokens"] == 100


def test_multiple_tool_calls_and_rounds():
    client = FakeClient([assistant(tool_call("a"), tool_call("b")), assistant(tool_call("c")), final()])
    result = run(client)
    assert len(result["requests"]) == 3
    assert [t["tool_call_id"] for t in result["tool_events"]] == ["a", "b", "c"]
    assert len([m for m in client.calls[1]["messages"] if m["role"] == "tool"]) == 2


@pytest.mark.parametrize("arguments", ["not json", "[]", "null", '{"x":NaN}', '{"x":1,"x":2}', '"x"', "[" * 1000])
def test_invalid_json(arguments):
    result = run(FakeClient([assistant(tool_call(arguments=arguments)), final()]))
    assert result["tool_events"][0]["result"]["error"]["code"] == "INVALID_ARGUMENTS"
    assert result["status"] == "completed"


def test_unknown_tool():
    result = run(FakeClient([assistant(tool_call(name="system")), final()]))
    assert result["tool_events"][0]["result"]["error"]["code"] == "UNKNOWN_TOOL"


def test_tool_exception_is_contained():
    def broken(**kwargs):
        raise RuntimeError("secret-value")
    result = run_loop(FakeClient([assistant(tool_call()), final()]), INITIAL, Config(), tool_definitions(), {"calculate": broken})
    assert result["tool_events"][0]["result"]["error"]["code"] == "INTERNAL_ERROR"
    assert "secret-value" not in json.dumps(result)


def test_round_limit_replies_to_last_tool():
    result = run(FakeClient([assistant(tool_call())]), max_calls=1)
    assert result["status"] == "unanswered" and result["reason"] == "round_limit"
    assert result["messages"][-1]["role"] == "tool"


def test_duplicate_ids_stop_before_invalid_next_request():
    client = FakeClient([assistant(tool_call(), tool_call())])
    result = run(client)
    assert result["reason"] == "protocol_error" and len(client.calls) == 1
    assert len(result["tool_events"]) == 1


def test_missing_id_is_protocol_failure():
    call = tool_call()
    del call["id"]
    assert run(FakeClient([assistant(call)]))["reason"] == "protocol_error"


def test_api_error_redacts_details_and_logs_attempt():
    result = run(FakeClient([RuntimeError("sk-never-log-this")]))
    assert result["reason"] == "api_error" and len(result["requests"]) == 1
    assert result["requests"][0]["usage"] is None
    assert "sk-never-log-this" not in json.dumps(result)


@pytest.mark.parametrize("message", [final("unknown"), final("")])
def test_bad_final_format(message):
    assert run(FakeClient([message]))["reason"] == "format_error"


def test_truncation_cannot_count_as_answer():
    assert run(FakeClient([ModelResponse(final(), finish_reason="length")]))["reason"] == "incomplete_completion"


def test_missing_usage_not_invented():
    result = run(FakeClient([ModelResponse(final())]))
    assert result["requests"][0]["usage"] is None


def test_invalid_input_no_calls():
    client = FakeClient([])
    result = run_loop(client, [{"role": "user", "content": " "}], Config())
    assert result["reason"] == "invalid_input" and not client.calls


def test_event_sink():
    events = []
    run(FakeClient([assistant(tool_call()), final()]), sink=events.append)
    assert [event["type"] for event in events] == ["request", "tool", "request"]


def test_exact_a2_contracts():
    import re
    from conftest import ROOT
    blocks = re.findall(r"```json\s*(.*?)\s*```", (ROOT / "SUBMISSION.md").read_text(encoding="utf-8"), re.S)
    expected = [json.loads(block) for block in blocks[:2]]
    assert tool_definitions() == expected
    vague = tool_definitions(vague_lookup=True)
    expected[0]["function"]["description"] = "Looks things up."
    assert vague == expected
