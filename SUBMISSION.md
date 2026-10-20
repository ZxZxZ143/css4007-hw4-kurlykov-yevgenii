# HW4 — submission

**AI assistance:** <!-- what you used, and for what. "None" is an answer too. -->

---

## Part A — Plan on paper (Easy)

> Commit this whole part before any `.py` file exists.

### A1 — The steps

| # | Step                                                         | What goes in (types)                                                                                                                                                                                                  | What comes out (types)                                                                                                                                                                                                                                                                           | When it goes wrong                                                                                                                                                                                                                                                                                      | Tool, loop, or model?                                            |
|---|--------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------|
| 1 | **Receive the question and prepare the conversation**        | `question: str` — the user’s question; `system_prompt: str` — system instructions; `tool_definitions: list[dict]` — definitions of the available tools; `max_rounds: int` — the maximum number of calls to the model. | `messages: list[dict]` — the initial conversation containing the system message and the user’s question; initial loop state `dict`, including the round counter.                                                                                                                                 | If the question is empty, the input types are incorrect, or the round limit is invalid, the loop returns a clear error. No request is sent to the model.                                                                                                                                                | **Loop**                                                         |
| 2 | **Choose the next action**                                   | `messages: list[dict]` — the complete conversation history so far; `tool_definitions: list[dict]` — definitions of the available tools.                                                                               | `assistant_message: dict` — the model’s message containing tool requests in `tool_calls: list[dict]`, or a final answer in `content: str`. Tool requests lead to Step 3; a final answer leads to Step 6.                                                                                         | If the API call fails or the model returns an empty or invalid message, the loop records the error. The run is not considered successfully completed.                                                                                                                                                   | **Model**; the **loop** sends the request and handles API errors |
| 3 | **Validate the tool requests**                               | `tool_calls: list[dict]`. Each call contains an identifier `id: str`, a tool name `name: str`, and arguments `arguments: str` encoded as a JSON string.                                                               | Validated calls in `validated_calls: list[dict]`, with parsed arguments `arguments: dict`; invalid calls produce error results in `tool_errors: list[dict]`, linked to their original call identifiers.                                                                                          | An unknown tool name, malformed JSON, a missing required parameter, or an incorrect argument type produces an error for the corresponding call. Invalid calls are not executed.                                                                                                                         | **Loop**                                                         |
| 4 | **Execute the requested tool**                               | `name: str` — the tool name; `arguments: dict` — validated search parameters or an arithmetic expression.                                                                                                             | `result: dict`. For `lookup`, a limited set of facts or text fragments with source document IDs; numerical facts retain information about their units and year. For `calculate`, a numerical result of type `int` or `float`. If execution is not possible, the tool returns a structured error. | `lookup` returns an error if the requested information is missing, the query is ambiguous, or a value cannot be interpreted correctly. `calculate` returns an error for an invalid or prohibited expression, division by zero, or an exceeded computational limit. Tool errors must not crash the loop. | **Tool: `lookup` or `calculate`**                                |
| 5 | **Update the conversation and continue the loop**            | The original model message `assistant_message: dict`; tool results and errors in `tool_results: list[dict]`; the current loop state `dict`.                                                                           | Updated conversation history `messages: list[dict]`: the model’s message containing `tool_calls` is preserved unchanged, followed by a result for every `tool_call_id`. Arguments, results, and execution times are recorded in the log. If rounds remain, execution returns to Step 2.          | Tool errors are returned to the model with the corresponding call identifiers. The next model request is sent only after results have been added for every call. If the round limit is reached without a final answer, execution ends with status `unanswered`.                                         | **Loop**                                                         |
| 6 | **Validate the final answer’s format and return the result** | `answer_text: str` — the model’s final answer; accumulated execution information `dict`.                                                                                                                              | An execution result `dict` containing the answer `answer: str`, completion status `status: str`, and collected metrics `metrics: dict`. The answer is saved and returned to the user or the experiment runner.                                                                                   | If the required `ANSWER` line is missing or its fields cannot be parsed, a format error is recorded and the original response is saved. Factual correctness is checked separately against the reference answer after the solving process has finished.                                                  | **Loop**                                                         |

**How the steps connect:**

