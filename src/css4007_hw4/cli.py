import argparse
import json
from pathlib import Path

from css4007_hw4.config import Config
from css4007_hw4.evaluation.pricing import Pricing
from css4007_hw4.experiments.ablation import run_ablation
from css4007_hw4.experiments.analysis import q09_trace, save_analysis
from css4007_hw4.experiments.diagnostics import probe, replay_manual_design, token_overhead
from css4007_hw4.experiments.runner import regenerate, run_experiment
from css4007_hw4.experiments.storage import read_json, write_json
from css4007_hw4.llm.client import OpenAIClient, credential_present
from css4007_hw4.tools.calculate import calculate
from css4007_hw4.tools.lookup import Lookup


def parser() -> argparse.ArgumentParser:
    cli = argparse.ArgumentParser(description="CSS4007 HW4 reproducible experiments")
    cli.add_argument("--root", type=Path, default=Path.cwd(), help="Repository root")
    sub = cli.add_subparsers(dest="command", required=True)
    for name in ("probe", "run", "overhead"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--output", type=Path, required=True)
        cmd.add_argument("--temperature", default="0.7", help="Number in [0,2] or none; no silent fallback")
        cmd.add_argument("--reasoning-effort", default="none")
        cmd.add_argument("--max-rounds", type=int, default=8)
        cmd.add_argument("--max-completion-tokens", type=int, default=4096)
        cmd.add_argument("--timeout", type=float, default=90)
        if name == "run":
            cmd.add_argument("--strategies", nargs="+", choices=["S1", "S2", "S3"], default=["S1", "S2", "S3"])
            cmd.add_argument("--questions", nargs="+")
            cmd.add_argument("--baseline", type=Path, help="Require matching settings/hashes with first run")
            cmd.add_argument("--preflight", type=Path, required=True, help="Successful probe JSON with identical configuration")
            cmd.add_argument("--pricing", type=Path, help="Pricing JSON; omit for verified 2026-10-20 standard rates")
            cmd.add_argument("--unknown-pricing", action="store_true")
    ablation = sub.add_parser("ablation")
    ablation.add_argument("--baseline", type=Path, required=True)
    ablation.add_argument("--output", type=Path, required=True)
    ablation.add_argument("--preflight", type=Path, required=True)
    metrics = sub.add_parser("metrics")
    metrics.add_argument("--run", type=Path, required=True)
    analyze = sub.add_parser("analyze")
    analyze.add_argument("--run-1", type=Path, required=True)
    analyze.add_argument("--run-2", type=Path)
    analyze.add_argument("--output", type=Path, required=True)
    q09 = sub.add_parser("inspect-trace")
    q09.add_argument("--trace", type=Path, required=True)
    q09.add_argument("--output", type=Path, required=True)
    replay = sub.add_parser("replay-design")
    replay.add_argument("--output", type=Path, required=True)
    lookup = sub.add_parser("lookup")
    lookup.add_argument("query")
    lookup.add_argument("--top-k", type=int, default=3)
    calc = sub.add_parser("calculate")
    calc.add_argument("arguments", help="JSON object with A2 calculate arguments")
    return cli


def require_preflight(path: Path, config: Config) -> None:
    check = read_json(path)
    if check.get("status") != "ready" or check.get("config") != config.to_dict():
        raise ValueError("A successful live preflight with identical configuration is required.")
    if not credential_present():
        raise ValueError("OPENAI_API_KEY is missing; live experiments are blocked.")


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    root = args.root.resolve()
    from dotenv import load_dotenv
    load_dotenv(root / ".env", override=False)
    try:
        config = None
        if args.command in {"probe", "run", "overhead"}:
            config = Config(temperature=None if args.temperature.lower() == "none" else float(args.temperature),
                            reasoning_effort=args.reasoning_effort, max_rounds=args.max_rounds,
                            max_completion_tokens=args.max_completion_tokens, timeout_seconds=args.timeout)
        if args.command == "lookup":
            result = Lookup(root / "data/corpus.jsonl")(query=args.query, top_k=args.top_k)
        elif args.command == "calculate":
            arguments = json.loads(args.arguments)
            if not isinstance(arguments, dict):
                raise ValueError("calculate arguments must be an object")
            result = calculate(**arguments)
        elif args.command in {"probe", "overhead", "replay-design"}:
            if args.output.exists():
                raise ValueError("Output already exists; choose a new diagnostic path.")
            result = (probe(root, config) if args.command == "probe" else token_overhead(root, config)
                      if args.command == "overhead" else replay_manual_design(root))
            write_json(args.output, result)
        elif args.command == "run":
            require_preflight(args.preflight, config)
            pricing = None if args.unknown_pricing else Pricing(**read_json(args.pricing)) if args.pricing else Pricing()
            result = run_experiment(root, args.output, OpenAIClient(config), config, args.strategies,
                                    args.questions, pricing=pricing, baseline=args.baseline)
        elif args.command == "ablation":
            config = Config(**read_json(args.baseline / "manifest.json")["config"])
            require_preflight(args.preflight, config)
            result = run_ablation(root, args.output, args.baseline, OpenAIClient(config))
        elif args.command == "metrics":
            result = regenerate(root, args.run)
        elif args.command == "analyze":
            result = save_analysis(args.run_1, args.run_2, args.output)
        else:
            result = q09_trace(read_json(args.trace))
            write_json(args.output, result)
        # ASCII-safe console JSON also works in legacy Windows code pages.
        print(json.dumps(result, ensure_ascii=True, indent=2, allow_nan=False))
        return 2 if isinstance(result, dict) and (result.get("status") == "blocked" or result.get("ok") is False) else 0
    except (OSError, ValueError, KeyError) as exc:
        # These are local validation failures, not raw API exceptions.
        print(json.dumps({"status": "blocked", "error": str(exc)}, ensure_ascii=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
