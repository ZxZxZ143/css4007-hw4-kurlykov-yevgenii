# Baseline and execution plan

Audit date: 2026-10-20 (Asia/Qyzylorda).

- Starting HEAD: `b9f4bcecfafbbdffc7c932dcf279830f73acbfa1` (`part a`).
- Earlier commit: `7ff0c4d` (assignment starter). No Python files in either commit.
- Initial worktree: only untracked `.idea/`; preserve it. Existing `.venv/` is ignored.
- `SUBMISSION.md` SHA-256: `8055e85b84febf580a50a965987228690aecb5df1507e369f970a2dd914b4ec8`.
- Read README, RUBRIC, complete SUBMISSION, all 17 corpus documents and 20 questions.
- No applicable AGENTS.md found in repository or ancestor directories.
- No OPENAI_API_KEY in process environment; no local `.env`.

## Mapping to Part A

A1 steps 1–6 map to prompts, a dependency-injected model client, dispatcher,
bounded agent loop and shared answer parser. Retrieval supplies evidence;
the model selects facts/formulas; the calculator evaluates or converts.
A2 schemas are copied exactly into a standalone resource, verified against
the committed design in tests. A3 expects two lookup calls, then one arithmetic
call and a final answer (three model responses). A4's separation is retained.

## Clarifications without changing Part A

- A1 asks for rounding using `decimals`, but evaluation fields may not enter
  inference. Prompts request unrounded final numbers; evaluation alone uses
  `decimals`. The answer format remains unchanged.
- A3 illustrates a particular ranking and one correction excerpt. Ranking is
  deterministic BM25, not scripted to reproduce this conversation. Complete
  correction context is returned, potentially in multiple bounded excerpts.
- A2's 512-character maximum takes precedence over the generic invalid-input
  category: exceeding computational limits returns `LIMIT_EXCEEDED`.
- Long source sentences cannot satisfy both complete-sentence and 500-character
  limits. Such evidence produces `CONTEXT_LIMIT_EXCEEDED`, never silent truncation.

## Sequential milestones

1. Commit this baseline before source code.
2. Implement and verify corpus-derived metadata, excerpt BM25 and lookup.
3. Implement bounded AST arithmetic and unit conversion; offline tests.
4. Implement client, tool loop and fake-client integration tests.
5. Implement S1/S2/S3, shared evaluation and commit the evaluation protocol.
6. Implement immutable experiment outputs, metrics regeneration, diagnostics,
   Q-09 analysis and description ablation; test offline.
7. Check credentials/model access, execute only possible real experiments;
   otherwise record blockers with no synthetic benchmark results.
8. Produce Russian implementation report, reproduce outputs, verify hashes,
   secret exclusion and commits.