> The loop acts as the orchestrator, passing information between the model and the tools. Step 1 prepares the conversation, which is sent to the model in Step 2. If the model requests tools, the requests are validated in Step 3, and valid requests are executed in Step 4. Both successful results and error results are added to the conversation in Step 5, with one result for every tool call ID. If rounds remain, the updated conversation returns to Step 2, where the model chooses its next action. If the round limit is reached without a final answer, the run ends as unanswered. When the model produces a final answer, execution proceeds from Step 2 to Step 6, where the loop checks its format, saves it, and returns the result.

![mermaid-diagram.png](./assets/mermaid-diagram.png)

**What I am assuming:**

>1. Source of facts.
I use data/corpus.jsonl as the source of factual information about the districts. The current profiles, together with their correction notices, determine which values the system should use. Reference answers from questions.json are used only for evaluation after an answer has been produced.
>2. Years and reporting periods.
I use the year or period specified in the question. Unless stated otherwise, population figures refer to the 2025 census, budgets refer to the 2025 fiscal year, and household water use refers to the 2025 calendar year. Questions about population change require both the 2020 and 2025 census figures. School enrolment figures refer to the 2025/26 school year.
>3. Archived profiles.
Profiles marked ARCHIVED have been superseded and must not replace the current profiles when answering questions about current data. When a question requires the 2020 census population, I use the 2020 figure recorded in the current profile rather than an estimate from an archived profile.
>4. Corrections take precedence.
An explicit correction notice overrides the corresponding value in the original profile. Only the corrected field is replaced; the other figures remain unchanged. For example, Brightwater’s area must be taken as 921.4 km², as stated in NR-16, rather than the incorrect 912.4 km² in NR-05. The corrected fact should retain a reference to the correction notice.
>5. Units remain attached to values.
Retrieved numerical facts retain their units and relevant reporting period. I use compatible units in each formula and perform numerical conversions through calculate. In particular, 1 million tenge = 1,000,000 tenge, 1 megalitre = 1,000 cubic metres, and 1 cubic metre = 1,000 litres.
>6. Daily water consumption.
For questions about average household water use per resident per day in 2025, I divide annual household water use by the 2025 census population and 365 days. This uses the census population as the population denominator for the annual average.
>7. Rounding.
I do not deliberately round intermediate results. Derived quantities and differences are calculated using the available numerical precision. Only the final reported number is rounded to the number of decimal places specified for the question in its decimals field.
>8. Missing or ambiguous information.
If a required fact is missing, a district name is ambiguous, or a unit cannot be interpreted, the tool returns a clear error rather than guessing a value. The model may use that error to revise its request, within the loop’s round limit.

### A2 — The two tools

#### `lookup`

```json
{
  "type": "function",
  "function": {
    "name": "lookup",
    "description": "Search data/corpus.jsonl using BM25 over short original excerpts, without using reference answers. Query by district, indicator and period; regional and multi-district queries are allowed. Exclude archived profiles but retain historical figures in current sources. Return excerpts preserving values, periods and units, with doc_id, title, chunk_id, text, kind (profile/reference/correction) and correction_of (document ID or null). Include and deduplicate related correction excerpts; corrections override only the facts they explicitly change. Limits: top_k primary matches, 10 excerpts overall, 2 complete sentences and 500 text characters per excerpt, and 3000 text characters overall. Return an error if necessary correction context cannot fit. Return selected passages, not whole documents. The model interprets the evidence and requests more if needed; the tool does not calculate or answer the question.",
    "strict": false,
    "parameters": {
      "type": "object",
      "properties": {
        "query": {
          "type": "string",
          "minLength": 1,
          "maxLength": 300,
          "pattern": "\\S",
          "description": "Non-blank search text. Prefer English corpus terminology, e.g. Brightwater population 2025 area."
        },
        "top_k": {
          "type": "integer",
          "minimum": 1,
          "maximum": 5,
          "default": 3,
          "description": "Maximum primary matches. The tool defaults to 3. Additional corrections share the overall limits but do not count toward top_k."
        }
      },
      "required": ["query"],
      "additionalProperties": false
    }
  }
}
```

