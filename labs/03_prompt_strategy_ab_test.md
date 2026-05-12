# Lab 03: Prompt Strategy A/B Test

## Objective

Compare how prompt order and target anchors change the benchmark prompt and,
optionally, model behavior.

## Concepts

- File-first vs task-first prompts
- Function-name vs line-number anchors
- Prompt strategy metadata in result JSON

## Files to inspect

- `bench/runner.py`
- `bench.py`
- `results/*.json` after a run

## Commands to run

```bash
uv run python bench.py prompt --corpus http_server --function run_cgi --prompt-order file-first >/tmp/file-first.txt
uv run python bench.py prompt --corpus http_server --function run_cgi --prompt-order task-first >/tmp/task-first.txt
diff /tmp/file-first.txt /tmp/task-first.txt || true
uv run python bench.py prompt --corpus http_server --function run_cgi --anchor-style line-number
```

Optional live-model run:

```bash
uv run python bench.py run --corpus http_server --model qwen36-35b --function run_cgi --prompt-order file-first --dump /tmp/file-first-run.json
uv run python bench.py run --corpus http_server --model qwen36-35b --function run_cgi --prompt-order task-first --dump /tmp/task-first-run.json
uv run python bench.py compare /tmp/file-first-run.json /tmp/task-first-run.json
```

No-LLM comparison fixture:

```bash
uv run python bench.py compare fixtures/results/compare_baseline.json fixtures/results/compare_candidate.json
```

## Expected output

- `file-first` prompt body starts with source.
- `task-first` prompt body starts with `Task:`.
- Line-number anchor mentions the source line directly.
- Result JSON records `prompt_strategy`.
- Compare output shows aggregate and per-function deltas.

## Student task

Compare the two prompt files. Then compare either the fixture result JSONs or
your live result JSONs and note latency, matched lines, and hallucinations.

## Reflection questions

- Which strategy is better for prefix-cache reuse?
- Does line-number anchoring make the task easier or harder?
- What production risk appears when prompt strategy changes silently?

## Verification checklist

- You can generate both prompt orders.
- You can explain which prompt is cache-friendly.
- You can run `bench.py compare` on two result dumps.
- Optional: you can find `prompt_strategy` in a run dump.
