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

For a full HTTP-path check without a real model, start the deterministic fake
OpenAI-compatible server:

```bash
uv run python tests/fake_openai_server.py --port 8765 --response-file fixtures/responses/send_head_perfect.txt
```

To rerun the deterministic lab runtime checks from one command:

```bash
uv run python scripts/run_lab_runtime_checks.py --json /tmp/lab-runtime-report.json
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
10. `10_result_contract_validation.md` — validate result JSON contracts.

Labs 1, 2, 4, 6, 7, 8, and 10 can run without any model server. Labs 3, 5,
and 9 include optional live-model sections.
