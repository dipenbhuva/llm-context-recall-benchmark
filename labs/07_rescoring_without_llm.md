# Lab 07: Rescoring Without an LLM

## Objective

Learn the scorer using canned model responses instead of a live model.

## Concepts

- Primary matches
- Hallucinated lines
- Truncation
- Strict vs relaxed indentation

## Files to inspect

- `bench/scorer.py`
- `bench/report.py`
- `fixtures/responses/`
- `fixtures/results/send_head_fake_results.json`

## Commands to run

```bash
uv run python bench.py rescore fixtures/results/send_head_fake_results.json --file fixtures/http_server.py
uv run python bench.py rescore fixtures/results/send_head_fake_results.json --file fixtures/http_server.py --relax-indent
uv run python bench.py diagnose fixtures/results/send_head_fake_results.json
uv run python bench.py rescore fixtures/results/send_head_fake_results.json --file fixtures/http_server.py >/tmp/rescore.txt
rg "SUMMARY|send_head" /tmp/rescore.txt
```

## Expected output

- Perfect response scores `20/20`.
- Truncated response scores `5/20`.
- Hallucinated response reports hallucinated lines.
- Relaxed indentation improves the indentation-changed case.
- Diagnosis output groups the fake cases into failure categories.

## Student task

Open each file in `fixtures/responses/` and predict the score before running
`rescore`. Compare your prediction with the terminal output.
Then run `diagnose` and decide which category is most concerning for a coding
assistant.

## Reflection questions

- Why is indentation strict by default?
- When is relaxed scoring fair?
- Why are API errors reported separately from recall failures?

## Verification checklist

- You can rescore without a model server.
- You can explain the pass threshold.
- You can identify which fake response hallucinated.
- You can map each fake response to a failure category.
