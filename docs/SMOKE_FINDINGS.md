# Smoke findings before frozen full runs

The original `outputs/smoke/` used source captured in commit `dab3222`.
It produced real, parseable responses with complete usage and timing records.
S1: 0/3; S2: 3/3; S3: 2/3. These are pilot results, not the final benchmark.

The Q-03 S3 trace exposed a generic retrieval defect: `resident`, absent verbatim
from the corpus (which uses `residents`), was fuzzy-matched to Redfen. Both initial
lookup requests returned UNKNOWN_ENTITY. The model retried and eventually answered
correctly. Before full runs, entity detection was fixed to recognize the same
normalized indicator vocabulary as BM25. Regression tests cover singular forms
and aliases. No question ID, answer or numeric fact was used in this fix.

A local inspection command also exposed Windows cp1251 console limitations for
model text containing `²`. CLI stdout now emits ASCII-safe JSON; saved files remain
UTF-8. The scoring protocol, prompts, schemas, calculator and inference settings
were not changed. The original pilot logs remain intact. A second three-question
smoke run uses the frozen implementation before the two full experiments.

Q-09's original S3 trace retrieved NR-16 and evaluated
`44675/921.4-37203/758.6 = -0.5556561156405735`, but named Brightwater in its final
answer. This is an observed interpretation/name error after successful retrieval
and arithmetic; it is not fixed by hardcoding a question-specific answer.
