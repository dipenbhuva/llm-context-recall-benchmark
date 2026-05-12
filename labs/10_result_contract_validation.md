# Lab 10: Result Contract Validation

## Objective

Validate benchmark result JSON before using it in dashboards, comparison
reports, or deployment decisions.

## Concepts

- Result schema contracts
- Strict lineage metadata
- Legacy result compatibility
- CI gates for evaluation artifacts

## Files to inspect

- `bench/validate.py`
- `bench.py`
- `fixtures/results/compare_candidate.json`
- `fixtures/results/send_head_fake_results.json`

## Commands to run

```bash
uv run python bench.py validate fixtures/results/compare_candidate.json --strict
uv run python bench.py validate fixtures/results/send_head_fake_results.json
uv run python bench.py validate fixtures/results/send_head_fake_results.json --strict || true
```

Optional JSON report:

```bash
uv run python bench.py validate fixtures/results/send_head_fake_results.json --json /tmp/validation-issues.json
python -m json.tool /tmp/validation-issues.json
```

## Expected output

- The schema-v2 fixture passes strict validation.
- The legacy fake-response fixture passes default validation with a warning.
- The legacy fake-response fixture fails strict validation because it lacks
  lineage metadata.
- The JSON report lists validation issues with `level`, `path`, and `message`.

## Student task

Run validation on one fixture result and one result produced by your own model
or the fake OpenAI server. Decide whether each artifact is acceptable for a
production model report.

## Reflection questions

- Which fields make a benchmark run reproducible?
- Why should dashboards accept legacy results but CI require strict metadata?
- What could go wrong if malformed result JSON is silently visualized?

## Verification checklist

- You can run strict validation on a schema-v2 result.
- You can explain the difference between warnings and errors.
- You can produce a JSON validation report for CI or review.
