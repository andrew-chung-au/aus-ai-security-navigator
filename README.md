# aus-ai-security-navigator

A lightweight retrieval-augmented generation (RAG) project that helps Australian organisations navigate official ACSC artificial intelligence security guidance. It brings together audience-specific ACSC HTML pages and PDF guidance so users can ask natural-language questions and retrieve grounded answers from the source material.

## Problem statement

Australian organisations now have access to a growing set of ACSC guidance on artificial intelligence, but the material is distributed across multiple documents, formats, and audience-specific publications. This makes it harder to quickly find the right guidance for a specific question, such as how a small business should adopt AI securely, what supply chain risks apply to an AI system, or what controls matter for AI-enabled cyber attacks.

A general LLM can provide broad advice, but it may miss the specific ACSC publication, audience context, or operational detail needed for a trustworthy answer. This project addresses that gap by building a retrieval-augmented assistant over a curated ACSC AI guidance corpus, so users can ask natural-language questions and receive answers grounded in the relevant source documents.

The project is designed for questions where retrieval adds clear value over generic generation, especially when the answer depends on document-specific guidance, audience type, or operational recommendations. It focuses on making ACSC AI guidance easier to access, compare, and use without requiring users to manually search across multiple HTML pages and PDF attachments.

## Project scope

This project focuses on a small, curated ACSC AI guidance corpus rather than a broad crawl of cyber-security content. The aim is to build a retrieval flow that is narrow enough to evaluate clearly, but broad enough to cover key AI security guidance for different organisation types.

The current first-build corpus includes:
- Core ACSC AI HTML guidance pages
- Attached ACSC PDF guidance on defending against AI-enabled cyber attacks
- A manifest-defined source list with provenance and audience metadata
- A cleaned Markdown corpus used for chunking and retrieval

Boundary documents are recorded for possible later expansion, but are excluded from the first index build.

## Dataset and decisions

The corpus is defined in `data/source_manifest_core.csv` and built from public ACSC AI guidance sources. Source selection, corpus boundaries, chunking assumptions, and project decisions are documented in:

- `docs/dataset-notes.md`
- `docs/decisions.md`
- `docs/project-log.md`

These documents record:
- the first-build source set
- the distinction between core and boundary sources
- the audience-aware corpus design
- the retrieval chunk schema
- the reasoning behind project scope decisions

## Workflow

The current workflow is:

1. Define and maintain the source manifest.
2. Download source documents from public ACSC URLs.
3. Extract HTML and PDF content into local Markdown files.
4. Manually review and clean extracted content.
5. Chunk the cleaned Markdown corpus into retrieval-ready records.
6. Build and evaluate retrieval.
7. Run the application or evaluation scripts.

This is a semi-manual workflow. Scripts perform downloading, extraction, and chunk preparation, while the corpus is manually reviewed before retrieval ingestion.

For reproducibility and step-by-step execution details, see `docs/reproducibility.md`.

## Repository structure

```text
.
├── data/
│   ├── raw/
│   │   ├── html/
│   │   └── pdfs/
│   ├── processed/
│   ├── chunks/
│   ├── download_metadata.json
│   └── source_manifest_core.csv
├── docs/
│   ├── dataset-notes.md
│   ├── decisions.md
│   ├── project-log.md
│   └── reproducibility.md
├── src/
│   ├── download_sources.py
│   ├── extract.py
│   ├── extract_pdfs.py
│   └── chunk_markdown.py
├── pyproject.toml
├── uv.lock
└── README.md
```

## Retrieval corpus

The first retrieval-ready corpus is written to:

- `data/chunks/chunks.jsonl`

Each chunk in `data/chunks/chunks.jsonl` uses the following minimum schema:

- `source_file`
- `document_title`
- `heading_path`
- `audience_tag`
- `chunk_text`

This schema preserves source provenance, section context, and audience metadata without overcomplicating the first build.

The chunking process is heading-aware rather than based only on fixed-size windows. It preserves Markdown structure where practical, keeps lists intact, and can split long enumerated sections into item-level chunks when that improves retrieval focus.

## Setup

This project uses Python and `uv` for environment and dependency management.

### Requirements
- Python 3.13
- `uv`

### Install dependencies

```bash
uv sync
```

Dependencies and versions are specified in:
- `pyproject.toml`
- `uv.lock`

## Usage

### 1. Download sources

```bash
uv run python src/download_sources.py
```

### 2. Extract HTML sources

```bash
uv run python src/extract.py data/raw/html
```

### 3. Extract PDF sources

```bash
uv run python src/extract_pdfs.py data/raw/pdfs
```

### 4. Manually review and clean extracted Markdown

After extraction, review the processed outputs and correct issues such as:
- broken headings
- repeated headers or footers
- missing or malformed lists
- duplicated paragraphs
- table structure problems
- PDF reading-order issues

### 5. Build retrieval chunks

```bash
uv run python src/prepare_chunks.py
```

## Outputs

Key outputs include:
- `data/raw/html/`
- `data/raw/pdfs/`
- `data/processed/`
- `data/chunks/chunks.jsonl`
- `data/download_metadata.json`

## Reproducibility

This project is designed to be reproducible from a clean checkout.

- Source documents are public ACSC HTML and PDF documents.
- The first-build corpus is defined in `data/source_manifest_core.csv`.
- Dependency versions are pinned in `pyproject.toml` and `uv.lock`.
- The end-to-end workflow is documented in `docs/reproducibility.md`.
- Retrieval chunks are produced from reviewed Markdown rather than directly from raw source files.

See `docs/reproducibility.md` for detailed setup and execution steps.

## Evaluation criteria mapping

This section maps the project to the course evaluation criteria.

- **Problem description**: see `## Problem statement`
- **Ingestion pipeline**: see `## Workflow`
- **Corpus design and scope**: see `## Project scope` and `docs/dataset-notes.md`
- **Project decisions**: see `docs/decisions.md` and `docs/project-log.md`
- **Reproducibility**: see `## Reproducibility` and `docs/reproducibility.md`

Additional sections can be expanded as retrieval evaluation and the application layer are completed.

## Status

The project has completed:
- corpus scoping and manifest definition
- source downloading and extraction
- manual Markdown cleanup
- minimum chunk schema definition
- heading-aware chunk preparation for the first retrieval corpus

Current work is focused on retrieval indexing, testing, and evaluation.