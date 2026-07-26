# Reviewed corpus snapshot: v1_2026-07-25a

## Purpose

This directory preserves the reviewed Markdown files used as the semi-manual cleaned corpus for the current retrieval baseline of `aus-ai-security-navigator`.

These files were produced by:
1. downloading manifest-defined ACSC HTML and PDF sources,
2. extracting them into Markdown, and
3. manually correcting extraction artefacts without changing the source meaning.

This snapshot exists so the current corpus can be reproduced without rerunning extraction and manually redoing the same cleanup work.

## Contents

- reviewed Markdown files copied from `data/processed/`
- `manifest.csv` — the source manifest associated with this snapshot
- `checksums.sha256` — file checksums for snapshot verification

## How to use this snapshot

To reproduce the current corpus exactly, copy the reviewed Markdown files from this snapshot back into `data/processed/` and continue from chunk preparation onward.

Example restore command:

```bash
mkdir -p data/processed
cp -iv data/corpus_snapshots/v1_2026-07-25a/*.md data/processed/
```

Then continue with:

```bash
uv run python src/prepare_chunks.py
uv run python src/spotcheck_chunks.py
uv run python src/db_init.py
uv run python src/db_load_chunks.py
uv run python src/db_build_embeddings.py
uv run python src/evaluate_retrieval.py
```

## Important note

This snapshot should be treated as a versioned corpus input, not as a working directory.

- `data/processed/` remains the overwriteable working location for new extraction and manual cleanup.
- This snapshot should not be edited in place.
- If the corpus is updated later, create a new dated snapshot directory rather than modifying this one.