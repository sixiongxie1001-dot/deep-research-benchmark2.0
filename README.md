# DEEPWEB-BENCH Evaluation Code

This repository contains only the public evaluation utilities for DEEPWEB-BENCH.
It does not contain benchmark-generation code, internal pipelines, prompts, raw
generation artifacts, private traces, or released dataset records.

The released dataset files are hosted separately at:

https://huggingface.co/datasets/deepweb-bench-anon/deepweb-bench

## Contents

- `code/validate_release.py`: validate downloaded release JSONL files.
- `code/summarize_results.py`: rebuild the compact leaderboard.
- `code/rebuild_report.py`: rebuild a Markdown summary report.
- `code/score_answer.py`: rerun the rubric-based grader for one answer.
- `code/run_openai_compatible_agent.py`: run one OpenAI-compatible model on one case with the public search/visit/PDF tool contract.

## Setup

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r code/requirements.txt
```

Offline validation and aggregation use only the Python standard library. The
`huggingface_hub` package is only needed if you want to download the public data
from Hugging Face with the CLI.

## Download Public Release Data

```bash
pip install huggingface_hub
hf download deepweb-bench-anon/deepweb-bench --repo-type dataset --include "data/*" --local-dir .
```

This creates a local `data/` directory used by the scripts below.

## Validate And Rebuild

```bash
python code/validate_release.py
python code/summarize_results.py
python code/rebuild_report.py --output rebuilt_report.md
```

Expected validation summary:

```text
cases: 100
model_results: 900
model_answers: 900
score_details: 900
scored_rows: 874
answers_with_text: 874
validation: ok
```

## Rerun Scoring

```bash
OPENAI_API_KEY=... \
python code/score_answer.py \
  --case-id 01_ai_foundation_labs \
  --model-answer-id claude-sonnet-4-6::01_ai_foundation_labs \
  --model gpt-5.5 \
  --output scratch_score.json
```

Use `--api-base` for OpenAI-compatible gateways.

## Rerun A Model

```bash
OPENAI_API_KEY=... SERPER_API_KEY=... \
python code/run_openai_compatible_agent.py \
  --case-id 01_ai_foundation_labs \
  --model your-model-id \
  --output scratch_answer.md \
  --trace scratch_trace.jsonl
```

The runner exposes three public tools to the model: `web_search`, `page_visit`,
and `pdf_fetch`. Live model reruns require user-provided model and search API
keys; offline validation does not.
