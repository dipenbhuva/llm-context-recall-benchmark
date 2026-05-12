#!/usr/bin/env python3
"""Positional recall benchmark — CLI entry.

Tests an LLM's ability to reproduce the first N lines of a named function
inside a large source corpus loaded into context. Measures positional recall,
not just named-entity lookup.

Source selection (extract / run / rescore):
    --corpus NAME      a config under configs/corpora/, or a path to one
    --file PATH        single source file (.js/.mjs/.cjs/.py)

Model selection (run only):
    --model NAME       a config under configs/models/, OR a raw model identifier
                       (raw names get sane defaults; create a config for control)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent
DEFAULT_RESULTS_DIR = REPO_ROOT / "results"


# --- source resolution ---------------------------------------------------


def _resolve_source(args: argparse.Namespace):
    """Return (Source, CorpusConfig|None) from --corpus or --file."""
    from bench.extract import load_source_glob
    from bench.runner import source_from_single_file

    if getattr(args, "corpus", None):
        from bench.config import load_corpus

        corpus = load_corpus(args.corpus)
        src = load_source_glob(corpus.directory, corpus.glob, corpus.limit)
        return src, corpus
    if getattr(args, "file", None):
        return source_from_single_file(Path(args.file)), None
    raise SystemExit("error: pass either --corpus NAME or --file PATH")


# --- extract -------------------------------------------------------------


def cmd_extract(args: argparse.Namespace) -> int:
    from bench.extract import stratified_sample

    source, corpus = _resolve_source(args)

    if args.show:
        match = next((t for t in source.targets if t.name == args.show), None)
        if match is None:
            print(f"function {args.show!r} not found")
            return 1
        loc = f"  ({match.source_path})" if match.source_path else ""
        print(f"# {match.name} — start_line={match.start_line}  body_lines={len(match.body_lines)}{loc}")
        print(f"# -- primary (first {len(match.primary_lines)}) --")
        for i, l in enumerate(match.primary_lines, 1):
            print(f"{i:>3}| {l}")
        if match.bonus_lines:
            print(f"# -- bonus (next {len(match.bonus_lines)}) --")
            for i, l in enumerate(match.bonus_lines, len(match.primary_lines) + 1):
                print(f"{i:>3}| {l}")
        return 0

    total_lines = source.text.count("\n") + 1
    print(
        f"{len(source.targets)} function(s) with ≥20 body lines across "
        f"{len(source.files)} file(s) ({len(source.text):,} chars, {total_lines:,} lines)"
    )
    if source.skipped_duplicates:
        print(f"skipped {len(source.skipped_duplicates)} duplicate function name(s):")
        for dup in source.skipped_duplicates:
            print(
                f"  {dup.name:<40}  kept={dup.kept_path.name}  skipped={dup.skipped_path.name}"
            )
    k = args.k if args.k is not None else (corpus.sample_k if corpus else 16)
    seed = args.seed if args.seed is not None else (corpus.sample_seed if corpus else 42)
    if args.all:
        chosen = source.targets
    else:
        chosen = stratified_sample(source.targets, total_lines, k=k, seed=seed)
        print(f"stratified sample of {len(chosen)}:")
    for t in chosen:
        loc = f"  ({t.source_path.name})" if t.source_path else ""
        print(f"  {t.name:<40}  line={t.start_line:>6}  body_lines={len(t.body_lines)}{loc}")
    return 0


# --- run ------------------------------------------------------------------


def cmd_prompt(args: argparse.Namespace) -> int:
    """Print the exact model prompt for one target without querying a model."""
    from bench.runner import PromptStrategy, build_prompt

    source, corpus = _resolve_source(args)
    match = next((t for t in source.targets if t.name == args.function), None)
    if match is None:
        print(f"function {args.function!r} not found", file=sys.stderr)
        return 1

    suppress_thinking = not args.think
    prompt_strategy = PromptStrategy(
        prompt_order=args.prompt_order,
        anchor_style=args.anchor_style,
        include_signature=args.include_signature,
    )
    prompt = build_prompt(
        target=match,
        text=source.text,
        multi_file=len(source.files) > 1,
        suppress_thinking=suppress_thinking,
        strategy=prompt_strategy,
    )
    source_label = corpus.name if corpus is not None else str(Path(args.file))
    source_path = str(match.source_path) if match.source_path else ""
    print(f"# source: {source_label}")
    print(f"# files: {len(source.files)}")
    print(f"# function: {match.name}")
    print(f"# source_path: {source_path}")
    print(f"# start_line: {match.start_line}")
    print(f"# language: {match.language}")
    print(f"# prompt_chars: {len(prompt)}")
    print(f"# suppress_thinking: {str(suppress_thinking).lower()}")
    print(f"# prompt_order: {prompt_strategy.prompt_order}")
    print(f"# anchor_style: {prompt_strategy.anchor_style}")
    print(f"# include_signature: {str(prompt_strategy.include_signature).lower()}")
    print("# --- prompt ---")
    print(prompt, end="" if prompt.endswith("\n") else "\n")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    from bench.config import auto_dump_path, load_model
    from bench.runner import PromptStrategy, run_benchmark

    source, corpus = _resolve_source(args)

    if not args.model:
        raise SystemExit("error: --model is required (a name in configs/models/, a path, or a raw model id)")
    model, model_from_file = load_model(args.model)
    if not model_from_file:
        print(
            f"  (no model config '{args.model}' found; using as raw model identifier with defaults)",
            file=sys.stderr,
        )

    # CLI overrides — applied on top of whichever source the model came from.
    if args.base_url:
        model.client.base_url = args.base_url
    if args.api_key:
        model.client.api_key = args.api_key
    if args.temperature is not None:
        model.client.temperature = args.temperature
    if args.max_tokens is not None:
        model.client.max_tokens = args.max_tokens
    if args.timeout is not None:
        model.client.timeout = args.timeout
    suppress_thinking = model.suppress_thinking and not args.think

    if corpus is not None:
        k = args.k if args.k is not None else corpus.sample_k
        seed = args.seed if args.seed is not None else corpus.sample_seed
    else:
        k = args.k if args.k is not None else 16
        seed = args.seed if args.seed is not None else 42

    if args.dump:
        dump_path = Path(args.dump)
    elif corpus is not None:
        DEFAULT_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        dump_path = auto_dump_path(corpus, model, DEFAULT_RESULTS_DIR)
    else:
        # --file mode: derive corpus stem from filename
        from bench.config import CorpusConfig

        synthetic_corpus = CorpusConfig(
            name=Path(args.file).stem,
            directory=Path(args.file).parent,
            glob=Path(args.file).name,
            limit=1,
            sample_k=k,
            sample_seed=seed,
        )
        DEFAULT_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        dump_path = auto_dump_path(synthetic_corpus, model, DEFAULT_RESULTS_DIR)

    # Indent-tolerant scoring: take from model config, allow CLI overrides in either direction.
    relax_indent = model.relax_indent
    if args.relax_indent:
        relax_indent = True
    if args.strict_indent:
        relax_indent = False

    fn_filter = args.function if args.function else None
    prompt_strategy = PromptStrategy(
        prompt_order=args.prompt_order,
        anchor_style=args.anchor_style,
        include_signature=args.include_signature,
    )
    scores = run_benchmark(
        source=source,
        cfg=model.client,
        k=k,
        seed=seed,
        dump_path=dump_path,
        function_filter=fn_filter,
        suppress_thinking=suppress_thinking,
        skip_preflight=args.skip_preflight,
        fail_fast_after=None if args.no_fail_fast else args.fail_fast_after,
        relax_indent=relax_indent,
        prompt_strategy=prompt_strategy,
    )
    passed = sum(1 for s in scores if s.passed)
    return 0 if passed == len(scores) else 1


# --- rescore --------------------------------------------------------------


def cmd_rescore(args: argparse.Namespace) -> int:
    """Re-score a previous run's dump without re-querying the model."""
    import json

    from bench.extract import load_source_glob
    from bench.report import render_function, render_summary
    from bench.runner import source_from_single_file
    from bench.scorer import score

    dump = json.loads(Path(args.dump).read_text())
    if args.corpus:
        from bench.config import load_corpus

        corpus = load_corpus(args.corpus)
        source = load_source_glob(corpus.directory, corpus.glob, corpus.limit)
    elif args.file:
        source = source_from_single_file(Path(args.file))
    else:
        files = dump.get("files") or ([dump["source"]] if dump.get("source") else [])
        if len(files) == 1 and Path(files[0]).is_file():
            source = source_from_single_file(Path(files[0]))
        else:
            raise SystemExit(
                "error: dump references a missing or multi-file corpus; "
                "pass --corpus NAME or --file PATH to re-locate it"
            )

    # Honor original dump's relax_indent unless overridden on the CLI.
    relax_indent = bool(dump.get("relax_indent", False))
    if args.relax_indent:
        relax_indent = True
    if args.strict_indent:
        relax_indent = False

    targets = {t.name: t for t in source.targets}
    scores = []
    for r in dump["results"]:
        t = targets.get(r["function"])
        if t is None:
            print(f"skip: {r['function']} not found in source", file=sys.stderr)
            continue
        sc = score(
            t.name, t.primary_lines, t.bonus_lines,
            r.get("response", ""), relax_indent=relax_indent,
        )
        if r.get("error"):
            sc.error = r["error"]
        scores.append(sc)
        print(render_function(sc))
    if relax_indent:
        print("\n(scored with relax_indent=true — leading whitespace ignored on both sides)")
    print(render_summary(scores))
    return 0


