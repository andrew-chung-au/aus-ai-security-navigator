from __future__ import annotations

import json
from pathlib import Path
from statistics import mean

from retrieve_text import retrieve_chunks
from retrieve_vector import retrieve_chunks_vector


GROUND_TRUTH_PATH = Path("data/ground_truth_synthetic.jsonl")

TOP_K_STRICT = 5
TOP_K_RELAXED = 10

DEBUG_TOP_K = 100
DEBUG_N_QUESTIONS = 0


def load_ground_truth(path: Path) -> list[dict]:
    records: list[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


def last_heading(path_value) -> str | None:
    if path_value is None:
        return None
    if isinstance(path_value, list):
        return path_value[-1] if path_value else None
    if isinstance(path_value, str):
        try:
            data = json.loads(path_value)
            if isinstance(data, list) and data:
                return data[-1]
        except json.JSONDecodeError:
            return path_value.strip() or None
    return None


def call_retriever(
    retriever,
    question: str,
    top_k: int,
    target_size: str | None,
    target_role: str | None,
) -> list[dict]:
    if retriever is retrieve_chunks_vector:
        return retriever(
            query=question,
            k=top_k,
            size_tag=target_size,
            role_tag=target_role,
        )

    return retriever(
        query=question,
        limit=top_k,
        size_tag=target_size,
        role_tag=target_role,
    )


def compute_relevance_exact(
    retriever,
    question: str,
    gold_chunk_id: str,
    target_size: str | None,
    target_role: str | None,
    limit: int = TOP_K_STRICT,
) -> list[int]:
    results = call_retriever(
        retriever=retriever,
        question=question,
        top_k=limit,
        target_size=target_size,
        target_role=target_role,
    )
    return [1 if row["chunk_id"] == gold_chunk_id else 0 for row in results]


def compute_relevance_relaxed(
    retriever,
    question: str,
    gold_chunk_id: str,
    gold_source_id: str,
    gold_heading_path: list[str],
    target_size: str | None,
    target_role: str | None,
    limit: int = TOP_K_RELAXED,
) -> list[int]:
    results = call_retriever(
        retriever=retriever,
        question=question,
        top_k=limit,
        target_size=target_size,
        target_role=target_role,
    )

    gold_leaf = gold_heading_path[-1] if gold_heading_path else None

    scores: list[int] = []
    for row in results:
        row_chunk_id = row["chunk_id"]
        row_source_id = row.get("source_id")
        row_leaf = last_heading(row.get("heading_path"))

        if row_chunk_id == gold_chunk_id:
            scores.append(2)
        elif (
            row_source_id == gold_source_id
            and gold_leaf is not None
            and row_leaf is not None
            and row_leaf == gold_leaf
        ):
            scores.append(1)
        else:
            scores.append(0)

    return scores


def hit_rate_binary(relevance_scores: list[list[int]], positive_values: set[int]) -> float:
    per_question_hits = [
        1 if any(v in positive_values for v in scores) else 0
        for scores in relevance_scores
    ]
    return mean(per_question_hits) if per_question_hits else 0.0


def mrr_from_binary(relevance_scores: list[list[int]], positive_values: set[int]) -> float:
    reciprocal_ranks: list[float] = []

    for scores in relevance_scores:
        rr = 0.0
        for rank, value in enumerate(scores, start=1):
            if value in positive_values:
                rr = 1.0 / rank
                break
        reciprocal_ranks.append(rr)

    return mean(reciprocal_ranks) if reciprocal_ranks else 0.0


def evaluate_with_retriever(ground_truth: list[dict], retriever) -> dict:
    strict_scores: list[list[int]] = []
    relaxed_scores: list[list[int]] = []

    for record in ground_truth:
        question = record["question"]
        gold_chunk_id = record["chunk_id"]
        gold_source_id = record["source_id"]
        gold_heading_path = record.get("chunk_heading_path") or []
        target_size = record.get("target_size")
        target_role = record.get("target_role")

        strict = compute_relevance_exact(
            retriever=retriever,
            question=question,
            gold_chunk_id=gold_chunk_id,
            target_size=target_size,
            target_role=target_role,
            limit=TOP_K_STRICT,
        )
        relaxed = compute_relevance_relaxed(
            retriever=retriever,
            question=question,
            gold_chunk_id=gold_chunk_id,
            gold_source_id=gold_source_id,
            gold_heading_path=gold_heading_path,
            target_size=target_size,
            target_role=target_role,
            limit=TOP_K_RELAXED,
        )

        strict_scores.append(strict)
        relaxed_scores.append(relaxed)

    return {
        "n_questions": len(ground_truth),
        "strict_top_k": TOP_K_STRICT,
        "relaxed_top_k": TOP_K_RELAXED,
        "strict_hit_rate": hit_rate_binary(strict_scores, positive_values={1}),
        "strict_mrr": mrr_from_binary(strict_scores, positive_values={1}),
        "relaxed_hit_rate_any": hit_rate_binary(relaxed_scores, positive_values={1, 2}),
        "relaxed_mrr_any": mrr_from_binary(relaxed_scores, positive_values={1, 2}),
    }


def debug_top_k(ground_truth: list[dict], retriever, label: str) -> None:
    for i, record in enumerate(ground_truth[:DEBUG_N_QUESTIONS], start=1):
        question = record["question"]
        gold_chunk_id = record["chunk_id"]
        gold_source_id = record["source_id"]
        gold_heading_path = record.get("chunk_heading_path") or []
        gold_leaf = gold_heading_path[-1] if gold_heading_path else None
        target_size = record.get("target_size")
        target_role = record.get("target_role")

        results = call_retriever(
            retriever=retriever,
            question=question,
            top_k=DEBUG_TOP_K,
            target_size=target_size,
            target_role=target_role,
        )

        print(f"\n=== DEBUG QUESTION {i} ({label}) ===")
        print("Q:", question)
        print("GOLD chunk_id:", gold_chunk_id)
        print("GOLD source_id:", gold_source_id)
        print("GOLD leaf heading:", gold_leaf)
        print("Top", DEBUG_TOP_K, "results:")

        if not results:
            continue

        for rank, row in enumerate(results, start=1):
            row_leaf = last_heading(row.get("heading_path"))
            score = row.get("score", row.get("similarity"))
            score_str = f"{score:.4f}" if isinstance(score, (int, float)) else "n/a"
            print(
                f"{rank:3d}. {row['chunk_id']} "
                f"src={row.get('source_id')} "
                f"leaf={row_leaf} "
                f"score={score_str}"
            )


def main() -> None:
    ground_truth = load_ground_truth(GROUND_TRUTH_PATH)

    text_metrics = evaluate_with_retriever(ground_truth, retrieve_chunks)
    vector_metrics = evaluate_with_retriever(ground_truth, retrieve_chunks_vector)

    print(
        json.dumps(
            {
                "text": text_metrics,
                "vector": vector_metrics,
            },
            indent=2,
            ensure_ascii=False,
        )
    )

    debug_top_k(ground_truth, retrieve_chunks, "text")
    debug_top_k(ground_truth, retrieve_chunks_vector, "vector")


if __name__ == "__main__":
    main()