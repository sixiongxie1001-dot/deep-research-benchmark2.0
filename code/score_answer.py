#!/usr/bin/env python3
"""Rerun the rubric-based grading prompt for one DEEPWEB-BENCH answer."""

from __future__ import annotations

import argparse
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def post_json(url: str, headers: dict[str, str], payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={**headers, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code}: {body[:2000]}") from exc


def extract_json(text: str) -> dict[str, Any]:
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        raise SystemExit("grader response did not contain JSON")
    return json.loads(match.group(0))


def build_prompt(case: dict[str, Any], answer: str) -> str:
    return f"""You are scoring one DEEPWEB-BENCH answer.

Use only the provided reference answer and rubric. Return strict JSON with:
- ok: boolean
- scores: object keyed by Q1...Q8; each value has per_entity, avg, rationale
- overall_pct: number from 0 to 100
- verdict: one of pass, too_easy, too_hard

Question:
```markdown
{case["question_md"]}
```

Reference answer:
```markdown
{case["reference_answer_md"]}
```

Scoring rubric:
```markdown
{case["scoring_rubric_md"]}
```

Candidate model answer:
```markdown
{answer}
```
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--model-answer-id", help="record_id in data/model_answers.jsonl")
    parser.add_argument("--answer-file", type=Path, help="External markdown answer to score")
    parser.add_argument("--api-base", default=os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1"))
    parser.add_argument("--api-key-env", default="OPENAI_API_KEY")
    parser.add_argument("--model", required=True)
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    api_key = os.getenv(args.api_key_env)
    if not api_key:
        raise SystemExit(f"missing API key env var: {args.api_key_env}")

    cases = {row["case_id"]: row for row in read_jsonl(DATA / "cases.jsonl")}
    if args.case_id not in cases:
        raise SystemExit(f"unknown case id: {args.case_id}")

    if args.answer_file:
        answer = args.answer_file.read_text(encoding="utf-8")
    else:
        if not args.model_answer_id:
            raise SystemExit("provide --model-answer-id or --answer-file")
        answers = {row["record_id"]: row for row in read_jsonl(DATA / "model_answers.jsonl")}
        if args.model_answer_id not in answers:
            raise SystemExit(f"unknown answer id: {args.model_answer_id}")
        answer = answers[args.model_answer_id].get("answer_md") or ""
        if not answer.strip():
            raise SystemExit(f"answer id has no released answer text: {args.model_answer_id}")

    payload = {
        "model": args.model,
        "temperature": 0,
        "messages": [{"role": "user", "content": build_prompt(cases[args.case_id], answer)}],
    }
    data = post_json(
        args.api_base.rstrip("/") + "/chat/completions",
        {"Authorization": f"Bearer {api_key}"},
        payload,
        args.timeout,
    )
    content = data["choices"][0]["message"]["content"]
    result = extract_json(content)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