| Case                                     | What the tool returns                                                                                                                                                                            |
|------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| success                                  | `ok: true`, `matches: array` of primary excerpts, `corrections: array` of additional correction excerpts, and `has_more: boolean`, indicating whether eligible candidates remain unreturned.     |
| no eligible matches                      | `{"ok":true,"matches":[],"corrections":[],"has_more":false}`. Archived sources are excluded; missing facts are not invented.                                                                     |
| invalid arguments                        | `{"ok":false,"error":{"code":"INVALID_ARGUMENTS","message":"..."}}`. The message identifies missing, blank, incorrectly typed, excessive or unexpected arguments. All errors use this structure. |
| detected district-name typo or ambiguity | `UNKNOWN_ENTITY` or `AMBIGUOUS_ENTITY`, with up to three names in `error.suggestions`. Exact names are never silently replaced.                                                                  |
| required context exceeds limits          | `CONTEXT_LIMIT_EXCEEDED`, asking for a narrower query or smaller `top_k`. Required corrections are never silently dropped.                                                                       |
| unavailable or invalid corpus/index      | `CORPUS_ERROR`, explaining the problem without fabricating results.                                                                                                                              |
| unexpected failure                       | `INTERNAL_ERROR`, with a short message and no internal paths or stack trace.                                                                                                                     |

**Worst thing it could do with strange or dangerous input:**

> Return evidence for the wrong district or period, or omit a correction, causing an incorrect answer. Input/output limits bound processing and context use. Queries are plain text against a fixed, read-only corpus; they cannot execute commands or open arbitrary files. Retrieved text is treated as data, not instructions.

#### `calculate`

```json
{
  "type": "function",
  "function": {
    "name": "calculate",
    "description": "Evaluate arithmetic or convert one numeric quantity. evaluate requires only mode and expression; convert requires mode, value, from_unit and to_unit, with optional scale. Reject fields belonging to the other mode. Arithmetic permits real numeric literals (including scientific notation), parentheses, unary +/- and +, -, *, /. Reject all other syntax. Use AST parsing and whitelisted evaluation, never eval or exec. Limits: 512 expression characters, 128 AST nodes, depth 16 (root depth 1), and finite inputs/intermediate results/results with absolute value <= 1e15. Check length before parsing. Conversion applies input scale first, then compatible unit conversion: 1 km=1000 m; 1 km2=1000000 m2; 1 ML=1000 m3; 1 m3=1000 L. Reverse conversions are supported. one is dimensionless; one, KZT, person, pupil and school each convert only to the same label. No compound units, currency exchange or calendar conversion. Normalise quantities separately before calculating ratios. Return finite floating-point results without extra intermediate rounding; evaluate does not check units or the meaning of a formula.",
    "strict": false,
    "parameters": {
      "type": "object",
      "properties": {
        "mode": {
          "type": "string",
          "enum": ["evaluate", "convert"]
        },
        "expression": {
          "type": "string",
          "minLength": 1,
          "maxLength": 512,
          "description": "Required only for evaluate. Non-blank expression; use decimal points and no thousands separators."
        },
        "value": {
          "type": "number",
          "minimum": -1e15,
          "maximum": 1e15,
          "description": "Required only for convert. Numeric quantity before scaling; booleans are invalid."
        },
        "scale": {
          "type": "string",
          "enum": ["one", "thousand", "million"],
          "default": "one",
          "description": "Optional only for convert. Input multiplier: 1, 1000 or 1000000. The tool defaults to one; output uses ordinary target units."
        },
        "from_unit": {
          "type": "string",
          "enum": ["one", "KZT", "person", "pupil", "school", "m", "km", "m2", "km2", "L", "m3", "ML"],
          "description": "Required only for convert. Case-sensitive source unit."
        },
        "to_unit": {
          "type": "string",
          "enum": ["one", "KZT", "person", "pupil", "school", "m", "km", "m2", "km2", "L", "m3", "ML"],
          "description": "Required only for convert. Compatible, case-sensitive target unit."
        }
      },
      "required": ["mode"],
      "additionalProperties": false
    }
  }
}
```

