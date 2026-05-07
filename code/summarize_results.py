#!/usr/bin/env python3
"""Print a compact model leaderboard from model_results.jsonl."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "data" / "model_results.jsonl"


def main() -> None:
    by_model: dict[str, list[float]] = defaultdict(list)
    with RESULTS.open(encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            if row.get("overall_pct") is not None:
                by_model[row["model"]].append(float(row["overall_pct"]))

    rows = []
    for model, scores in by_model.items():
        rows.append((sum(scores) / len(scores), len(scores), model))

    print("| model | scored | average_pct |")
    print("| --- | ---: | ---: |")
    for avg, n, model in sorted(rows, reverse=True):
        print(f"| {model} | {n} | {avg:.3f} |")


if __name__ == "__main__":
    main()
