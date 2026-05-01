#!/usr/bin/env python3
"""Summarize Trialogue manual eval scorecards.

Usage:
    python evals/scripts/summarize_scorecard.py evals/scorecards/manual_eval_2026_05.jsonl
"""

import json
import sys
from collections import Counter
from pathlib import Path


def load_rows(path: str):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def count_true(rows, field: str) -> int:
    return sum(1 for row in rows if row.get(field) is True)


def main(path: str) -> None:
    rows = load_rows(path)
    prompts = {row.get("prompt", "") for row in rows}

    print(f"rows: {len(rows)}")
    print(f"exact unique prompts: {len(prompts)}")
    print("note: rows may include reruns/regression variants; do not treat this as an independent benchmark count")

    print("\nby canonical recommended_mode:")
    for key, value in Counter(row.get("recommended_mode") for row in rows).most_common():
        print(f"  {key}: {value}")

    print("\nby detailed recommended_mode:")
    for key, value in Counter(row.get("recommended_mode_detail") for row in rows).most_common():
        print(f"  {key}: {value}")

    print("\nby outcome:")
    for key, value in Counter(row.get("outcome") for row in rows).most_common():
        print(f"  {key}: {value}")

    print("\nflags:")
    print(f"  critic_missed_critical_issue: {count_true(rows, 'critic_missed_critical_issue')}")
    print(f"  judge_introduced_error: {count_true(rows, 'judge_introduced_error')}")
    print(f"  judge_preserved_error: {count_true(rows, 'judge_preserved_error')}")
    print(f"  needs_source_or_verifier: {count_true(rows, 'needs_source_or_verifier')}")
    print(f"  worth_full_trialogue: {count_true(rows, 'worth_full_trialogue')}")

    print("\njudge-introduced error details:")
    for row in rows:
        if row.get("judge_introduced_error"):
            detail = row.get("judge_introduced_error_detail") or "true"
            print(f"  {row['id']}: {detail}")

    print("\nsource/verifier-needed details:")
    for row in rows:
        if row.get("needs_source_or_verifier"):
            detail = row.get("needs_source_or_verifier_detail") or row.get("recommended_mode")
            print(f"  {row['id']}: {detail}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: summarize_scorecard.py <scorecard.jsonl>", file=sys.stderr)
        raise SystemExit(2)
    main(sys.argv[1])
