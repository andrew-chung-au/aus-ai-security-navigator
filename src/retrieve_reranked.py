from __future__ import annotations

import argparse
import json
from typing import Any

from sentence_transformers import CrossEncoder

from retrieve_text import ALLOWED_ROLE_TAGS, ALLOWED_SIZE_TAGS
from retrieve_vector import resolve_limit, retrieve_chunks_vector


RERANKER_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"
DEFAULT_CANDIDATE_LIMIT = 20
DEFAULT_BATCH_SIZE = 16


_reranker: CrossEncoder | None = None


def get_reranker() -> CrossEncoder:
    global _reranker
    if _reranker is None:
        _reranker = CrossEncoder(RERANKER_MODEL_NAME)
    return _reranker


def retrieve_chunks_reranked(
    query: str,
    limit: int | None = None,
    k: int | None = None,
    size_tag: str | None = None,
    role_tag: str | None = None,
    candidate_limit: int = DEFAULT_CANDIDATE_LIMIT,
) -> list[dict[str, Any]]:
    if not query.strip():
        return []

    resolved_limit = resolve_limit(limit=limit, k=k)

    if candidate_limit <= 0:
        raise ValueError("candidate_limit must be positive.")
    if candidate_limit < resolved_limit:
        raise ValueError("candidate_limit must be greater than or equal to limit.")

    vector_results = retrieve_chunks_vector(
        query=query,
        limit=candidate_limit,
        size_tag=size_tag,
        role_tag=role_tag,
    )

    if not vector_results:
        return []

    pairs = [(query, row["chunk_text"]) for row in vector_results]
    reranker = get_reranker()
    scores = reranker.predict(
        pairs,
        batch_size=DEFAULT_BATCH_SIZE,
        show_progress_bar=False,
    )

    reranked_results: list[dict[str, Any]] = []

    for vector_rank, (row, score) in enumerate(zip(vector_results, scores), start=1):
        result = dict(row)
        result["vector_rank"] = vector_rank
        result["vector_similarity"] = row["similarity"]
        result["vector_cosine_distance"] = row["cosine_distance"]
        result["reranker_score"] = float(score)
        reranked_results.append(result)

    reranked_results.sort(
        key=lambda row: (-row["reranker_score"], row["vector_rank"])
    )

    return reranked_results[:resolved_limit]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Retrieve vector candidates and rerank them with a cross-encoder."
    )
    parser.add_argument("query", help="Search query text.")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Number of reranked results to return.",
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
    args = parser.parse_args()

    results = retrieve_chunks_reranked(
        query=args.query,
        limit=args.limit,
        k=args.k,
        size_tag=args.size_tag,
        role_tag=args.role_tag,
        candidate_limit=args.candidate_limit,
    )

    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()