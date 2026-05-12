# AI Accelerator Labs PRD and Build Tracker

This document is the working plan for turning this repository into a set of
hands-on labs for AI accelerator students learning production-ready AI through
one concrete benchmark:

> Give an LLM a source-code corpus in context, ask it to reproduce the body of a
> named function, and measure exact positional recall.

The labs should stay anchored to the existing repo mechanics: extraction,
prompt construction, model calls, scoring, result dumps, and visual analysis.
They should not become generic chatbot, RAG, agent, or safety labs unless the
exercise directly improves or interrogates this code-recall benchmark.

## Status Legend

Use this document as the implementation tracker. Update status as PRs land.

| Status | Meaning |
| --- | --- |
| Proposed | Idea is defined, but implementation has not started. |
| Ready | Scope is clear enough to implement. |
| In progress | A PR or branch is actively implementing it. |
| Done | Code, docs, and verification have landed. |
| Blocked | Cannot proceed without a decision or dependency. |

## Current Repo Baseline

The repository already has the core benchmark loop:

| Area | Existing files | Current behavior |
| --- | --- | --- |
| CLI | `bench.py` | Commands: `extract`, `run`, `rescore`. |
| Corpus config | `configs/corpora/*.toml` | Defines fixture directory, glob, limit, sample size, seed. |
| Model config | `configs/models/*.toml` | Defines model ID, endpoint, generation knobs, auth source. |
| Extraction | `bench/extract.py` | Extracts Python and JavaScript functions with at least 20 body lines. |
| Prompting | `bench/runner.py` | Puts full source first, task suffix last, then queries the model. |
| Model API | `bench/client.py` | Calls OpenAI-compatible `/v1/chat/completions`. |
| Scoring | `bench/scorer.py` | Uses line-level matching against primary and bonus lines. |
| Reporting | `bench/report.py` | Renders ANSI terminal summaries. |
| Visualization | `analysis/visualize.py` | Builds Plotly dashboards from `results/*.json`. |
| Smoke test | `smoke_test.py` | Tests Python extraction, sampling, and scoring without an LLM. |

Important environment finding:

- The code imports `tomllib`, so normal CLI use requires Python 3.11 or newer.
- On this machine, `python3` and `uv run python` currently resolve to Python
  3.10.6, which fails on `bench.py extract --corpus ...`.
- `python3.11 bench.py extract --corpus http_server --all` works for the Python
  fixture, but JavaScript extraction also needs `esprima` installed into the
  Python 3.11 environment.

## Target Student Outcomes

By the end of the lab sequence, students should be able to:

1. Explain how ground-truth code spans are extracted from a source corpus.
2. Inspect the exact prompt sent to the model and predict how prompt wording
   affects recall.
3. Run the benchmark against a local or hosted OpenAI-compatible endpoint.
4. Interpret `matched`, `missing`, `hallucinated`, `bonus`, `passed`, and
   position-depth charts.
5. Construct synthetic corpora that isolate context-depth, distractor, and
   ambiguity failures.
6. Modify scoring policy intentionally and explain the tradeoff.
7. Produce a reproducible model comparison report from result JSON.
8. Distinguish "model saw the code" from "model can retrieve the correct span."

## Implementation Roadmap

Each row below is intended to be a PR-sized unit of work.

| PR ID | Status | Title | Primary files | Student-facing output |
| --- | --- | --- | --- | --- |
| PR-001 | Done | Reproducible Python environment | `pyproject.toml`, `uv.lock`, `README.md`, `tests/test_smoke.py` | Students can run all non-LLM commands with one documented setup. |
| PR-002 | Done | Add prompt inspection command | `bench.py`, `bench/runner.py`, `tests/test_prompt_cli.py` | `bench.py prompt --corpus http_server --function run_cgi` prints exact model prompt. |
| PR-003 | Done | Add prompt strategy variants | `bench.py`, `bench/runner.py`, `tests/test_prompt_cli.py` | Students compare file-first vs task-first and anchor wording. |
| PR-004 | Done | Add synthetic recall corpus generator | `scripts/generate_synthetic_corpus.py`, `fixtures/synthetic_recall.py`, `configs/corpora/synthetic_recall.toml`, tests | Students generate controlled long-context Python corpora. |
| PR-005 | Done | Add distractor corpus mode | generator, `fixtures/synthetic_distractors.py`, configs/tests | Students test near-duplicate function confusion. |
| PR-006 | Done | Make duplicate function handling visible | `bench/extract.py`, `bench.py`, `fixtures/multi_file/`, tests | Multi-file corpora report skipped duplicate names. |
| PR-007 | Done | Add fake-response rescoring lab | `fixtures/responses/`, `fixtures/results/`, tests | Students learn scoring without needing an LLM. |
| PR-008 | Done | Add result lineage metadata | `bench/runner.py`, `tests/test_result_lineage.py`, docs | Result JSONs include enough metadata to compare runs. |
| PR-009 | Done | Add lab-focused dashboard summary | `analysis/visualize.py`, `tests/test_visualize.py`, docs | Dashboards include a deployment-style recall report. |
| PR-010 | Done | Add full lab workbook and instructor runbook | `labs/*.md`, `README.md`, `tests/test_lab_docs.py` | Course can be run end to end from the repo. |
| PR-011 | Done | Add deterministic mock LLM server | `tests/fake_openai_server.py`, `tests/test_fake_openai_server.py`, docs | `mock-llm` runtime tests exercise the full HTTP/run/dump path without a real model. |
| PR-012 | Done | Add result comparison CLI | `bench/compare.py`, `bench.py`, `fixtures/results/compare_*.json`, tests/docs | Students can compare two run dumps for prompt/model A/B reports. |

