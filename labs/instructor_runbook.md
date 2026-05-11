# Instructor Runbook

## Objective

Run the code-recall lab sequence consistently for a cohort.

## Concepts

- Keep no-LLM labs separate from live-model labs.
- Require Python 3.11+ and locked dependencies.
- Treat model runs as optional unless local hardware or API keys are ready.

## Files to inspect

- `labs/README.md`
- `docs/AI_ACCELERATOR_LABS_PRD.md`
- `configs/models/*.toml`
- `configs/corpora/*.toml`

## Commands to run

No-LLM setup:

```bash
uv venv --python 3.11
uv sync --dev
uv run pytest
```

No-LLM teaching path:

```bash
uv run python bench.py extract --corpus http_server --show send_head
uv run python bench.py prompt --corpus http_server --function run_cgi
uv run python bench.py extract --corpus synthetic_recall
uv run python bench.py extract --corpus synthetic_distractors
uv run python bench.py extract --corpus multi_file_duplicates --all
uv run python bench.py rescore fixtures/results/send_head_fake_results.json --file fixtures/http_server.py
uv run python analysis/visualize.py --results-dir fixtures/results --output-dir /tmp/lab-charts
```

Live-model path:

```bash
lms load qwen3.6-35b-a3b --context-length 131072 --gpu max -y
uv run python bench.py run --corpus http_server --model qwen36-35b
uv run python analysis/visualize.py
```

## Expected output

- No-LLM labs complete in a few minutes.
- Live-model labs produce result JSON under `results/`.
- Visualization writes dashboards under `analysis/charts/`.

## Student task

Students should submit their commands, one result artifact or dashboard, and a
short final model report.

## Reflection questions

- Which labs require model access?
- Which commands are safe to run in CI?
- What should students do if context preflight fails?

## Verification checklist

- The instructor can run `uv run pytest`.
- The instructor can complete the no-LLM path.
- Live-model prerequisites are clear before class starts.
