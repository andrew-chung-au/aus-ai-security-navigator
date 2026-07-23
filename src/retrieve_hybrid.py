from __future__ import annotations

import argparse
import json
from typing import Any

from retrieve_text import ALLOWED_ROLE_TAGS, ALLOWED_SIZE_TAGS, retrieve_chunks
from retrieve_vector import retrieve_chunks_vector


DEFAULT_FUSION_POOL = 10
DEFAULT_RRF_K = 60


def reciprocal_rank_score(rank: int, rrf_k: int) -> float:
    return 1.0 / (rrf_k + rank)


def retrieve_chunks_hybrid(
    query: str,
    limit: int = 5,
    size_tag: str | None = None,
    role_tag: str | None = None,
    fusion_pool: int = DEFAULT_FUSION_POOL,
    rrf_k: int = DEFAULT_RRF_K,
) -> list[dict[str, Any]]:
    if not query.strip():
        return []

    text_results = retrieve_chunks(
        query=query,
        limit=fusion_pool,
        size_tag=size_tag,
        role_tag=role_tag,
    )

    vector_results = retrieve_chunks_vector(
        query=query,
        k=fusion_pool,
        size_tag=size_tag,
        role_tag=role_tag,
    )

    merged: dict[str, dict[str, Any]] = {}

    for rank, row in enumerate(text_results, start=1):
        chunk_id = row["chunk_id"]
        entry = merged.setdefault(chunk_id, dict(row))
        entry["hybrid_score"] = entry.get("hybrid_score", 0.0) + reciprocal_rank_score(rank, rrf_k)
        entry["text_rank"] = rank
        entry["text_score"] = row.get("score")
        entry.setdefault("vector_rank", None)
        entry.setdefault("vector_similarity", None)
        entry.setdefault("vector_cosine_distance", None)
        entry["present_in_text"] = True
        entry.setdefault("present_in_vector", False)

    for rank, row in enumerate(vector_results, start=1):
        chunk_id = row["chunk_id"]
        if chunk_id in merged:
            entry = merged[chunk_id]
        else:
            entry = dict(row)
            merged[chunk_id] = entry

        entry["hybrid_score"] = entry.get("hybrid_score", 0.0) + reciprocal_rank_score(rank, rrf_k)
        entry["vector_rank"] = rank
        entry["vector_similarity"] = row.get("similarity")
        entry["vector_cosine_distance"] = row.get("cosine_distance")
        entry.setdefault("text_rank", None)
        entry.setdefault("text_score", None)
        entry["present_in_vector"] = True
        entry.setdefault("present_in_text", False)

        if "score" not in entry:
            entry["score"] = None

    results = list(merged.values())

    for row in results:
        row.setdefault("hybrid_score", 0.0)
        row.setdefault("text_rank", None)
        row.setdefault("vector_rank", None)
        row.setdefault("text_score", None)
        row.setdefault("vector_similarity", None)
        row.setdefault("vector_cosine_distance", None)
        row.setdefault("present_in_text", False)
        row.setdefault("present_in_vector", False)

    results.sort(
        key=lambda row: (
            -float(row.get("hybrid_score", 0.0)),
            row.get("text_rank") if row.get("text_rank") is not None else 10_000,
            row.get("vector_rank") if row.get("vector_rank") is not None else 10_000,
            row.get("chunk_words") if row.get("chunk_words") is not None else 10_000,
        )
    )

    return results[:limit]


def print_results(results: list[dict[str, Any]]) -> None:
    if not results:
        print("No results found.")
        return

    for i, row in enumerate(results, start=1):
        heading_path = row.get("heading_path") or []
        if isinstance(heading_path, str):
            try:
                heading_path = json.loads(heading_path)
            except json.JSONDecodeError:
                heading_path = [heading_path]

        role_tags = row.get("role_audience_tags") or []
        if isinstance(role_tags, str):
            try:
                role_tags = json.loads(role_tags)
            except json.JSONDecodeError:
                role_tags = [role_tags]

        hybrid_score = row.get("hybrid_score")
        hybrid_score_str = (
            f"{hybrid_score:.6f}" if isinstance(hybrid_score, (int, float)) else "n/a"
        )

        text_score = row.get("text_score")
        text_score_str = (
            f"{text_score:.4f}" if isinstance(text_score, (int, float)) else "n/a"
        )

        vector_similarity = row.get("vector_similarity")
        vector_similarity_str = (
            f"{vector_similarity:.4f}" if isinstance(vector_similarity, (int, float)) else "n/a"
        )

        print(f"[{i}] {row['chunk_id']}  hybrid_score={hybrid_score_str}")
        print(f"    source_file: {row.get('source_file')}")
        print(f"    title: {row.get('document_title')}")
        print(f"    heading_path: {' > '.join(heading_path)}")
        print(f"    size_audience_tag: {row.get('size_audience_tag')}")
        print(f"    role_audience_tags: {', '.join(role_tags)}")
        print(f"    chunk_words: {row.get('chunk_words')}")
        print(
            f"    text_rank: {row.get('text_rank')}  "
            f"text_score: {text_score_str}  "
            f"present_in_text: {row.get('present_in_text')}"
        )
        print(
            f"    vector_rank: {row.get('vector_rank')}  "
            f"vector_similarity: {vector_similarity_str}  "
            f"present_in_vector: {row.get('present_in_vector')}"
        )
        print("    chunk_text:")
        preview = (row.get("chunk_text") or "").strip()
        print(f"    {preview[:800]}")
        if len(preview) > 800:
            print("    ...")
        print()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Retrieve chunks with hybrid RRF over text and vector retrieval."
    )
    parser.add_argument("query", help="Search query text.")
    parser.add_argument("--limit", type=int, default=5, help="Number of fused results to return.")
    parser.add_argument(
        "--fusion-pool",
        type=int,
        default=DEFAULT_FUSION_POOL,
        help="Number of results to pull from each backend before fusion.",
    )
    parser.add_argument(
        "--rrf-k",
        type=int,
        default=DEFAULT_RRF_K,
        help="RRF smoothing constant.",
    )
    parser.add_argument(
        "--size-tag",
        choices=sorted(ALLOWED_SIZE_TAGS - {"all_sizes"}),
        default=None,
        help="Optional organisation size filter.",
    )
    parser.add_argument(
        "--role-tag",
        choices=sorted(ALLOWED_ROLE_TAGS),
        default=None,
        help="Optional role filter.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    results = retrieve_chunks_hybrid(
        query=args.query,
        limit=args.limit,
        size_tag=args.size_tag,
        role_tag=args.role_tag,
        fusion_pool=args.fusion_pool,
        rrf_k=args.rrf_k,
    )
    print_results(results)


if __name__ == "__main__":
    main()