## PR-001: Reproducible Python Environment

Status: Done

### Goal

Make the repository runnable by students without interpreter ambiguity.

### Proposed Changes

- Add `pyproject.toml` with Python `>=3.11`.
- Move dependencies from `requirements.txt` into project metadata while keeping
  `requirements.txt` as a compatibility reference.
- Add `pytest` as a dev dependency.
- Convert or wrap `smoke_test.py` so it can run through `pytest`.
- Update `README.md` setup commands to force Python 3.11 or newer.

### Acceptance Criteria

- A fresh student environment can run:

```bash
uv venv --python 3.11
uv sync
uv run python bench.py extract --corpus http_server --all
uv run python smoke_test.py
```

- The setup path also installs `esprima`, so this works:

```bash
uv run python bench.py extract --corpus jquery
```

### Test Cases

| Test | Command | Expected |
| --- | --- | --- |
| Python version | `uv run python --version` | Python 3.11 or newer. |
| Smoke test | `uv run python smoke_test.py` | All smoke checks pass. |
| Python corpus extraction | `uv run python bench.py extract --corpus http_server --all` | Lists 11 functions. |
| JS corpus extraction | `uv run python bench.py extract --corpus jquery` | Lists sampled JS targets. |

### Verification

Verified on 2026-05-11:

```bash
uv venv --python 3.11 && uv sync --dev
uv run python --version
uv run python smoke_test.py
uv run pytest
uv run python bench.py extract --corpus http_server --all
uv run python bench.py extract --corpus jquery
```

## PR-002: Add Prompt Inspection Command

Status: Done

### Goal

Let students inspect exactly what is sent to the model before they run an
expensive or slow benchmark.

### Proposed CLI

```bash
python bench.py prompt --corpus http_server --function run_cgi
python bench.py prompt --file fixtures/http_server.py --function send_head
python bench.py prompt --corpus http_server --function run_cgi --no-think
```

### Proposed Changes

- Expose the existing prompt builder in `bench/runner.py` as a public helper.
- Add `cmd_prompt` and a `prompt` subcommand in `bench.py`.
- Reuse the existing source resolution path from `_resolve_source`.
- Error clearly if the function name is not present.
- Print prompt metadata before the prompt body:
  - corpus/file
  - function
  - source line
  - prompt characters
  - language
  - whether `/no_think` is appended

### Acceptance Criteria

- Students can see the source-first prompt and explain why the task suffix is
  last.
- The command does not call any model endpoint.
- The printed prompt is byte-for-byte equivalent to the prompt used by
  `bench.py run` for the same function and options.

### Test Cases

| Test | Command | Expected |
| --- | --- | --- |
| Existing function | `python bench.py prompt --corpus http_server --function run_cgi` | Prints prompt containing `Task:` and `def run_cgi(` guidance. |
| Missing function | `python bench.py prompt --corpus http_server --function nope` | Exits non-zero with clear error. |
| Single-file mode | `python bench.py prompt --file fixtures/http_server.py --function send_head` | Prints prompt for `send_head`. |
| No model call | Run with no model server running | Command still succeeds. |

### Verification

Verified on 2026-05-11:

```bash
uv run python bench.py prompt --corpus http_server --function run_cgi
uv run python bench.py prompt --file fixtures/http_server.py --function send_head
uv run python bench.py prompt --corpus http_server --function nope
uv run pytest
```

## PR-003: Add Prompt Strategy Variants

Status: Done

### Goal

Teach that recall is affected by prompt structure, not only model quality.

### Proposed CLI

```bash
python bench.py run --corpus http_server --model qwen36-35b --prompt-order file-first
python bench.py run --corpus http_server --model qwen36-35b --prompt-order task-first
python bench.py run --corpus http_server --model qwen36-35b --anchor-style function-name
python bench.py run --corpus http_server --model qwen36-35b --anchor-style line-number
```

### Strategy Variants

| Variant | Purpose |
| --- | --- |
| `file-first` | Existing production-friendly prompt layout that enables prefix cache reuse. |
| `task-first` | Places the task before the source to show cache and instruction-order effects. |
| `function-name` | Existing anchor: ask for a named function body. |
| `line-number` | Ask by source line number to compare positional vs symbolic recall. |
| `include-signature` | Ask for signature plus body to test off-by-one behavior. |

### Proposed Changes

- Add a small `PromptStrategy` representation in `bench/runner.py`.
- Keep the current prompt as the default.
- Include prompt strategy metadata in result JSON.
- Add a lab page where students run A/B comparisons.

### Acceptance Criteria

- Default behavior is unchanged.
- Each run records the strategy in the result dump.
- Strategy changes are visible in `bench.py prompt`.

### Test Cases

