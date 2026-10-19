from importlib.metadata import version
import json
from pathlib import Path
import re
from time import perf_counter

from css4007_hw4.config import Config
from css4007_hw4.evaluation.metrics import usage_totals
from css4007_hw4.evaluation.pricing import Pricing
from css4007_hw4.experiments.storage import digest, timestamp
from css4007_hw4.llm.client import OpenAIClient, credential_present, safe_api_error
from css4007_hw4.orchestration.agent_loop import run_loop
from css4007_hw4.orchestration.dispatcher import dispatch
from css4007_hw4.retrieval.loader import full_corpus, load_corpus
from css4007_hw4.tools.registry import registry
from css4007_hw4.tools.schemas import tool_definitions


def probe(root: Path, config: Config) -> dict:
    report = {"kind": "live_preflight", "created_utc": timestamp(), "config": config.to_dict(),
              "credential_present": credential_present(), "model_access": "unverified",
              "temperature_support": "unverified", "requests": []}
    if not credential_present():
        report.update(status="blocked", reason="missing_api_key", api_requests=0,
                      message="OPENAI_API_KEY is absent or a placeholder; account access and billing cannot be verified.")
        return report
    client = OpenAIClient(config)
    started = perf_counter()
    try:
        model = client.sdk.models.retrieve(config.model)
        report["model_retrieval"] = {"id": model.id, "elapsed_seconds": perf_counter() - started}
        if model.id != config.model:
            report.update(status="blocked", reason="model_identity_mismatch")
            return report
        report["model_access"] = "listed_for_account"
    except Exception as exc:
        report.update(status="blocked", reason="model_access_failed", error=safe_api_error(exc),
                      model_retrieval={"elapsed_seconds": perf_counter() - started})
        return report
    messages = [{"role": "system", "content": "Use the calculate tool for arithmetic. End with ANSWER: yes | <number>."},
                {"role": "user", "content": "Use calculate to evaluate 2+3, then give its result."}]
    execution = run_loop(client, messages, config, tool_definitions(), registry(root / "data/corpus.jsonl"))
    success = any(r.get("error") is None for r in execution["requests"])
    report.update(execution=execution, requests=execution["requests"],
                  usage=usage_totals(execution["requests"], Pricing()),
                  temperature_support=("accepted" if config.temperature is not None else "omitted") if success else "unverified",
                  tools_observed=bool(execution["tool_events"]),
                  status="ready" if execution["status"] == "completed" and execution["tool_events"] else "blocked",
                  reason=execution["reason"] or (None if execution["tool_events"] else "tool_call_not_observed"))
    if success:
        report["model_access"] = "chat_completion_succeeded"
    return report


def token_overhead(root: Path, config: Config) -> dict:
    import tiktoken
    try:
        encoding = tiktoken.encoding_for_model(config.model)
        mapping = "model_mapping"
    except KeyError:
        encoding = tiktoken.get_encoding("o200k_base")
        mapping = "explicit_fallback_not_verified_for_model"
    definitions = tool_definitions()
    compact = json.dumps(definitions, ensure_ascii=False, separators=(",", ":"))
    return {"kind": "tokenizer_estimate", "api_measured": False, "created_utc": timestamp(),
            "model": config.model, "encoding": encoding.name, "encoding_selection": mapping,
            "tiktoken_version": version("tiktoken"), "serialization": "UTF-8 compact JSON, ensure_ascii=False",
            "tool_definition_tokens": len(encoding.encode(compact)),
            "per_tool_tokens": {d["function"]["name"]: len(encoding.encode(json.dumps(d, ensure_ascii=False, separators=(",", ":"))))
                                for d in definitions},
            "full_corpus_text_tokens": len(encoding.encode(full_corpus(load_corpus(root / "data/corpus.jsonl")))),
            "tool_definitions": definitions,
            "limitations": "Schema text estimate only; API internal formatting and message framing are not measured."}


def replay_manual_design(root: Path) -> dict:
    """Execute tool calls from the student's manual conversation, with NO model."""
    source = root / "SUBMISSION.md"
    blocks = re.findall(r"```json\s*(.*?)\s*```", source.read_text(encoding="utf-8"), re.S)
    conversation = next(json.loads(b) for b in blocks if isinstance(json.loads(b), list))
    tools = registry(root / "data/corpus.jsonl")
    calls = []
    for message in conversation:
        for call in message.get("tool_calls", []):
            started = perf_counter()
            result = dispatch(call, tools)
            calls.append({"call": call, "result": result, "elapsed_seconds": perf_counter() - started})
    return {"kind": "offline_manual_tool_replay", "model_invocations": 0, "created_utc": timestamp(),
            "design_sha256": digest(source), "calls": calls,
            "manual_final_answer_not_generated": conversation[-1].get("content"),
            "limitation": "Actual Python tool outputs for manually prescribed calls; not an S3 model conversation or benchmark."}
