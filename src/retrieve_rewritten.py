from __future__ import annotations

import argparse
import json
from typing import Any

from retrieve_reranked import (
    DEFAULT_CANDIDATE_LIMIT,
    retrieve_chunks_reranked,
)
from retrieve_text import ALLOWED_ROLE_TAGS, ALLOWED_SIZE_TAGS
from retrieve_vector import resolve_limit
from rewrite_query import rewrite_query


def merge_results_by_best_rank(
    result_sets: list[list[dict[str, Any]]],
    limit: int,
) -> list[dict[str, Any]]:
    best_by_chunk_id: dict[str, dict[str, Any]] = {}

    for query_index, results in enumerate(result_sets):
        for rank, row in enumerate(results, start=1):
            chunk_id = row["chunk_id"]
            enriched = dict(row)
            enriched["rewrite_query_index"] = query_index
            enriched["rewrite_rank"] = rank

            existing = best_by_chunk_id.get(chunk_id)
            if existing is None:
                best_by_chunk_id[chunk_id] = enriched
                continue

            existing_key = (
                existing["rewrite_rank"],
                existing.get("rewrite_query_index", 0),
                -existing.get("reranker_score", float("-inf")),
                existing.get("vector_rank", 10**9),
            )
            candidate_key = (
                enriched["rewrite_rank"],
                enriched.get("rewrite_query_index", 0),
                -enriched.get("reranker_score", float("-inf")),
                enriched.get("vector_rank", 10**9),
            )

            if candidate_key < existing_key:
                best_by_chunk_id[chunk_id] = enriched

    merged = sorted(
        best_by_chunk_id.values(),
        key=lambda row: (
            row["rewrite_rank"],
            row.get("rewrite_query_index", 0),
            -row.get("reranker_score", float("-inf")),
            row.get("vector_rank", 10**9),
        ),
    )

    return merged[:limit]


def retrieve_chunks_rewritten(
    query: str,
    limit: int | None = None,
    k: int | None = None,
    size_tag: str | None = None,
    role_tag: str | None = None,
    candidate_limit: int = DEFAULT_CANDIDATE_LIMIT,
    use_original_query: bool = True,
) -> list[dict[str, Any]]:
    if not query.strip():
        return []

    resolved_limit = resolve_limit(limit=limit, k=k)

    rewritten_query, rewrite_usage = rewrite_query(query)

    queries_to_run: list[str] = []
    if use_original_query:
        queries_to_run.append(query)

    if rewritten_query not in queries_to_run:
        queries_to_run.append(rewritten_query)

    result_sets: list[list[dict[str, Any]]] = []
    for retrieval_query in queries_to_run:
        results = retrieve_chunks_reranked(
            query=retrieval_query,
            limit=resolved_limit,
            size_tag=size_tag,
            role_tag=role_tag,
            candidate_limit=candidate_limit,
        )

        annotated_results: list[dict[str, Any]] = []
        for row in results:
            item = dict(row)
            item["original_query"] = query
            item["rewritten_query"] = rewritten_query
            item["retrieval_query"] = retrieval_query
            item["rewrite_used"] = retrieval_query == rewritten_query
            item["rewrite_usage"] = (
                {
                    "prompt_tokens": getattr(rewrite_usage, "prompt_tokens", None),
                    "completion_tokens": getattr(rewrite_usage, "completion_tokens", None),
                    "total_tokens": getattr(rewrite_usage, "total_tokens", None),
                }
                if rewrite_usage is not None
                else None
            )
            annotated_results.append(item)

        result_sets.append(annotated_results)

    return merge_results_by_best_rank(result_sets, limit=resolved_limit)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rewrite a query, then retrieve ACSC chunks with reranked vector search."
    )
    parser.add_argument("query", help="Search query text.")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Number of results to return.",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=None,
        help="Backward-compatible alias for --limit.",
    )
    parser.add_argument(
        "--candidate-limit",
        type=int,
        default=DEFAULT_CANDIDATE_LIMIT,
        help="Number of vector candidates to score before reranking.",
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
        help="Optional AI role filter.",
    )
    parser.add_argument(
        "--rewrite-only",
        action="store_true",
        help="Use only the rewritten query, not original+rewritten fusion.",
    )
    args = parser.parse_args()

    results = retrieve_chunks_rewritten(
        query=args.query,
        limit=args.limit,
        k=args.k,
        size_tag=args.size_tag,
        role_tag=args.role_tag,
        candidate_limit=args.candidate_limit,
        use_original_query=not args.rewrite_only,
    )

    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()