| Test | Command | Expected |
| --- | --- | --- |
| Default compatibility | Existing `bench.py run` command | Produces same prompt as current code. |
| Prompt diff | `bench.py prompt` with two strategies | Output differs only in intended sections. |
| Result metadata | Run with non-default strategy | JSON includes prompt strategy fields. |

### Verification

Verified on 2026-05-11:

```bash
uv run python bench.py prompt --corpus http_server --function run_cgi --prompt-order file-first
uv run python bench.py prompt --corpus http_server --function run_cgi --prompt-order task-first
uv run python bench.py prompt --corpus http_server --function run_cgi --anchor-style line-number
uv run python bench.py run --file fixtures/http_server.py --model fake-model \
  --base-url http://127.0.0.1:9 --function send_head \
  --prompt-order task-first --anchor-style line-number \
  --skip-preflight --fail-fast-after 1 --dump /tmp/strategy.json
uv run pytest
```

## PR-004: Add Synthetic Recall Corpus Generator

Status: Done

### Goal

Give students a controlled way to create source corpora of different sizes and
difficulty levels.

### Proposed CLI

```bash
python scripts/generate_synthetic_corpus.py \
  --functions 200 \
  --body-lines 30 \
  --out fixtures/synthetic_recall.py

python bench.py extract --file fixtures/synthetic_recall.py
python bench.py run --file fixtures/synthetic_recall.py --model qwen36-35b -k 16
```

### Proposed Generator Behavior

- Emit valid Python source.
- Create functions named `target_000`, `target_001`, and so on.
- Give each function at least 30 body lines.
- Include repeated boilerplate and small per-function differences.
- Support deterministic output with `--seed`.
- Optionally insert filler blocks between functions to increase context depth.

### Implemented Files

- `scripts/generate_synthetic_corpus.py`
- `fixtures/synthetic_recall.py`
- `configs/corpora/synthetic_recall.toml`
- `tests/test_synthetic_generator.py`

The student lab page is deferred to PR-010 so the workbook can use a single
consistent lab format.

### Acceptance Criteria

- Generated file can be parsed by `bench.extract.extract`.
- `bench.py extract` finds the expected number of functions.
- The generated corpus has deterministic content for the same seed.

### Test Cases

| Test | Command | Expected |
| --- | --- | --- |
| Generate small corpus | `python scripts/generate_synthetic_corpus.py --functions 10 --body-lines 30 --out /tmp/synth.py` | File exists. |
| Extract generated corpus | `python bench.py extract --file /tmp/synth.py --all` | Lists 10 functions. |
| Determinism | Generate twice with same seed and compare hash | Hashes match. |
| Minimum body length | Generate with body lines 20 | All functions are extractable. |

### Verification

Verified on 2026-05-11:

```bash
uv run python scripts/generate_synthetic_corpus.py --functions 10 --body-lines 30 --seed 7 --out /tmp/synth_a.py
uv run python bench.py extract --file /tmp/synth_a.py --all
uv run python scripts/generate_synthetic_corpus.py --functions 10 --body-lines 30 --seed 7 --out /tmp/synth_b.py
shasum -a 256 /tmp/synth_a.py /tmp/synth_b.py
uv run python scripts/generate_synthetic_corpus.py --functions 200 --body-lines 30 --filler-lines 20 --out /tmp/synth_long.py
uv run python bench.py extract --file /tmp/synth_long.py
uv run python bench.py extract --corpus synthetic_recall
uv run pytest
```

## PR-005: Add Distractor Corpus Mode

Status: Done

### Goal

Teach that long-context recall can fail by retrieving the wrong nearby or
similar function, not just by forgetting.

### Proposed CLI

```bash
python scripts/generate_synthetic_corpus.py \
  --functions 200 \
  --body-lines 30 \
  --distractor-groups 20 \
  --near-duplicate-rate 0.8 \
  --out fixtures/synthetic_distractors.py
```

### Proposed Behavior

- Generate groups of functions with similar names and similar bodies.
- Ensure each target has a small unique marker in the first 20 lines.
- Let students observe whether the model copies from a sibling function.

### Implemented Files

- `scripts/generate_synthetic_corpus.py`
- `fixtures/synthetic_distractors.py`
- `configs/corpora/synthetic_distractors.toml`
- `tests/test_synthetic_generator.py`

### Acceptance Criteria

- Distractor corpus is valid Python.
- Extraction finds all target functions.
- Lab asks students to inspect hallucinated lines and identify wrong-source
  retrieval.

### Test Cases

| Test | Command | Expected |
| --- | --- | --- |
| Generate distractors | Generator with distractor flags | File contains grouped near-duplicate functions. |
| Extract | `bench.py extract --file fixtures/synthetic_distractors.py --all` | Lists generated functions. |
| Unique markers | Static check over generated file | Each target has a unique marker. |

### Verification

Verified on 2026-05-11:

```bash
uv run python scripts/generate_synthetic_corpus.py --functions 40 --body-lines 30 \
  --distractor-groups 8 --near-duplicate-rate 0.8 --out /tmp/distractors.py
uv run python bench.py extract --file /tmp/distractors.py --all
rg "UNIQUE_MARKER" /tmp/distractors.py
uv run python bench.py extract --corpus synthetic_distractors
uv run pytest
```

