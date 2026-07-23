from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean
from typing import Any, Callable

from retrieve_hybrid import retrieve_chunks_hybrid
from retrieve_text import retrieve_chunks
from retrieve_vector import retrieve_chunks_vector


GROUND_TRUTH_PATH = Path("data/ground_truth_synthetic.jsonl")

TOP_K_STRICT = 5
TOP_K_RELAXED = 10

DEBUG_TOP_K = 100
DEBUG_N_QUESTIONS = 0


RetrieverFn = Callable[..., list[dict[str, Any]]]


RETRIEVERS: dict[str, dict[str, Any]] = {
    "text": {
        "fn": retrieve_chunks,
        "top_k_param": "limit",
        "score_field": "score",
    },
    "vector": {
        "fn": retrieve_chunks_vector,
        "top_k_param": "k",
        "score_field": "similarity",
    },
    "hybrid": {
        "fn": retrieve_chunks_hybrid,
        "top_k_param": "limit",
        "score_field": "hybrid_score",
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate text, vector, and hybrid retrieval on the synthetic ground-truth set."
    )
    parser.add_argument(
        "--ground-truth",
        type=Path,
        default=GROUND_TRUTH_PATH,
        help="Path to the synthetic ground-truth JSONL file.",
    )
    parser.add_argument(
        "--debug-output",
        type=Path,
        default=None,
        help="Optional JSONL file to write per-question retrieval outputs for manual review.",
    )
    return parser.parse_args()


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


def call_backend(
    backend_name: str,
    question: str,
    top_k: int,
    target_size: str | None,
    target_role: str | None,
) -> list[dict[str, Any]]:
    backend = RETRIEVERS[backend_name]
    fn: RetrieverFn = backend["fn"]
    top_k_param = backend["top_k_param"]

    kwargs: dict[str, Any] = {
        "query": question,
        "size_tag": target_size,
        "role_tag": target_role,
        top_k_param: top_k,
    }

    return fn(**kwargs)


def compute_relevance_exact(
    backend_name: str,
    question: str,
    gold_chunk_id: str,
    target_size: str | None,
    target_role: str | None,
    limit: int = TOP_K_STRICT,
) -> tuple[list[int], list[dict[str, Any]]]:
    results = call_backend(
        backend_name=backend_name,
        question=question,
        top_k=limit,
        target_size=target_size,
        target_role=target_role,
    )
    scores = [1 if row["chunk_id"] == gold_chunk_id else 0 for row in results]
    return scores, results


def compute_relevance_relaxed(
    backend_name: str,
    question: str,
    gold_chunk_id: str,
    gold_source_id: str,
    gold_heading_path: list[str],
    target_size: str | None,
    target_role: str | None,
    limit: int = TOP_K_RELAXED,
) -> tuple[list[int], list[dict[str, Any]]]:
    results = call_backend(
        backend_name=backend_name,
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

    return scores, results


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


def build_debug_result_rows(results: list[dict[str, Any]], backend_name: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for rank, row in enumerate(results, start=1):
        item: dict[str, Any] = {
            "rank": rank,
            "chunk_id": row.get("chunk_id"),
            "source_id": row.get("source_id"),
            "document_title": row.get("document_title"),
            "leaf_heading": last_heading(row.get("heading_path")),
            "size_audience_tag": row.get("size_audience_tag"),
            "role_audience_tags": row.get("role_audience_tags"),
            "chunk_words": row.get("chunk_words"),
        }

        if backend_name == "text":
            item["score"] = row.get("score")
        elif backend_name == "vector":
            item["similarity"] = row.get("similarity")
            item["cosine_distance"] = row.get("cosine_distance")
        elif backend_name == "hybrid":
            item["hybrid_score"] = row.get("hybrid_score")
            item["text_rank"] = row.get("text_rank")
            item["vector_rank"] = row.get("vector_rank")
            item["text_score"] = row.get("text_score")
            item["vector_similarity"] = row.get("vector_similarity")
            item["vector_cosine_distance"] = row.get("vector_cosine_distance")
            item["present_in_text"] = row.get("present_in_text")
            item["present_in_vector"] = row.get("present_in_vector")

        rows.append(item)

    return rows


def evaluate_with_backend(
    ground_truth: list[dict],
    backend_name: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    strict_scores: list[list[int]] = []
    relaxed_scores: list[list[int]] = []
    debug_records: list[dict[str, Any]] = []

    for record in ground_truth:
        question = record["question"]
        gold_chunk_id = record["chunk_id"]
        gold_source_id = record["source_id"]
        gold_heading_path = record.get("chunk_heading_path") or []
        gold_leaf = gold_heading_path[-1] if gold_heading_path else None
        target_size = record.get("target_size")
        target_role = record.get("target_role")

        strict, strict_results = compute_relevance_exact(
            backend_name=backend_name,
            question=question,
            gold_chunk_id=gold_chunk_id,
            target_size=target_size,
            target_role=target_role,
            limit=TOP_K_STRICT,
        )
        relaxed, relaxed_results = compute_relevance_relaxed(
            backend_name=backend_name,
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

        debug_records.append(
            {
                "backend": backend_name,
                "question": question,
                "target_size": target_size,
                "target_role": target_role,
                "gold_chunk_id": gold_chunk_id,
                "gold_source_id": gold_source_id,
                "gold_leaf_heading": gold_leaf,
                "strict_top_k": TOP_K_STRICT,
                "relaxed_top_k": TOP_K_RELAXED,
                "strict_relevance_scores": strict,
                "relaxed_relevance_scores": relaxed,
                "strict_results": build_debug_result_rows(strict_results, backend_name),
                "relaxed_results": build_debug_result_rows(relaxed_results, backend_name),
            }
        )

    metrics = {
        "n_questions": len(ground_truth),
        "strict_top_k": TOP_K_STRICT,
        "relaxed_top_k": TOP_K_RELAXED,
        "strict_hit_rate": hit_rate_binary(strict_scores, positive_values={1}),
        "strict_mrr": mrr_from_binary(strict_scores, positive_values={1}),
        "relaxed_hit_rate_any": hit_rate_binary(relaxed_scores, positive_values={1, 2}),
        "relaxed_mrr_any": mrr_from_binary(relaxed_scores, positive_values={1, 2}),
    }

    return metrics, debug_records


def write_debug_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def debug_top_k(ground_truth: list[dict], backend_name: str) -> None:
    for i, record in enumerate(ground_truth[:DEBUG_N_QUESTIONS], start=1):
        question = record["question"]
        gold_chunk_id = record["chunk_id"]
        gold_source_id = record["source_id"]
        gold_heading_path = record.get("chunk_heading_path") or []
        gold_leaf = gold_heading_path[-1] if gold_heading_path else None
        target_size = record.get("target_size")
        target_role = record.get("target_role")

        results = call_backend(
            backend_name=backend_name,
            question=question,
            top_k=DEBUG_TOP_K,
            target_size=target_size,
            target_role=target_role,
        )

        print(f"\n=== DEBUG QUESTION {i} ({backend_name}) ===")
        print("Q:", question)
        print("GOLD chunk_id:", gold_chunk_id)
        print("GOLD source_id:", gold_source_id)
        print("GOLD leaf heading:", gold_leaf)
        print("Top", DEBUG_TOP_K, "results:")

        if not results:
            continue

        for rank, row in enumerate(results, start=1):
            row_leaf = last_heading(row.get("heading_path"))

            if backend_name == "text":
                score = row.get("score")
                score_str = f"{score:.4f}" if isinstance(score, (int, float)) else "n/a"
                extra = f"score={score_str}"
            elif backend_name == "vector":
                score = row.get("similarity")
                score_str = f"{score:.4f}" if isinstance(score, (int, float)) else "n/a"
                extra = f"similarity={score_str}"
            else:
                hybrid_score = row.get("hybrid_score")
                hybrid_score_str = (
                    f"{hybrid_score:.6f}" if isinstance(hybrid_score, (int, float)) else "n/a"
                )
                extra = (
                    f"hybrid_score={hybrid_score_str} "
                    f"text_rank={row.get('text_rank')} "
                    f"vector_rank={row.get('vector_rank')}"
                )

            print(
                f"{rank:3d}. {row['chunk_id']} "
                f"src={row.get('source_id')} "
                f"leaf={row_leaf} "
                f"{extra}"
            )


def main() -> None:
    args = parse_args()
    ground_truth = load_ground_truth(args.ground_truth)

    all_metrics: dict[str, Any] = {}
    all_debug_records: list[dict[str, Any]] = []

    for backend_name in RETRIEVERS:
        metrics, debug_records = evaluate_with_backend(ground_truth, backend_name)
        all_metrics[backend_name] = metrics
        all_debug_records.extend(debug_records)

    print(json.dumps(all_metrics, indent=2, ensure_ascii=False))

    if args.debug_output is not None:
        write_debug_jsonl(args.debug_output, all_debug_records)

    for backend_name in RETRIEVERS:
        debug_top_k(ground_truth, backend_name)


if __name__ == "__main__":
    main()