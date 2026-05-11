# Lab 08: Result Lineage

## Objective

Inspect result metadata that makes benchmark runs reproducible and comparable.

## Concepts

- Run IDs
- Corpus checksums
- Prompt template IDs
- Selected function order

## Files to inspect

- `bench/runner.py`
- `fixtures/results/send_head_fake_results.json`
- Any JSON written under `results/` or `/tmp`

## Commands to run

This command intentionally points at a closed local port. It records an errored
result but still writes metadata, so no model server is required.

```bash
uv run python bench.py run --file fixtures/http_server.py --model fake-model \
  --base-url http://127.0.0.1:9 --function send_head \
  --skip-preflight --fail-fast-after 1 --dump /tmp/lineage.json || true
python -m json.tool /tmp/lineage.json | sed -n '1,80p'
```

## Expected output

The JSON contains:

- `schema_version`
- `run_id`
- `created_at`
- `git_sha`
- `python_version`
- `corpus_sha256`
- `prompt_template_id`
- `sample_k`
- `sample_seed`
- `selected_functions`

## Student task

Run the command twice. Compare `run_id` and `corpus_sha256`. Explain which
field should change and which should stay stable.

## Reflection questions

- Which fields prove two runs used the same corpus?
- Which fields prove two runs used the same prompt strategy?
- What metadata would you add for hosted API cost tracking?

## Verification checklist

- You can write a result JSON without a working model server.
- You can find lineage fields in the JSON.
- You can explain why checksum stability matters.