## PR-006: Make Duplicate Function Handling Visible

Status: Done

### Goal

Teach corpus ambiguity and dataset hygiene with multi-file corpora.

Current behavior in `bench/extract.py`: duplicate function names across files
are skipped silently after the first occurrence.

### Proposed Changes

- Track skipped duplicate names during `load_source_glob`.
- Add an optional duplicate summary to `Source`.
- Show duplicate count in `bench.py extract`.
- Add a lab fixture with two files defining the same function name.

### Proposed Files

- `fixtures/multi_file/a.py`
- `fixtures/multi_file/b.py`
- `configs/corpora/multi_file_duplicates.toml`
- `tests/test_duplicate_extraction.py`

The student lab page is deferred to PR-010 so the workbook can use a single
consistent lab format.

### Acceptance Criteria

- Existing single-file corpora behave the same.
- Multi-file extraction reports skipped duplicates.
- Students can explain why ambiguous function names make recall evaluation
  invalid.

### Test Cases

| Test | Command | Expected |
| --- | --- | --- |
| Multi-file extract | `bench.py extract --corpus multi_file_duplicates --all` | Reports duplicate skip count. |
| First occurrence retained | Inspect listed targets | First file's function is kept. |
| No duplicate regression | `bench.py extract --corpus http_server --all` | No duplicate warning. |

### Verification

Verified on 2026-05-11:

```bash
uv run python bench.py extract --corpus multi_file_duplicates --all
uv run python bench.py extract --corpus multi_file_duplicates --show repeated_name
uv run python bench.py extract --corpus http_server --all
uv run pytest
```

## PR-007: Add Fake-Response Rescoring Lab

Status: Done

### Goal

Teach scoring mechanics without requiring model access.

### Proposed Files

- `fixtures/responses/send_head_perfect.txt`
- `fixtures/responses/send_head_truncated.txt`
- `fixtures/responses/send_head_hallucinated.txt`
- `fixtures/responses/send_head_indent_changed.txt`
- `fixtures/results/send_head_fake_results.json`
- `tests/test_rescore_fixtures.py`

The student lab page is deferred to PR-010 so the workbook can use a single
consistent lab format.

### Student Flow

```bash
python bench.py rescore fixtures/results/send_head_fake_results.json \
  --file fixtures/http_server.py

python bench.py rescore fixtures/results/send_head_fake_results.json \
  --file fixtures/http_server.py \
  --relax-indent
```

### Acceptance Criteria

- Students can see how perfect, truncated, hallucinated, and indentation-changed
  outputs produce different scores.
- The lab explains primary matches, bonus matches, hallucinations, and pass
  threshold.

### Test Cases

| Test | Command | Expected |
| --- | --- | --- |
| Rescore fixture | `bench.py rescore fixtures/results/send_head_fake_results.json --file fixtures/http_server.py` | Prints all fake cases. |
| Relaxed indentation | Same command with `--relax-indent` | Indentation case improves. |
| Missing source | Run without `--file` if stored path is invalid | Clear error message. |

### Verification

Verified on 2026-05-11:

```bash
uv run python bench.py rescore fixtures/results/send_head_fake_results.json --file fixtures/http_server.py
uv run python bench.py rescore fixtures/results/send_head_fake_results.json --file fixtures/http_server.py --relax-indent
uv run python bench.py rescore fixtures/results/send_head_fake_results.json --file fixtures/http_server.py >/tmp/rescore.txt
rg "SUMMARY|send_head" /tmp/rescore.txt
uv run pytest
```

## PR-008: Add Result Lineage Metadata

Status: Done

### Goal

Make result JSONs comparable and auditable.

### Proposed Result Fields

Add top-level fields to result dumps:

```json
{
  "schema_version": 2,
  "run_id": "...",
  "created_at": "...",
  "git_sha": "...",
  "python_version": "...",
  "corpus_sha256": "...",
  "prompt_template_id": "...",
  "sample_k": 16,
  "sample_seed": 42,
  "selected_functions": ["..."]
}
```

### Proposed Changes

- Compute source file checksums in `bench/runner.py`.
- Include sampling metadata and selected function order.
- Keep visualization backward-compatible with old result files. No
  visualization code change was needed because unknown JSON fields are ignored.
- Cover metadata and checksum stability in `tests/test_result_lineage.py`.

### Acceptance Criteria

- Old result files still load in `analysis/visualize.py`.
- New result files contain enough information to explain whether two runs are
  comparable.

### Test Cases

| Test | Command | Expected |
| --- | --- | --- |
| Run dump | `bench.py run ... --dump /tmp/result.json` | New metadata fields exist. |
| Backward compatibility | Visualize existing minimal result JSON | No crash. |
| Hash stability | Same corpus produces same checksum | Checksums match. |

### Verification

Verified on 2026-05-11:

```bash
uv run python bench.py run --file fixtures/http_server.py --model fake-model \
  --base-url http://127.0.0.1:9 --function send_head \
  --skip-preflight --fail-fast-after 1 --dump /tmp/lineage.json
python -m json.tool /tmp/lineage.json
uv run python analysis/visualize.py --results-dir fixtures/results --output-dir /tmp/charts
uv run pytest
```

