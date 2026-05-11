# Lab 06: Duplicate Function Names

## Objective

Understand why duplicate function names make function-name recall ambiguous.

## Concepts

- Multi-file corpus concatenation
- First-occurrence deduplication
- Dataset hygiene

## Files to inspect

- `bench/extract.py`
- `fixtures/multi_file/a.py`
- `fixtures/multi_file/b.py`
- `configs/corpora/multi_file_duplicates.toml`

## Commands to run

```bash
uv run python bench.py extract --corpus multi_file_duplicates --all
uv run python bench.py extract --corpus multi_file_duplicates --show repeated_name
uv run python bench.py extract --corpus http_server --all
```

## Expected output

- `multi_file_duplicates` reports one skipped duplicate function name.
- `repeated_name` is kept from `a.py`.
- `http_server` has no duplicate warning.

## Student task

Explain why evaluating both `repeated_name` functions by name would be invalid.
Propose two ways to make duplicate targets unambiguous.

## Reflection questions

- Is silently skipping duplicates acceptable in production evals?
- When should the benchmark fail instead of warning?
- How does file qualification affect prompt clarity?

## Verification checklist

- You can show the duplicate warning.
- You can show the kept first occurrence.
- You can explain why duplicate names are a benchmark data issue.
