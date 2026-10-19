# Отчёт о реализации CSS4007 HW4

Дата: 20 октября 2026, Asia/Qyzylorda. Автор отчёта: Codex; реализация и проверка
выполнены с помощью AI. Студенту необходимо самостоятельно отразить использование
AI и написать Parts B/C. `SUBMISSION.md` не редактировался и не добавлялся в index.

## A. Обзор реализации

Создан модульный Python-проект с `src/` layout: детерминированный BM25-поиск,
инструменты `lookup` и `calculate`, адаптер официального OpenAI SDK, ограниченный
цикл вызовов инструментов, S1/S2/S3, единый парсер и scorer, запись исходных трасс,
воспроизведение метрик, C1 ablation и программные сводки для Part C.

Offline-проверка: **146 passed, 0 failed, 0 skipped**. Первоначальный аудит не
обнаружил ключ; во время работы появился локальный `.env`. Реальный preflight
успешно проверил `gpt-5.6-luna`, `temperature=0.7` и tool calling. Подмена модели
не применялась. Результаты полных экспериментов приведены ниже исключительно
по сохранённым данным; тестовые ответы fake client в них не используются.

Исходный HEAD: `b9f4bcecfafbbdffc7c932dcf279830f73acbfa1` (`part a`). До него
и в нём нет Python-файлов. Первый код появился позднее, в `57ad225`.
Исходный SHA-256 `SUBMISSION.md`:
`8055e85b84febf580a50a965987228690aecb5df1507e369f970a2dd914b4ec8`.

## B. Архитектура и соответствие Part A

```text
css4007-hw4-kurlykov-yevgenii/
├── data/                         исходные corpus.jsonl и questions.json
├── src/css4007_hw4/
│   ├── __init__.py, __main__.py, config.py, cli.py
│   ├── domain/                   models.py, errors.py
│   ├── retrieval/                loader.py, chunker.py, metadata.py, bm25.py, search.py
│   ├── tools/                    definitions.json, schemas.py, validation.py,
│   │                             lookup.py, calculate.py, units.py, registry.py
│   ├── llm/                      client.py, prompts.py
│   ├── orchestration/            dispatcher.py, agent_loop.py
│   ├── strategies/               direct.py, self_consistency.py, tool_based.py
│   ├── evaluation/               parser.py, scorer.py, voting.py, metrics.py, pricing.py
│   └── experiments/              storage.py, runner.py, ablation.py,
│                                 diagnostics.py, analysis.py
├── tests/                        conftest.py, fakes.py, test_lookup.py,
│                                 test_calculate.py, test_units.py, test_agent_loop.py,
│                                 test_evaluation.py, test_strategies.py,
│                                 test_client.py, test_experiments.py
├── outputs/                      preflight.json, offline/, smoke/, smoke_validated/,
│                                 q09/, run_1/, run_2/, ablation/, part_c.json
├── docs/                         BASELINE.md, evaluation_protocol.md,
│                                 SMOKE_FINDINGS.md, USAGE.md, IMPLEMENTATION_REPORT.md
├── pyproject.toml, requirements.txt, requirements-lock.txt
├── .gitignore, .env.example
└── README.md, RUBRIC.md, SUBMISSION.md, assets/    документы задания
```

В каждом Python-пакете также есть `__init__.py`.

| Модуль | Ответственность |
|---|---|
| `config.py` | Фиксирует допустимую модель, параметры генерации, k, timeout, лимит раундов. |
| `domain/models.py`, `errors.py` | Типы Document/Excerpt/Question и единая структура ошибок. Question содержит только id/text. |
| `retrieval/loader.py` | Читает и проверяет JSONL, уникальность ID, непустые строковые поля; формирует полный корпус для S1/S2. |
| `chunker.py` | Сохраняет предложения и десятичные числа, создаёт короткие перекрывающиеся passages. |
| `metadata.py` | Определяет архивы, текущие профили, справки, correction notices и их связи из самого корпуса. |
| `bm25.py`, `search.py` | BM25 k1=1.5/b=0.75, нормализация терминов, проверка имён, детерминированное ранжирование и полный correction context. |
| `tools/definitions.json`, `schemas.py` | Точные A2 JSON-схемы; C1 меняет только lookup.description в свежей копии. |
| `validation.py`, `calculate.py`, `units.py` | Проверка аргументов, безопасный AST, масштабирование и совместимые единицы. |
| `lookup.py`, `registry.py` | Безопасная оболочка поиска и закрытый реестр двух функций. |
| `llm/client.py` | Только транспорт Chat Completions, SDK и преобразование ответа; без поиска, scorer и experiment logic. |
| `llm/prompts.py` | Общие предпосылки и разные инструкции S1/S2/S3. |
| `dispatcher.py` | JSON-валидация, обнаружение duplicate keys, unknown tools и локализация исключений. |
| `agent_loop.py` | История, запросы, tool_call_id, лимиты, конечный статус и события логирования. |
| `strategies/*` | Один direct-запрос, пять независимых think-and-vote samples, либо tool loop. |
| `evaluation/*` | Парсинг, голосование, проверка после inference, токены, время и стоимость. |
| `experiments/storage.py`, `runner.py` | Атомарная запись JSON, журнал JSONL, manifest, контроль воспроизводимости, выполнение и regeneration. |
| `ablation.py`, `analysis.py`, `diagnostics.py` | C1, случаи ошибок/стоимости, различия запусков, Q-09, preflight и оценка overhead. |
| `cli.py` | Команды без ручного редактирования исходников. |