| Case                                       | What the tool returns                                                                                                                                                                                                             |
|--------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| success: arithmetic                        | `{"ok":true,"mode":"evaluate","value":50,"unit":null}` for `(100 + 50) / 3`. `unit: null` means units were not checked.                                                                                                           |
| success: scaling                           | `{"ok":true,"mode":"convert","value":1000000,"unit":"KZT"}` for `value: 1`, `scale: "million"`, and both units `"KZT"`.                                                                                                           |
| success: unit conversion                   | `{"ok":true,"mode":"convert","value":2500,"unit":"m3"}` for `2.5 ML` converted to `m3`.                                                                                                                                           |
| invalid arguments                          | `{"ok":false,"error":{"code":"INVALID_ARGUMENTS","message":"..."}}`. Covers missing mode-specific fields, wrong types, blank expressions, invalid mode/scale, and unexpected or wrong-mode fields. All errors use this structure. |
| malformed expression                       | `INVALID_EXPRESSION`, identifying a syntax problem such as unmatched parentheses.                                                                                                                                                 |
| forbidden expression                       | `UNSUPPORTED_EXPRESSION`. Rejects names, calls, attributes, containers, booleans, complex numbers and unsupported operators, including `__import__('os').system('echo hi')`, `(1).__class__` and `9**9**9`.                       |
| division by zero                           | `DIVISION_BY_ZERO`; no numeric result is returned.                                                                                                                                                                                |
| size, complexity or numeric limit exceeded | `LIMIT_EXCEEDED`, identifying the exceeded limit. Includes non-finite values and excessive values after scaling or conversion.                                                                                                    |
| unknown or compound unit                   | `UNSUPPORTED_UNIT`, identifying the unsupported label.                                                                                                                                                                            |
| incompatible units                         | `INCOMPATIBLE_UNITS`, e.g. `m3` to `KZT` or `school` to `person`.                                                                                                                                                                 |
| unexpected failure                         | `INTERNAL_ERROR`, with a short message and no stack trace.                                                                                                                                                                        |

**Worst thing it could do with strange or dangerous input:**

> An implementation bug could allow code execution or resource exhaustion. AST whitelisting, the prohibition of eval/exec, and input, complexity and numeric limits address these risks. Valid but incorrectly specified formulas or units can still produce misleading results, and floating-point precision can affect the last digits. Final rounding follows the question’s requirements.

### A3 — Q-09 by hand

```json
[
  {
    "role": "user",
    "content": "Which district has the higher population density in 2025, Brightwater or Millbrook, and by how many residents per square kilometre?"
  },
  {
    "role": "assistant",
    "content": null,
    "tool_calls": [
      {
        "id": "call_lookup_brightwater",
        "type": "function",
        "function": {
          "name": "lookup",
          "arguments": "{\"query\":\"Brightwater population 2025 area\",\"top_k\":1}"
        }
      },
      {
        "id": "call_lookup_millbrook",
        "type": "function",
        "function": {
          "name": "lookup",
          "arguments": "{\"query\":\"Millbrook population 2025 area\",\"top_k\":1}"
        }
      }
    ]
  },
  {
    "role": "tool",
    "tool_call_id": "call_lookup_brightwater",
    "content": "{\"ok\":true,\"matches\":[{\"doc_id\":\"NR-05\",\"title\":\"Brightwater district profile (2025)\",\"chunk_id\":\"NR-05:s2-3\",\"text\":\"The district, founded in 1889, stretches along the Bright over 912.4 square kilometres and keeps 455.0 km of paved road. Census population: 39,902 in 2020 and 44,675 in 2025.\",\"kind\":\"profile\",\"correction_of\":null}],\"corrections\":[{\"doc_id\":\"NR-16\",\"title\":\"Correction notice - Brightwater\",\"chunk_id\":\"NR-16:s3-4\",\"text\":\"The correct area is 921.4 square kilometres. All other figures in that profile are correct.\",\"kind\":\"correction\",\"correction_of\":\"NR-05\"}],\"has_more\":true}"
  },
  {
    "role": "tool",
    "tool_call_id": "call_lookup_millbrook",
    "content": "{\"ok\":true,\"matches\":[{\"doc_id\":\"NR-11\",\"title\":\"Millbrook district profile (2025)\",\"chunk_id\":\"NR-11:s2-3\",\"text\":\"The district, founded in 1897, stretches along the Mill Brook over 758.6 square kilometres and keeps 360.1 km of paved road. Census population: 34,590 in 2020 and 37,203 in 2025.\",\"kind\":\"profile\",\"correction_of\":null}],\"corrections\":[],\"has_more\":true}"
  },
  {
    "role": "assistant",
    "content": null,
    "tool_calls": [
      {
        "id": "call_calculate_difference",
        "type": "function",
        "function": {
          "name": "calculate",
          "arguments": "{\"mode\":\"evaluate\",\"expression\":\"37203 / 758.6 - 44675 / 921.4\"}"
        }
      }
    ]
  },
  {
    "role": "tool",
    "tool_call_id": "call_calculate_difference",
    "content": "{\"ok\":true,\"mode\":\"evaluate\",\"value\":0.5556561156405735,\"unit\":null}"
  },
  {
    "role": "assistant",
    "content": "ANSWER: Millbrook | 0.6"
  }
]
```

