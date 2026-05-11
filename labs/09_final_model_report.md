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
```

Without live model access:

```bash
uv run python analysis/visualize.py --results-dir fixtures/results --output-dir /tmp/lab-charts
open /tmp/lab-charts/index.html
```

## Expected output

- Result JSONs exist for model runs.
- Dashboard pages include Lab summary, Leaderboard, Per-function score, and
  Recall vs position.
- A final report can cite concrete matched-line and hallucination numbers.

## Student task

Write a report with these sections:

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
- You can open a dashboard summary.
- Your report includes a concrete recommendation backed by metrics.
