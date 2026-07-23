from __future__ import annotations

import json

from sentence_transformers import SentenceTransformer
from pgvector.psycopg import register_vector

from db import get_db_connection


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
BATCH_SIZE = 32


def build_embedding_text(
    document_title: str | None,
    heading_path,
    chunk_text: str,
) -> str:
    if isinstance(heading_path, str):
        try:
            heading_path = json.loads(heading_path)
        except Exception:
            heading_path = [heading_path]

    heading_bits = heading_path or []
    breadcrumb = " > ".join(heading_bits)

    parts = []
    if document_title:
        parts.append(document_title)
    if breadcrumb:
        parts.append(breadcrumb)
    parts.append(chunk_text)

    return "\n\n".join(parts)


def fetch_rows_without_embeddings(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT chunk_id, document_title, heading_path, chunk_text
            FROM chunks
            WHERE chunk_embedding IS NULL
            ORDER BY source_id, chunk_index
            """
        )
        return cur.fetchall()


def update_batch(conn, batch_ids, batch_vectors) -> None:
    with conn.cursor() as cur:
        for chunk_id, embedding in zip(batch_ids, batch_vectors):
            cur.execute(
                """
                UPDATE chunks
                SET chunk_embedding = %s
                WHERE chunk_id = %s
                """,
                (embedding, chunk_id),
            )


def main() -> None:
    model = SentenceTransformer(MODEL_NAME)

    conn = get_db_connection()
    register_vector(conn)

    try:
        rows = fetch_rows_without_embeddings(conn)

        if not rows:
            print("No rows need embeddings.")
            return

        batch_ids = []
        batch_texts = []
        total = 0

        for chunk_id, document_title, heading_path, chunk_text in rows:
            batch_ids.append(chunk_id)
            batch_texts.append(
                build_embedding_text(document_title, heading_path, chunk_text)
            )

            if len(batch_texts) >= BATCH_SIZE:
                embeddings = model.encode(
                    batch_texts,
                    normalize_embeddings=True,
                    show_progress_bar=False,
                )
                update_batch(conn, batch_ids, embeddings)
                conn.commit()
                total += len(batch_ids)
                print(f"Embedded {total} chunks")
                batch_ids = []
                batch_texts = []

        if batch_texts:
            embeddings = model.encode(
                batch_texts,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            update_batch(conn, batch_ids, embeddings)
            conn.commit()
            total += len(batch_ids)
            print(f"Embedded {total} chunks")

    finally:
        conn.close()


if __name__ == "__main__":
    main()