## PR-009: Add Lab-Focused Dashboard Summary

Status: Done

### Goal

Make the visualization answer the questions students are asked in the labs.

### Proposed Dashboard Additions

- Run metadata summary: model, corpus, strategy, seed, prompt size.
- Recall by depth summary: early/middle/late averages.
- Failure table: worst functions by matched lines.
- Error table: failed API calls and empty responses.
- Optional "compare two runs" page for prompt strategy A/B testing.

### Proposed Changes

- Extend `analysis/visualize.py`.
- Keep existing pages.
- Add a short lab interpretation checklist.

### Acceptance Criteria

- Existing `analysis/visualize.py` behavior remains.
- New pages are generated only when enough data exists.
- Students can answer lab questions from dashboard output without manually
  inspecting JSON.

### Test Cases

| Test | Command | Expected |
| --- | --- | --- |
| Empty results dir | `python analysis/visualize.py --results-dir /tmp/empty` | Clear no-results message. |
| Existing result JSON | `python analysis/visualize.py` | Existing charts plus new summary. |
| Old result JSON | Visualize old schema | No crash. |

### Verification

Verified on 2026-05-11:

```bash
uv run python analysis/visualize.py --results-dir fixtures/results --output-dir /tmp/lab-charts
test -f /tmp/lab-charts/http_server/summary.html
rg "Lab summary|Worst Failure|fake-responses" /tmp/lab-charts/http_server/summary.html
uv run python analysis/visualize.py --results-dir /tmp/empty-results --output-dir /tmp/empty-charts || true
uv run pytest
```

## PR-010: Full Lab Workbook and Instructor Runbook

Status: Done

### Goal

Package the work into a course-ready sequence.

### Proposed Files

```text
labs/
  README.md
  01_ground_truth_extraction.md
  02_prompt_inspection.md
  03_prompt_strategy_ab_test.md
  04_synthetic_recall.md
  05_distractor_recall.md
  06_duplicate_names.md
  07_rescoring_without_llm.md
  08_result_lineage.md
  09_final_model_report.md
  instructor_runbook.md
```

### Lab Format

Each lab should use the same structure:

1. Objective
2. Concepts
3. Files to inspect
4. Commands to run
5. Expected output
6. Student task
7. Reflection questions
8. Verification checklist

### Final Student Deliverable

Students produce a short model comparison report:

- Corpus used
- Model configs used
- Prompt strategy
- Pass count
- Matched line totals
- Hallucinated line totals
- Recall vs position observation
- Known failure mode
- Recommendation: deploy, do not deploy, or needs more evals

### Acceptance Criteria

- A student can start from a fresh clone and complete non-LLM labs locally.
- LLM-dependent labs clearly mark model/server prerequisites.
- Instructor runbook includes estimated runtime and troubleshooting notes.

### Verification

Verified on 2026-05-11:

```bash
rg "Objective|Commands to run|Verification checklist" labs
rg "bench.py extract|bench.py prompt|bench.py rescore" labs
uv run pytest
```

## Runtime Test Contract

Every lab PR must document runtime tests before it is considered ready. A
runtime test is a command a student or instructor can run from the repo root to
prove the lab works in a real checkout.

Each runtime test entry must include:

| Field | Required meaning |
| --- | --- |
| ID | Stable test ID, for example `PR-002-RT-01`. |
| Type | `ci`, `local-no-llm`, `mock-llm`, or `live-llm`. |
| Setup | One-time setup or generated fixture needed before the command. |
| Command | Exact command to run from repo root. |
| Expected | Observable output, file, exit code, or JSON field. |
| Artifact | File created or inspected, if any. |

Runtime test types:

| Type | Meaning | Should run in CI? |
| --- | --- | --- |
| `ci` | Fully deterministic and quick. No model server, no API keys. | Yes |
| `local-no-llm` | Runs locally without model access, but may write `/tmp` files or generated fixtures. | Usually |
| `mock-llm` | Uses a deterministic local fake OpenAI-compatible server. | Yes, after the fake server exists |
| `live-llm` | Requires LM Studio, llama.cpp, Ollama, or a hosted model key. | No, manual/instructor only |

The repo includes `tests/fake_openai_server.py`, a deterministic
OpenAI-compatible server for `mock-llm` tests. It returns a known response so
`bench.py run` can exercise the full HTTP/runtime/dump path without GPUs or API
keys.

Proposed command shape:

```bash
python tests/fake_openai_server.py --port 8765 --response-file fixtures/responses/send_head_perfect.txt
python bench.py run \
  --file fixtures/http_server.py \
  --model fake-model \
  --base-url http://127.0.0.1:8765 \
  --function send_head \
  --skip-preflight \
  --dump /tmp/fake-run.json
```

Expected behavior:

- The fake server receives an OpenAI-compatible `/v1/chat/completions` request.
- `bench.py run` writes a result JSON.
- The result can be rescored and visualized.

## Runtime Test Matrix By PR

Use this section as the source of truth for what each PR must make runnable.

### PR-001 Runtime Tests