**My arithmetic:**
Population density is population divided by area. NR-16 corrects Brightwater’s area from **912.4 to 921.4 km²**; its population remains unchanged. Millbrook’s figures come from NR-11.

$$
\rho_{\text{Brightwater}}
=\frac{44675}{921.4}
\approx 48.4859995659\text{ residents/km}^2
$$

$$
\rho_{\text{Millbrook}}
=\frac{37203}{758.6}
\approx 49.0416556815\text{ residents/km}^2
$$

Using the original fractions, without rounding intermediate values:

$$
\Delta
=\frac{37203}{758.6}-\frac{44675}{921.4}
=\frac{9709730}{17474351}
\approx 0.5556561156\text{ residents/km}^2
$$

The difference is positive, so **Millbrook** has the higher density. Rounded to one decimal place, the difference is **0.6 residents/km²**.
### A4 — Why I split it this way

> An alternative would be one solve_question tool that retrieves documents, selects facts, performs calculations and returns the final answer. This would simplify the loop’s external interface. I chose separate lookup and calculate tools so that retrieval and arithmetic can be tested independently, their outputs inspected, and failures traced to a specific step. The model interprets the question and evidence and chooses the formula; lookup provides source excerpts; calculate performs bounded numerical operations; and the loop validates calls and passes results between components.
---

## Part B — Build it and run it (Medium)

### What I changed from Part A while coding

>The original architecture was preserved: the model selects the required information and formulas, lookup retrieves evidence, calculate performs numerical operations, and the loop manages tool execution and conversation history.
>
>Four implementation refinements were introduced:
>
>Rounding: The model returns a sufficiently precise number, while the evaluator applies the question-specific decimals after inference. This prevents reference-answer information from leaking into model prompts.
>
>Correction handling: The lookup tool returns all necessary correction excerpts. For Q-09, both parts of NR-16 are included instead of the single excerpt shown in the manual scenario.
>
>Context preservation: Source sentences are not silently truncated when necessary information would be lost. The tool returns CONTEXT_LIMIT_EXCEEDED if required evidence cannot fit within the limits.
>
>Additional safety checks: Tool arguments are limited to 8,192 JSON characters and 32 tool executions per model response. Missing or duplicate tool-call IDs are treated as protocol errors.
>
>These adjustments improve reliability and safety without changing the original separation of responsibilities.
### B2 — Tests

```text
(.venv) PS C:\Users\kyrlu\PycharmProjects\css4007-hw4-kurlykov-yevgenii> python -m pytest -q
..................................................................................................................................................                           [100%]
146 passed in 5.74s
```

### B3 — The loop

- Round limit, and why: The limit is 8 model calls per question, including the final response. A typical question requires three rounds: retrieval, calculation, and final answer. Additional rounds allow the model to refine searches, perform conversions, or recover from tool errors. If the limit is reached without a valid answer, the question is marked unanswered.
- Where the logs are: Individual question traces are stored in outputs/run_1/traces/<strategy>/<question_id>.json and outputs/run_2/traces/<strategy>/<question_id>.json, with corresponding .events.jsonl journals. The separate real Q-09 execution is stored in outputs/q09/traces/S3/Q-09.json. Logs include model requests, token usage, tool calls, arguments, results, execution times, and completion status.
- Real Q-09 conversation compared with my A3 version, what is different: The manual scenario predicted 3 model responses, 2 lookup calls, and 1 calculation. The real execution used 4 model responses, 2 lookup calls, and 3 calculations.

In the first round, the model requested Brightwater and Millbrook data through two lookup calls. It omitted top_k, so the default value of 3 was applied. The search returned NR-05, NR-11, and both correction excerpts from NR-16.

Instead of calculating the difference directly, the model first calculated both densities separately:

44675 / 921.4 = 48.48599956587801
37203 / 758.6 = 49.041655681518584

Then it calculated the difference:

49.041655681518584 - 48.48599956587801
= 0.5556561156405735

The final response was:

ANSWER: Millbrook | 0.5556561156405735

The evaluator rounded the result to 0.6, matching the manual answer. The corrected area of 921.4 km² was explicitly used in the calculation.

