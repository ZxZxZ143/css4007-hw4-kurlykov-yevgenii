from pathlib import Path

from css4007_hw4.config import Config
from css4007_hw4.evaluation.pricing import Pricing
from css4007_hw4.experiments.runner import load_records, run_experiment
from css4007_hw4.experiments.storage import read_json, write_json
from css4007_hw4.llm.client import Client

ABLATION_IDS = ["Q-01", "Q-03", "Q-08", "Q-09", "Q-18"]


def run_ablation(root: Path, output: Path, baseline: Path, client: Client) -> list[dict]:
    manifest = read_json(baseline / "manifest.json")
    config = Config(**manifest["config"])
    pricing = Pricing(**manifest["pricing"]) if manifest["pricing"] else None
    run_experiment(root, output, client, config, ["S3"], ABLATION_IDS, pricing=pricing,
                   vague_lookup=True, baseline=baseline, kind=manifest["kind"])
    return compare_ablation(baseline, output)


def compare_ablation(baseline: Path, output: Path) -> list[dict]:
    originals = {r["question_id"]: r for r in load_records(baseline) if r["strategy"] == "S3"}
    rows = []
    for record in load_records(output):
        original = originals[record["question_id"]]
        row = {"question_id": record["question_id"]}
        for name, entry in [("original", original), ("vague", record)]:
            row[name] = {"tool_calls": len(entry["execution"]["tool_events"]),
                         "arguments": [t["call"]["function"] for t in entry["execution"]["tool_events"]],
                         "answer": entry["execution"]["final_text"], "correct": entry["score"]["correct"]}
        rows.append(row)
    write_json(output / "comparison.json", rows)
    return rows