Поток данных: JSONL → Document → metadata/chunks/BM25 → lookup evidence → model;
model tool call → dispatcher → lookup/calculate → tool message → model. Runner
передаёт стратегиям только `Question(id,text)`; в model message попадает только
`text`. Reference answer/value/decimals/sources/unit используются после inference.
Тест с подставленными sentinel references проверяет отсутствие их в запросах.

Соответствие A1: подготовка messages; выбор действия моделью; валидация;
исполнение; сохранение assistant + tool replies; общий парсер финального ответа.
A4 сохранён: инструмент не отвечает на вопрос целиком, модель выбирает факты и
формулу, lookup ищет, calculate считает.

Уточнения относительно Part A:

1. A1 требует округлять по `decimals`, но передавать это поле модели запрещено.
   Модель возвращает достаточно точное число; scorer округляет после inference.
2. В A3 показана одна часть NR-16. Реальный lookup возвращает оба двухпредложных
   фрагмента notice, чтобы не потерять необходимый контекст. Контракт A2 сохранён.
3. Предложение длиннее 500 символов не обрезается молча: если оно требуется,
   возвращается `CONTEXT_LIMIT_EXCEEDED`.
4. Дополнительно ограничены JSON arguments (8192 символа), число исполнений
   инструментов в одном ответе (32), malformed/duplicate call IDs. Такие ответы
   обрабатываются безопасно; некорректная история не отправляется дальше в API.

## C. Реальные реализации инструментов

`lookup(query, top_k=3)` принимает query длиной 1–300 и целый top_k 1–5.
Архивность определяется заголовком либо начальным маркером ARCHIVED; упоминание
архивов в справке NR-00 не исключает саму справку. Исторические census 2020 внутри
текущих профилей сохраняются. Имена районов извлекаются из заголовков; fuzzy match
не заменяет их автоматически: UNKNOWN_ENTITY/AMBIGUOUS_ENTITY возвращают до трёх
suggestions. Точные Ossbridge/Ossford фильтруются отдельно.

BM25 применяется к тексту passages, с нормализацией индикаторов. При нескольких
явно названных районах сначала выбирается лучший passage каждого, насколько
позволяет top_k. Равные оценки упорядочены по doc_id/chunk_id. Исправления связаны
с текущими профилями по явному ID либо упомянутому имени из корпуса, без NR-16-
или Q-09-specific ветвлений. Они добавляются отдельно от primary top_k,
дедуплицируются и никогда не отбрасываются из-за общего лимита. Все четыре лимита
A2 проверяются; невозможность вместить correction context возвращает ошибку.

Пример реального offline-вызова:

```json
{"query":"Brightwater population 2025 area","top_k":1}
```

Он возвращает primary `NR-05:s2-3`, обе correction parts `NR-16:s1-2` и
`NR-16:s3-4`, `correction_of="NR-05"`, `has_more=true`. Точный JSON находится
в `outputs/offline/a3_tool_replay.json`. Для `Ossbrige population` возвращается
`{"ok":false,"error":{"code":"UNKNOWN_ENTITY",...,"suggestions":["Ossbridge"]}}`.
Пустой запрос даёт INVALID_ARGUMENTS; повреждённый корпус — CORPUS_ERROR.

`calculate` выполняет AST parsing с whitelist Expression/BinOp/UnaryOp/Constant
и только операциями `+ - * /`, unary `+/-`. Динамическое выполнение кода не
используется. Проверяются длина до parse, все AST nodes/depth, каждый литерал и
каждый промежуточный результат. Пределы: 512 символов, 128 узлов, глубина 16 с
корнем на уровне 1, конечные значения с модулем ≤1e15. Деление на ноль — отдельная
ошибка; boolean, names, imports, calls, attributes, containers, complex, power и
остальные операторы отвергаются.

```json
{"ok":true,"mode":"evaluate","value":52892.6199,"unit":null}
{"ok":true,"mode":"convert","value":1000000.0,"unit":"KZT"}
{"ok":true,"mode":"convert","value":2500.0,"unit":"m3"}
{"ok":false,"error":{"code":"DIVISION_BY_ZERO","message":"Cannot divide by zero."}}
```

