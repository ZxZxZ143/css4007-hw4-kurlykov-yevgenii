from copy import deepcopy
import json
from pathlib import Path

import pytest

from conftest import ROOT
from css4007_hw4.cli import main
from css4007_hw4.config import Config
from css4007_hw4.evaluation.pricing import Pricing
from css4007_hw4.experiments.ablation import ABLATION_IDS, run_ablation
from css4007_hw4.experiments.analysis import analyze_runs
from css4007_hw4.experiments.diagnostics import probe, replay_manual_design
from css4007_hw4.experiments.runner import regenerate, run_experiment, verify_comparable
from css4007_hw4.experiments.storage import read_json, write_json
from fakes import FakeClient, final


def test_full_fake_pipeline_and_metric_regeneration(tmp_path):
    # Synthetic transport responses are TEST FIXTURES ONLY, never saved to outputs/.
    first, second = tmp_path / "run1", tmp_path / "run2"
    for path in [first, second]:
        summary = run_experiment(ROOT, path, FakeClient([final()] * 140), Config(), ["S1", "S2", "S3"],
                                 pricing=Pricing(), baseline=first if path == second else None, kind="test_fixture")
        assert all(s["questions"] == 20 for s in summary.values())
        assert summary["S2"]["api_requests"] == 100
        assert summary == regenerate(ROOT, path)
    analysis = analyze_runs(first, second)
    assert len(analysis["run_1_correctness"]) == 20
    assert set(analysis["representative_cases"]) == {"S1", "S2", "S3"}
    assert all(v["correct_change"] == 0 for v in analysis["run_variation"].values())
    rows = run_ablation(ROOT, tmp_path / "ablation", first, FakeClient([final()] * 5))
    assert [r["question_id"] for r in rows] == ABLATION_IDS
    assert all(r["original"]["answer"] == r["vague"]["answer"] for r in rows)


def test_reference_fields_do_not_cross_inference_boundary(tmp_path, monkeypatch):
    from css4007_hw4.experiments import runner
    original = runner.read_json
    def modified(path):
        value = original(path)
        if path.name == "questions.json":
            for row in value:
                row.update(answer="REFERENCE_SENTINEL", value=987654321.123, sources=["SECRET_SOURCE"], decimals=11, unit="SECRET_UNIT")
        return value
    monkeypatch.setattr(runner, "read_json", modified)
    client = FakeClient([final()] * 7)
    runner.run_experiment(ROOT, tmp_path / "run", client, Config(), ["S1", "S2", "S3"], ["Q-01"], kind="test_fixture")
    serialized = json.dumps(client.calls)
    assert all(marker not in serialized for marker in ["REFERENCE_SENTINEL", "987654321", "SECRET_SOURCE", "SECRET_UNIT", "Q-01"])
    question = original(ROOT / "data/questions.json")[0]["question"]
    assert all(call["messages"][1] == {"role": "user", "content": question} for call in client.calls)


def test_existing_output_never_overwritten(tmp_path):
    output = tmp_path / "run"
    output.mkdir()
    with pytest.raises(FileExistsError):
        run_experiment(ROOT, output, FakeClient([]), Config(), ["S1"], ["Q-01"])


def test_incomplete_trace_detected(tmp_path):
    output = tmp_path / "run"
    run_experiment(ROOT, output, FakeClient([final()]), Config(), ["S1"], ["Q-01"], kind="test_fixture")
    (output / "traces/S1/Q-01.json").unlink()
    with pytest.raises(ValueError, match="incomplete"):
        regenerate(ROOT, output)


def test_changed_protocol_refuses_regeneration(tmp_path):
    output = tmp_path / "run"
    run_experiment(ROOT, output, FakeClient([final()]), Config(), ["S1"], ["Q-01"], kind="test_fixture")
    manifest = read_json(output / "manifest.json")
    manifest["protocol_sha256"] = "different"
    write_json(output / "manifest.json", manifest)
    with pytest.raises(ValueError, match="rescoring"):
        regenerate(ROOT, output)


def test_paired_config_mismatch_refused(tmp_path):
    output = tmp_path / "run"
    run_experiment(ROOT, output, FakeClient([final()]), Config(), ["S1"], ["Q-01"], kind="test_fixture")
    first = read_json(output / "manifest.json")
    second = deepcopy(first)
    second["config"]["temperature"] = None
    with pytest.raises(ValueError, match="config"):
        verify_comparable(first, second)


def test_missing_key_preflight(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = probe(ROOT, Config())
    assert result["status"] == "blocked" and result["reason"] == "missing_api_key"
    assert result["api_requests"] == 0 and result["temperature_support"] == "unverified"


def test_manual_replay_explicitly_not_live():
    result = replay_manual_design(ROOT)
    assert result["model_invocations"] == 0 and result["kind"] == "offline_manual_tool_replay"
    assert len(result["calls"]) == 3 and all(c["result"]["ok"] for c in result["calls"])


def test_cli_offline(capsys):
    assert main(["--root", str(ROOT), "lookup", "Ossbridge population", "--top-k", "1"]) == 0
    assert json.loads(capsys.readouterr().out)["matches"][0]["doc_id"] == "NR-01"
    assert main(["calculate", '{"mode":"evaluate","expression":"2+3"}']) == 0
    assert json.loads(capsys.readouterr().out)["value"] == 5