| ID | Type | Setup | Command | Expected | Artifact |
| --- | --- | --- | --- | --- | --- |
| PR-001-RT-01 | `ci` | Fresh environment | `uv venv --python 3.11 && uv sync` | Environment creates successfully. | `.venv/` |
| PR-001-RT-02 | `ci` | PR-001 env active | `uv run python --version` | Python 3.11 or newer. | none |
| PR-001-RT-03 | `ci` | PR-001 env active | `uv run python smoke_test.py` | All smoke checks pass. | none |
| PR-001-RT-04 | `ci` | PR-001 env active | `uv run python bench.py extract --corpus http_server --all` | Lists 11 extractable functions. | none |
| PR-001-RT-05 | `ci` | PR-001 env active | `uv run python bench.py extract --corpus jquery` | Extracts sampled JavaScript targets without missing `esprima`. | none |

### PR-002 Runtime Tests

| ID | Type | Setup | Command | Expected | Artifact |
| --- | --- | --- | --- | --- | --- |
| PR-002-RT-01 | `ci` | PR-002 implemented | `python bench.py prompt --corpus http_server --function run_cgi` | Prints metadata and full prompt; contains `Task:` and `def run_cgi(` guidance. | stdout |
| PR-002-RT-02 | `ci` | PR-002 implemented | `python bench.py prompt --file fixtures/http_server.py --function send_head` | Prints a source-first prompt for `send_head`. | stdout |
| PR-002-RT-03 | `ci` | PR-002 implemented | `python bench.py prompt --corpus http_server --function nope` | Exits non-zero with a clear missing-function error. | stderr/stdout |
| PR-002-RT-04 | `ci` | No model server running | `python bench.py prompt --corpus http_server --function run_cgi >/tmp/prompt.txt` | Succeeds without any HTTP call. | `/tmp/prompt.txt` |

### PR-003 Runtime Tests

| ID | Type | Setup | Command | Expected | Artifact |
| --- | --- | --- | --- | --- | --- |
| PR-003-RT-01 | `ci` | PR-003 implemented | `python bench.py prompt --corpus http_server --function run_cgi --prompt-order file-first >/tmp/file-first.txt` | Prompt starts with source contents before `Task:`. | `/tmp/file-first.txt` |
| PR-003-RT-02 | `ci` | PR-003 implemented | `python bench.py prompt --corpus http_server --function run_cgi --prompt-order task-first >/tmp/task-first.txt` | Prompt starts with task/instructions before source contents. | `/tmp/task-first.txt` |
| PR-003-RT-03 | `ci` | Outputs from previous tests | `diff /tmp/file-first.txt /tmp/task-first.txt` | Files differ in prompt order only. | stdout |
| PR-003-RT-04 | `mock-llm` | Fake server running | `python bench.py run --corpus http_server --model fake-model --base-url http://127.0.0.1:8765 --function run_cgi --prompt-order task-first --skip-preflight --dump /tmp/task-first-run.json` | Result JSON includes prompt strategy metadata. | `/tmp/task-first-run.json` |
| PR-003-RT-05 | `live-llm` | Local or hosted model configured | Run same function with `file-first` and `task-first` | Students compare latency and score. | result JSONs |

### PR-004 Runtime Tests

| ID | Type | Setup | Command | Expected | Artifact |
| --- | --- | --- | --- | --- | --- |
| PR-004-RT-01 | `ci` | PR-004 implemented | `python scripts/generate_synthetic_corpus.py --functions 10 --body-lines 30 --seed 7 --out /tmp/synth_a.py` | Synthetic Python file is created. | `/tmp/synth_a.py` |
| PR-004-RT-02 | `ci` | Generated `/tmp/synth_a.py` | `python bench.py extract --file /tmp/synth_a.py --all` | Lists 10 functions named `target_000` through `target_009`. | stdout |
| PR-004-RT-03 | `ci` | PR-004 implemented | `python scripts/generate_synthetic_corpus.py --functions 10 --body-lines 30 --seed 7 --out /tmp/synth_b.py && shasum -a 256 /tmp/synth_a.py /tmp/synth_b.py` | Hashes match for same seed and parameters. | `/tmp/synth_b.py` |
| PR-004-RT-04 | `local-no-llm` | Generated larger corpus | `python scripts/generate_synthetic_corpus.py --functions 200 --body-lines 30 --filler-lines 20 --out /tmp/synth_long.py && python bench.py extract --file /tmp/synth_long.py` | Extract succeeds and reports sampled targets across file depth. | `/tmp/synth_long.py` |

### PR-005 Runtime Tests

| ID | Type | Setup | Command | Expected | Artifact |
| --- | --- | --- | --- | --- | --- |
| PR-005-RT-01 | `ci` | PR-005 implemented | `python scripts/generate_synthetic_corpus.py --functions 40 --body-lines 30 --distractor-groups 8 --near-duplicate-rate 0.8 --out /tmp/distractors.py` | Distractor corpus is created. | `/tmp/distractors.py` |
| PR-005-RT-02 | `ci` | Generated distractor corpus | `python bench.py extract --file /tmp/distractors.py --all` | Extracts all generated functions. | stdout |
| PR-005-RT-03 | `ci` | Generated distractor corpus | `rg "UNIQUE_MARKER" /tmp/distractors.py` | Every target group has unique markers to identify wrong-span retrieval. | stdout |
| PR-005-RT-04 | `live-llm` | Model configured | `python bench.py run --file /tmp/distractors.py --model <model> -k 16` | Students inspect hallucinated lines for sibling-function leakage. | result JSON |

