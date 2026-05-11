# Lab 01: Ground Truth Extraction

## Objective

Understand how the benchmark decides which source lines a model must recall.

## Concepts

- Function body extraction
- Primary lines vs bonus lines
- Why exact evals depend on trustworthy ground truth

## Files to inspect

- `bench/extract.py`
- `bench.py`
- `fixtures/http_server.py`

## Commands to run

```bash
uv run python bench.py extract --corpus http_server
uv run python bench.py extract --corpus http_server --all
uv run python bench.py extract --corpus http_server --show send_head
```

## Expected output

- `http_server` reports 11 extractable functions.
- `send_head` shows 20 primary lines and bonus lines after them.
- The function signature is not part of the primary body.

## Student task

Pick two functions from the extractor output and explain why each starts at the
reported line. Identify the first primary line and the first bonus line.

## Reflection questions

- What would happen if the extractor included the signature line?
- Why does the benchmark require at least 20 body lines?
- Which extractor behavior could make model scores unfair?

## Verification checklist

- You can show `send_head` ground truth.
- You can explain primary vs bonus lines.
- You can name the file and line where extraction logic lives.
