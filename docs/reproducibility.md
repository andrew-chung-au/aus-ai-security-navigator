# Reproducibility

## Environment
- Python 3.13
- uv
- Dependencies from `pyproject.toml` and `uv.lock`

## Data access
- Source manifest: `data/source_manifest_core.csv`
- Sources are public ACSC HTML and PDF documents

## Workflow
1. Download sources
2. Extract HTML
3. Extract PDF documents
4. Manually review and edit extracted text
5. Prepare processed corpus
6. Build retrieval index
7. Run evaluation / app

## Commands
```bash
uv sync
uv run python src/download_sources.py
uv run python src/extract.py data/raw/html
uv run python src/extract_pdf.py data/raw/pdf
```

## Outputs
- `data/raw/html/`
- `data/raw/pdf/`
- `data/processed/`
- `data/download_metadata.json`

## Notes
- Extraction is semi-manual: scripts perform the initial HTML and PDF text extraction, then the extracted text is manually reviewed and edited before ingestion.
- This manual review step is used to correct issues such as broken headings, repeated headers, missing lists, table structure, and reading-order problems.