### PR-006 Runtime Tests

| ID | Type | Setup | Command | Expected | Artifact |
| --- | --- | --- | --- | --- | --- |
| PR-006-RT-01 | `ci` | Multi-file duplicate fixture exists | `python bench.py extract --corpus multi_file_duplicates --all` | Output reports skipped duplicate function names. | stdout |
| PR-006-RT-02 | `ci` | Multi-file duplicate fixture exists | `python bench.py extract --corpus multi_file_duplicates --show repeated_name` | Shows the first occurrence selected for evaluation. | stdout |
| PR-006-RT-03 | `ci` | Existing corpus | `python bench.py extract --corpus http_server --all` | No duplicate warning for single-file corpus. | stdout |

### PR-007 Runtime Tests

| ID | Type | Setup | Command | Expected | Artifact |
| --- | --- | --- | --- | --- | --- |
| PR-007-RT-01 | `ci` | Fake result fixture exists | `python bench.py rescore fixtures/results/send_head_fake_results.json --file fixtures/http_server.py` | Prints perfect, truncated, hallucinated, and indentation cases. | stdout |
| PR-007-RT-02 | `ci` | Fake result fixture exists | `python bench.py rescore fixtures/results/send_head_fake_results.json --file fixtures/http_server.py --relax-indent` | Indentation-changed case improves relative to strict scoring. | stdout |
| PR-007-RT-03 | `ci` | Fake result fixture exists | `python bench.py rescore fixtures/results/send_head_fake_results.json --file fixtures/http_server.py >/tmp/rescore.txt && rg "SUMMARY|send_head" /tmp/rescore.txt` | Summary and function names are present. | `/tmp/rescore.txt` |

### PR-008 Runtime Tests

| ID | Type | Setup | Command | Expected | Artifact |
| --- | --- | --- | --- | --- | --- |
| PR-008-RT-01 | `local-no-llm` | No model server needed; command intentionally uses a closed local port and records the request error | `python bench.py run --file fixtures/http_server.py --model fake-model --base-url http://127.0.0.1:9 --function send_head --skip-preflight --fail-fast-after 1 --dump /tmp/lineage.json` | Result JSON is written with lineage metadata and an errored result. | `/tmp/lineage.json` |
| PR-008-RT-02 | `ci` | `/tmp/lineage.json` exists | `python -m json.tool /tmp/lineage.json >/tmp/lineage.pretty.json` | JSON is valid. | `/tmp/lineage.pretty.json` |
| PR-008-RT-03 | `ci` | `/tmp/lineage.json` exists | `python -c "import json; d=json.load(open('/tmp/lineage.json')); print(d['schema_version'], d['run_id'], d['corpus_sha256'])"` | Required lineage fields are present. | stdout |
| PR-008-RT-04 | `ci` | Old-style fixture result exists | `python analysis/visualize.py --results-dir fixtures/results --output-dir /tmp/charts` | Old result files still visualize without crashing. | `/tmp/charts` |

### PR-009 Runtime Tests

| ID | Type | Setup | Command | Expected | Artifact |
| --- | --- | --- | --- | --- | --- |
| PR-009-RT-01 | `ci` | Empty temp dir | `mkdir -p /tmp/empty-results && python analysis/visualize.py --results-dir /tmp/empty-results --output-dir /tmp/empty-charts` | Clear no-results message and non-zero exit. | stdout |
| PR-009-RT-02 | `ci` | Fixture result JSON exists | `python analysis/visualize.py --results-dir fixtures/results --output-dir /tmp/lab-charts` | Generates chart pages and lab summary pages. | `/tmp/lab-charts` |
| PR-009-RT-03 | `ci` | Generated charts | `rg "Recall|Leaderboard|Failure" /tmp/lab-charts` | Expected page content exists. | stdout |

### PR-010 Runtime Tests

| ID | Type | Setup | Command | Expected | Artifact |
| --- | --- | --- | --- | --- | --- |
| PR-010-RT-01 | `ci` | Lab docs exist | `rg "Objective|Commands to run|Verification checklist" labs` | Every lab follows the required structure. | stdout |
| PR-010-RT-02 | `ci` | Lab docs exist | `rg "bench.py extract|bench.py prompt|bench.py rescore" labs` | Labs include concrete repo commands. | stdout |
| PR-010-RT-03 | `local-no-llm` | Fresh checkout | Follow `labs/README.md` non-LLM path | Non-LLM labs complete without model server or API key. | student outputs |
| PR-010-RT-04 | `live-llm` | Instructor model/server ready | Follow `labs/instructor_runbook.md` live-model path | Live benchmark labs produce result JSON and charts. | `results/*.json`, `analysis/charts/` |

### PR-011 Runtime Tests

These tests prove the benchmark can run through an OpenAI-compatible HTTP
boundary without a real LLM.