Первый результат соответствует `48317 * 1.0947`, второй — 1 million KZT,
третий — 2.5 ML → m3. Convert сначала применяет one/thousand/million, затем
отношение множителей совместимых единиц. m/km, m2/km2, L/m3/ML поддерживаются в
обе стороны; KZT/person/pupil/school/one — только в тот же label. Compound units,
валютный обмен и календарные преобразования отсутствуют. В evaluate единицы и
правильность выбранной формулы не проверяются. Float сохраняет обычные ограничения
двоичной точности; специального промежуточного округления нет.

Первый live smoke обнаружил ложное распознавание `resident` как Redfen. До full
runs исправлена общая нормализация vocabulary и добавлены regression tests.
Старые логи сохранены, scoring protocol не менялся; подробности —
`docs/SMOKE_FINDINGS.md`.

## D. Тесты и фактический вывод

Команда в корне проекта:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Сохранённый вывод `outputs/offline/pytest.txt`:

```text
........................................................................ [ 49%]
........................................................................ [ 98%]
..                                                                       [100%]
146 passed in 5.03s
```

| Файл | Проверенные требования |
|---|---|
| `test_lookup.py` | 2025 и исторические факты, опечатки/неоднозначность, похожие имена, архивы, Q-09 evidence, correction linkage на расширенном корпусе, несколько районов, лимиты, повреждённый/отсутствующий корпус, детерминизм, vocabulary regression. |
| `test_calculate.py` | Требуемое произведение, все три опасных выражения, остальные запрещённые AST, zero division, length/node/depth границы, nonfinite/overflow, precision, mode-specific поля, отсутствие eval/exec вызовов. |
| `test_units.py` | Million/thousand, water-volume и обратные преобразования, length/area, case sensitivity, unknown/compound/incompatible units, bool/NaN/Inf и scale. |
| `test_agent_loop.py` | Один/несколько tool calls, multi-round, сохранение assistant, ровно один reply на корректный ID, bad JSON/duplicates/unknown tool, исключения, final/format/truncation, round limit, sink, точное равенство A2 schemas. |
| `test_evaluation.py` | Единый формат, scientific notation, неправильные строки/огромные exponent, ROUND_HALF_UP, tolerance, wrong vs unanswered, joint voting/tie, cached usage и unknown cost. |
| `test_strategies.py` | Один вызов S1, пять независимых S2, все samples/errors/votes, S3 без initial corpus, отсутствие ID в prompt. |
| `test_client.py` | Mapping официального SDK через mock, max_retries=0, secret не входит в request, model substitution запрещена, temperature omission. |
| `test_experiments.py` | Два полных fixture runs во временной директории, regeneration, ablation, reference leakage sentinel test, immutable outputs, missing traces, changed protocol/config rejection, preflight без ключа, CLI. |

Ранее найденные и исправленные технические ошибки: Git subprocess в Windows
декодировался локальной code page вместо UTF-8; это ошибочно блокировало проверку
commit протокола. Исправлено явным `encoding="utf-8"`. Установка с
`--no-build-isolation` выявила отсутствие setuptools в существующей среде;
обычный `pip install -e . --no-deps` установил build dependency и пакет успешно.
Окончательных падающих или skipped тестов нет. Fake fixtures не являются API
измерениями и не смешаны с `outputs/run_1`/`outputs/run_2`.

## E. Цикл агента

Лимит — 8 обращений к модели на вопрос, включая final response. Типовой сценарий
требует retrieval, calculation, final (3), иногда ещё поиск/конверсию/сравнение.
Восемь оставляет место для уточнений и recovery; это инженерное ограничение, не
гарантия ответа на любой вопрос. При исчерпании статус unanswered/round_limit;
все tool replies последнего раунда всё равно сохраняются.

Assistant message сохраняется как полученный адаптером словарь, без переписывания
tool_calls/arguments/content. Каждому допустимому уникальному tool_call_id
соответствует один JSON tool message, в том числе при ошибке. Missing/duplicate
IDs дают protocol_error; функция не придумывает IDs. Bad JSON, duplicate keys,
неизвестный tool, неверные поля и runtime exceptions возвращают структурированные
ошибки. До следующего model call обработаны все calls текущего ответа.

Каждый request содержит полный snapshot messages/tools, model settings, UTC time,
latency, usage, returned model, finish_reason, request_id, service_tier и error.
Tool events отдельно содержат ID, arguments, result и execution time. Per-question
JSON содержит исходные сообщения, final_text, статус, метрики и post-inference
score. JSONL journal сбрасывается после событий. SDK retries отключены; exception
body/credential values не логируются. Сбой API без usage означает неизвестную
стоимость, а не фиктивный ноль. Полный timeout допускает неопределённость remote
charge; interruption во время HTTP request также нельзя восстановить из воздуха.

## F. Q-09: A3 и фактическая отдельная S3-трасса

Источник: `outputs/q09/traces/S3/Q-09.json`, программная сводка
`outputs/q09/comparison.json`. Это отдельный реальный запуск, не ручной replay.

