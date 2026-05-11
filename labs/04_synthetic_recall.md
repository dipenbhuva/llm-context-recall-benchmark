# Lab 04: Synthetic Recall Corpus

## Objective

Generate controlled Python corpora for recall experiments.

## Concepts

- Deterministic fixtures
- Corpus size and depth
- Similar-but-unique function bodies

## Files to inspect

- `scripts/generate_synthetic_corpus.py`
- `configs/corpora/synthetic_recall.toml`
- `fixtures/synthetic_recall.py`

## Commands to run

```bash
uv run python scripts/generate_synthetic_corpus.py --functions 10 --body-lines 30 --seed 7 --out /tmp/synth_a.py
uv run python bench.py extract --file /tmp/synth_a.py --all
uv run python scripts/generate_synthetic_corpus.py --functions 10 --body-lines 30 --seed 7 --out /tmp/synth_b.py
shasum -a 256 /tmp/synth_a.py /tmp/synth_b.py
uv run python bench.py extract --corpus synthetic_recall
```

## Expected output

- The generated corpus has extractable `target_000`, `target_001`, and later functions.
- Matching seed and parameters produce the same hash.
- `synthetic_recall` extracts 32 committed functions.

## Student task

Generate a larger corpus with filler lines and explain how it changes function
positions:

```bash
uv run python scripts/generate_synthetic_corpus.py --functions 200 --body-lines 30 --filler-lines 20 --out /tmp/synth_long.py
uv run python bench.py extract --file /tmp/synth_long.py
```

## Reflection questions

- Why does deterministic generation matter for model comparisons?
- Which part of this corpus tests depth rather than code complexity?
- What would make this synthetic corpus too easy?

## Verification checklist

- You can generate and extract a 10-function corpus.
- You can prove deterministic output with a hash.
- You can generate a longer corpus with deeper function positions.
