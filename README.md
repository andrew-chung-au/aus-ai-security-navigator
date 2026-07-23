# aus-ai-security-navigator

A lightweight retrieval-augmented generation (RAG) project that helps Australian organisations navigate official ACSC artificial intelligence security guidance. It brings together audience-specific ACSC HTML pages and PDF guidance so users can ask natural-language questions and retrieve grounded answers from the source material.

---

## Problem statement

Australian organisations now have access to a growing set of ACSC guidance on artificial intelligence, but the material is distributed across multiple documents, formats, and audience-specific publications. This makes it harder to quickly find the right guidance for a specific question, such as how a small business should adopt AI securely, what supply chain risks apply to an AI system, or what controls matter for AI-enabled cyber attacks.

A general LLM can provide broad advice, but it may miss the specific ACSC publication, audience context, or operational detail needed for a trustworthy answer. This project addresses that gap by building a retrieval-augmented assistant over a curated ACSC AI guidance corpus, so users can ask natural-language questions and receive answers grounded in the relevant source documents.

The project is designed for questions where retrieval adds clear value over generic generation, especially when the answer depends on document-specific guidance, organisation size, role context, or operational recommendations.

---

## Project scope

This project focuses on a small, curated ACSC AI guidance corpus rather than a broad crawl of cyber security content. The aim is to build a retrieval flow that is narrow enough to evaluate clearly, but broad enough to cover key AI security guidance for different organisation types and use contexts.

The current corpus includes:

- Core ACSC AI HTML guidance pages
- Attached ACSC PDF guidance on defending against AI-enabled cyber attacks
- A manifest-defined source list with provenance and audience metadata
- A cleaned Markdown corpus used for chunking, retrieval, and evaluation

Boundary documents are recorded for possible later expansion, but are excluded from the current index build.

For the current corpus description and boundaries, see:

- `docs/dataset-notes.md`
- `data/source_manifest_core.csv`

---

## Documentation map

Project structure, design rationale, and reproducible execution are intentionally split across a small set of focused documents:

- `docs/dataset-notes.md` — current description of the dataset, chunking approach, audience model, and evaluation-data design
- `docs/reproducibility.md` — step-by-step runbook for rebuilding the corpus, evaluation data, and retrieval index from a clean checkout
- `docs/decisions.md` — accepted architectural and pipeline decisions
- `docs/project-log.md` — chronological implementation history and major changes

Use this README as the high-level entry point. Use the documents above as the source of truth for implementation details, reproducibility steps, and project history.

---

## Audience-aware design

The project treats ACSC AI guidance as an audience-aware corpus. The manifest separates audience context into two dimensions:

- `size_audience_tag`
  - `small_business`
  - `medium_business`
  - `large_enterprise_gov_critical`
  - `all_sizes`
- `role_audience_tags`
  - `ai_consumer`
  - `ai_builder`

This allows the retrieval corpus to represent both organisational scale and role or responsibility. These fields are propagated into each chunk and can be used as filters in retrieval and evaluation.

For the full audience model and chunk schema, see `docs/dataset-notes.md`.

---

## Evaluation design

The project includes an evaluation-data pipeline based on curated seed passages and synthetic question generation:

1. Define a curated seed manifest (`data/ground_truth_seed_draft.json`) describing important passages and audience slices to test.
2. Match each seed to a concrete chunk in `data/chunks/chunks.jsonl`.
3. Vet matched chunks with an LLM judge to produce a vetted seed file.
4. Generate synthetic evaluation questions from vetted passages (A → Q*) and store them in `data/ground_truth_synthetic.jsonl`.

This keeps the evaluation pipeline traceable: each test question can be linked back to a concrete `chunk_id`, source document, and audience slice.

For the detailed seed-matching workflow, matching heuristics, and evaluation-data structure, see:

- `docs/dataset-notes.md`
- `docs/reproducibility.md`
- `docs/decisions.md`

---

## Workflow

At a high level, the project workflow is:

1. Define and maintain the source manifest.
2. Download source documents from public ACSC URLs.
3. Extract HTML and PDF content into local Markdown files.
4. Manually review and clean extracted content.
5. Chunk the cleaned Markdown corpus into retrieval-ready records.
6. Spot-check sampled chunks for quality assurance.
7. Create and match evaluation seeds to concrete chunks.
8. Vet candidate seed passages with an LLM judge.
9. Generate synthetic ground-truth questions.
10. Build the PostgreSQL retrieval index.
11. Run text and vector retrieval plus retrieval evaluation.
12. Add the application or interface layer.

Scripts perform downloading, extraction, chunk preparation, deterministic seed matching, question generation, database loading, embedding generation, retrieval, and evaluation. For the full executable runbook, see `docs/reproducibility.md`.

---

## Repository structure

