import json

from css4007_hw4.config import Config
from css4007_hw4.domain.models import Question
from css4007_hw4.strategies.direct import direct
from css4007_hw4.strategies.self_consistency import self_consistency
from css4007_hw4.strategies.tool_based import tool_based
from fakes import FakeClient, final


def test_direct_one_request_and_complete_corpus():
    client = FakeClient([final()])
    direct(client, Question("PRIVATE-ID", "question only"), "ALL DOCUMENTS", Config())
    assert len(client.calls) == 1 and client.calls[0]["tools"] is None
    assert "ALL DOCUMENTS" in client.calls[0]["messages"][0]["content"]
    assert client.calls[0]["messages"][1]["content"] == "question only"
    assert "PRIVATE-ID" not in json.dumps(client.calls)


def test_s2_exactly_five_independent_samples():
    client = FakeClient([final(f"ANSWER: yes | {n}") for n in [5, 6, 6, 6, 5]])
    result = self_consistency(client, Question("id", "question"), "corpus", Config())
    assert len(client.calls) == len(result["requests"]) == len(result["samples"]) == 5
    assert result["final_text"] == "ANSWER: yes | 6"
    assert all(c["messages"] == client.calls[0]["messages"] for c in client.calls)


def test_s2_failures_saved_not_voted():
    client = FakeClient([RuntimeError("error"), final("bad"), final(), final(), final()])
    result = self_consistency(client, Question("id", "question"), "corpus", Config())
    assert result["status"] == "completed" and len(result["votes"]) == 3
    assert len(result["requests"]) == 5


def test_s3_no_corpus_or_reference_fields():
    client = FakeClient([final()])
    tool_based(client, Question("id", "question only"), Config(), {})
    assert client.calls[0]["messages"][1]["content"] == "question only"
    assert "source_corpus" not in json.dumps(client.calls)
    assert len(client.calls[0]["tools"]) == 2
