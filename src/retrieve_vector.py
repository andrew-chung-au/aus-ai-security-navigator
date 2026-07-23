from __future__ import annotations

import argparse
import json
from typing import Any

from pgvector.psycopg import register_vector
from psycopg.rows import dict_row
from sentence_transformers import SentenceTransformer

from db import get_db_connection
from retrieve_text import ALLOWED_ROLE_TAGS, ALLOWED_SIZE_TAGS


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def resolve_limit(limit: int | None = None, k: int | None = None) -> int:
    if limit is not None and k is not None and limit != k:
        raise ValueError("Pass either limit or k, or pass the same value for both.")
    if limit is not None:
        return limit
    if k is not None:
        return k
    return 5


def retrieve_chunks_vector(
    query: str,
    limit: int | None = None,
    k: int | None = None,
    size_tag: str | None = None,
    role_tag: str | None = None,
) -> list[dict[str, Any]]:
    if not query.strip():
        return []

    resolved_limit = resolve_limit(limit=limit, k=k)

    model = get_model()
    query_embedding = model.encode(query, normalize_embeddings=True)

    sql = """
    SELECT
        chunk_id,
        source_id,
        source_file,
        chunk_index,
        chunking_version,
        document_title,
        heading_path,
        size_audience_tag,
        role_audience_tags,
        chunk_text,
        chunk_chars,
        chunk_words,
        chunk_lines,
        (chunk_embedding <=> %(query_embedding)s) AS cosine_distance,
        (1 - (chunk_embedding <=> %(query_embedding)s)) AS similarity
    FROM chunks
    WHERE chunk_embedding IS NOT NULL
    """
    params: dict[str, Any] = {
        "query_embedding": query_embedding,
        "limit": resolved_limit,
    }

    if size_tag:
        sql += " AND (size_audience_tag = %(size_tag)s OR size_audience_tag = 'all_sizes')"
        params["size_tag"] = size_tag

    if role_tag:
        sql += " AND role_audience_tags @> %(role_tag_json)s::jsonb"
        params["role_tag_json"] = json.dumps([role_tag])

    sql += """
    ORDER BY cosine_distance ASC, chunk_words ASC
    LIMIT %(limit)s
    """

    conn = get_db_connection()
    register_vector(conn)

    try:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
    finally:
        conn.close()

    results: list[dict[str, Any]] = []
    for row in rows:
        results.append(
            {
                "chunk_id": row["chunk_id"],
                "source_id": row["source_id"],
                "source_file": row["source_file"],
                "chunk_index": row["chunk_index"],
                "chunking_version": row["chunking_version"],
                "document_title": row["document_title"],
                "heading_path": row["heading_path"],
                "size_audience_tag": row["size_audience_tag"],
                "role_audience_tags": row["role_audience_tags"],
                "chunk_text": row["chunk_text"],
                "chunk_chars": row["chunk_chars"],
                "chunk_words": row["chunk_words"],
                "chunk_lines": row["chunk_lines"],
                "cosine_distance": float(row["cosine_distance"]),
                "similarity": float(row["similarity"]),
            }
        )

    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Retrieve chunks from pgvector semantic search."
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
    args = parser.parse_args()

    results = retrieve_chunks_vector(
        query=args.query,
        limit=args.limit,
        k=args.k,
        size_tag=args.size_tag,
        role_tag=args.role_tag,
    )

    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()