| Показатель | A3 вручную | Реальный запуск |
|---|---|---|
| Ответы модели | 3 | 4 |
| lookup calls | 2, в первом ответе | 2, в первом ответе |
| calculate calls | 1 | 3: две плотности, затем разность |
| Primary top_k | явно 1 | параметр опущен, применяется 3 |
| Источники | NR-05, NR-11, NR-16 | NR-05, NR-11, NR-16 |
| Correction | один excerpt NR-16 | оба excerpts NR-16 |
| Финал | Millbrook / 0.6 | Millbrook / 0.5556561156405735, scorer → 0.6 |

Точные запросы lookup:

```json
{"query":"Brightwater population area population density 2025"}
{"query":"Millbrook population area population density 2025"}
```

NR-05 вернул `44,675` и исходное ошибочное `912.4`; NR-16 содержит
`The correct area is 921.4 square kilometres.` с `correction_of="NR-05"`.
NR-11 вернул `37,203` и `758.6`. Следующие фактические calculate calls:

```text
round 2: 44675/921.4 → 48.48599956587801
round 2: 37203/758.6 → 49.041655681518584
round 3: 49.041655681518584-48.48599956587801 → 0.5556561156405735
round 4: ANSWER: Millbrook | 0.5556561156405735
```

Следовательно, correction не только retrieved: литерал 921.4 непосредственно
использован в calculate. Порядок инструментов: lookup, lookup, calculate,
calculate, calculate. Четыре запросa: 7798 input / 198 output tokens,
5.474120500002755 s, $0.00043280 по сохранённым usage и rates. Модель сама
выбрала раздельные вычисления; воспроизведение A3 принудительно не задавалось.

Отдельный `outputs/offline/a3_tool_replay.json` подтверждает исполнение тех же
ручных аргументов Python-инструментами; в нём **0 model invocations**. Его нельзя
использовать вместо live-трассы.

## G. Экспериментальные настройки

| Параметр | Значение |
|---|---|
| Model/API | `gpt-5.6-luna`, Chat Completions, official `openai==3.33.0` |
| Temperature | 0.7, фактически accepted в preflight |
| Reasoning effort | `none` у всех стратегий; S2 получает явную step-by-step инструкцию |
| Output limit | `max_completion_tokens=4096` |
| Service tier / timeout / retries | default / 90 s / 0 |
| S2 samples / S3 model calls limit | 5 / 8 |
| Порядок | Последовательно S1, S2, S3; Q-01…Q-20; samples также последовательно |
| Ответ | `ANSWER: <name or yes/no> | <number>` |
| Корпус/вопросы | Одни и те же исходные 17 документов и 20 вопросов |
| Цена за 1M tokens | input $0.20 / cached input $0.02 / output $1.20 |

Параметры — `config.py`; точный текст prompts — `llm/prompts.py`, также в raw
requests. S1/S2 получают весь corpus, включая предупреждения, архивы и correction;
S3 получает только question, system instructions и два инструмента. Эти различия
определяют сравниваемые стратегии. S2 делает ровно пять запросов, выбирая самый
частый **name + number** с нормализацией числа до шести знаков; ties — earliest
sample. Reference decimals при voting не используется.

Scoring protocol `docs/evaluation_protocol.md` впервые зафиксирован в `e75c41d`
до full runs. Exact name comparison после outer trim; prediction/reference
округляются Decimal ROUND_HALF_UP по reference decimals; допускается одна единица
последнего разряда включительно. Неверный, но parseable ответ — wrong; API/format/
round-limit/protocol/truncation — unanswered и incorrect.