```text
.
├── data/
│   ├── raw/
│   │   ├── html/
│   │   └── pdf/
│   ├── processed/
│   ├── chunks/
│   ├── download_metadata.json
│   ├── source_manifest_core.csv
│   ├── ground_truth_seed_draft.json
│   ├── seed_chunk_candidates.json
│   ├── ground_truth_seeds_vetted.jsonl
│   └── ground_truth_synthetic.jsonl
├── docs/
│   ├── dataset-notes.md
│   ├── decisions.md
│   ├── project-log.md
│   └── reproducibility.md
├── src/
│   ├── download_sources.py
│   ├── extract.py
│   ├── extract_pdfs.py
│   ├── prepare_chunks.py
│   ├── spotcheck_chunks.py
│   ├── match_seeds_to_chunks.py
│   ├── generate_ground_truth_questions.py
│   ├── llm_client.py
│   ├── db.py
│   ├── db_init.py
│   ├── db_load_chunks.py
│   ├── db_build_embeddings.py
│   ├── retrieve_text.py
│   ├── retrieve_vector.py
│   └── evaluate_retrieval.py
├── pyproject.toml
├── uv.lock
└── README.md
```

---

## Retrieval corpus

The retrieval-ready corpus is written to:

- `data/chunks/chunks.jsonl`

Each chunk includes the core fields needed for provenance, retrieval, and evaluation:

- `chunk_id`
- `source_id`
- `source_file`
- `chunk_index`
- `chunking_version`
- `document_title`
- `heading_path`
- `size_audience_tag`
- `role_audience_tags`
- `chunk_text`

Diagnostic fields such as `chunk_chars`, `chunk_words`, and `chunk_lines` may also be present for inspection.

For the full chunking behaviour — including heading-aware chunking, list and table handling, enumerated item splitting, and document-specific patterns — see `docs/dataset-notes.md`.

---

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

For the complete environment and pipeline runbook, see `docs/reproducibility.md`.

---

## Usage

For the complete step-by-step workflow — download, extraction, cleanup, chunking, seed matching, question generation, database loading, embeddings, retrieval, and evaluation — see `docs/reproducibility.md`.

A minimal quick-start looks like this:

### 1. Download sources

```bash
uv run python src/download_sources.py
```

### 2. Extract sources

```bash
uv run python src/extract.py data/raw/html
uv run python src/extract_pdfs.py data/raw/pdf
```

### 3. Prepare chunks

```bash
uv run python src/prepare_chunks.py
```

### 4. Build and load the database

```bash
uv run python src/db_init.py
uv run python src/db_load_chunks.py
```

### 5. Run retrieval

```bash
uv run python src/retrieve_text.py "your query"
uv run python src/retrieve_vector.py "your query"
```

### 6. Run evaluation

```bash
uv run python src/evaluate_retrieval.py
```

---

## Outputs

Key outputs include:

- `data/raw/html/`
- `data/raw/pdf/`
- `data/processed/`
- `data/chunks/chunks.jsonl`
- `data/chunks/spotcheck.jsonl`
- `data/chunks/spotcheck.json`
- `data/ground_truth_seed_draft.json`
- `data/seed_chunk_candidates.json`
- `data/ground_truth_seeds_vetted.jsonl`
- `data/ground_truth_synthetic.jsonl`
- `data/download_metadata.json`

Additional database-backed retrieval artefacts are documented in `docs/reproducibility.md`.

---

## Reproducibility

This project is designed to be reproducible from a clean checkout:

- Source documents are public ACSC HTML and PDF documents.
- The corpus is defined in `data/source_manifest_core.csv`.
- Dependency versions are pinned in `pyproject.toml` and `uv.lock`.
- Retrieval chunks are produced from reviewed Markdown.
- The retrieval corpus propagates organisation size and role tags from the manifest into each chunk.
- Evaluation seeds are resolved deterministically before LLM-based vetting.
- Synthetic questions are generated from vetted seed passages and stored for later evaluation.
- A PostgreSQL-backed retrieval index supports both text and vector retrieval over the same chunk corpus.

Treat `docs/reproducibility.md` as the primary runbook for recreating the corpus, evaluation data, and retrieval setup.

---

## Evaluation criteria mapping

This section maps the project to the course evaluation criteria:

- **Problem description**: see `## Problem statement`
- **Ingestion pipeline**: see `## Workflow` and `docs/reproducibility.md`
- **Corpus design and scope**: see `## Project scope` and `docs/dataset-notes.md`
- **Project decisions**: see `docs/decisions.md` and `docs/project-log.md`
- **Reproducibility**: see `## Reproducibility` and `docs/reproducibility.md`
- **Evaluation design**: see `## Evaluation design`, `docs/dataset-notes.md`, and `docs/reproducibility.md`
- **Retrieval evaluation**: see `docs/reproducibility.md`, `docs/decisions.md`, and `docs/project-log.md`

---

## Status

The project currently includes:

- corpus scoping and manifest definition
- source downloading and extraction
- manual Markdown cleanup
- audience-aware schema design
- heading-aware chunk preparation for the retrieval corpus
- chunk spot-checking for quality assurance
- evaluation seed design, matching, and vetting
- synthetic ground-truth question generation
- PostgreSQL schema initialisation and chunk loading
- audience-aware text retrieval
- pgvector-based vector retrieval
- comparative retrieval evaluation over the synthetic question set

Current work is focused on:

- RAG answer generation over retrieved chunks
- evaluation of final LLM answers
- application or interface implementation
- possible hybrid retrieval or reranking