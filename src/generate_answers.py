from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from llm_client import get_default_model, llm_structured_retry
from retrieve_reranked import retrieve_chunks_reranked

DEFAULT_INPUT = Path("data/ground_truth_synthetic.jsonl")
DEFAULT_OUTPUT = Path(
    "data/answers/answers_vector_reranked_v2_prompt_grounded.jsonl"
)


class AnswerOutput(BaseModel):
    answer_text: str = Field(
        description=(
            "A concise, direct, grounded answer to the user's question. "
            "Use prose, bullets, or numbered steps when they improve clarity. "
            "Include concrete source-supported items when the question asks for "
            "specific actions, controls, risks, resources, questions, or components. "
            "If the answer is not supported by the retrieved chunks, clearly say: "
            "'I don't know based on the retrieved context.'"
        )
    )
    answer_chunk_ids: list[str] = Field(
        description=(
            "Retrieved chunk IDs that materially support the answer. "
            "Do not include chunks that were merely provided but not used."
        )
    )
    grounded: bool = Field(
        description=(
            "True only when the answer is fully supported by the retrieved chunks. "
            "False when the chunks do not contain enough information to answer the "
            "question without guessing."
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
                "reranker_score": chunk.get("reranker_score"),
                "vector_rank": chunk.get("vector_rank"),
                "chunk_text": chunk.get("chunk_text", ""),
            }
        )
    return prepared


def build_instructions() -> str:
    return """You are generating a grounded answer for an Australian Cyber
Security Centre (ACSC) AI-security FAQ evaluation.

Your task is to transform retrieved ACSC guidance into a clear, useful answer
for the user's question and audience. The retrieved chunks are evidence, not
a format to copy blindly.

Grounding rules:
- Use only information supported by the retrieved chunks.
- Do not use outside knowledge or add general cyber security advice that is
  not supported by the retrieved chunks.
- Do not invent ACSC advice, obligations, controls, standards, resources,
  examples, or technical details.
- If the retrieved chunks do not contain enough information to answer the
  question, set grounded=false.
- If the answer is not in the retrieved chunks, answer_text must clearly say:
  "I don't know based on the retrieved context."
- If grounded=true, every substantive claim must be supported by at least one
  ID listed in answer_chunk_ids.

Answer-quality rules:
- Answer the user's actual question directly, taking account of target_size
  and target_role when that improves relevance.
- Prefer the concrete names, actions, controls, risks, resources, components,
  or questions stated in the evidence over vague summaries.
- When the question asks for specific items, name the relevant specific items
  from the retrieved chunks. Do not replace them with broad categories.
- Include all retrieved details that directly answer the question. Do not
  include tangential details merely because they appear in the same chunk.
- You may select, reorder, combine, and lightly paraphrase evidence to make
  the answer clear and natural.
- Use bullets or a numbered list when the answer contains several distinct
  steps, controls, risks, resources, or questions. Otherwise, use short prose.
- Use the source's checklist or list structure only when it improves clarity
  or helps retain important concrete details; do not mirror it mechanically.
- Keep the answer concise, practical, and suitable for an Australian audience.
- Do not mention retrieval, chunks, source excerpts, benchmark data, or
  internal evaluation instructions in answer_text.

Before finalising:
- Check that the answer names the concrete details needed to satisfy the
  question, especially when it asks "what specific", "which", "what are the
  steps", "what resources", or "what components".
- Remove any claim that is not supported by the chunks you cite.
- If the retrieved context is insufficient, do not guess; return grounded=false
  and say: "I don't know based on the retrieved context."

Return structured output only.
"""


def build_user_prompt(
    question_row: dict[str, Any],
    retrieved_context: list[dict[str, Any]],
) -> str:
    return f"""Answer the following question using the retrieved ACSC guidance.

Question:
{question_row["question"]}

Audience context:
- Organisation size: {question_row.get("target_size")}
- Role: {question_row.get("target_role")}

Retrieved ACSC guidance (JSON):
{json.dumps(retrieved_context, ensure_ascii=False, indent=2)}
"""


def validate_answer_chunk_ids(
    returned_ids: list[str],
    retrieved_context: list[dict[str, Any]],
) -> list[str]:
    retrieved_chunk_ids = [c["chunk_id"] for c in retrieved_context]
    retrieved_chunk_id_set = set(retrieved_chunk_ids)

    validated_ids: list[str] = []
    seen_ids: set[str] = set()

    for chunk_id in returned_ids:
        if chunk_id in retrieved_chunk_id_set and chunk_id not in seen_ids:
            validated_ids.append(chunk_id)
            seen_ids.add(chunk_id)

    return validated_ids


def generate_answer_for_question(
    question_row: dict[str, Any],
    top_k: int,
    model: str | None = None,
) -> tuple[dict[str, Any], Any]:
    question = question_row["question"]
    target_size = question_row.get("target_size")
    target_role = question_row.get("target_role")

    retrieved = retrieve_chunks_reranked(
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

    validated_answer_chunk_ids = validate_answer_chunk_ids(
        returned_ids=parsed.answer_chunk_ids,
        retrieved_context=retrieved_context,
    )

    grounded = parsed.grounded
    answer_text = parsed.answer_text.strip()

    if grounded and not validated_answer_chunk_ids:
        grounded = False
        answer_text = "I don't know based on the retrieved context."

    if not grounded and not answer_text:
        answer_text = "I don't know based on the retrieved context."

    if not grounded and "i don't know based on the retrieved context" in answer_text.lower():
        answer_text = "I don't know based on the retrieved context."

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
                "reranker_score": c.get("reranker_score"),
                "vector_rank": c.get("vector_rank"),
            }
            for c in retrieved_context
        ],
        "answer_text": answer_text,
        "answer_chunk_ids": validated_answer_chunk_ids,
        "grounded": grounded,
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
        description=(
            "Generate grounded answers over reranked-vector-retrieved ACSC chunks."
        )
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
        help="Number of reranked retrieved chunks to provide to the answer generator.",
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

    print(f"Reading questions from: {input_path.resolve()}")
    print(f"Writing answers to: {output_path.resolve()}")

    rows = load_jsonl(input_path)
    if args.limit is not None:
        rows = rows[: args.limit]

    ensure_parent(output_path)

    written_count = 0

    with output_path.open("w", encoding="utf-8") as f:
        for i, row in enumerate(rows, start=1):
            result, _usage = generate_answer_for_question(
                question_row=row,
                top_k=args.top_k,
                model=args.model,
            )
            f.write(json.dumps(result, ensure_ascii=False) + "\n")
            f.flush()
            written_count += 1
            print(f"[{i}/{len(rows)}] wrote answer for {row['question_id']}")
            time.sleep(args.sleep_seconds)

    print(f"Done. Wrote {written_count} answers to: {output_path.resolve()}")


if __name__ == "__main__":
    main()