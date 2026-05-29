#!/usr/bin/env bash
# eval/lib/harness_fresh.sh — EverMemBench harness wrapper with auto-purge of prior results.
#
# Lesson codified: [[evermembench-eval-gotchas-2026-05-28]]
#   EverMemBench harness silently resumes from answer_results_<batch>.json if it
#   exists in the results dir. This caused Phase G batch 004 to short-circuit the
#   answer stage and reuse stale Phase D answers — inflating scores by ~3-6pp
#   depending on batch alignment. The fix is to unconditionally delete both
#   answer_results and evaluation_results before each run.
#
# Usage (source in any run-batch-*.sh):
#
#   source "$(dirname "$0")/../lib/harness_fresh.sh"
#
#   harness_run_fresh \
#       --batch     "004" \
#       --adapter   "nox_mem" \
#       --eval-dir  "$EVAL" \
#       --stages    "search answer evaluate" \
#       [-- extra args passed to eval.cli]
#
# The function deletes stale result files, then delegates to `python -m eval.cli`
# with the provided arguments. Must be called from inside the harness root
# (where `eval/cli.py` lives).

set -euo pipefail

# harness_run_fresh [options] [-- extra_args...]
#
# Options:
#   --batch    BATCH      Batch identifier, e.g. "004" (required)
#   --adapter  ADAPTER    System name, e.g. "nox_mem" (required)
#   --eval-dir EVAL_DIR   Path to EverMemBench root (required)
#   --stages   STAGES     Space-separated stage list: "search answer evaluate"
#   --dataset  DATASET    Dataset path relative to EVAL_DIR
#   --qa       QA         QA file path relative to EVAL_DIR
#   --user-id  USER_ID    User id for harness (defaults to BATCH)
#   --top-k    TOP_K      Top-k for search stage (default: 20)
#   -- ...                Extra args forwarded verbatim to eval.cli
#
# Env:
#   HARNESS_DRY_RUN=1   Print what would be deleted + the command, but do not execute.
harness_run_fresh() {
    local batch=""
    local adapter=""
    local eval_dir=""
    local stages="search answer evaluate"
    local dataset=""
    local qa=""
    local user_id=""
    local top_k="20"
    local extra_args=()

    # Parse named options
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --batch)    batch="$2";    shift 2 ;;
            --adapter)  adapter="$2";  shift 2 ;;
            --eval-dir) eval_dir="$2"; shift 2 ;;
            --stages)   stages="$2";   shift 2 ;;
            --dataset)  dataset="$2";  shift 2 ;;
            --qa)       qa="$2";       shift 2 ;;
            --user-id)  user_id="$2";  shift 2 ;;
            --top-k)    top_k="$2";    shift 2 ;;
            --)         shift; extra_args=("$@"); break ;;
            *)
                echo "[harness_fresh] ERROR: unknown option '$1'" >&2
                return 1
                ;;
        esac
    done

    : "${batch:?harness_run_fresh: --batch required}"
    : "${adapter:?harness_run_fresh: --adapter required}"
    : "${eval_dir:?harness_run_fresh: --eval-dir required}"

    user_id="${user_id:-$batch}"
    dataset="${dataset:-dataset/$batch/dialogue.json}"
    qa="${qa:-dataset/$batch/qa_$batch.json}"

    local results_dir="$eval_dir/eval/results/$adapter"
    local answer_file="$results_dir/answer_results_${batch}.json"
    local eval_file="$results_dir/evaluation_results_${batch}.json"
    local search_file="$results_dir/search_results_${batch}.json"

    # ── Step 1: purge stale results ───────────────────────────────────────────
    # Per [[evermembench-eval-gotchas-2026-05-28]]: harness resumes silently
    # from answer_results_<batch>.json. Delete BOTH files unconditionally so
    # every run starts from scratch.
    echo "[harness_fresh] purging stale results for batch=${batch} adapter=${adapter}"
    if [ "${HARNESS_DRY_RUN:-0}" = "1" ]; then
        echo "[harness_fresh] DRY_RUN: would delete: $answer_file $eval_file $search_file"
    else
        rm -f "$answer_file" "$eval_file" "$search_file"
        echo "[harness_fresh] deleted (or already absent): answer / evaluation / search results"
    fi

    # ── Step 2: build eval.cli args ───────────────────────────────────────────
    local cli_args=(
        "--dataset" "$dataset"
        "--qa"      "$qa"
        "--system"  "$adapter"
        "--user-id" "$user_id"
        "--stages"  $stages        # word-split intentional (space-separated list)
        "--top-k"   "$top_k"
    )
    if [ "${#extra_args[@]}" -gt 0 ]; then
        cli_args+=("${extra_args[@]}")
    fi

    # ── Step 3: run harness ───────────────────────────────────────────────────
    echo "[harness_fresh] running: python -m eval.cli ${cli_args[*]}"
    if [ "${HARNESS_DRY_RUN:-0}" = "1" ]; then
        echo "[harness_fresh] DRY_RUN: skipping actual eval.cli invocation"
        return 0
    fi

    (cd "$eval_dir" && python -m eval.cli "${cli_args[@]}")
}