Input/output суммируются по usage всех actual requests. Для S2 включены все
samples, для S3 — все раунды. Median считается по всем вопросам, total_seconds —
сумма question latency; runner_wall_seconds отдельно включает orchestration/
storage overhead. Стоимость учитывает prompt caching; это расчёт token charges,
не счёт с налогами/кредитами. Preflight/smoke/Q-09/ablation не включены в six-row
full-run table. Тарифы проверены 2026-10-20 по
[официальной странице модели](https://developers.openai.com/api/docs/models/gpt-5.6-luna).

Tokenizer diagnostic: `tiktoken==0.14.0`, `o200k_base`, model mapping найден.
Компактный JSON двух schemas — **834 tokens** (lookup 303, calculate 531);
полный текст корпуса с ID/title — 2076 tokens. Это оценка schema text, а не
API-measured delta: серверное formatting/framing может отличаться. Файл
`outputs/offline/tool_overhead.json` сохраняет encoding, serialization и сами schemas.

## H. Полные результаты

Числа ниже автоматически перенесены из `outputs/run_1/summary.json` и
`outputs/run_2/summary.json`. Время показано до трёх знаков; исходные JSON содержат
полную precision. `Total seconds` — сумма latencies вопросов, не время между
запуском shell-команды и её завершением. Accuracy использует заранее установленный
tolerance; «правильно» не означает побитовое совпадение чисел.

| Run | Strategy | Correct /20 | Unanswered | Input tokens | Output tokens | Median seconds per question | Total seconds | Cost ($) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | S1 | 4/20 | 1 | 46320 | 315 | 1.350 | 28.164 | 0.00143364 |
| 1 | S2 | 16/20 | 0 | 232700 | 14035 | 10.012 | 202.769 | 0.02166844 |
| 1 | S3 | 19/20 | 0 | 163063 | 4239 | 4.731 | 111.277 | 0.01296092 |
| 2 | S1 | 2/20 | 4 | 46320 | 312 | 1.350 | 28.101 | 0.00131160 |
| 2 | S2 | 15/20 | 0 | 232700 | 14364 | 10.311 | 209.366 | 0.02194480 |
| 2 | S3 | 18/20 | 0 | 166123 | 4156 | 4.801 | 111.220 | 0.01101110 |

Таблица правильности всех 20 вопросов Run 1. ✗ включает wrong и unanswered;
последние отдельно посчитаны в сводке выше.

| Question | S1 | S2 | S3 |
|---|:---:|:---:|:---:|
| Q-01 | ✗ | ✓ | ✓ |
| Q-02 | ✗ | ✓ | ✓ |
| Q-03 | ✗ | ✓ | ✓ |
| Q-04 | ✗ | ✓ | ✓ |
| Q-05 | ✗ | ✗ | ✓ |
| Q-06 | ✓ | ✓ | ✓ |
| Q-07 | ✗ | ✓ | ✓ |
| Q-08 | ✗ | ✓ | ✓ |
| Q-09 | ✗ | ✓ | ✓ |
| Q-10 | ✓ | ✓ | ✓ |
| Q-11 | ✗ | ✓ | ✗ |
| Q-12 | ✗ | ✗ | ✓ |
| Q-13 | ✓ | ✓ | ✓ |
| Q-14 | ✗ | ✓ | ✓ |
| Q-15 | ✗ | ✓ | ✓ |
| Q-16 | ✓ | ✓ | ✓ |
| Q-17 | ✗ | ✓ | ✓ |
| Q-18 | ✗ | ✗ | ✓ |
| Q-19 | ✗ | ✓ | ✓ |
| Q-20 | ✗ | ✗ | ✓ |

Метрики обоих full runs регенерированы из исходных per-question executions.
`summary.regenerated.json` сравнивается с `summary.json`; ручных чисел в scorer
или aggregate tables нет. Контрольные hashes исходников, корпуса, вопросов,
prompts, schemas и evaluation protocol совпадают между запусками.

Стоимость двух full runs: **$0.07033050** за 394 Chat Completions requests.
Все реальные обращения этой работы, включая preflight, оба smoke runs,
отдельный Q-09 и ablation: **480 requests, $0.08820250** по token usage.
Полная разбивка — `outputs/cost_ledger.json`; GET model metadata не является
оплачиваемым Chat Completions request. Это вычисленная стоимость, не банковское списание.

## I. Доказательства для Part C

### C1 — Описание lookup

Предвыбранные вопросы: Q-01, Q-03, Q-08, Q-09, Q-18. Baseline — S3 Run 1.
Единственное изменение — lookup.description = `Looks things up.`. Настройки,
parameters, implementation и system prompt сохранены; runner проверяет baseline.
Все arguments обеих версий находятся в `outputs/ablation/comparison.json`.

| Question | Calls original | Calls vague | Answer original | Answer vague | Correct original/vague |
|---|---:|---:|---|---|---|
| Q-01 | 3 | 3 | Ossbridge \| 4.57015387231975 | Ossbridge \| 4.57015387231975 | ✓/✓ |
| Q-03 | 9 | 10 | Lindenmoor \| 5.34015866513721 | Lindenmoor \| 5.34015866513721 | ✓/✓ |
| Q-08 | 4 | 5 | Brightwater \| 72.45615 | Brightwater \| 72.45615 | ✓/✓ |
| Q-09 | 5 | 3 | Millbrook \| 0.5556561156405735 | Brightwater \| 0.5556561156405735 | ✓/✗ |
| Q-18 | 3 | 4 | yes \| 40013.391413703386 | yes \| 40013.391413703386 | ✓/✓ |

На этих пяти вопросах accuracy изменилась **5/5 → 4/5**, суммарное число tool calls
**24 → 25**. Q-03: 9→10 calls, появились уточнения с top_k=5; Q-08: 4→5;
Q-18: 3→4, включая дополнительный поиск `Millbrook population 2030 projection`.
Q-01 остался на трёх calls. В Q-09 calls стало меньше, 5→3: вместо двух плотностей
и разности использована формула `44675/921.4-37203/758.6`, вернувшая отрицательное
число. Финал назвал Brightwater, поэтому ответ неверен, хотя corrected area
использована. Четыре остальных complete answer pairs совпали с baseline.

Изменения между двумя выборками не доказывают причинное влияние описания:
temperature 0.7 и отсутствие фиксированного seed дают sampling variation. Кроме
того, общая system instruction продолжает объяснять назначение lookup/calculate;
поэтому ablation удаляет только текст function.description, не всё руководство.

### C2 — Три наблюдаемых ошибки

**S1, Q-01.** `outputs/run_1/traces/S1/Q-01.json` заканчивается
`ANSWER: Ossford | 0.7911737459`. Неверны и район, и число: reference ожидает
Ossbridge / 4.6; сохранённый scorer помечает name_and_numeric. S1 не оставил
промежуточных вычислений, поэтому нельзя утверждать, какой именно факт или
арифметический шаг был причиной. Гипотеза о трудности вычисления плотностей
совместима с ответом, но непосредственно лог подтверждает только неправильный
финал без внешней проверки.

**S2, Q-05.** `outputs/run_1/traces/S2/Q-05.json`, winning_sample=0:
`ANSWER: Coldharbour | 14221.1082172118`. В объяснении перечислены правильные
исходные budget/population значения, но численные результаты деления неверны.
Повторное выполнение записанной формулы `2366900000/11407-2884600000/14926`
инструментом даёт **14235.314486389194**; проверка сохранена отдельно в
`outputs/offline/case_arithmetic.json`, а не выдана за ответ модели.

Четыре valid samples дают 14221.108217…, 14236.951227…, 14210.786646…,
14204.992231…; пятый содержит буквенный suffix и не проходит parser.
Одинаковых полных vote keys нет, поэтому заранее заданный tie-break выбирает
первый. Voting может снижать случайные ошибки, если правильный ответ повторяется,
но не гарантирует их исправление при разрозненных или систематически неверных
вычислениях. Шесть знаков vote normalization — честно зафиксированное, но строгое
условие; после просмотра результатов оно не менялось.

**S3, Q-11.** `outputs/run_1/traces/S3/Q-11.json`: lookup извлёк NR-09, NR-10 и
NR-11, затем model запросила только
`{"mode":"evaluate","expression":"8837/24-3147/10"}`. Calculate вернул
**53.508333333333326**, что правильно для этой формулы. Однако максимум среди
трёх районов даёт Millbrook (`5562/15`), а модель сравнила Ashgrove с Redfen.
Финал `ANSWER: Redfen | 53.508333333333326` имеет верное имя минимального района,
но неверную разность; ожидалось 56.1. Ошибка выбора формулы остаётся у модели,
даже когда retrieval и арифметика исправны.

### C3/C4 — Сравнение, вариативность и ограничения

Accuracy Run 1→Run 2: S1 **4→2**, S2 **16→15**, S3 **19→18** из 20. Разница между
лучшими S3/S2 — **3 вопроса / 15 percentage points** в обоих runs; это больше
наблюдаемого изменения каждой из этих стратегий на 1 вопрос / 5 points, но двух
repeats недостаточно для уверенного статистического вывода. В Run 1 они расходятся
на Q-05/Q-11/Q-12/Q-18/Q-20: S3 выигрывает четыре из этих пяти, S2 — Q-11.

Median latency изменилась: S1 −0.000595 s, S2 +0.298939 s, S3 +0.070417 s.
Cost changes: S1 −$0.00012204, S2 +$0.00027636, S3 −$0.00194982. S3 дешевле S2
на **40.19% / 49.82%** соответственно и требует примерно вдвое меньшую median
latency. Разная доля cached input объясняет, почему cost может уменьшиться даже
при увеличении input tokens; сами cache counts доступны в usage каждого request.

Для этого benchmark предпочтительна **S3**: наблюдаемое сочетание accuracy,
стоимости и времени лучше S2; стоимость и задержка выше дешёвой, но неточной S1.
При жёстком ограничении на один HTTP round trip S1 становится возможным выбором,
но только если допустима показанная потеря accuracy либо меняется характер задач.
Для маленького корпуса и простых неарифметических вопросов имеет смысл заново
сравнить S1 с S2: tool overhead может не окупаться. При 1000-кратном увеличении
корпуса S3 с масштабируемым retrieval вероятнее подходит лучше, поскольку S1/S2
повторно отправляют весь корпус; это прогноз по устройству системы, не измерение
такого большого корпуса.

Один вопрос меняет accuracy на 5 процентных пунктов. Двадцать специально созданных
вопросов из одной области и два запуска не подтверждают универсальное превосходство.
Нужны дополнительные независимые вопросы разных типов и повторные paired runs;
обоснованный размер выборки зависит от ожидаемого эффекта, частоты disagreements
и требуемой мощности, которых два запуска не определяют. Model alias, caching и
remote load могут меняться; запуск S1→S2→S3 не рандомизирован. Поэтому текущие
числа поддерживают локальный выбор, а не причинный или статистически окончательный
вывод для всех задач.

Наблюдаемые категории ошибок и результаты по типам вопросов:

| Run | Strategy | name_and_numeric | numeric_mismatch | name_mismatch | format_error |
|---|---|---:|---:|---:|---:|
| 1 | S1 | 9 | 5 | 1 | 1 |
| 1 | S2 | 0 | 3 | 1 | 0 |
| 1 | S3 | 0 | 1 | 0 | 0 |
| 2 | S1 | 10 | 4 | 0 | 4 |
| 2 | S2 | 0 | 4 | 1 | 0 |
| 2 | S3 | 0 | 0 | 2 | 0 |

S2 samples: Run 1 — 94 completed / 6 format_error; Run 2 — 93 completed / 7 format_error.
API failures, tool errors, round-limit terminations: 0 in both full runs.

| Lexical question group (Run 1) | S1 correct | S2 correct | S3 correct |
|---|---:|---:|---:|
| density | 0/2 | 2/2 | 2/2 |
| population | 2/4 | 3/4 | 4/4 |
| water | 0/5 | 5/5 | 5/5 |
| schools | 0/3 | 3/3 | 2/3 |
| budget | 0/3 | 0/3 | 3/3 |
| road | 0/1 | 1/1 | 1/1 |
| other | 2/2 | 2/2 | 2/2 |

Названия типов в автоматической сводке определяются поиском подстрок в question
text; численности невелики. В частности, группа `water` включает density-вопрос
Q-09 из-за имени Brightwater, а `density` включает Q-19 о road density. Это
лексические диагностические группы, не строгая семантическая таксономия; ниже
собственно water questions перечислены явно, чтобы не приписывать им лишний вопрос.
Особенно полезное отличие S3 от S2 в Run 1 — budget questions Q-05/Q-12/Q-20:
3/3 против 0/3. Для собственно water questions Q-03/Q-08/Q-14/Q-17 обе стратегии
получили 4/4, то есть прироста
accuracy относительно S2 здесь не наблюдалось. Для Q-06/Q-10/Q-13/Q-16 все три
стратегии были правильны; дополнительного улучшения correctness в Run 1 нет.
Q-11 показывает возможное ухудшение выбора формулы даже с инструментами.

### Данные для восьми финальных вопросов

1. При получении `tool_calls` уже завершён HTTP-вызов модели и генерация описания
   запрошенных действий. Python-функция ещё не выполнялась: её после проверки
   вызывает dispatcher, что видно по отдельным request/tool events и latencies.
2. `arguments` — строка с JSON согласно протоколу function calling. Её необходимо
   декодировать в object, проверить типы/поля/duplicates и только затем передавать
   keyword arguments; прямой вызов с raw string нарушит интерфейс и обойдёт проверки.
3. Оценка text overhead обеих schemas — **834 tokens**: 303 lookup + 531 calculate,
   `o200k_base`, tiktoken 0.14.0. Это воспроизводимая tokenizer-based оценка,
   не обещание точного API delta; исходные schemas/serialization сохранены.
4. S2 дороже S1 в **15.1143 раза** в Run 1 (+$0.02023480) и **16.7313 раза**
   в Run 2 (+$0.02063320). Пять samples повторно передают corpus и генерируют более
   длинные объяснения. Кэширование изменяет фактическую стоимость, поэтому
   коэффициент не обязан равняться пяти.
5. **Q-14 потребовал 7 model calls в обоих full runs**. В Run 1 это шесть lookup
   requests для воды/населения Tarnvale/Ashgrove, три calculate calls и final
   response; часть calls объединена в одном model response. Input usage по семи
   раундам: 1186, 1863, 2540, 3081, 3643, 3788, 3869 tokens.
   Рост истории добавляет прошлые assistant/tool messages к
   следующему запросу; token count обычно растёт, хотя cache может удешевить input.
   Число вызовов не равно числу model rounds: независимые calls могут идти вместе.
6. Для 100000 документов нужны inverted BM25 index и сохранённые passage metadata,
   инкрементальные обновления, явные связи version/correction, dictionary/alias
   lookup имён и измерение recall на отдельной выборке. Текущий линейный обход
   passages разумен для 17 документов, но такое масштабирование не проверялось.
7. AST whitelist, запрет names/calls/attributes/power, size/node/depth и finite
   numeric limits не позволяют выполнить опасный Python-код. Модель всё ещё может
   выбрать неправильную формулу или единицы, получить bounded error либо неверный
   смысловой ответ; именно это демонстрирует S3 Q-11.
8. Наибольшее преимущество S3 над S2 в Run 1 видно в budget-per-person/pupil
   сравнении, где крупные числа и деление дали ошибки S2. Для четырёх собственно
   water questions обе версии показали 4/4, а Q-06/Q-10/Q-13/Q-16 были правильны даже у S1; эти
   наблюдения не равны доказательству, что инструменты никогда не помогают там.

## J. Файлы, commits и воспроизведение

Основные созданные файлы перечислены в B; пользовательская инструкция —
`docs/USAGE.md`, правила оценки — `docs/evaluation_protocol.md`, protocol/evidence
JSON — в `outputs/`. `requirements.txt` оставлен исходным; добавлены packaging и
зафиксированный список установленных зависимостей `requirements-lock.txt`.

| Commit | Содержание |
|---|---|
| `b9f4bce` | Исходная Part A, до первого Python-кода. |
| `8074605` | Baseline audit и milestones. |
| `57ad225` | Retrieval/calculator и 81 offline test. |
| `e75c41d` | Agent/client/strategies/evaluation и предварительно зафиксированный protocol. |
| `dab3222` | CLI/diagnostics, end-to-end checks и первый реальный smoke. |
| `b714ef1` | Исправление generic vocabulary, Windows console и 146 tests; frozen source full runs. |
| `a3b23b4` | Validated smoke и отдельный Q-09. |
| `1b40fbe` | Run 1, regeneration и Part C analysis. |
| `7c90677` | Run 2, paired comparison и дополнительные производные показатели. |
| `6012091` | C1 ablation, regeneration и полный ledger фактических API calls. |

Финальный commit документации и integrity evidence находится через
`git log -1 --format=%H -- docs/IMPLEMENTATION_REPORT.md` (его SHA появляется
после записи самого отчёта).

Оба full-run manifests содержат один и тот же source SHA-256:
`19e0beea7b8620b4ffd9ca3f89dc79ebf3702932893c06cb6eec9da53a5d5bd9`.
Разница Git HEAD из-за commits документации/результатов не означает изменение
исполняемого source; сравниваются именно content hashes.

Фактические команды полного сравнения и анализа:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m css4007_hw4 probe --output outputs/preflight.json
.\.venv\Scripts\python.exe -m css4007_hw4 run --questions Q-01 Q-03 Q-09 --preflight outputs/preflight.json --output outputs/smoke_validated
.\.venv\Scripts\python.exe -m css4007_hw4 run --strategies S3 --questions Q-09 --preflight outputs/preflight.json --output outputs/q09
.\.venv\Scripts\python.exe -m css4007_hw4 run --preflight outputs/preflight.json --output outputs/run_1
.\.venv\Scripts\python.exe -m css4007_hw4 run --preflight outputs/preflight.json --baseline outputs/run_1 --output outputs/run_2
.\.venv\Scripts\python.exe -m css4007_hw4 ablation --baseline outputs/run_1 --preflight outputs/preflight.json --output outputs/ablation
.\.venv\Scripts\python.exe -m css4007_hw4 metrics --run outputs/run_1
.\.venv\Scripts\python.exe -m css4007_hw4 metrics --run outputs/run_2
.\.venv\Scripts\python.exe -m css4007_hw4 analyze --run-1 outputs/run_1 --run-2 outputs/run_2 --output outputs/part_c.json
```

Для повторного inference используйте новые output paths (например `_new`), чтобы
не переписать реальные измерения. Для повторного scoring существующих outputs
применяется `metrics`; при изменении source/protocol/reference он откажется
молча пересчитывать. Пример Python-окружения: `.venv`, Python 3.14.2, pytest 9.1.1.

## K. Ограничения и оставшиеся действия

Завершённая и проверенная часть: оба инструмента, 146 tests, все три стратегии,
preflight, smoke, live Q-09, два full runs, C1 ablation, raw traces, regeneration,
Part C evidence и документация. Failing tests и пропущенных обязательных live
экспериментов нет. Не проверялись на реальном API искусственные network timeouts,
model-denial и malformed tool-call IDs: для них используются offline tests.

Ограничения реализации: эвристическое распознавание correction notices по текущему
формату корпуса; linear BM25 retrieval; floating-point arithmetic; ограничение
rounds; отсутствие resume частично выполненного run; неизвестные charges при
ответах без usage. Смысловую правильность формулы инструменты не гарантируют.
S2 consensus с шестью знаками может часто сводиться к deterministic tie-break;
протокол не менялся после наблюдения этого эффекта.

Первоначальный credential blocker устранён во время работы: приложение обнаружило
локальный `.env` и успешно выполнило реальные запросы. Ключ не выводился и не
сохранялся в результатах/commits. Когда локальное переименование `.env.example`
в `.env` также изменило ignore rules, исключение `.env` было восстановлено;
безопасный placeholder `.env.example` возвращён из Git.

`SUBMISSION.md`, RUBRIC и оба data-файла совпадают с исходным commit. Во время
работы извне также изменился README: `cp .env.example .env` стал `cp .env .env`.
Эта пользовательская правка не включена в наши commits и оставлена unstaged,
чтобы не перезаписать параллельную работу. Содержимое `.idea/` сохранено.

Результаты финальных integrity checks находятся в `outputs/offline/verification.json`:
hash документа, порядок Part A → Python, равенство regenerated metrics, равенство
контролируемых настроек, отсутствие ключа в deliverables и исключение `.env` из Git.

Студенту остаётся самостоятельно заполнить Parts B/C и AI disclosure, используя
этот отчёт и точные логи, проверить указанную README-правку, затем при необходимости
push в свой fork и отправка ссылки на LMS. `SUBMISSION.md` намеренно не заполнен
за студента. Pull request в upstream не создавался; push/LMS submission не выполнялись.
