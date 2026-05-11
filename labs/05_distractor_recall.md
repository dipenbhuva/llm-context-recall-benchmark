# Lab 05: Distractor Recall

## Objective

Create near-duplicate functions to test whether a model recalls the correct
span or copies from a similar sibling.

## Concepts

- Wrong-span retrieval
- Unique markers
- Near-duplicate function groups

## Files to inspect

- `scripts/generate_synthetic_corpus.py`
- `configs/corpora/synthetic_distractors.toml`
- `fixtures/synthetic_distractors.py`

## Commands to run

```bash
uv run python scripts/generate_synthetic_corpus.py --functions 40 --body-lines 30 --distractor-groups 8 --near-duplicate-rate 0.8 --out /tmp/distractors.py
uv run python bench.py extract --file /tmp/distractors.py --all
rg "UNIQUE_MARKER" /tmp/distractors.py
uv run python bench.py extract --corpus synthetic_distractors
```

Optional live-model run:

```bash
uv run python bench.py run --corpus synthetic_distractors --model qwen36-35b -k 16
```

## Expected output

- Function names are grouped, for example `target_g000_m000`.
- Each function has a unique marker.
- Functions in the same group share many repeated update lines.

## Student task

Pick one group and compare two sibling functions. Identify which lines are
shared and which line proves the correct function was recalled.

## Reflection questions

- Why are near-duplicates harder than random filler?
- How would a wrong sibling show up in the scorer?
- Why is this closer to production code than a random needle?

## Verification checklist

- You can generate a distractor corpus.
- You can list unique markers.
- Optional: you can identify sibling leakage in a model response.
