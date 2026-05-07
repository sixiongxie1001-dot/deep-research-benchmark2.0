#!/usr/bin/env python3
"""Validate the released DEEPWEB-BENCH JSONL tables."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

CASE_FIELDS = {
    "case_id",
    "case_number",
    "title",
    "question_md",
    "reference_answer_md",
    "scoring_rubric_md",
    "entities",
    "dimensions",
}
RESULT_FIELDS = {
    "record_id",
    "case_id",
    "case_number",
    "model",
    "status",
    "overall_pct",
    "verdict",
    "search_count",
    "visit_count",
    "answer_record_id",
    "score_record_id",
}
ANSWER_FIELDS = {
    "record_id",
    "case_id",
    "case_number",
    "model",
    "status",
    "ok",
    "answer_md",
}
SCORE_FIELDS = {
    "record_id",
    "case_id",
    "case_number",
    "model",
    "status",
    "overall_pct",
    "scores",
}


def read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise SystemExit(f"{path}:{line_no}: invalid JSON: {exc}") from exc
    return rows


def require_fields(rows: list[dict], fields: set[str], name: str) -> None:
    for idx, row in enumerate(rows, start=1):
        missing = fields - row.keys()
        if missing:
            raise SystemExit(f"{name} row {idx} missing fields: {sorted(missing)}")


def require_count(name: str, rows: list[dict], expected: int) -> None:
    if len(rows) != expected:
        raise SystemExit(f"expected {expected} {name} rows, found {len(rows)}")


def main() -> None:
    cases = read_jsonl(DATA / "cases.jsonl")
    results = read_jsonl(DATA / "model_results.jsonl")
    answers = read_jsonl(DATA / "model_answers.jsonl")
    score_details = read_jsonl(DATA / "score_details.jsonl")

    require_fields(cases, CASE_FIELDS, "cases")
    require_fields(results, RESULT_FIELDS, "model_results")
    require_fields(answers, ANSWER_FIELDS, "model_answers")
    require_fields(score_details, SCORE_FIELDS, "score_details")

    require_count("cases", cases, 100)
    require_count("model_results", results, 900)
    require_count("model_answers", answers, 900)
    require_count("score_details", score_details, 900)

    case_ids = {row["case_id"] for row in cases}
    for name, rows in [
        ("model_results", results),
        ("model_answers", answers),
        ("score_details", score_details),
    ]:
        unknown = {row["case_id"] for row in rows} - case_ids
        if unknown:
            raise SystemExit(f"{name} contains unknown case ids: {sorted(unknown)}")

    result_ids = {row["record_id"] for row in results}
    answer_ids = {row["record_id"] for row in answers}
    score_ids = {row["record_id"] for row in score_details}
    if result_ids != answer_ids:
        raise SystemExit("model_results and model_answers record ids do not match")
    if result_ids != score_ids:
        raise SystemExit("model_results and score_details record ids do not match")

    scored_rows = sum(1 for row in results if row.get("overall_pct") is not None)
    answers_with_text = sum(1 for row in answers if row.get("answer_md"))
    score_rows = sum(1 for row in score_details if row.get("scores"))
    if scored_rows != 874:
        raise SystemExit(f"expected 874 scored rows, found {scored_rows}")
    if answers_with_text != 874:
        raise SystemExit(f"expected 874 answer texts, found {answers_with_text}")
    if score_rows != 874:
        raise SystemExit(f"expected 874 score-detail rows, found {score_rows}")

    print(f"cases: {len(cases)}")
    print(f"model_results: {len(results)}")
    print(f"model_answers: {len(answers)}")
    print(f"score_details: {len(score_details)}")
    print(f"scored_rows: {scored_rows}")
    print(f"answers_with_text: {answers_with_text}")
    print("validation: ok")


if __name__ == "__main__":
    main()