### B4 — Three strategies

**What I kept the same:**

>Both full runs used the same 17 documents, 20 questions, model, source assumptions, answer format, and evaluation protocol.
>
>Common settings:
>
> - Model: gpt-5.6-luna
>
>- API: OpenAI Chat Completions
>
> - Temperature: 0.7
>
> - Reasoning effort: none
>
> - Maximum completion tokens: 4096
>
> - Timeout: 90 seconds
>
> - SDK retries: 0
>
> - Answer format: ANSWER: <name or yes/no> | <number>
>
>All questions were processed sequentially from Q-01 to Q-20, with strategies executed in the order S1, S2, S3.
>
>Only the strategy-specific behavior differed:
>
>S1: One direct model call with the complete corpus and question.
>
>S2: Five independent model calls (k = 5) with the complete corpus and step-by-step instructions. The most frequent complete answer was selected, with ties resolved by the earliest valid sample.
>
>S3: Tool-based reasoning using lookup and calculate, without including the corpus in the initial prompt. The maximum was 8 model calls per question.

**My rule for a correct answer** (written before the first full run):

> The evaluation protocol was fixed in docs/evaluation_protocol.md before the full experiments.
>
> A valid response must end with exactly one line in the format:
>
>ANSWER: <name or yes/no> | <number>
>
>The name must match the reference exactly after removing surrounding whitespace. Both predicted and reference numbers are rounded using Decimal ROUND_HALF_UP to the number of decimal places specified in the reference question.
>
>A numerical difference of at most one unit in the last decimal place is accepted. Both the name and numerical value must match for the answer to be correct.
>
>A valid but incorrect answer is marked wrong. Missing, malformed, truncated, or unsuccessful answers are marked unanswered.
>
>Reference answers and their decimals are used only after inference and are never included in model prompts.

| Run | Strategy                  | Correct /20 | Unanswered | Input tokens | Output tokens | Median seconds per question | Total seconds | Cost ($)   |
| --- | ------------------------- | ----------- | ---------- | ------------ | ------------- | --------------------------- | ------------- | ---------- |
| 1   | S1 direct                 | 4/20        | 1          | 46320        | 315           | 1.350                       | 28.164        | 0.00143364 |
| 1   | S2 think and vote (k = 5) | 16/20       | 0          | 232700       | 14035         | 10.012                      | 202.769       | 0.02166844 |
| 1   | S3 tools                  | 19/20       | 0          | 163063       | 4239          | 4.731                       | 111.277       | 0.01296092 |
| 2   | S1 direct                 | 2/20        | 4          | 46320        | 312           | 1.350                       | 28.101        | 0.00131160 |
| 2   | S2 think and vote (k = 5) | 15/20       | 0          | 232700       | 14364         | 10.311                      | 209.366       | 0.02194480 |
| 2   | S3 tools                  | 18/20       | 0          | 166123       | 4156          | 4.801                       | 111.220       | 0.01101110 |

Token counts include the usage of every API request: all five samples in S2 and all model rounds in S3.

Median latency includes all processing required to answer each question. Total seconds represent the sum of per-question execution times, rather than overall runner wall-clock time.

Costs were calculated using the recorded token usage and model pricing, accounting for cached input tokens where applicable.

**Per question (run 1):**

| Question | S1 | S2 | S3 |
|----------|----|----|----|
| Q-01     | ✗  | ✓  | ✓  |
| Q-02     | ✗  | ✓  | ✓  |
| Q-03     | ✗  | ✓  | ✓  |
| Q-04     | ✗  | ✓  | ✓  |
| Q-05     | ✗  | ✗  | ✓  |
| Q-06     | ✓  | ✓  | ✓  |
| Q-07     | ✗  | ✓  | ✓  |
| Q-08     | ✗  | ✓  | ✓  |
| Q-09     | ✗  | ✓  | ✓  |
| Q-10     | ✓  | ✓  | ✓  |
| Q-11     | ✗  | ✓  | ✗  |
| Q-12     | ✗  | ✗  | ✓  |
| Q-13     | ✓  | ✓  | ✓  |
| Q-14     | ✗  | ✓  | ✓  |
| Q-15     | ✗  | ✓  | ✓  |
| Q-16     | ✓  | ✓  | ✓  |
| Q-17     | ✗  | ✓  | ✓  |
| Q-18     | ✗  | ✗  | ✓  |
| Q-19     | ✗  | ✓  | ✓  |
| Q-20     | ✗  | ✗  | ✓  |

