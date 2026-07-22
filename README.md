# aus-ai-security-navigator

A lightweight RAG tool that helps Australian organisations navigate official ACSC artificial intelligence security guidance. It brings together audience-specific ACSC HTML pages and PDF guidance so users can ask natural-language questions and retrieve grounded answers from the source material.

## Problem statement

Australian organisations now have access to a growing set of ACSC guidance on artificial intelligence, but the material is distributed across multiple documents, formats, and audience-specific publications. This makes it harder to quickly find the right guidance for a specific question, such as how a small business should adopt AI securely, what supply chain risks apply to an AI system, or what controls matter for AI-enabled cyber attacks.

A general LLM can provide broad advice, but it may miss the specific ACSC publication, audience context, or operational detail needed for a trustworthy answer. This project solves that problem by building a retrieval-augmented assistant over a curated ACSC AI guidance corpus, so users can ask natural-language questions and receive answers grounded in the relevant source documents.

The project is designed for questions where retrieval adds clear value over generic generation, especially when the answer depends on document-specific guidance, audience type, or operational recommendations. It focuses on making ACSC AI guidance easier to access, compare, and use without requiring users to manually search across multiple HTML pages and PDF attachments.

## Project scope

This project focuses on a small, curated corpus of ACSC AI guidance rather than a broad crawl of all cyber-security content. The aim is to build a retrieval flow that is narrow enough to evaluate clearly, but broad enough to cover key AI security guidance for different organisation types.

The current corpus includes:
- Core ACSC AI HTML guidance pages
- Attached ACSC PDF guidance on defending against AI-enabled cyber attacks
- A source manifest with provenance and metadata for each source

## Dataset and decisions

The corpus is defined in `data/source_manifest_core.csv` and built from public ACSC AI guidance sources. Source selection, corpus boundaries, and project decisions are documented in:

- `docs/dataset-notes.md`
- `docs/decisions.md`
- `docs/project-log.md`

These documents record the source set, the reasoning behind core versus boundary choices, and how the project scope evolved over time.

## Workflow

The project workflow is:

1. Define and maintain the source manifest.
2. Download source documents from public ACSC URLs.
3. Extract HTML and PDF content into local processed files.
4. Manually review and clean extracted text.
5. Prepare the processed corpus for retrieval.
6. Build and evaluate the retrieval flow.
7. Run the application or evaluation scripts.

This is a semi-manual workflow: scripts perform the initial extraction, and the resulting text is manually reviewed before ingestion.

For the detailed workflow and reproducibility steps, see `docs/reproducibility.md`.

## Repository structure

```text
.
├── data/
│   ├── raw/
│   │   ├── html/
│   │   └── pdfs/
│   ├── processed/
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
│   └── extract_pdfs.py
├── pyproject.toml
├── uv.lock
└── README.md
```

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

### 4. Manually review and edit extracted text

After extraction, review the processed outputs and correct issues such as:
- broken headings
- repeated headers or footers
- missing lists
- table structure problems
- duplicated paragraphs
- reading-order issues

## Outputs

Key outputs include:
- `data/raw/html/`
- `data/raw/pdf/`
- `data/processed/`
- `data/download_metadata.json`

## Reproducibility

This project is designed to be reproducible from a clean checkout.

- Source documents are public ACSC HTML and PDF documents.
- The corpus is defined in `data/source_manifest_core.csv`.
- Dependency versions are pinned in `pyproject.toml` and `uv.lock`.
- The end-to-end workflow is documented in `docs/reproducibility.md`.

See `docs/reproducibility.md` for detailed setup and execution steps.

## Evaluation criteria mapping

This section maps the project to the course evaluation criteria.

- **Problem description**: see `## Problem statement`
- **Ingestion pipeline**: manifest-driven downloading and semi-manual extraction
- **Reproducibility**: see `## Reproducibility` and `docs/reproducibility.md`
- **Project decisions and scope**: see `docs/decisions.md`, `docs/dataset-notes.md`, and `docs/project-log.md`

Additional sections will be expanded as the project implementation and evaluation are completed.

## Status

This project is currently focused on corpus curation, extraction, and retrieval setup for Project 1.