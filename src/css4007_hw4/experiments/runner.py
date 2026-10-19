from pathlib import Path
from time import perf_counter

from css4007_hw4.config import Config
from css4007_hw4.domain.models import Question
from css4007_hw4.evaluation.metrics import summarize, usage_totals
from css4007_hw4.evaluation.pricing import Pricing
from css4007_hw4.evaluation.scorer import score
from css4007_hw4.experiments.storage import (append_event, digest, git_value, json_digest,
                                           protocol_commit, read_json, source_digest, timestamp, write_json)
from css4007_hw4.llm.client import Client
from css4007_hw4.llm.prompts import COMMON, DIRECT, THINK, TOOLS
from css4007_hw4.retrieval.loader import full_corpus, load_corpus
from css4007_hw4.strategies.direct import direct
from css4007_hw4.strategies.self_consistency import self_consistency
from css4007_hw4.strategies.tool_based import tool_based
from css4007_hw4.tools.registry import registry
from css4007_hw4.tools.schemas import tool_definitions


def run_experiment(root: Path, output: Path, client: Client, config: Config,
                   strategies: list[str], ids: list[str] | None = None, *,
                   pricing: Pricing | None = None, vague_lookup: bool = False,
                   baseline: Path | None = None, kind: str = "live") -> dict:
    started = perf_counter()
    if any(s not in {"S1", "S2", "S3"} for s in strategies) or not strategies or len(set(strategies)) != len(strategies):
        raise ValueError("Strategies must be a nonempty unique list of S1, S2 and/or S3.")
    references = read_json(root / "data/questions.json")
    if ids is not None and (len(ids) != len(set(ids)) or not ids or set(ids) - {r["id"] for r in references}):
        raise ValueError("Unknown, empty or duplicate question IDs.")
    selected = [r for r in references if ids is None or r["id"] in ids]
    docs = load_corpus(root / "data/corpus.jsonl")
    corpus, tools = full_corpus(docs), registry(root / "data/corpus.jsonl")
    protocol_sha = protocol_commit(root)
    manifest = {"schema_version": 1, "kind": kind, "created_utc": timestamp(), "status": "running",
                "config": config.to_dict(), "strategies": strategies, "question_ids": [r["id"] for r in selected],
                "vague_lookup": vague_lookup, "pricing": pricing.to_dict() if pricing else None,
                "git_commit": git_value(root, "rev-parse", "HEAD"),
                "tracked_worktree_changes": git_value(root, "status", "--porcelain", "--untracked-files=no"),
                "protocol_commit": protocol_sha, "protocol_sha256": digest(root / "docs/evaluation_protocol.md"),
                "corpus_sha256": digest(root / "data/corpus.jsonl"), "questions_sha256": digest(root / "data/questions.json"),
                "source_sha256": source_digest(root), "prompts_sha256": json_digest([COMMON, DIRECT, THINK, TOOLS]),
                "tool_definitions": tool_definitions(vague_lookup=vague_lookup), "max_retries": 0}
    if baseline:
        original = read_json(baseline / "manifest.json")
        verify_comparable(original, manifest, ablation=vague_lookup)
        manifest["baseline"] = str(baseline.resolve())
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "manifest.json", manifest)
    records = []
    for strategy in strategies:
        for reference in selected:
            question = Question(reference["id"], reference["question"])
            journal = output / "traces" / strategy / f"{question.id}.events.jsonl"
            def sink(event: dict) -> None:
                append_event(journal, event)
            # The reference mapping never enters the strategy/client boundary.
            if strategy == "S1":
                execution = direct(client, question, corpus, config, sink=sink)
            elif strategy == "S2":
                execution = self_consistency(client, question, corpus, config, sink=sink)
            else:
                execution = tool_based(client, question, config, tools, vague_lookup=vague_lookup, sink=sink)
            record = {"question_id": question.id, "question": question.text, "strategy": strategy,
                      "execution": execution, "score": score(execution, reference),
                      "usage": usage_totals(execution["requests"], pricing)}
            write_json(output / "traces" / strategy / f"{question.id}.json", record)
            records.append(record)
    summary = {s: summarize([r for r in records if r["strategy"] == s], pricing) for s in strategies}
    write_json(output / "summary.json", summary)
    manifest.update(status="completed", completed_utc=timestamp(), runner_wall_seconds=perf_counter() - started)
    write_json(output / "manifest.json", manifest)
    return summary


def verify_comparable(original: dict, current: dict, *, ablation: bool = False) -> None:
    fields = ["kind", "config", "pricing", "protocol_sha256", "corpus_sha256", "questions_sha256",
              "source_sha256", "prompts_sha256"]
    if original["status"] != "completed":
        raise ValueError("Baseline experiment is incomplete.")
    if not ablation:
        fields += ["question_ids", "strategies", "tool_definitions", "vague_lookup"]
    else:
        expected = tool_definitions(vague_lookup=True)
        actual = original["tool_definitions"]
        import copy
        actual = copy.deepcopy(actual)
        actual[0]["function"]["description"] = "Looks things up."
        if actual != expected or current["tool_definitions"] != expected or current["strategies"] != ["S3"]:
            raise ValueError("Ablation may change only the lookup description.")
        if original["vague_lookup"] or "S3" not in original["strategies"] or set(current["question_ids"]) - set(original["question_ids"]):
            raise ValueError("Ablation needs a matching original S3 baseline.")
    mismatches = [field for field in fields if original[field] != current[field]]
    if mismatches:
        raise ValueError("Incomparable settings: " + ", ".join(mismatches))


def load_records(output: Path) -> list[dict]:
    return [read_json(path) for path in sorted((output / "traces").glob("*/*.json"))]


def regenerate(root: Path, output: Path) -> dict:
    manifest = read_json(output / "manifest.json")
    for name, field in [("data/questions.json", "questions_sha256"), ("docs/evaluation_protocol.md", "protocol_sha256")]:
        if digest(root / name) != manifest[field]:
            raise ValueError(f"Changed {name}; refuse silent rescoring.")
    # Current scoring code must match the archived experiment, too.
    if source_digest(root) != manifest["source_sha256"]:
        raise ValueError("Changed source code; checkout the recorded implementation before regeneration.")
    pricing = Pricing(**manifest["pricing"]) if manifest["pricing"] else None
    references = {r["id"]: r for r in read_json(root / "data/questions.json")}
    records = load_records(output)
    seen = [(r["strategy"], r["question_id"]) for r in records]
    expected = {(s, q) for s in manifest["strategies"] for q in manifest["question_ids"]}
    if len(set(seen)) != len(seen) or set(seen) != expected:
        raise ValueError("Missing, duplicate or unexpected per-question traces; run is incomplete.")
    for record in records:
        record["score"] = score(record["execution"], references[record["question_id"]])
    summary = {s: summarize([r for r in records if r["strategy"] == s], pricing) for s in manifest["strategies"]}
    write_json(output / "summary.regenerated.json", summary)
    return summary
