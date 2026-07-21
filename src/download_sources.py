from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import time

import pandas as pd
import requests


MANIFEST_PATH = "data/source_manifest_core.csv"
RAW_DIR = Path("data/raw")
METADATA_PATH = Path("data/download_metadata.json")


RAW_DIR.mkdir(parents=True, exist_ok=True)

manifest = pd.read_csv(MANIFEST_PATH)

session = requests.Session()
session.headers.update(
    {
        "User-Agent": "AustralianAISecurityNavigator/0.1 (educational RAG project)"
    }
)

records = []

for row in manifest.itertuples(index=False):
    print(f"Downloading: {row.source_id} -> {row.url}")

    response = session.get(row.url, timeout=30)
    response.raise_for_status()

    content = response.content
    local_file = RAW_DIR / f"{row.source_id}.html"
    local_file.write_bytes(content)

    records.append(
        {
            "source_id": row.source_id,
            "title": row.title,
            "url": row.url,
            "local_file": str(local_file),
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
            "status_code": response.status_code,
            "http_content_type": response.headers.get("Content-Type"),
            "manifest_content_type": row.content_type,
            "published_date": row.published_date,
            "audience": row.audience,
            "primary_use_case": row.primary_use_case,
            "topic_tags": row.topic_tags,
            "sha256": hashlib.sha256(content).hexdigest(),
        }
    )

    time.sleep(1)

METADATA_PATH.write_text(json.dumps(records, indent=2), encoding="utf-8")

print(f"\nDownloaded {len(records)} files.")
print(f"Metadata written to {METADATA_PATH}")