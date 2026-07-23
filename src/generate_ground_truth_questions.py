import json
import time
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from llm_client import get_client, llm_structured_retry


QUESTIONS_PER_CHUNK = 1
REQUEST_DELAY_SECONDS = 4.0
INPUT_PATH = Path("data/seed_chunk_candidates.json")
OUTPUT_PATH = Path("data/ground_truth_synthetic.jsonl")


class GeneratedQuestion(BaseModel):
    question: str = Field(description="One realistic user question answerable by the chunk.")


def get_project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def load_seed_candidates(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def build_user_prompt(record: dict[str, Any]) -> str:
    candidate_chunk = record["candidate_chunk"]

    payload = {
        "generation_target": {
            "seed_id": record.get("seed_id"),
            "target_size": record.get("target_size"),
            "target_role": record.get("target_role"),
            "passage_type": record.get("passage_type"),
        },
        "chunk": {
            "chunk_id": candidate_chunk.get("chunk_id"),
            "source_id": candidate_chunk.get("source_id"),
            "source_file": candidate_chunk.get("source_file"),
            "document_title": candidate_chunk.get("document_title"),
            "heading_path": candidate_chunk.get("heading_path"),
            "size_audience_tag": candidate_chunk.get("size_audience_tag"),
            "role_audience_tags": candidate_chunk.get("role_audience_tags"),
            "chunk_text": candidate_chunk.get("chunk_text"),
        },
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


GENERATION_INSTRUCTIONS = """
You are generating synthetic evaluation questions for a RAG system over official AI security guidance.

You will receive:
1. generation_target: metadata that tells you which audience perspective and question style to simulate
2. chunk: the source-of-truth chunk that the question must be answerable from

Your task:
- Generate exactly one realistic user question.
- The question must be fully grounded in the chunk text, not in external assumptions.
- Use generation_target.target_size and generation_target.target_role to shape who is asking and how they would phrase the question.
- You may use generation_target.passage_type as a soft hint for the style or focus of the question, but do not force it if it does not fit the chunk naturally.
- Use the chunk metadata and chunk text as the factual basis for the question.
- Do not mention headings, section names, source files, chunk IDs, or document structure.
- Do not quote or closely copy long phrases from the chunk unless unavoidable.
- Do not make the question broader than the chunk can support.
- Return only the structured output.

Write the question in natural, realistic language. Prefer practical organisational phrasing over academic phrasing.
""".strip()


def generate_question_for_record(record: dict[str, Any], client) -> str:
    out, _usage = llm_structured_retry(
        instructions=GENERATION_INSTRUCTIONS,
        user_prompt=build_user_prompt(record),
        output_type=GeneratedQuestion,
        client=client,
    )
    return out.question.strip()


def make_output_record(
    record: dict[str, Any],
    question_text: str,
    question_index: int = 1,
) -> dict[str, Any]:
    candidate_chunk = record["candidate_chunk"]
    chunk_id = candidate_chunk["chunk_id"]
    seed_id = record["seed_id"]

    question_id = f"{chunk_id}::q{question_index:02d}"

    return {
        "question_id": question_id,
        "question": question_text,
        "seed_id": seed_id,
        "target_size": record.get("target_size"),
        "target_role": record.get("target_role"),
        "source_id": candidate_chunk.get("source_id"),
        "chunk_id": chunk_id,
        "document_title": candidate_chunk.get("document_title"),
        "chunk_heading_path": candidate_chunk.get("heading_path", []),
        "size_audience_tag": candidate_chunk.get("size_audience_tag"),
        "role_audience_tags": candidate_chunk.get("role_audience_tags", []),
    }


def write_jsonl(records: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def main() -> None:
    project_root = get_project_root()
    input_path = project_root / INPUT_PATH
    output_path = project_root / OUTPUT_PATH

    records = load_seed_candidates(input_path)
    client = get_client()

    output_records: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    print(f"Request delay: {REQUEST_DELAY_SECONDS:.1f}s")

    for idx, record in enumerate(records, start=1):
        seed_id = record.get("seed_id", f"row-{idx}")
        candidate_chunk = record.get("candidate_chunk") or {}
        source_id = candidate_chunk.get("source_id", "")
        chunk_id = candidate_chunk.get("chunk_id", "")

        try:
            for question_index in range(1, QUESTIONS_PER_CHUNK + 1):
                question_text = generate_question_for_record(record, client=client)
                output_record = make_output_record(
                    record,
                    question_text=question_text,
                    question_index=question_index,
                )
                output_records.append(output_record)

                if REQUEST_DELAY_SECONDS > 0:
                    time.sleep(REQUEST_DELAY_SECONDS)

            print(f"[OK] {seed_id} -> {chunk_id}")

        except Exception as e:
            failures.append(
                {
                    "row_index": idx,
                    "seed_id": seed_id,
                    "source_id": source_id,
                    "chunk_id": chunk_id,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                }
            )
            print(f"[FAIL] {seed_id} -> {chunk_id}: {type(e).__name__}: {e}")

    write_jsonl(output_records, output_path)

    print("\nDone.")
    print(f"Wrote {len(output_records)} question records to: {output_path}")
    print(f"Failed rows: {len(failures)}")

    if failures:
        print("\nFailure summary:")
        for failure in failures:
            print(
                f"- row {failure['row_index']}: "
                f"seed_id={failure['seed_id']} | "
                f"source_id={failure['source_id']} | "
                f"chunk_id={failure['chunk_id']} | "
                f"{failure['error_type']}: {failure['error_message']}"
            )


if __name__ == "__main__":
    main()