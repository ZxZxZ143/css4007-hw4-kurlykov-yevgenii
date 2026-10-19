# Installation and reproduction

Use Python 3.11+ and run from the repository root. The verified environment was
Windows, Python 3.14.2; `requirements-lock.txt` records the installed versions.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -e .
```

For the exact dependency versions, replace `requirements.txt` with
`requirements-lock.txt`. An editable install exposes both `hw4` and
`python -m css4007_hw4`; examples below use the latter. On Linux/macOS replace
`.\.venv\Scripts\python.exe` with `.venv/bin/python`.

## Configuration and offline checks

Copy `.env.example` to `.env` only if `.env` does not already exist; edit it locally
and set `OPENAI_API_KEY`. Alternatively set that environment variable through your
shell or secret manager. `.env` is ignored. Do not put a real key in a command,
log, notebook, example file or Git commit. The CLI loads the repository `.env`
without overriding an existing environment variable.

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m css4007_hw4 lookup "Brightwater population 2025 area" --top-k 1
.\.venv\Scripts\python.exe -m css4007_hw4 calculate '{"mode":"evaluate","expression":"48317 * 1.0947"}'
.\.venv\Scripts\python.exe -m css4007_hw4 calculate '{"mode":"convert","value":2.5,"from_unit":"ML","to_unit":"m3"}'
```

Tests use deterministic fake clients, including two complete 20-question fixture
runs in pytest's temporary directory. They do not call OpenAI and do not create
synthetic experiment results in `outputs/`.

The tool contracts are in `src/css4007_hw4/tools/definitions.json` and are tested
against A2. This application never writes `SUBMISSION.md`.

## Preflight and smoke experiment

Output paths must be new. Existing diagnostics and runs are never overwritten.
Choose a fresh filename for a later probe; preserve the original evidence.

```powershell
.\.venv\Scripts\python.exe -m css4007_hw4 probe --output outputs/preflight_new.json
.\.venv\Scripts\python.exe -m css4007_hw4 run --questions Q-01 Q-03 Q-09 --preflight outputs/preflight_new.json --output outputs/smoke_new
```

Preflight checks account model access with `models.retrieve`, then performs a real
Chat Completions tool conversation. It records parameter acceptance, tokens,
timing and cost separately from the benchmark. A missing credential, rejected
model, failed request or unobserved tool call blocks readiness. No alternative
model is substituted. Temperature defaults to 0.7 with `reasoning_effort=none`.
If the API rejects temperature, retain that failure and explicitly repeat the
probe and ALL experiments with `--temperature none`. Do not mix settings.

Other run/probe settings: `--max-rounds 8`, `--max-completion-tokens 4096`,
`--timeout 90`, `--reasoning-effort none`. S2 is fixed at five samples.
`--root PATH` goes BEFORE the subcommand when running outside the repository.

## One question, Q-09, each strategy and two full runs

```powershell
.\.venv\Scripts\python.exe -m css4007_hw4 run --strategies S1 --questions Q-01 --preflight outputs/preflight_new.json --output outputs/one_question_new
.\.venv\Scripts\python.exe -m css4007_hw4 run --strategies S3 --questions Q-09 --preflight outputs/preflight_new.json --output outputs/q09_new
.\.venv\Scripts\python.exe -m css4007_hw4 inspect-trace --trace outputs/q09_new/traces/S3/Q-09.json --output outputs/q09_new/comparison.json

.\.venv\Scripts\python.exe -m css4007_hw4 run --strategies S1 --preflight outputs/preflight_new.json --output outputs/s1_new
.\.venv\Scripts\python.exe -m css4007_hw4 run --strategies S2 --preflight outputs/preflight_new.json --output outputs/s2_new
.\.venv\Scripts\python.exe -m css4007_hw4 run --strategies S3 --preflight outputs/preflight_new.json --output outputs/s3_new

.\.venv\Scripts\python.exe -m css4007_hw4 run --preflight outputs/preflight_new.json --output outputs/run_1_new
.\.venv\Scripts\python.exe -m css4007_hw4 run --preflight outputs/preflight_new.json --baseline outputs/run_1_new --output outputs/run_2_new
```

The individual strategy commands are optional diagnostics; the last two commands
produce the complete comparison. All work runs sequentially. Questions use dataset
order; S1, S2 and S3 run in that order. Keep source/configuration/protocol/data fixed
between paired runs. Before any full run, `docs/evaluation_protocol.md` must be
committed; the runner enforces this. The second run checks all controlled settings
and hashes against its baseline. Failures are saved, not silently retried; SDK
retries are disabled. A failed request may have unknown usage/charges.

