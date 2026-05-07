#!/usr/bin/env python3
"""Run one OpenAI-compatible model on one DEEPWEB-BENCH case with benchmark tools."""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

SYSTEM_PROMPT = """You are taking DEEPWEB-BENCH, a deep-research benchmark.

Use the provided web_search, page_visit, and pdf_fetch tools. Do not answer from memory.
For each Q1-Q8, research the relevant entities, cite concrete source URLs, and provide
units, derivations, assumptions, and uncertainty notes. Return a final Markdown answer.
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the public web and return candidate pages.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "page_visit",
            "description": "Fetch and extract text from a web page URL.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "pdf_fetch",
            "description": "Fetch and extract text from a PDF URL when text extraction is available.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"],
            },
        },
    },
]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def request_json(url: str, headers: dict[str, str], payload: dict[str, Any], timeout: int) -> dict[str, Any]:
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
        raise RuntimeError(f"HTTP {exc.code}: {body[:2000]}") from exc


def serper_search(query: str, api_key: str, timeout: int) -> dict[str, Any]:
    return request_json(
        "https://google.serper.dev/search",
        {"X-API-KEY": api_key},
        {"q": query, "num": 10},
        timeout,
    )


def serper_scrape(url: str, api_key: str, timeout: int) -> dict[str, Any]:
    return request_json(
        "https://scrape.serper.dev",
        {"X-API-KEY": api_key},
        {"url": url},
        timeout,
    )


def compact_tool_result(name: str, data: dict[str, Any], char_limit: int) -> str:
    if name == "web_search":
        rows = []
        for item in data.get("organic", [])[:10]:
            rows.append(
                {
                    "title": item.get("title"),
                    "url": item.get("link"),
                    "snippet": item.get("snippet"),
                }
            )
        return json.dumps(rows, ensure_ascii=False)[:char_limit]
    text = data.get("text") or data.get("markdown") or data.get("content") or json.dumps(data, ensure_ascii=False)
    return str(text)[:char_limit]


def call_model(args: argparse.Namespace, messages: list[dict[str, Any]]) -> dict[str, Any]:
    api_key = os.getenv(args.api_key_env)
    if not api_key:
        raise SystemExit(f"missing model API key env var: {args.api_key_env}")
    return request_json(
        args.api_base.rstrip("/") + "/chat/completions",
        {"Authorization": f"Bearer {api_key}"},
        {
            "model": args.model,
            "temperature": args.temperature,
            "max_tokens": args.max_tokens,
            "messages": messages,
            "tools": TOOLS,
            "tool_choice": "auto",
        },
        args.timeout,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--api-base", default=os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1"))
    parser.add_argument("--api-key-env", default="OPENAI_API_KEY")
    parser.add_argument("--serper-key-env", default="SERPER_API_KEY")
    parser.add_argument("--max-tool-rounds", type=int, default=30)
    parser.add_argument("--max-tokens", type=int, default=32000)
    parser.add_argument("--tool-result-char-limit", type=int, default=20000)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--trace", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    serper_key = os.getenv(args.serper_key_env)
    if not serper_key:
        raise SystemExit(f"missing search/scrape API key env var: {args.serper_key_env}")

    cases = {row["case_id"]: row for row in read_jsonl(DATA / "cases.jsonl")}
    if args.case_id not in cases:
        raise SystemExit(f"unknown case id: {args.case_id}")
    case = cases[args.case_id]

    user_prompt = (
        f"Benchmark case: {args.case_id}\n\n"
        "Question:\n```markdown\n"
        f"{case['question_md']}\n"
        "```\n\nOutput only the final answer in Markdown."
    )
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    args.trace.parent.mkdir(parents=True, exist_ok=True)
    with args.trace.open("w", encoding="utf-8") as trace:
        start = time.time()
        final_text = ""
        for round_idx in range(args.max_tool_rounds + 1):
            response = call_model(args, messages)
            msg = response["choices"][0]["message"]
            trace.write(json.dumps({"type": "model", "round": round_idx, "message": msg}, ensure_ascii=False) + "\n")
            tool_calls = msg.get("tool_calls") or []
            if not tool_calls:
                final_text = msg.get("content") or ""
                break
            messages.append(msg)
            for tool_call in tool_calls:
                fn = tool_call.get("function") or {}
                name = fn.get("name")
                try:
                    params = json.loads(fn.get("arguments") or "{}")
                except json.JSONDecodeError:
                    params = {}
                try:
                    if name == "web_search":
                        raw = serper_search(str(params.get("query", "")), serper_key, min(args.timeout, 120))
                    elif name in {"page_visit", "pdf_fetch"}:
                        raw = serper_scrape(str(params.get("url", "")), serper_key, min(args.timeout, 120))
                    else:
                        raw = {"error": f"unknown tool {name}"}
                except Exception as exc:
                    raw = {"error": str(exc)}
                content = compact_tool_result(str(name), raw, args.tool_result_char_limit)
                trace.write(
                    json.dumps(
                        {"type": "tool", "round": round_idx, "name": name, "params": params, "content": content[:1000]},
                        ensure_ascii=False,
                    )
                    + "\n"
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "name": name,
                        "content": content,
                    }
                )
        else:
            final_text = ""

        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(final_text, encoding="utf-8")
        trace.write(
            json.dumps(
                {"type": "summary", "elapsed_s": round(time.time() - start, 1), "answer_chars": len(final_text)},
                ensure_ascii=False,
            )
            + "\n"
        )
    print(f"wrote {args.output} ({len(final_text)} chars)")


if __name__ == "__main__":
    main()
