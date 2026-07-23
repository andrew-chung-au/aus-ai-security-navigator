from __future__ import annotations

import argparse
import json
from typing import Any

from psycopg.rows import dict_row

from db import get_db_connection


ALLOWED_SIZE_TAGS = {
    "small_business",
    "medium_business",
    "large_enterprise_gov_critical",
    "all_sizes",
}

ALLOWED_ROLE_TAGS = {
    "ai_consumer",
    "ai_builder",
}


def retrieve_chunks(
    query: str,
    limit: int = 5,
    size_tag: str | None = None,
    role_tag: str | None = None,
) -> list[dict[str, Any]]:
    if not query.strip():
        return []

    where_clauses = [
        "score > 0"
    ]
    params: dict[str, Any] = {
        "query": query,
        "limit": limit,
    }

    if size_tag:
        where_clauses.append(
            "(size_audience_tag = %(size_tag)s OR size_audience_tag = 'all_sizes')"
        )
        params["size_tag"] = size_tag

    if role_tag:
        where_clauses.append("role_audience_tags @> %(role_tag_json)s::jsonb")
        params["role_tag_json"] = json.dumps([role_tag])

    sql = f"""
    WITH ranked AS (
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
            ts_rank(
                fts,
                websearch_to_tsquery('english', %(query)s),
                1
            ) AS score
        FROM chunks
    )
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
        score
    FROM ranked
    WHERE {" AND ".join(where_clauses)}
    ORDER BY score DESC, chunk_words ASC NULLS LAST
    LIMIT %(limit)s;
    """

    conn = get_db_connection()
    try:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
    finally:
        conn.close()

    return rows


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

        score = row.get("score")
        score_str = f"{score:.4f}" if isinstance(score, (int, float)) else "n/a"

        print(f"[{i}] {row['chunk_id']}  score={score_str}")
        print(f"    source_file: {row.get('source_file')}")
        print(f"    title: {row.get('document_title')}")
        print(f"    heading_path: {' > '.join(heading_path)}")
        print(f"    size_audience_tag: {row.get('size_audience_tag')}")
        print(f"    role_audience_tags: {', '.join(role_tags)}")
        print(f"    chunk_words: {row.get('chunk_words')}")
        print("    chunk_text:")
        preview = (row.get("chunk_text") or "").strip()
        print(f"    {preview[:800]}")
        if len(preview) > 800:
            print("    ...")
        print()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Retrieve chunks from PostgreSQL full-text search."
    )
    parser.add_argument("query", help="Search query text.")
    parser.add_argument("--limit", type=int, default=5, help="Number of results to return.")
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
    results = retrieve_chunks(
        query=args.query,
        limit=args.limit,
        size_tag=args.size_tag,
        role_tag=args.role_tag,
    )
    print_results(results)


if __name__ == "__main__":
    main()