## Ablation and analysis

```powershell
.\.venv\Scripts\python.exe -m css4007_hw4 ablation --baseline outputs/run_1_new --preflight outputs/preflight_new.json --output outputs/ablation_new
.\.venv\Scripts\python.exe -m css4007_hw4 metrics --run outputs/run_1_new
.\.venv\Scripts\python.exe -m css4007_hw4 metrics --run outputs/run_2_new
.\.venv\Scripts\python.exe -m css4007_hw4 analyze --run-1 outputs/run_1_new --run-2 outputs/run_2_new --output outputs/part_c_new.json
```

C1 uses Q-01, Q-03, Q-08, Q-09, Q-18, selected in the protocol before runs. Only
lookup's description becomes `Looks things up.`. Baseline settings, parameters and
implementation must match. Comparison includes all arguments, call counts, answers
and correctness. `analyze` reports representative failures/expensive cases,
maximum S3 rounds, error categories, question types and paired variation. These
are descriptive observations; the student supplies justified interpretations.

`metrics` recalculates scores and totals from per-question raw execution data and
writes `summary.regenerated.json`. It refuses modified source/protocol/reference
hashes or missing traces. For archived runs, check out their recorded implementation
commit before regenerating. It does not silently replace `summary.json`.

## Token and design diagnostics

```powershell
.\.venv\Scripts\python.exe -m css4007_hw4 overhead --output outputs/offline/tool_overhead_new.json
.\.venv\Scripts\python.exe -m css4007_hw4 replay-design --output outputs/offline/a3_tool_replay_new.json
```

`overhead` is a tiktoken estimate of compact schema JSON, with tokenizer and version
recorded. It is not an API token delta. `replay-design` executes the handwritten A3
tool arguments with real Python tools and NO model. Its manual final answer is
explicitly labeled and must not be reported as a real S3 response.

## Prices and stored evidence

Default verified rates on 2026-10-20: input $0.20, cached input $0.02, output $1.20
per million tokens, standard service tier and <=272,000 prompt tokens. Source:
[OpenAI GPT-5.6 Luna model page](https://developers.openai.com/api/docs/models/gpt-5.6-luna).
Rates/source/date go into every manifest. `--unknown-pricing` records unknown cost;
`--pricing path.json` accepts an explicit `Pricing` configuration with the same
fields as the manifest's pricing object. Reverify prices for future runs. Missing
usage or cache details produces unknown totals/cost, not invented numbers.

```text
outputs/
  preflight.json                  real account/capability diagnostic
  offline/
    pytest.txt                    actual offline test output
    tool_overhead.json             tokenizer estimate
    a3_tool_replay.json            manually prescribed tool execution
    verification.json              final integrity checks
  smoke/                          three-question live smoke run
  q09/                            separate actual Q-09 conversation
  run_1/ and run_2/
    manifest.json                 configuration, hashes, prices, revision, status
    summary.json                  measured strategy totals
    summary.regenerated.json      independent regeneration
    traces/S1/Q-01.json            execution, post-inference score, usage
    traces/S1/Q-01.events.jsonl    flushed request/tool event journal
    traces/S2/...                  all five samples and votes
    traces/S3/...                  messages, requests and tool results
  ablation/
    comparison.json               original versus vague lookup description
    manifest.json, summary.json, traces/...
  part_c.json                     programmatic evidence
```

Request journals flush after each completed invocation/tool. If the process stops
mid-request, its remote charge/usage may be unknowable; retain the partial run and
create a new output directory. No resume/overwrite behavior is implied. Manifest
`completed` means all questions were attempted, not that all answers were correct.

## Architecture

`retrieval` loads and indexes only corpus data. `tools` validates inputs and returns
evidence/arithmetic. `llm` builds prompts and adapts the official SDK. `orchestration`
preserves message history, dispatches calls and limits rounds. `strategies` supplies
the three inference paths; none accepts reference answers. `evaluation` parses,
votes, scores and accounts for usage after inference. `experiments` coordinates
sequential runs, journals and reproducible analysis. `cli` provides the commands.

All input/output documents are treated as data. Corpus paths are fixed by the
application, not model arguments. Calculations never invoke dynamic code. Error
logs omit raw API exception bodies. No secrets or `.env` belong in Git. Preserve
the original assignment documents and write Parts B/C separately in your own words.
