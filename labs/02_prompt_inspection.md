# Lab 02: Prompt Inspection

## Objective

Inspect the exact prompt sent to the model without running inference.

## Concepts

- Source-first prompt layout
- Function-name anchor
- `/no_think` suffix
- Prompt length as a production concern

## Files to inspect

- `bench.py`
- `bench/runner.py`
- `fixtures/http_server.py`

## Commands to run

```bash
uv run python bench.py prompt --corpus http_server --function run_cgi
uv run python bench.py prompt --file fixtures/http_server.py --function send_head
uv run python bench.py prompt --corpus http_server --function run_cgi --think
```

## Expected output

- Metadata appears before `# --- prompt ---`.
- The source code appears before the task in the default prompt.
- `--think` removes the `/no_think` suffix.

## Student task

Save two prompt outputs, one with default thinking suppression and one with
`--think`. Compare the final prompt lines and describe the only intended
difference.

## Reflection questions

- Why is the source placed before the task?
- What makes this a recall benchmark instead of a coding benchmark?
- Why should students inspect prompts before spending model/API budget?

## Verification checklist

- You can print a prompt with no model server running.
- You can find `prompt_chars` in the metadata.
- You can point to the task suffix in the printed prompt.