| ID | Type | Setup | Command | Expected | Artifact |
| --- | --- | --- | --- | --- | --- |
| PR-011-RT-01 | `mock-llm` | Start fake server in one terminal: `python tests/fake_openai_server.py --port 8765 --response-file fixtures/responses/send_head_perfect.txt --record-jsonl /tmp/fake-requests.jsonl` | `python bench.py run --file fixtures/http_server.py --model fake-model --base-url http://127.0.0.1:8765 --function send_head --skip-preflight --dump /tmp/fake-run.json` | Run exits zero and prints `=== send_head`, `[PASS]`, and `matched=20/20`. | `/tmp/fake-run.json` |
| PR-011-RT-02 | `ci` | `/tmp/fake-run.json` exists from PR-011-RT-01 | `python -m json.tool /tmp/fake-run.json >/tmp/fake-run.pretty.json` | Result JSON is valid. | `/tmp/fake-run.pretty.json` |
| PR-011-RT-03 | `ci` | `/tmp/fake-requests.jsonl` exists from PR-011-RT-01 | `python -c "import json; r=json.loads(open('/tmp/fake-requests.jsonl').readline()); print(r['model'], r['stream'], r['messages'][0]['role'])"` | Prints `fake-model False user`. | stdout |
| PR-011-RT-04 | `ci` | Test environment active | `uv run pytest tests/test_fake_openai_server.py` | Full mock server regression passes. | none |

### PR-012 Runtime Tests

These tests make prompt/model A/B comparisons reproducible from existing result
JSONs.

| ID | Type | Setup | Command | Expected | Artifact |
| --- | --- | --- | --- | --- | --- |
| PR-012-RT-01 | `ci` | Comparison fixtures exist | `python bench.py compare fixtures/results/compare_baseline.json fixtures/results/compare_candidate.json >/tmp/compare.txt` | Prints aggregate metric deltas and per-function matched/hallucination deltas. | `/tmp/compare.txt` |
| PR-012-RT-02 | `ci` | `/tmp/compare.txt` exists from PR-012-RT-01 | `rg "Primary matched" /tmp/compare.txt && rg "send_head" /tmp/compare.txt && rg "pass no -> yes" /tmp/compare.txt` | Comparison output includes report-ready evidence. | stdout |
| PR-012-RT-03 | `ci` | Test environment active | `uv run pytest tests/test_compare_cli.py` | Compare CLI regression passes. | none |

## Shared Verification Commands

These commands should remain valid as the lab buildout progresses.

```bash
# Environment
python --version
python -c "import esprima, httpx, plotly; print('deps ok')"

# No-LLM checks
python smoke_test.py
python bench.py extract --corpus http_server --all
python bench.py extract --corpus http_server --show send_head

# JS extraction, requires esprima
python bench.py extract --corpus jquery

# Prompt inspection, after PR-002
python bench.py prompt --corpus http_server --function run_cgi

# Synthetic corpus, after PR-004
python scripts/generate_synthetic_corpus.py --functions 10 --body-lines 30 --out /tmp/synth.py
python bench.py extract --file /tmp/synth.py --all

# Rescoring lab, after PR-007
python bench.py rescore fixtures/results/send_head_fake_results.json --file fixtures/http_server.py

# Visualization, after at least one result JSON exists
python analysis/visualize.py
```

## Lab-Specific Edge Cases To Preserve

| Edge case | Why it matters | Current or future coverage |
| --- | --- | --- |
| Function has docstring as first body line | The benchmark asks for body lines, not semantic code only. | Existing `http_server.py` functions. |
| Model emits markdown fences | Real models do this despite instructions. | Existing `_clean_output` in `bench/scorer.py`. |
| Model truncates after a few lines | Common recall failure. | Existing smoke test and future fake responses. |
| Model emits extra correct lines | Should count as bonus, not hallucination. | Existing smoke test. |
| Model changes indentation | Tests strict vs relaxed scoring. | Existing `--relax-indent`; future lab fixture. |
| Duplicate function names | Makes function-name recall ambiguous. | Future PR-006. |
| Similar distractor functions | Tests wrong-span retrieval. | Future PR-005. |
| Deep functions fail more often | Tests positional recall degradation. | Existing `recall-vs-position` chart. |
| Empty model response | Should be ERROR, not recall FAIL. | Existing runner behavior. |
| Context-too-small server error | Common local model setup issue. | Existing preflight check. |

## PR Review Checklist

Every implementation PR for these labs should answer:

- Which lab or PR ID does this implement?
- What files changed?
- Does it preserve default benchmark behavior?
- What commands were run?
- Are any tests LLM-dependent?
- Are generated artifacts committed intentionally?
- Does the lab work without a model server when possible?
- Does result JSON remain backward-compatible?
- Does the README or lab doc show exact commands?
- Did this PR add or update the relevant runtime tests in this document?
- Are all `ci` and `local-no-llm` runtime tests passing?
- If a test is `mock-llm` or `live-llm`, is that dependency clearly marked?

## Initial Recommended Order

1. PR-001: Fix environment reproducibility first.
2. PR-002: Add prompt inspection so students can see the core artifact.
3. PR-007: Add fake-response rescoring so scoring can be taught without GPUs or API keys.
4. PR-004: Add synthetic corpus generator for controlled recall experiments.
5. PR-010: Add initial lab workbook pages that point to the working commands.
6. PR-003, PR-005, PR-006, PR-008, PR-009: Add deeper experiments and reporting.