---

## Part C — Explain and choose (Hard)

### C1 — Does the tool description matter?

>I selected Q-01, Q-03, Q-08, Q-09, and Q-18 and reran S3 with the lookup description replaced by "Looks things up.". The tool implementation, parameters, model, temperature, and other settings remained unchanged. The original S3 results from Run 1 were used as the baseline.

| Question | Calls (your description) | Calls (vague) | Answer (yours) | Answer (vague) |
|---|---:|---:|---|---|
| | | | | |

> Accuracy decreased from 5/5 to 4/5, while total tool calls increased from 24 to 25. The vague-description version made additional searches in Q-03, Q-08, and Q-18.
>
>The most interesting difference was Q-09. The original version correctly identified Millbrook, while the vague version used the opposite subtraction order and incorrectly selected Brightwater, despite retrieving the corrected area.
>
>This suggests that tool descriptions may influence how efficiently and correctly the model uses tools. However, because temperature was 0.7 and no fixed seed was used, the observed differences may also reflect sampling variability. Therefore, one five-question experiment cannot establish a causal effect.

### C2 — Three mistakes explained

1. S1 — Q-01: Incorrect district and density difference

    Trace: outputs/run_1/traces/S1/Q-01.json

    The direct strategy returned:

    ANSWER: Ossford | 0.7911737459

    The correct answer was Ossbridge | 4.6.

    Both the district and numerical value were incorrect. Since S1 used a single model call without tool traces or intermediate calculations, the saved output does not show exactly where the error occurred.

    This illustrates a limitation of direct answering: even with all documents available, the model may produce incorrect results without an independently verifiable calculation. The precise cause cannot be established from this trace alone.

2. S2 — Q-05: Incorrect arithmetic despite repeated reasoning

    Trace: outputs/run_1/traces/S2/Q-05.json

    The selected answer was:

    ANSWER: Coldharbour | 14221.1082172118

    The model selected the correct district and identified the relevant budget and population values, but calculated the difference incorrectly.

    The correct calculation is:

    2366900000 / 11407 - 2884600000 / 14926
= 14235.314486389194

    The five samples produced different numerical results. Four were parseable, but none had the same complete voting key. The fifth contained an invalid numeric suffix. Therefore, the predefined tie-breaking rule selected the earliest valid answer.

    Self-consistency can reduce random errors when independently generated solutions agree on the correct answer. However, voting cannot guarantee correctness when every calculation differs or several samples share the same mistake. It also increases token usage because the complete prompt is processed five times.

3. S3 — Q-11: Correct calculation of the wrong expression

    Trace: outputs/run_1/traces/S3/Q-11.json

    The model retrieved the relevant information from NR-09, NR-10, and NR-11, then called calculate with:

    {
  "mode": "evaluate",
  "expression": "8837/24-3147/10"
}

    The calculator correctly returned:

    53.508333333333326

    However, the question required the difference between the highest and lowest pupils-per-school ratios among three districts.

    The highest ratio belonged to Millbrook:

    5562 / 15 = 370.8

    The lowest belonged to Redfen:

    3147 / 10 = 314.7

    Therefore, the correct difference was:

    370.8 - 314.7 = 56.1

    The model correctly identified Redfen as the lowest but mistakenly used Ashgrove instead of Millbrook for the highest value.

    This demonstrates that tools improve arithmetic reliability but do not eliminate reasoning errors. The calculator guarantees the result of the supplied expression, not that the model selected the correct expression.

### C3 — Which strategy I would use, and what would change it
>For this problem, I would choose S3 — Tools, because it provided the best balance of accuracy, cost, and execution time.
>
>In Run 1, S3 answered 19/20 questions correctly, compared with 16/20 for S2 and 4/20 for S1. Run 2 showed a similar ranking: S3 achieved 18/20, S2 achieved 15/20, and S1 achieved 2/20.
>
>S3 was also approximately 40% cheaper than S2 in Run 1 and 50% cheaper in Run 2, with roughly half the median execution time.
>
>The main advantage is the separation of responsibilities. The model retrieves evidence through lookup and delegates arithmetic to calculate, reducing numerical errors and making the process easier to inspect.
>
>I would not choose S1 because its low accuracy makes it unsuitable for these multi-step numerical questions, despite its lower cost and latency. I would not choose S2 because generating five answers increases costs and execution time, while voting does not reliably correct arithmetic mistakes.
>
>My choice could change under different conditions:
>
> - Strict latency requirements or a very small budget: S1 may be preferable for simple questions when lower accuracy is acceptable and only one model request is allowed.
>
> - Questions without arithmetic: Direct answering may provide sufficient accuracy without tool overhead.
>
> - A much larger document collection: I would prefer S3 with a scalable retrieval index, because repeatedly sending all documents to S1 or S2 would become expensive and potentially exceed context limits.
>
>These choices depend on the task requirements and should be validated with new experiments.

