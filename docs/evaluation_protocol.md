# Evaluation protocol v1 — fixed before full experiments

This file is committed before any full run. Its SHA-256 and Git commit are stored
in manifests. Regeneration refuses changed reference/protocol files. Do not edit
this protocol between paired runs. Any later correction requires a new version,
separate output directory and explicit explanation, never silent rescoring.

## Inference boundary and controls

Only question text enters inference. IDs select/store results; `answer`, `value`,
`unit`, `decimals`, and `sources` remain outside model inputs. S1/S2 receive the
complete unmodified corpus; S3 receives the two A2 schemas. Same required model
`gpt-5.6-luna`, shared source assumptions and answer format, temperature 0.7,
reasoning_effort `none`, max_completion_tokens 4096, standard service tier,
timeout 90 seconds. These are intended settings, not claims of live support.
Preflight must confirm them. If temperature is unsupported, explicitly choose
`--temperature none` for BOTH runs and all strategies and retain the failed probe.
There is no automatic model or parameter substitution. S2 k=5; S3 limit=8.

## Parsing, correctness and unanswered responses

Exactly one ANSWER line must be the last nonblank line:
`ANSWER: <name or yes/no> | <number>`. It must use the literal delimiters above.
Trim line/name outer whitespace only. Names are case-sensitive, including yes/no;
no fuzzy names or semantic grading. The number may be signed decimal/scientific
notation, with no commas or unit suffix; finite, absolute value <=1e15, at most
100 fractional exponent places and a maximum 512-character answer line.
Additional preceding explanation is permitted. Multiple ANSWER lines are invalid.

After inference, round prediction and reference independently using Decimal
ROUND_HALF_UP to reference `decimals`. A difference <=10^(-decimals), inclusive,
is accepted, matching the assignment's one-last-digit tolerance. BOTH name and
number must pass. A parseable incorrect answer is wrong, not unanswered.
API/protocol failures, truncated/refused completions, round limits and missing/
malformed final answers are unanswered and incorrect. Never infer an answer
from intermediate arithmetic or a last incomplete model message.

A1 requests final rounding using `decimals`; that conflicts with keeping that
field private. The implementation requests a precise final number and performs
the specified rounding exclusively here, after inference.

## S2 voting

Exactly five independent sequential calls use identical S2 input, no conversation
carryover. Only completed parseable samples vote. A vote key is the exact trimmed
name plus numeric value rounded HALF_UP to SIX decimal places (negative zero is
normalized). This fixed precision does not use reference values or decimals.
The complete pair with most votes wins. Ties use the earliest sample index among
the tied groups. Return that group's earliest original final answer; do not
average numbers. If no sample is valid the question is unanswered. All five
samples, failures, vote keys and winner are saved and charged.

## Requests, tokens, latency and cost

Sequential execution; perf_counter measures each model request, each tool call,
and the entire question separately. Question latency includes all samples/rounds,
tools and in-question logging. Strategy total_seconds is the sum of question
elapsed_seconds; runner_wall_seconds separately includes persistence/setup overhead.
Median is over every attempted question, including failures. Full comparisons
require exactly 20 questions per strategy; partial runs are explicitly labeled.

Sum prompt_tokens and completion_tokens from EVERY actual SDK invocation, including
all S2 samples and S3 rounds. Completion usage includes reasoning tokens when the
API counts them. Cached prompt tokens remain part of input token totals. Never
count the aggregate S2 requests and nested samples twice. Disable SDK retries;
no automatic retries. A later rerun is a separate immutable run, not a replacement.
An attempted request without usage contributes to missing_usage_requests, not a
fabricated zero. Report measured subtotals and null totals/cost when incomplete.

Cost is (uncached input*input rate + cached input*cached rate + output*output rate)
/1,000,000, using exact decimal arithmetic. Rates, currency, source, verification
date and applicable model/service tier are recorded in every manifest. Missing
rates, cache details, incompatible service tier, or incomplete usage means unknown
cost, never zero. Rates are estimates of token charges, not an invoice including
taxes/credits. Supplied rates apply only to standard text requests <=272,000 input
tokens; other pricing tiers remain unknown. Probe/diagnostic calls are accounted
for separately from benchmark totals. Failed requests may have unknown charges.

## Tool definition overhead

The offline diagnostic encodes compact JSON serialization of the EXACT two tool
definitions with a named tiktoken encoding and version. It is a tokenizer-based
estimate of schema text, NOT an API-measured prompt-token difference, because
server tool serialization/framing can differ. Explicit fallback encoding is
recorded when the model-specific mapping is unavailable. No estimate is mixed
into measured API usage.

## Experiments and interpretation

First run a 3-question smoke test (Q-01, Q-03, Q-09), then an independent Q-09 S3
trace, then two complete runs with identical configurations and question order.
S1, S2, S3 run in that order; samples and questions are sequential. Manifest hashes
cover source code, corpus, questions, prompts, schemas and protocol. API randomness,
caching and remote load are uncontrolled and must be acknowledged.

C1 preselects Q-01, Q-03, Q-08, Q-09, Q-18: similar names, volume conversion,
tariff, corrected area, projection. Reuse run_1 S3 as baseline. Change ONLY lookup
description to `Looks things up.`; retain schema parameters, code and settings.
Report calls, arguments, answers and correctness without inventing causal claims.

C2 selects the first wrong/unanswered question in dataset order for each strategy;
if all correct, select highest known cost, then total tokens if cost is unknown,
then earliest ID. Report most S3 rounds, paired changes, disagreement of the two
highest-accuracy strategies, and observable error categories. Question type labels
come from question wording only. No causal explanation follows from a category
alone. Twenty questions and two runs are descriptive evidence, not a reliable
population ranking or sufficient basis for a numeric sample-size guarantee.
