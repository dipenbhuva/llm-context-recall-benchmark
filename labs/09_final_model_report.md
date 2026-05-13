# Lab 09: Final Model Report

## Objective

Write a short production-style model comparison report using benchmark outputs.

## Concepts

- Evidence-based model selection
- Recall vs hallucination tradeoffs
- Depth sensitivity
- Reproducible recommendations

## Files to inspect

- `results/*.json`
- `analysis/charts/index.html`
- `docs/AI_ACCELERATOR_LABS_PRD.md`

## Commands to run

With live model access:

```bash
uv run python bench.py run --corpus http_server --model qwen36-35b
uv run python bench.py run --corpus synthetic_recall --model qwen36-35b
uv run python analysis/visualize.py
uv run python bench.py report results/http_server__qwen36-35b.json --out /tmp/model-report.md
```

Without live model access:

```bash
uv run python bench.py compare fixtures/results/compare_baseline.json fixtures/results/compare_candidate.json
uv run python bench.py report fixtures/results/compare_candidate.json --baseline fixtures/results/compare_baseline.json --out /tmp/model-report.md
uv run python bench.py summarize fixtures/results --format csv --out /tmp/run-summary.csv
uv run python bench.py depth fixtures/results/compare_candidate.json --json /tmp/depth-analysis.json
uv run python analysis/visualize.py --results-dir fixtures/results --output-dir /tmp/lab-charts
open /tmp/lab-charts/index.html
```

## Expected output

- Result JSONs exist for model runs.
- Dashboard pages include Lab summary, Leaderboard, Per-function score, and
  Recall vs position.
- Compare output includes aggregate and per-function deltas between two runs.
- `/tmp/model-report.md` contains validation status, metrics, worst failures,
  baseline comparison, and a recommendation.
- `/tmp/run-summary.csv` contains aggregate metrics for each fixture run.
- `/tmp/depth-analysis.json` groups recall by source-file depth bucket.

## Student task

Generate `/tmp/model-report.md`, then review whether the recommendation is
justified. If you edit it manually, keep these sections:

- Corpus and model configs used
- Prompt strategy used
- Pass count
- Primary lines matched
- Hallucinated lines
- Recall vs position observation
- Worst failure
- Recommendation: deploy, do not deploy, or needs more evals

## Reflection questions

- What score would block deployment?
- Which failure is most concerning for a coding assistant?
- What additional corpus would make your recommendation stronger?

## Verification checklist

- You can produce or inspect a result JSON.
- You can compare two result JSONs.
- You can generate a Markdown model report.
- You can export aggregate run metrics as CSV.
- You can produce a depth-sensitivity artifact.
- You can open a dashboard summary.
- Your report includes a concrete recommendation backed by metrics.
