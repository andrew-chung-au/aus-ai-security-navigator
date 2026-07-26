from __future__ import annotations

from db import get_db_connection


CREATE_EXTENSION_SQL = """
CREATE EXTENSION IF NOT EXISTS vector;
"""


DROP_SQL = """
DROP TABLE IF EXISTS feedback;
DROP TABLE IF EXISTS conversations;
DROP TABLE IF EXISTS chunks;
"""


CREATE_CHUNKS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS chunks (
    chunk_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    source_file TEXT NOT NULL,
    chunk_index INTEGER,
    chunking_version TEXT,
    document_title TEXT,
    heading_path JSONB,
    size_audience_tag TEXT,
    role_audience_tags JSONB,
    chunk_text TEXT NOT NULL,
    chunk_chars INTEGER,
    chunk_words INTEGER,
    chunk_lines INTEGER,
    search_text TEXT NOT NULL,
    fts tsvector NOT NULL
);
"""


ADD_EMBEDDING_COLUMN_SQL = """
ALTER TABLE chunks
ADD COLUMN IF NOT EXISTS chunk_embedding vector(384);
"""


CREATE_CHUNKS_INDEXES_SQL = """
CREATE INDEX IF NOT EXISTS chunks_fts_idx ON chunks USING GIN (fts);
CREATE INDEX IF NOT EXISTS chunks_source_id_idx ON chunks (source_id);
CREATE INDEX IF NOT EXISTS chunks_size_audience_idx ON chunks (size_audience_tag);
CREATE INDEX IF NOT EXISTS chunks_role_tags_idx ON chunks USING GIN (role_audience_tags);
"""


CREATE_CONVERSATIONS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    model VARCHAR(100) NOT NULL,
    target_size VARCHAR(100),
    target_role VARCHAR(100),
    prompt_tokens INTEGER NOT NULL,
    completion_tokens INTEGER NOT NULL,
    total_tokens INTEGER NOT NULL,
    response_time FLOAT NOT NULL,
    cost FLOAT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL
);
"""


CREATE_FEEDBACK_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS feedback (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER REFERENCES conversations(id) ON DELETE CASCADE,
    score INTEGER NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL
);
"""


CREATE_MONITORING_INDEXES_SQL = """
CREATE INDEX IF NOT EXISTS conversations_timestamp_idx ON conversations (timestamp);
CREATE INDEX IF NOT EXISTS conversations_target_size_idx ON conversations (target_size);
CREATE INDEX IF NOT EXISTS conversations_target_role_idx ON conversations (target_role);
CREATE INDEX IF NOT EXISTS feedback_conversation_id_idx ON feedback (conversation_id);
CREATE INDEX IF NOT EXISTS feedback_timestamp_idx ON feedback (timestamp);
"""


def init_db(drop: bool = False) -> None:
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(CREATE_EXTENSION_SQL)

            if drop:
                cur.execute(DROP_SQL)

            cur.execute(CREATE_CHUNKS_TABLE_SQL)
            cur.execute(ADD_EMBEDDING_COLUMN_SQL)
            cur.execute(CREATE_CHUNKS_INDEXES_SQL)

            cur.execute(CREATE_CONVERSATIONS_TABLE_SQL)
            cur.execute(CREATE_FEEDBACK_TABLE_SQL)
            cur.execute(CREATE_MONITORING_INDEXES_SQL)

        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    init_db(drop=False)
    print("Database initialized.")