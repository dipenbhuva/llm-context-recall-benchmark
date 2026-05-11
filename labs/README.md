# AI Accelerator Code-Recall Labs

These labs teach production-ready AI evaluation through this repository's core
benchmark: put source code in an LLM context, ask for a named function body,
and measure exact recall.

## Setup

```bash
uv venv --python 3.11
uv sync --dev
uv run pytest
```

## Lab Sequence

1. `01_ground_truth_extraction.md` — inspect extracted functions and expected lines.
2. `02_prompt_inspection.md` — inspect the exact prompt before calling a model.
3. `03_prompt_strategy_ab_test.md` — compare prompt order and anchor styles.
4. `04_synthetic_recall.md` — generate controlled recall corpora.
5. `05_distractor_recall.md` — create near-duplicate functions and analyze wrong-span risk.
6. `06_duplicate_names.md` — inspect multi-file duplicate-name ambiguity.
7. `07_rescoring_without_llm.md` — learn scoring from fake responses.
8. `08_result_lineage.md` — inspect reproducibility metadata in result JSON.
9. `09_final_model_report.md` — write a model comparison report.

Labs 1, 2, 4, 6, 7, and 8 can run without any model server. Labs 3, 5, and 9
include optional live-model sections.
