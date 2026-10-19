from decimal import Decimal

import pytest

from css4007_hw4.evaluation.metrics import usage_totals
from css4007_hw4.evaluation.parser import parse_answer
from css4007_hw4.evaluation.pricing import Pricing
from css4007_hw4.evaluation.scorer import score
from css4007_hw4.evaluation.voting import vote


def completed(text):
    return {"status": "completed", "final_text": text}


@pytest.mark.parametrize("text,valid", [("ANSWER: yes | 1e3", True), ("Explanation\nANSWER: Millbrook | .6", True),
                                       ("ANSWER: yes | NaN", False), ("ANSWER: yes | 1,000", False),
                                       ("ANSWER: yes | 1\nafter", False), ("ANSWER: yes | 1\nANSWER: yes | 2", False),
                                       ("ANSWER: yes | 1e900", False), ("ANSWER: yes | 1e-900", False),
                                       ("ANSWER: yes | 1e999999999", False),
                                       ("ANSWER:yes|1", False), ("ANSWER: yes | 1 m", False), (None, False)])
def test_parser(text, valid):
    assert (parse_answer(text) is not None) is valid


def test_rounding_tolerance_and_wrong_vs_unanswered():
    ref = {"answer": "Millbrook", "value": 0.6, "decimals": 1}
    assert score(completed("ANSWER: Millbrook | 0.5556561156"), ref)["correct"]
    assert score(completed("ANSWER: Millbrook | 0.7"), ref)["correct"]
    assert not score(completed("ANSWER: Millbrook | 0.75"), ref)["correct"]
    assert score(completed("ANSWER: millbrook | 0.6"), ref)["category"] == "name_mismatch"
    assert not score(completed("ANSWER: no | 5"), ref)["unanswered"]
    assert score({"status": "unanswered", "reason": "round_limit", "final_text": "ANSWER: Millbrook | .6"}, ref)["unanswered"]


def test_joint_voting_and_ties():
    samples = [completed(f"ANSWER: {name} | {value}") for name, value in
               [("yes", "5"), ("no", "5"), ("no", "5.0"), ("yes", "6"), ("yes", "5e0")]]
    winner, votes = vote(samples)
    assert winner == 0 and len(votes) == 5
    assert vote([completed("bad")])[0] is None
    assert vote([completed("ANSWER: yes | -0"), completed("ANSWER: yes | 0")])[1][0]["number"] == "0.000000"


def test_exact_usage_and_cached_cost():
    requests = [{"usage": {"prompt_tokens": 1000, "completion_tokens": 100,
                           "prompt_tokens_details": {"cached_tokens": 500}}} for _ in range(5)]
    totals = usage_totals(requests, Pricing())
    assert totals["input_tokens"] == 5000 and totals["output_tokens"] == 500
    assert Decimal(totals["cost_usd"]) == Decimal("0.00115")


def test_missing_usage_and_pricing():
    totals = usage_totals([{"usage": {"prompt_tokens": 10, "completion_tokens": 5}}, {"usage": None}], Pricing())
    assert totals["input_tokens"] is None and totals["measured_input_tokens"] == 10
    assert totals["cost_usd"] is None and totals["missing_usage_requests"] == 1
    assert usage_totals([], None)["cost_usd"] is None


@pytest.mark.parametrize("modification", [{"service_tier": "priority"}, {"returned_model": "different-model"},
                                          {"error": {"code": "API_ERROR"}}, {"usage": {"prompt_tokens": 500000, "completion_tokens": 2,
                                                                                                  "prompt_tokens_details": {"cached_tokens": 0}}}])
def test_unknown_price_cases(modification):
    request = {"usage": {"prompt_tokens": 5, "completion_tokens": 2, "prompt_tokens_details": {"cached_tokens": 0}}}
    request.update(modification)
    assert usage_totals([request], Pricing())["cost_usd"] is None
