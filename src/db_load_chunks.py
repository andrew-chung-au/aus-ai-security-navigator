from __future__ import annotations

import json
from pathlib import Path

from db import get_db_connection


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CHUNKS_PATH = PROJECT_ROOT / "data" / "chunks" / "chunks.jsonl"


UPSERT_SQL = """
INSERT INTO chunks (
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
    fts
)
VALUES (
    %(chunk_id)s,
    %(source_id)s,
    %(source_file)s,
    %(chunk_index)s,
    %(chunking_version)s,
    %(document_title)s,
    %(heading_path)s::jsonb,
    %(size_audience_tag)s,
    %(role_audience_tags)s::jsonb,
    %(chunk_text)s,
    %(chunk_chars)s,
    %(chunk_words)s,
    %(chunk_lines)s,
    %(search_text)s,
    setweight(to_tsvector('english', coalesce(%(document_title)s, '')), 'A') ||
    setweight(to_tsvector('english', coalesce(%(heading_path_text)s, '')), 'B') ||
    setweight(to_tsvector('english', coalesce(%(audience_text)s, '')), 'C') ||
    setweight(to_tsvector('english', coalesce(%(chunk_text)s, '')), 'D')
)
ON CONFLICT (chunk_id) DO UPDATE SET
    source_id = EXCLUDED.source_id,
    source_file = EXCLUDED.source_file,
    chunk_index = EXCLUDED.chunk_index,
    chunking_version = EXCLUDED.chunking_version,
    document_title = EXCLUDED.document_title,
    heading_path = EXCLUDED.heading_path,
    size_audience_tag = EXCLUDED.size_audience_tag,
    role_audience_tags = EXCLUDED.role_audience_tags,
    chunk_text = EXCLUDED.chunk_text,
    chunk_chars = EXCLUDED.chunk_chars,
    chunk_words = EXCLUDED.chunk_words,
    chunk_lines = EXCLUDED.chunk_lines,
    search_text = EXCLUDED.search_text,
    fts = EXCLUDED.fts;
"""


def load_jsonl(path: Path) -> list[dict]:
    records: list[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


def normalise_heading_path(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    text = str(value).strip()
    return [text] if text else []


def normalise_role_tags(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    text = str(value).strip()
    return [text] if text else []


def dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        item = item.strip()
        if not item or item in seen:
            continue
        seen.add(item)
        output.append(item)
    return output


def build_search_text(record: dict) -> str:
    title = (record.get("document_title") or "").strip()
    heading_path = normalise_heading_path(record.get("heading_path"))
    size_tag = (record.get("size_audience_tag") or "").strip()
    role_tags = normalise_role_tags(record.get("role_audience_tags"))
    chunk_text = (record.get("chunk_text") or "").strip()

    parts = [
        title,
        " > ".join(heading_path),
        f"size: {size_tag}" if size_tag else "",
        f"roles: {', '.join(role_tags)}" if role_tags else "",
        chunk_text,
    ]
    return "\n\n".join(part for part in parts if part).strip()


def build_size_phrases(size_tag: str | None) -> list[str]:
    if size_tag == "small_business":
        return [
            "small business",
            "small organisation",
            "small company",
            "business",
            "organisation",
        ]
    if size_tag == "medium_business":
        return [
            "medium business",
            "medium-sized business",
            "mid-sized organisation",
            "business",
            "organisation",
        ]
    if size_tag == "large_enterprise_gov_critical":
        return [
            "large enterprise",
            "large organisation",
            "government organisation",
            "critical infrastructure",
            "enterprise",
            "organisation",
        ]
    if size_tag == "all_sizes":
        return [
            "small business",
            "medium business",
            "large enterprise",
            "large organisation",
            "government organisation",
            "critical infrastructure",
            "business",
            "organisation",
            "all sizes",
        ]
    return []


def build_role_phrases(role_tags: list[str]) -> list[str]:
    phrases: list[str] = []

    for tag in role_tags:
        if tag == "ai_consumer":
            phrases.extend([
                "ai consumer",
                "end user",
                "business user",
            ])
        elif tag == "ai_builder":
            phrases.extend([
                "ai builder",
                "ai developer",
                "system provider",
                "service provider",
            ])

    return phrases


def prepare_row(record: dict) -> dict:
    heading_path = normalise_heading_path(record.get("heading_path"))
    role_tags = normalise_role_tags(record.get("role_audience_tags"))

    chunk_id = record.get("chunk_id")
    if not chunk_id:
        raise ValueError("Missing chunk_id in chunk record.")

    chunk_text = (record.get("chunk_text") or "").strip()
    if not chunk_text:
        raise ValueError(f"Missing chunk_text for chunk_id={chunk_id}")

    size_tag = (record.get("size_audience_tag") or "").strip() or None
    heading_path_text = " ".join(heading_path).strip()

    size_phrases = build_size_phrases(size_tag)
    role_phrases = build_role_phrases(role_tags)
    audience_text = " ".join(dedupe_preserve_order(size_phrases + role_phrases))

    return {
        "chunk_id": chunk_id,
        "source_id": record.get("source_id"),
        "source_file": record.get("source_file"),
        "chunk_index": record.get("chunk_index"),
        "chunking_version": record.get("chunking_version"),
        "document_title": record.get("document_title"),
        "heading_path": json.dumps(heading_path, ensure_ascii=False),
        "size_audience_tag": size_tag,
        "role_audience_tags": json.dumps(role_tags, ensure_ascii=False),
        "chunk_text": chunk_text,
        "chunk_chars": record.get("chunk_chars"),
        "chunk_words": record.get("chunk_words"),
        "chunk_lines": record.get("chunk_lines"),
        "search_text": build_search_text(record),
        "heading_path_text": heading_path_text,
        "audience_text": audience_text,
    }


def main() -> None:
    if not CHUNKS_PATH.exists():
        raise FileNotFoundError(f"Chunks file not found: {CHUNKS_PATH}")

    records = load_jsonl(CHUNKS_PATH)
    rows = [prepare_row(r) for r in records]

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            for row in rows:
                cur.execute(UPSERT_SQL, row)
        conn.commit()
    finally:
        conn.close()

    print(f"Loaded {len(rows)} chunks into PostgreSQL from {CHUNKS_PATH}")


if __name__ == "__main__":
    main()