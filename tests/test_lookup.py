import json

import pytest

from css4007_hw4.retrieval.chunker import sentences
from css4007_hw4.tools.lookup import Lookup


def passages(result):
    assert result["ok"], result
    return result["matches"] + result["corrections"]


def test_current_and_historical_population(lookup):
    result = lookup(query="Ossbridge population 2025 2020", top_k=1)
    text = " ".join(p["text"] for p in passages(result))
    assert "52,904" in text and "48,317" in text
    assert result["matches"][0]["doc_id"] == "NR-01"


@pytest.mark.parametrize("name,doc", [("Ossbridge", "NR-01"), ("Ossford", "NR-02")])
def test_similar_names_not_confused(lookup, name, doc):
    result = lookup(query=f"{name} population", top_k=1)
    assert passages(result)[0]["doc_id"] == doc


@pytest.mark.parametrize("name", ["Ossbrige", "Brightwatr"])
def test_typo_requires_explicit_retry(lookup, name):
    result = lookup(query=f"{name} population")
    assert result["error"]["code"] == "UNKNOWN_ENTITY"
    assert result["error"]["suggestions"]


def test_ambiguous_name(lookup):
    result = lookup(query="Oss population")
    # Oss is the actual river name, so it is a valid regional query.
    assert result["ok"]
    assert lookup(query="Ossbridford population")["error"]["code"] == "AMBIGUOUS_ENTITY"


def test_archives_excluded(lookup):
    result = lookup(query="Tarnvale Kelmarsh ARCHIVED population 2019", top_k=5)
    assert not {"NR-13", "NR-14"} & {p["doc_id"] for p in passages(result)}


def test_correction_and_q09_evidence(lookup):
    bright = lookup(query="Brightwater population 2025 area", top_k=1)
    assert "44,675" in bright["matches"][0]["text"]
    correction = " ".join(p["text"] for p in bright["corrections"])
    assert "921.4" in correction
    assert all(p["doc_id"] == "NR-16" and p["correction_of"] == "NR-05" for p in bright["corrections"])
    mill = lookup(query="Millbrook population 2025 area", top_k=1)
    assert "37,203" in mill["matches"][0]["text"] and "758.6" in mill["matches"][0]["text"]


@pytest.mark.parametrize("args", [{}, {"query": ""}, {"query": "   "}, {"query": 1},
                                  {"query": "x" * 301}, {"query": "water", "top_k": True},
                                  {"query": "water", "top_k": 0}, {"query": "water", "top_k": 6},
                                  {"query": "water", "path": "secrets"}])
def test_invalid_arguments(lookup, args):
    assert lookup(**args)["error"]["code"] == "INVALID_ARGUMENTS"


def test_multiple_districts(lookup):
    found = lookup(query="Redfen Kelmarsh Ossford population 2025", top_k=3)
    assert {p["doc_id"] for p in found["matches"]} == {"NR-09", "NR-04", "NR-02"}


def test_limits_and_determinism(lookup):
    for query in ["population 2025", "Brightwater Millbrook area", "water", "budget school"]:
        result = lookup(query=query, top_k=5)
        assert result == lookup(query=query, top_k=5)
        excerpts = passages(result)
        assert len(result["matches"]) <= 5 and len(excerpts) <= 10
        assert sum(len(p["text"]) for p in excerpts) <= 3000
        assert all(len(p["text"]) <= 500 and len(sentences(p["text"])) <= 2 for p in excerpts)


@pytest.mark.parametrize("content", [None, "", "not json", '{"id":"x"}',
                                      '{"id":"x","title":"a","text":"b"}\n' * 2])
def test_damaged_or_missing_corpus(tmp_path, content):
    path = tmp_path / "corpus.jsonl"
    if content is not None:
        path.write_text(content, encoding="utf-8")
    assert Lookup(path)(query="population")["error"]["code"] == "CORPUS_ERROR"


def test_unknown_query(lookup):
    assert lookup(query="zyxqv")["matches"] == []


@pytest.mark.parametrize("word", ["resident", "density", "pupil", "school", "budgets"])
def test_indicator_words_are_not_district_typos(lookup, word):
    assert lookup(query=f"Lindenmoor {word} 2025")["ok"]


def test_generic_corrections_and_context_limit(tmp_path):
    rows = [{"id": "X-1", "title": "Newtown district profile (2025)", "text": "Newtown area is 20 km2. Population is 10."}]
    rows += [{"id": f"C-{i}", "title": "Correction notice - Newtown", "text": f"Correction: Newtown area is {i} km2."}
             for i in range(11)]
    path = tmp_path / "corpus.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    assert Lookup(path)(query="Newtown population", top_k=1)["error"]["code"] == "CONTEXT_LIMIT_EXCEEDED"
    rows = rows[:2]
    path.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    assert Lookup(path)(query="Newtown population", top_k=1)["corrections"][0]["correction_of"] == "X-1"


def test_required_long_sentence_not_truncated(tmp_path):
    rows = [{"id": "X", "title": "Newtown district profile", "text": "Newtown population 5."},
            {"id": "C", "title": "Correction notice - Newtown", "text": "Correction: Newtown " + "area " * 120 + "."}]
    path = tmp_path / "corpus.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    assert Lookup(path)(query="Newtown population", top_k=1)["error"]["code"] == "CONTEXT_LIMIT_EXCEEDED"
