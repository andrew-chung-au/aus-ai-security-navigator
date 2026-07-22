# Reproducibility

This project is designed to be reproducible from a clean checkout using a documented environment, a manifest-defined dataset, and a semi-manual extraction workflow.

## Environment

- Python 3.13
- `uv` for environment and dependency management
- Dependencies pinned in:
  - `pyproject.toml`
  - `uv.lock`

### Setup

From the project root:

```bash
uv sync
```

This creates the Python environment and installs all dependencies at the pinned versions.

## Data access

### Source manifest

- Core dataset is defined in: `data/source_manifest_core.csv`
- Each row describes a single ACSC source with:
  - `source_id`
  - `title`
  - `url`
  - `content_type` (`html` or `pdf`)
  - `published_date`
  - `audience`
  - `primary_use_case`
  - `topic_tags`
  - `core`
  - `boundary`
  - `notes`
  - `audience_tag` (normalized audience label for retrieval, e.g. `small_business`, `medium_business`, `large_enterprise_gov_critical`, `ai_system_provider`, `general_organisation`)

### Source documents

- All sources are public ACSC HTML pages and PDF documents.
- No private or local-only data is required; the dataset can be reconstructed by downloading from the URLs in the manifest.

## Workflow

The end-to-end workflow is:

1. **Download sources**

   Read `data/source_manifest_core.csv` and download each URL to the appropriate raw folder based on `content_type`.

2. **Extract HTML**

   Convert downloaded HTML files into local text/Markdown files in `data/processed/`, preserving headings, lists, and tables as far as practical.

3. **Extract PDF documents**

   Convert downloaded PDFs into local text/Markdown files in `data/processed/`, with attention to reading order and structural elements.

4. **Manually review and edit extracted text**

   Review the processed text files and correct extraction issues such as:
   - broken or missing headings
   - repeated headers, footers, or navigation chrome
   - duplicated paragraphs
   - missing or malformed lists
   - table structure problems
   - PDF reading-order issues

   The corrected Markdown files form the cleaned corpus used for retrieval.

5. **Prepare processed corpus**

   Use the cleaned Markdown to:
   - apply heading-aware chunking (sections anchored to titles and heading paths)
   - propagate `audience_tag` from the manifest into each chunk
   - handle tables as special chunks (intact tables or row-wise text as appropriate)

6. **Build retrieval index**

   Embed the chunks and build the retrieval index over the processed corpus, using the manifest metadata (e.g. `source_id`, `title`, `audience_tag`) for filtering and evaluation.

7. **Run evaluation / app**

   - Run retrieval evaluation scripts over a small set of test queries.
   - Run the application (e.g. Streamlit or CLI) to interact with the RAG assistant.

## Commands

From the project root, the core ingestion and extraction steps can be reproduced with:

```bash
uv sync
uv run python src/download_sources.py
uv run python src/extract_text_html.py data/raw/html
uv run python src/extract_pdf.py data/raw/pdf
```

Adjust paths as needed if your extractor scripts take different arguments.

## Outputs

Key outputs after running the ingestion and extraction workflow:

- Raw downloads:
  - `data/raw/html/` – downloaded HTML sources (`{source_id}.html`)
  - `data/raw/pdf/` – downloaded PDF sources (`{source_id}.pdf`)
- Processed text:
  - `data/processed/` – extracted and manually reviewed Markdown/text files for each source
- Provenance metadata:
  - `data/download_metadata.json` – download-time metadata including:
    - source ID, title, URL
    - local file path
    - retrieval time
    - HTTP content type
    - manifest metadata (audience, tags)
    - status code
    - SHA-256 hash

Downstream corpus and index files (e.g. `data/corpus/chunks.jsonl`) are produced by later steps and are documented in the retrieval/evaluation code.

## Notes

- **Semi-manual extraction**

  Extraction is semi-manual by design: scripts perform the initial HTML and PDF text extraction, and the extracted text is then manually reviewed and edited before ingestion. This is a one-time quality-improvement step for a small, curated corpus and is documented so reviewers can understand where human judgement was applied.

- **Audience-aware design**

  The manifest’s `audience_tag` field defines a deterministic audience label per document. This label is used when preparing the retrieval corpus so that chunks carry audience metadata, supporting audience-aware retrieval and evaluation.

- **Reproducibility guarantees**

  - Environment: pinned dependencies and a documented setup command (`uv sync`).
  - Data: manifest-defined, public ACSC sources with recorded URLs and basic provenance metadata.
  - Workflow: each ingestion step is driven by scripts whose commands and expected outputs are documented here and in `README.md`.
  - Manual steps: the manual review of extracted text is explicitly described, and cleaned files are stored in `data/processed/` for inspection.