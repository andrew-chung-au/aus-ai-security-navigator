from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from llm_client import get_default_model, llm_structured_retry


DEFAULT_ANSWERS_INPUT = Path("data/answers/answers_vector_v1.jsonl")
DEFAULT_CHUNKS_INPUT = Path("data/chunks/chunks.jsonl")
DEFAULT_OUTPUT = Path("data/answers/answers_vector_v1_judged.jsonl")


class AnswerEvaluation(BaseModel):
    reasoning: str = Field(
        description=(
            "Reason step-by-step about whether the generated answer is semantically "
            "consistent with the ground-truth answer, covers the core information, "
            "and avoids major unsupported claims."
        )
    )
    score: Literal["good", "bad"] = Field(
        description=(
            "Output 'good' if the generated answer is correct and sufficiently complete "
            "relative to the ground-truth answer; output 'bad' otherwise."
        )
    )


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def build_chunk_index(chunks_path: Path) -> dict[str, dict[str, Any]]:
    rows = load_jsonl(chunks_path)
    idx: dict[str, dict[str, Any]] = {}
    for row in rows:
        chunk_id = row.get("chunk_id")
        if chunk_id:
            idx[chunk_id] = row
    return idx


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def normalize_heading_path(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(x) for x in value]
    return []


def build_instructions() -> str:
    return """You are an expert evaluator for grounded ACSC AI security answers.

You will compare:
1) a user question,
2) a ground-truth answer passage from the corpus,
3) a generated answer from the system.

Evaluation rubric:
- Focus on semantic equivalence, not exact wording.
- The generated answer does NOT need to be word-for-word identical to the ground-truth passage.
- Mark the answer as 'good' if it captures the core meaning, is materially correct, is sufficiently complete for the question, and does not add major unsupported claims.
- Extra detail is acceptable if it remains consistent with the ground-truth passage.
- Mark the answer as 'bad' if it is materially wrong, misses key information, or introduces major unsupported claims.

Return structured output only.
"""


def build_user_prompt(
    answer_row: dict[str, Any],
    gold_chunk: dict[str, Any],
) -> str:
    gold_heading_path = normalize_heading_path(gold_chunk.get("heading_path"))
    gold_heading_text = " > ".join(gold_heading_path) if gold_heading_path else "(none)"

    return f"""Evaluate the generated answer against the ground-truth passage.

Question:
{answer_row.get("question", "")}

Ground-truth metadata:
- gold_source_id: {answer_row.get("gold_source_id")}
- gold_chunk_id: {answer_row.get("gold_chunk_id")}
- gold_document_title: {gold_chunk.get("document_title")}
- gold_heading_path: {gold_heading_text}

Ground-truth answer passage:
{gold_chunk.get("chunk_text", "")}

Generated answer:
{answer_row.get("answer_text", "")}
"""


def judge_one_answer(
    answer_row: dict[str, Any],
    chunks_by_id: dict[str, dict[str, Any]],
    model: str | None = None,
) -> tuple[dict[str, Any], Any]:
    gold_chunk_id = answer_row.get("gold_chunk_id")
    if not gold_chunk_id:
        raise ValueError("Missing gold_chunk_id in answer row.")

    gold_chunk = chunks_by_id.get(gold_chunk_id)
    if gold_chunk is None:
        raise KeyError(f"Gold chunk_id not found in chunks index: {gold_chunk_id}")

    parsed, usage = llm_structured_retry(
        instructions=build_instructions(),
        user_prompt=build_user_prompt(answer_row, gold_chunk),
        output_type=AnswerEvaluation,
        model=model,
    )

    judged_row = dict(answer_row)
    judged_row["judge_model_id"] = model or get_default_model()
    judged_row["judge_score"] = parsed.score
    judged_row["judge_reasoning"] = parsed.reasoning
    judged_row["judge_gold_chunk_text"] = gold_chunk.get("chunk_text", "")
    judged_row["judge_gold_heading_path"] = normalize_heading_path(
        gold_chunk.get("heading_path")
    )
    judged_row["judge_usage"] = {
        "prompt_tokens": getattr(usage, "prompt_tokens", None),
        "completion_tokens": getattr(usage, "completion_tokens", None),
        "total_tokens": getattr(usage, "total_tokens", None),
    }

    return judged_row, usage


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Judge generated answers against gold chunks using an LLM-as-a-judge."
    )
    parser.add_argument(
        "--answers-input",
        default=str(DEFAULT_ANSWERS_INPUT),
        help="Path to generated answers JSONL.",
    )
    parser.add_argument(
        "--chunks-input",
        default=str(DEFAULT_CHUNKS_INPUT),
        help="Path to chunks JSONL used to look up gold chunk text.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="Path to judged answers JSONL.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit on number of answers to judge.",
    )
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=2.0,
        help="Delay between successful judge requests.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Optional model override. Defaults to MODEL_ID from .env.",
    )
    args = parser.parse_args()

    answers_input = Path(args.answers_input)
    chunks_input = Path(args.chunks_input)
    output_path = Path(args.output)

    chunks_by_id = build_chunk_index(chunks_input)
    answer_rows = load_jsonl(answers_input)

    if args.limit is not None:
        answer_rows = answer_rows[: args.limit]

    ensure_parent(output_path)

    with output_path.open("w", encoding="utf-8") as f:
        for i, row in enumerate(answer_rows, start=1):
            judged_row, _usage = judge_one_answer(
                answer_row=row,
                chunks_by_id=chunks_by_id,
                model=args.model,
            )
            f.write(json.dumps(judged_row, ensure_ascii=False) + "\n")
            f.flush()
            print(f"[{i}/{len(answer_rows)}] judged {row.get('question_id')}")
            time.sleep(args.sleep_seconds)


if __name__ == "__main__":
    main()