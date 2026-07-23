# Reproducibility

This project is designed to be reproducible from a clean checkout using a documented environment, a manifest-defined dataset, a semi-manual extraction workflow, a structure-aware chunking process, and a small manual QA step before retrieval indexing. Reproducible workflows benefit from clearly documented inputs, scripted transformations, and explicit validation points, especially where human review is part of the pipeline.

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

- The core dataset is defined in `data/source_manifest_core.csv`.
- Each row describes a single ACSC source with fields such as:
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
  - `size_audience_tag` (organisation size / criticality, e.g. `small_business`, `medium_business`, `large_enterprise_gov_critical`, `all_sizes`)
  - `role_audience_tags` (role / responsibility, e.g. `ai_consumer`, `ai_builder`, or both, stored as a `;`-separated list)

### Source documents

- All sources are public ACSC HTML pages and PDF documents.
- No private or local-only data is required; the dataset can be reconstructed by downloading from the URLs in the manifest.

## Workflow

The end-to-end workflow is:

1. **Download sources**

   Read `data/source_manifest_core.csv` and download each URL to the appropriate raw folder based on `content_type`.

   ```bash
   uv run python src/download_sources.py
   ```

2. **Extract HTML**

   Convert downloaded HTML files into local Markdown files in `data/processed/`, preserving headings, lists, and tables as far as practical.

   ```bash
   uv run python src/extract.py data/raw/html
   ```

3. **Extract PDF documents**

   Convert downloaded PDFs into local Markdown files in `data/processed/`, with attention to reading order and structural elements.

   ```bash
   uv run python src/extract_pdfs.py data/raw/pdf
   ```

4. **Manually review and edit extracted Markdown**

   Review the processed Markdown files and correct extraction issues such as:

   - broken or missing headings
   - repeated headers, footers, or navigation chrome
   - duplicated paragraphs
   - missing or malformed lists
   - table structure problems
   - PDF reading-order issues

   The corrected Markdown files form the **cleaned corpus** used for chunking and retrieval.

5. **Prepare retrieval-ready chunks**

   Use the cleaned Markdown to build the retrieval corpus in `data/chunks/chunks.jsonl`:

   - apply heading-aware chunking (chunks anchored to document titles and heading paths)
   - propagate `size_audience_tag` and `role_audience_tags` from the manifest into each chunk
   - keep lists intact where practical
   - treat tables and related risk / mitigation sections as special cases so structure and semantics are preserved
   - handle long enumerated sections by splitting into smaller item-level chunks when needed

   ```bash
   uv run python src/prepare_chunks.py
   ```

   The minimum chunk schema is:

   - `source_file`
   - `document_title`
   - `heading_path`
   - `size_audience_tag`
   - `role_audience_tags`
   - `chunk_text`

6. **Spot-check sampled chunks**

   After `data/chunks/chunks.jsonl` is produced, manually inspect a small sample of chunks before building the retrieval index. This spot-check is a lightweight QA step to confirm that the chunking rules behaved as intended across representative source types. Explicit validation steps improve reproducibility because they document how intermediate outputs are checked, not just how they are created.

   A representative spot-check should include around 10 to 15 chunks, covering one or two chunks from each important source type, for example:

   - the small-business PDF
   - the medium-business PDF
   - the government / critical infrastructure / large enterprise PDF
   - selected HTML guidance pages

   During inspection, confirm that:

   - `heading_path` reflects the cleaned Markdown structure
   - `size_audience_tag` and `role_audience_tags` match the manifest values
   - lists and tables were not broken badly
   - section groupings remain coherent where intended

   Example command:

   ```bash
   uv run python src/spotcheck_chunks.py
   ```

   Expected outputs:

   - `data/chunks/spotcheck.jsonl`
   - `data/chunks/spotcheck.json`

   The JSON array output can be opened in VS Code or another JSON viewer for easier visual inspection.

7. **Build retrieval index**

   Embed the chunks and build a retrieval index over `data/chunks/chunks.jsonl`, using manifest metadata such as `source_id`, `title`, `size_audience_tag`, and `role_audience_tags` for filtering and evaluation.

   Embedding and index-building commands depend on the chosen library or service and are documented alongside the retrieval code.

8. **Run evaluation / app**

   - Run retrieval evaluation scripts over a small set of test queries.
   - Run the application (for example, a notebook, CLI, or simple UI) to interact with the RAG assistant.

## Commands

From the project root, the core ingestion, chunk-preparation, and QA steps can be reproduced with:

```bash
uv sync
uv run python src/download_sources.py
uv run python src/extract.py data/raw/html
uv run python src/extract_pdfs.py data/raw/pdf
uv run python src/prepare_chunks.py
uv run python src/spotcheck_chunks.py
```

Adjust paths or script names as needed if local filenames differ.

## Outputs

Key outputs after running the ingestion, chunk-preparation, and spot-check workflow:

- Raw downloads:
  - `data/raw/html/` – downloaded HTML sources (e.g. `{source_id}.html`)
  - `data/raw/pdf/` – downloaded PDF sources (e.g. `{source_id}.pdf`)
- Processed Markdown:
  - `data/processed/` – extracted and manually reviewed Markdown files for each source
- Retrieval corpus:
  - `data/chunks/chunks.jsonl` – retrieval-ready chunks with the minimum schema
- Chunk QA samples:
  - `data/chunks/spotcheck.jsonl` – sampled chunks for manual review
  - `data/chunks/spotcheck.json` – JSON array version for easier visual inspection
- Provenance metadata:
  - `data/download_metadata.json` – download-time metadata including:
    - source ID, title, URL
    - local file path
    - retrieval time
    - HTTP content type
    - manifest metadata (including audience, size, and role tags)
    - status code
    - SHA-256 hash

## Notes

- **Semi-manual extraction**

  Extraction is semi-manual by design: scripts perform the initial HTML and PDF text extraction, and the extracted Markdown is then manually reviewed and edited before chunking. This is a one-time quality-improvement step for a small, curated corpus and is documented so reviewers can understand where human judgement was applied.

- **Audience-aware design**

  The manifest’s `size_audience_tag` and `role_audience_tags` fields define deterministic audience metadata per document along two dimensions (organisation size and AI responsibility). These fields are used when preparing the retrieval corpus so that chunks carry audience metadata, supporting audience-aware retrieval and evaluation.

- **Manual chunk QA**

  After `data/chunks/chunks.jsonl` is produced, a small sample of chunks can be exported for manual inspection. This spot-check is used to confirm that heading-aware chunking preserved section structure, audience metadata, and important list or table content across representative source types before retrieval indexing begins.

- **Reproducibility guarantees**

  - Environment: pinned dependencies and a documented setup command (`uv sync`).
  - Data: manifest-defined, public ACSC sources with recorded URLs and provenance metadata.
  - Workflow: each ingestion and chunking step is driven by scripts whose commands and expected outputs are documented here and in `README.md`.
  - Manual steps: the manual review of extracted Markdown is explicitly described, and cleaned files are stored in `data/processed/` for inspection.
  - Retrieval corpus: the first-build chunks are produced deterministically from the cleaned Markdown and manifest, and written to `data/chunks/chunks.jsonl`.
  - QA: a small documented spot-check step is included before retrieval indexing so intermediate corpus quality can be inspected, not only assumed.