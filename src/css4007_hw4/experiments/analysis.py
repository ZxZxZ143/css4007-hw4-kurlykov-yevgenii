from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

from css4007_hw4.experiments.runner import load_records, verify_comparable
from css4007_hw4.experiments.storage import read_json, write_json


def question_type(text: str) -> str:
    text = text.lower()
    for words, label in [(('water',), "water"), (("density", "denser"), "density"),
                         (("budget",), "budget"), (("pupils",), "schools"),
                         (("population", "censuses"), "population"), (("road",), "road")]:
        if any(w in text for w in words):
            return label
    return "other"


def trace_excerpt(record: dict) -> dict:
    execution = record["execution"]
    return {"question_id": record["question_id"], "strategy": record["strategy"], "question": record["question"],
            "score": record["score"], "usage": record["usage"], "status": execution["status"],
            "final_text": execution["final_text"], "model_calls": len(execution["requests"]),
            "tool_calls": execution["tool_events"],
            "sample_answers": [s["final_text"] for s in execution.get("samples", [])],
            "assistant_excerpts": [str(r.get("assistant", {}).get("content", ""))[:1200] for r in execution["requests"]],
            "trace": f"traces/{record['strategy']}/{record['question_id']}.json"}


def analyze_runs(first: Path, second: Path | None = None) -> dict:
    manifest = read_json(first / "manifest.json")
    records = load_records(first)
    summary = read_json(first / "summary.json")
    representatives = {}
    for strategy in manifest["strategies"]:
        group = sorted((r for r in records if r["strategy"] == strategy), key=lambda r: r["question_id"])
        wrong = [r for r in group if not r["score"]["correct"]]
        costs_known = all(r["usage"]["cost_usd"] is not None for r in group)
        chosen = wrong[0] if wrong else max(group, key=lambda r: Decimal(r["usage"]["cost_usd"]) if costs_known
                     else r["usage"]["measured_input_tokens"] + r["usage"]["measured_output_tokens"])
        representatives[strategy] = {"selection": "first_incorrect" if wrong else "highest_cost" if costs_known else "highest_tokens",
                                     **trace_excerpt(chosen)}
    tool_records = [r for r in records if r["strategy"] == "S3"]
    failures = Counter(r["score"]["category"] for r in records if not r["score"]["correct"])
    tool_errors = Counter(t["result"]["error"]["code"] for r in records for t in r["execution"]["tool_events"]
                          if not t["result"].get("ok"))
    type_results: dict = defaultdict(dict)
    for record in records:
        group = type_results[question_type(record["question"])].setdefault(record["strategy"], {"questions": 0, "correct": 0})
        group["questions"] += 1
        group["correct"] += int(record["score"]["correct"])
    table = {qid: {r["strategy"]: r["score"]["correct"] for r in records if r["question_id"] == qid}
             for qid in manifest["question_ids"]}
    best = sorted(summary, key=lambda s: (-summary[s]["correct"], s))[:2]
    disagreement = [qid for qid, row in table.items() if len(best) == 2 and row.get(best[0]) != row.get(best[1])]
    result = {"kind": "descriptive_evidence", "run_1_summary": summary, "run_1_correctness": table,
              "representative_cases": representatives,
              "most_s3_rounds": trace_excerpt(max(tool_records, key=lambda r: len(r["execution"]["requests"]))) if tool_records else None,
              "failure_categories": dict(failures), "tool_error_categories": dict(tool_errors),
              "question_type_results": dict(type_results), "best_two_strategies": best,
              "best_two_disagreement_questions": disagreement,
              "interpretation": "Observed outcomes only. Correctness differences are not proof of causal benefit; 20 questions and two runs are limited evidence."}
    if second:
        verify_comparable(manifest, read_json(second / "manifest.json"))
        other = read_json(second / "summary.json")
        result["run_2_summary"] = other
        result["run_variation"] = {s: {"correct_change": other[s]["correct"] - summary[s]["correct"],
                                          "median_seconds_change": other[s]["median_seconds_per_question"] - summary[s]["median_seconds_per_question"],
                                          "cost_change_usd": str(Decimal(other[s]["cost_usd"]) - Decimal(summary[s]["cost_usd"]))
                                          if other[s]["cost_usd"] is not None and summary[s]["cost_usd"] is not None else None}
                                    for s in best + [s for s in summary if s not in best]}
    return result


def q09_trace(record: dict) -> dict:
    """Read observed evidence only; expression text is not proof of causal use."""
    execution = record["execution"]
    retrieved = sorted({p["doc_id"] for e in execution["tool_events"] for field in ("matches", "corrections")
                        for p in e["result"].get(field, [])})
    return {**trace_excerpt(record), "retrieved_doc_ids": retrieved,
            "nr16_retrieved": "NR-16" in retrieved,
            "corrected_area_literal_in_calculator": any("921.4" in e["call"].get("function", {}).get("arguments", "")
                                                       for e in execution["tool_events"] if e["call"].get("function", {}).get("name") == "calculate"),
            "manual_expectation": {"model_rounds": 3, "tool_order": ["lookup", "lookup", "calculate"]},
            "limitation": "A corrected-area literal is evidence of use in that call; absence does not prove correction was ignored."}


def save_analysis(first: Path, second: Path | None, output: Path) -> dict:
    result = analyze_runs(first, second)
    write_json(output, result)
    return result
