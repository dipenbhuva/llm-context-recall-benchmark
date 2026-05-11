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
```

## Expected output

- `file-first` prompt body starts with source.
- `task-first` prompt body starts with `Task:`.
- Line-number anchor mentions the source line directly.
- Result JSON records `prompt_strategy`.

## Student task

Compare the two prompt files. If you have model access, compare the two result
JSON files and note latency, matched lines, and hallucinations.

## Reflection questions

- Which strategy is better for prefix-cache reuse?
- Does line-number anchoring make the task easier or harder?
- What production risk appears when prompt strategy changes silently?

## Verification checklist

- You can generate both prompt orders.
- You can explain which prompt is cache-friendly.
- Optional: you can find `prompt_strategy` in a run dump.
