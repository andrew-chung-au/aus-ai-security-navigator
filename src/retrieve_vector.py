from __future__ import annotations

import argparse
import json

from pgvector.psycopg import register_vector
from sentence_transformers import SentenceTransformer

from db import get_db_connection


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def retrieve_chunks_vector(
    query: str,
    k: int = 5,
    size_tag: str | None = None,
    role_tag: str | None = None,
) -> list[dict]:
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
        search_text,
        (chunk_embedding <=> %s) AS cosine_distance
    FROM chunks
    WHERE chunk_embedding IS NOT NULL
    """
    params: list = [query_embedding]

    if size_tag:
        sql += " AND (size_audience_tag = %s OR size_audience_tag = 'all_sizes')"
        params.append(size_tag)

    if role_tag:
        sql += " AND role_audience_tags @> %s::jsonb"
        params.append(json.dumps([role_tag]))

    sql += """
    ORDER BY chunk_embedding <=> %s ASC, chunk_words ASC
    LIMIT %s
    """
    params.extend([query_embedding, k])

    conn = get_db_connection()
    register_vector(conn)

    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
    finally:
        conn.close()

    results = []
    for row in rows:
        results.append(
            {
                "chunk_id": row[0],
                "source_id": row[1],
                "source_file": row[2],
                "chunk_index": row[3],
                "chunking_version": row[4],
                "document_title": row[5],
                "heading_path": row[6],
                "size_audience_tag": row[7],
                "role_audience_tags": row[8],
                "chunk_text": row[9],
                "chunk_chars": row[10],
                "chunk_words": row[11],
                "chunk_lines": row[12],
                "search_text": row[13],
                "cosine_distance": float(row[14]),
                "similarity": float(1 - row[14]),
            }
        )

    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("query")
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--size-tag")
    parser.add_argument("--role-tag")
    args = parser.parse_args()

    results = retrieve_chunks_vector(
        query=args.query,
        k=args.k,
        size_tag=args.size_tag,
        role_tag=args.role_tag,
    )

    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()