### C4 — How sure I can be

>The two runs produced slightly different results:
>
>S1: 4/20 → 2/20
>
>S2: 16/20 → 15/20
>
>S3: 19/20 → 18/20
>
>S3 outperformed S2 by 3 questions (15 percentage points) in both runs. This difference was larger than the one-question variation observed within either S2 or S3 between runs.
>
>However, the benchmark contains only 20 questions from one fictional dataset. A single question changes accuracy by five percentage points, and two runs are insufficient to establish a statistically reliable ranking.
>
>I would start with at least 200 independently constructed questions covering different reasoning types and conduct several repeated runs. I would then estimate paired accuracy differences and confidence intervals and determine whether more questions are necessary.
>
>The 200-question target is a practical starting point, not a statistically proven minimum. The current results support S3 for this benchmark, but not a universal claim that tool-based reasoning is always better.

### Final questions

1. When the model sends a tool_calls message, what has actually run so far?

    Only the model's API request has completed, producing a description of the requested tool calls. No Python tool function has executed yet. The loop must validate the arguments, execute the corresponding tools, and return their results to the model.

2. Why does arguments arrive as a string, and what goes wrong if you pass it straight into your function?

    Function-call arguments are transmitted as a JSON string according to the API protocol. The loop must parse the string into a dictionary and validate its types, required fields, and structure before execution. Passing it directly to the tool would violate the expected function interface and bypass validation.

3. How many tokens do your two tool definitions add to every S3 request? Measure it.

    Using tiktoken with the o200k_base encoding, the serialized tool definitions contain 834 tokens: 303 for lookup and 531 for calculate. The measurement is saved in outputs/offline/tool_overhead.json. This is a tokenizer-based estimate of the schema text, not an exact API-measured difference, because server-side tool formatting may add overhead.

4. How much more did S2 cost than S1? Give the number from your table and explain it.

    In Run 1, S2 cost $0.02166844 versus $0.00143364 for S1, making it approximately 15.11 times more expensive. In Run 2, S2 was approximately 16.73 times more expensive. S2 makes five requests per question and generates longer reasoning responses, while prompt caching also affects the final cost.

5. Which question needed the most rounds in S3, and why?

    Q-14 required the most rounds, with 7 model calls in both runs. In Run 1, the model made six lookup calls to collect household water consumption and population data for Tarnvale and Ashgrove, followed by three calculator calls. Input tokens increased from 1,186 in the first round to 3,869 in the seventh because previous messages and tool results accumulated in the conversation.

6. What would you change in lookup if there were 100,000 documents?

    I would replace the current small-corpus search approach with a persistent inverted BM25 index and efficient metadata filtering. I would also add incremental indexing, document version management, and explicit correction relationships. Retrieval accuracy and performance would need evaluation on a larger independent dataset.

7. What stops your calculate from running dangerous code? Could the model still make it misbehave?

    The calculator uses AST parsing with a strict whitelist of arithmetic operations, rejecting function calls, imports, variables, attribute access, and exponentiation. It also limits expression length, AST complexity, and numerical values. However, the model can still provide incorrect formulas or units, producing mathematically valid but semantically incorrect answers, as demonstrated by Q-11.

8. For which kind of question did tools help most, and for which did they not help at all?

    The largest observed improvement over S2 was in budget-related calculations (Q-05, Q-12, Q-20), where S3 answered 3/3 correctly, compared with 0/3 for S2 in Run 1. For water-related questions Q-03, Q-08, Q-14, and Q-17, both S2 and S3 achieved 4/4, so tools provided no additional accuracy in that comparison. Questions Q-06, Q-10, Q-13, and Q-16 were answered correctly by all three strategies, showing no accuracy advantage from tools in those cases.
