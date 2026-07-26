from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from llm_client import get_default_model, llm_structured_retry
from retrieve_vector import retrieve_chunks_vector


DEFAULT_INPUT = Path("data/ground_truth_synthetic.jsonl")
DEFAULT_OUTPUT = Path("data/answers/answers_vector_v1.jsonl")


class AnswerOutput(BaseModel):
    answer_text: str = Field(
        description="A concise grounded answer using only the retrieved ACSC chunks."
    )
    answer_chunk_ids: list[str] = Field(
        description="List of chunk IDs actually used to support the answer."
    )
    grounded: bool = Field(
        description="True if the retrieved chunks are sufficient to support the answer; false otherwise."
    )


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def normalize_heading_path(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(x) for x in value]
    return []


def prepare_chunk_context(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    prepared: list[dict[str, Any]] = []
    for rank, chunk in enumerate(chunks, start=1):
        prepared.append(
            {
                "rank": rank,
                "chunk_id": chunk["chunk_id"],
                "source_id": chunk.get("source_id"),
                "document_title": chunk.get("document_title"),
                "heading_path": normalize_heading_path(chunk.get("heading_path")),
                "size_audience_tag": chunk.get("size_audience_tag"),
                "role_audience_tags": chunk.get("role_audience_tags", []),
                "similarity": chunk.get("similarity"),
                "chunk_text": chunk.get("chunk_text", ""),
            }
        )
    return prepared


def build_instructions() -> str:
    return """You are generating grounded answers for an ACSC AI security RAG evaluation.

Rules:
- Use ONLY the retrieved chunks provided in the prompt.
- Do not use outside knowledge.
- Do not invent ACSC advice, sources, or controls.
- Write a concise but useful answer in plain language.
- Respect the target audience context when relevant.
- Only include chunk IDs in answer_chunk_ids if they were actually used in the answer.
- If the retrieved chunks are insufficient, set grounded=false and say clearly that the answer is limited by the available retrieved context.
- Return structured output only.
"""


def build_user_prompt(
    question_row: dict[str, Any],
    retrieved_context: list[dict[str, Any]],
) -> str:
    return f"""Answer the following question using only the retrieved ACSC chunks.

Question:
{question_row["question"]}

Question metadata:
- question_id: {question_row.get("question_id")}
- target_size: {question_row.get("target_size")}
- target_role: {question_row.get("target_role")}
- gold_source_id: {question_row.get("source_id")}
- gold_chunk_id: {question_row.get("chunk_id")}

Retrieved chunks (JSON):
{json.dumps(retrieved_context, ensure_ascii=False, indent=2)}
"""


def generate_answer_for_question(
    question_row: dict[str, Any],
    top_k: int,
    model: str | None = None,
) -> tuple[dict[str, Any], Any]:
    question = question_row["question"]
    target_size = question_row.get("target_size")
    target_role = question_row.get("target_role")

    retrieved = retrieve_chunks_vector(
        query=question,
        limit=top_k,
        size_tag=target_size,
        role_tag=target_role,
    )
    retrieved_context = prepare_chunk_context(retrieved)

    parsed, usage = llm_structured_retry(
        instructions=build_instructions(),
        user_prompt=build_user_prompt(question_row, retrieved_context),
        output_type=AnswerOutput,
        model=model,
    )

    result = {
        "question_id": question_row.get("question_id"),
        "question": question,
        "seed_id": question_row.get("seed_id"),
        "target_size": target_size,
        "target_role": target_role,
        "gold_source_id": question_row.get("source_id"),
        "gold_chunk_id": question_row.get("chunk_id"),
        "retrieved_chunks": [
            {
                "rank": c["rank"],
                "chunk_id": c["chunk_id"],
                "source_id": c.get("source_id"),
                "document_title": c.get("document_title"),
                "heading_path": c.get("heading_path", []),
                "similarity": c.get("similarity"),
            }
            for c in retrieved_context
        ],
        "answer_text": parsed.answer_text,
        "answer_chunk_ids": parsed.answer_chunk_ids,
        "grounded": parsed.grounded,
        "model_id": model or get_default_model(),
        "top_k": top_k,
        "usage": {
            "prompt_tokens": getattr(usage, "prompt_tokens", None),
            "completion_tokens": getattr(usage, "completion_tokens", None),
            "total_tokens": getattr(usage, "total_tokens", None),
        },
    }
    return result, usage


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate grounded answers over vector-retrieved ACSC chunks."
    )
    parser.add_argument(
        "--input",
        default=str(DEFAULT_INPUT),
        help="Path to input synthetic questions JSONL.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="Path to output answers JSONL.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of vector-retrieved chunks to provide to the answer generator.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit on number of questions to process.",
    )
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=2.0,
        help="Delay between successful requests.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Optional model override. Defaults to MODEL_ID from .env.",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    rows = load_jsonl(input_path)
    if args.limit is not None:
        rows = rows[: args.limit]

    ensure_parent(output_path)

    with output_path.open("w", encoding="utf-8") as f:
        for i, row in enumerate(rows, start=1):
            result, _usage = generate_answer_for_question(
                question_row=row,
                top_k=args.top_k,
                model=args.model,
            )
            f.write(json.dumps(result, ensure_ascii=False) + "\n")
            f.flush()
            print(f"[{i}/{len(rows)}] wrote answer for {row['question_id']}")
            time.sleep(args.sleep_seconds)


if __name__ == "__main__":
    main()