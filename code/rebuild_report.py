#!/usr/bin/env python3
"""Rebuild a compact Markdown report from the released JSONL tables."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def pct(value: float | None) -> str:
    return "" if value is None else f"{value:.3f}%"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("rebuilt_report.md"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cases = read_jsonl(DATA / "cases.jsonl")
    results = read_jsonl(DATA / "model_results.jsonl")
    scored = [row for row in results if row.get("overall_pct") is not None]

    by_model: dict[str, list[dict]] = {}
    for row in scored:
        by_model.setdefault(row["model"], []).append(row)

    lines = [
        "# DEEPWEB-BENCH Rebuilt Report",
        "",
        f"- Cases: {len(cases)}",
        f"- Model-case pairs: {len(results)}",
        f"- Scored pairs: {len(scored)}",
        "",
        "## Leaderboard",
        "",
        "| # | Model | Scored | Average score | Pass count | Average tool calls |",
        "| ---: | --- | ---: | ---: | ---: | ---: |",
    ]

    leaderboard = []
    for model, rows in by_model.items():
        avg = sum(row["overall_pct"] for row in rows) / len(rows)
        pass_count = sum(1 for row in rows if row.get("verdict") == "pass")
        tool_rows = [row for row in rows if row.get("tool_call_count") is not None]
        avg_tools = sum(row["tool_call_count"] for row in tool_rows) / len(tool_rows) if tool_rows else None
        leaderboard.append((avg, model, len(rows), pass_count, avg_tools))

    for rank, (avg, model, n_rows, pass_count, avg_tools) in enumerate(sorted(leaderboard, reverse=True), 1):
        lines.append(
            f"| {rank} | `{model}` | {n_rows} | {pct(avg)} | {pass_count} | "
            f"{avg_tools:.1f} |" if avg_tools is not None else f"| {rank} | `{model}` | {n_rows} | {pct(avg)} | {pass_count} |  |"
        )

    lines.extend(["", "## Status Counts", "", "| Status | Count |", "| --- | ---: |"])
    for status, count in Counter(row["status"] for row in results).most_common():
        lines.append(f"| {status} | {count} |")

    lines.extend(["", "## Verdict Counts", "", "| Verdict | Count |", "| --- | ---: |"])
    for verdict, count in Counter(row.get("verdict") or "missing" for row in results).most_common():
        lines.append(f"| {verdict} | {count} |")

    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