# --- compare --------------------------------------------------------------


def cmd_compare(args: argparse.Namespace) -> int:
    """Compare two result dumps without re-scoring or re-querying a model."""
    from bench.compare import index_results, load_result_file, render_comparison

    left = Path(args.left)
    right = Path(args.right)
    left_data = load_result_file(left)
    right_data = load_result_file(right)
    has_common = bool(set(index_results(left_data)) & set(index_results(right_data)))
    report = render_comparison(left, left_data, right, right_data)
    print(report)
    return 0 if has_common else 1


# --- validate -------------------------------------------------------------


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate result dump structure and lineage metadata."""
    import json

    from bench.validate import load_result_file, render_validation, validate_result

    path = Path(args.dump)
    issues = validate_result(load_result_file(path), strict=args.strict)
    print(render_validation(path, issues))
    if args.json:
        json_path = Path(args.json)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(
            json.dumps([issue.as_dict() for issue in issues], indent=2),
            encoding="utf-8",
        )
    return 1 if any(issue.level == "error" for issue in issues) else 0


# --- report ---------------------------------------------------------------


def cmd_report(args: argparse.Namespace) -> int:
    """Generate a Markdown model report from one result dump."""
    import json

    from bench.model_report import ReportPolicy, render_model_report
    from bench.validate import validate_result

    result_path = Path(args.dump)
    result_data = json.loads(result_path.read_text(encoding="utf-8"))
    baseline_path = Path(args.baseline) if args.baseline else None
    baseline_data = (
        json.loads(baseline_path.read_text(encoding="utf-8"))
        if baseline_path is not None
        else None
    )
    policy = ReportPolicy(
        min_recall=args.min_recall,
        max_hallucinated=args.max_hallucinated,
        max_errors=args.max_errors,
        min_functions=args.min_functions,
    )
    report = render_model_report(
        result_path,
        result_data,
        baseline_path=baseline_path,
        baseline_data=baseline_data,
        policy=policy,
    )
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(report, encoding="utf-8")
        print(f"Report written to {out_path}")
    else:
        print(report, end="")

    has_errors = any(issue.level == "error" for issue in validate_result(result_data, strict=True))
    if has_errors and not args.allow_invalid:
        print("strict validation failed; pass --allow-invalid to keep this report", file=sys.stderr)
        return 1
    return 0


# --- diagnose -------------------------------------------------------------


def cmd_diagnose(args: argparse.Namespace) -> int:
    """Classify result failures into a compact taxonomy."""
    from bench.diagnose import load_and_diagnose, render_diagnosis, write_diagnosis_json

    path = Path(args.dump)
    diagnoses = load_and_diagnose(path)
    print(render_diagnosis(path, diagnoses))
    if args.json:
        write_diagnosis_json(Path(args.json), diagnoses)
    return 0


# --- argparse -------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    # --- extract ------------------------------------------------------------
    p_ex = sub.add_parser("extract", help="list functions the extractor would test")
    src_grp = p_ex.add_mutually_exclusive_group()
    src_grp.add_argument("--corpus", help="corpus config name (configs/corpora/<name>.toml) or path")
    src_grp.add_argument("--file", help="single source file")
    p_ex.add_argument("-k", type=int, default=None, help="override corpus sample.k")
    p_ex.add_argument("--seed", type=int, default=None, help="override corpus sample.seed")
    p_ex.add_argument("--all", action="store_true", help="list every extracted function, not a sample")
    p_ex.add_argument("--show", metavar="NAME", help="print expected primary+bonus lines for one function")
    p_ex.set_defaults(func=cmd_extract)

    # --- prompt -------------------------------------------------------------
    p_prompt = sub.add_parser("prompt", help="print the exact prompt for one target without calling a model")
    src_grp = p_prompt.add_mutually_exclusive_group()
    src_grp.add_argument("--corpus", help="corpus config name (configs/corpora/<name>.toml) or path")
    src_grp.add_argument("--file", help="single source file")
    p_prompt.add_argument("--function", required=True, help="target function name")
    p_prompt.add_argument(
        "--prompt-order",
        choices=("file-first", "task-first"),
        default="file-first",
        help="where to place the task relative to the source (default: file-first)",
    )
    p_prompt.add_argument(
        "--anchor-style",
        choices=("function-name", "line-number"),
        default="function-name",
        help="how to identify the target span (default: function-name)",
    )
    p_prompt.add_argument(
        "--include-signature",
        action="store_true",
        help="ask for the function signature before the body lines",
    )
    thinking_grp = p_prompt.add_mutually_exclusive_group()
    thinking_grp.add_argument("--think", action="store_true", help="omit the /no_think suffix")
    thinking_grp.add_argument("--no-think", action="store_false", dest="think", help="append the /no_think suffix")
    p_prompt.set_defaults(func=cmd_prompt, think=False)

    # --- run ----------------------------------------------------------------
    p_run = sub.add_parser("run", help="run the benchmark against an OpenAI-compatible endpoint")
    src_grp = p_run.add_mutually_exclusive_group()
    src_grp.add_argument("--corpus", help="corpus config name (configs/corpora/<name>.toml) or path")
    src_grp.add_argument("--file", help="single source file")
    p_run.add_argument(
        "--model", required=True,
        help="model config name (configs/models/<name>.toml), a path, or a raw model identifier",
    )
    p_run.add_argument("--base-url", default=None, help="overrides model config")
    p_run.add_argument("--api-key", default=None)
    p_run.add_argument("--temperature", type=float, default=None)
    p_run.add_argument("--max-tokens", type=int, default=None)
    p_run.add_argument("--timeout", type=float, default=None)
    p_run.add_argument("-k", type=int, default=None, help="overrides corpus.sample.k")
    p_run.add_argument("--seed", type=int, default=None)
    p_run.add_argument(
        "--dump", default=None,
        help="JSON path for full results (default: results/<corpus>__<model>.json)",
    )
    p_run.add_argument("--function", action="append", help="repeatable; overrides sampling")
    p_run.add_argument(
        "--prompt-order",
        choices=("file-first", "task-first"),
        default="file-first",
        help="where to place the task relative to the source (default: file-first)",
    )
    p_run.add_argument(
        "--anchor-style",
        choices=("function-name", "line-number"),
        default="function-name",
        help="how to identify the target span (default: function-name)",
    )
    p_run.add_argument(
        "--include-signature",
        action="store_true",
        help="ask for the function signature before the body lines",
    )
    p_run.add_argument("--think", action="store_true", help="allow chain-of-thought (default: suppress)")
    p_run.add_argument(
        "--skip-preflight", action="store_true",
        help="skip the context-fit pre-flight probe (not recommended)",
    )
    p_run.add_argument(
        "--fail-fast-after", type=int, default=2, metavar="N",
        help="abort the run after N consecutive ERROR results (default: 2)",
    )
    p_run.add_argument(
        "--no-fail-fast", action="store_true",
        help="disable fail-fast; run every query even if they're all erroring",
    )
    p_run.add_argument(
        "--relax-indent", action="store_true",
        help="ignore leading whitespace when matching (overrides model config to true)",
    )
    p_run.add_argument(
        "--strict-indent", action="store_true",
        help="enforce verbatim indentation (overrides model config to false)",
    )
    p_run.set_defaults(func=cmd_run)

    # --- rescore ------------------------------------------------------------
    p_rs = sub.add_parser("rescore", help="re-score a previous --dump without re-querying")
    p_rs.add_argument("dump", help="path to JSON dump from a prior `run`")
    src_grp = p_rs.add_mutually_exclusive_group()
    src_grp.add_argument("--corpus", help="re-locate corpus via this config")
    src_grp.add_argument("--file", help="re-locate corpus from a single file")
    p_rs.add_argument(
        "--relax-indent", action="store_true",
        help="ignore leading whitespace when matching (overrides dump's setting)",
    )
    p_rs.add_argument(
        "--strict-indent", action="store_true",
        help="enforce verbatim indentation (overrides dump's setting)",
    )
    p_rs.set_defaults(func=cmd_rescore)

    # --- compare -----------------------------------------------------------
    p_cmp = sub.add_parser("compare", help="compare two benchmark result JSON dumps")
    p_cmp.add_argument("left", help="baseline result JSON")
    p_cmp.add_argument("right", help="candidate result JSON")
    p_cmp.set_defaults(func=cmd_compare)

    # --- validate ----------------------------------------------------------
    p_val = sub.add_parser("validate", help="validate a benchmark result JSON dump")
    p_val.add_argument("dump", help="result JSON to validate")
    p_val.add_argument(
        "--strict",
        action="store_true",
        help="require schema_version=2 and full lineage metadata",
    )
    p_val.add_argument("--json", help="write validation issues as JSON")
    p_val.set_defaults(func=cmd_validate)

    # --- report ------------------------------------------------------------
    p_report = sub.add_parser("report", help="generate a Markdown model report from result JSON")
    p_report.add_argument("dump", help="candidate result JSON")
    p_report.add_argument("--baseline", help="optional baseline result JSON for comparison")
    p_report.add_argument("--out", help="write Markdown report to this path")
    p_report.add_argument("--min-recall", type=float, default=0.80)
    p_report.add_argument("--max-hallucinated", type=int, default=0)
    p_report.add_argument("--max-errors", type=int, default=0)
    p_report.add_argument("--min-functions", type=int, default=8)
    p_report.add_argument(
        "--allow-invalid",
        action="store_true",
        help="return success even if strict result validation fails",
    )
    p_report.set_defaults(func=cmd_report)

    # --- diagnose ----------------------------------------------------------
    p_diag = sub.add_parser("diagnose", help="classify result failures by failure mode")
    p_diag.add_argument("dump", help="result JSON to diagnose")
    p_diag.add_argument("--json", help="write diagnosis entries as JSON")
    p_diag.set_defaults(func=cmd_diagnose)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
