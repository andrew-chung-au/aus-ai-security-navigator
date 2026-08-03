# AUS AI Security Navigator

A lightweight retrieval-augmented generation (RAG) project that helps Australian organisations navigate official Australian Cyber Security Centre (ACSC) artificial intelligence security guidance.

It combines a curated ACSC HTML and PDF corpus, PostgreSQL/pgvector retrieval, reranking, grounded LLM answers, and a Streamlit interface so users can ask natural-language questions and inspect the source evidence behind each response.

## Live demo

**Try the deployed application:** [AUS AI Security Navigator — Streamlit app](http://54.167.24.156:8501/)

The deployed app includes:

- **AI Navigator** — ask ACSC AI security questions, apply organisation-size and role filters, and inspect retrieved evidence.
- **Monitoring Dashboard** — view conversation telemetry, feedback, latency, estimated cost, token usage, and audience-segment charts.

> The app is deployed as a lightweight EC2 demonstration environment for peer review. It uses the same Docker Compose runtime and evaluated default path documented in this repository: **reranked-vector retrieval plus v2 prompt-grounded answers**.

## Reviewer quick start

Use this short path to assess the project without first rebuilding the pipeline:

1. Open the [live Streamlit app](http://54.167.24.156:8501/).
2. In **AI Navigator**, ask a question such as:

   ```text
   How can a small business reduce the risk of data leakage when using AI tools?
   ```

3. Select `small_business` as the organisation-size filter and `ai_consumer` as the role filter.
4. Read the answer, then expand the evidence area to inspect retrieved ACSC chunks, document titles, headings, audience tags, and retrieval metadata.
5. Open the **Monitoring Dashboard** to inspect conversation telemetry, feedback collection, and monitoring charts.
6. Use the assessment table below to locate the repository evidence for each evaluation criterion.

## Assessment evidence

| Evaluation criterion | Target | Evidence |
|---|---:|---|
| Problem description | 2/2 | [Problem statement](#problem-statement) |
| Retrieval flow | 2/2 | [Retrieval and evaluation](#retrieval-and-evaluation), `src/`, `data/chunks/chunks.jsonl` |
| Retrieval evaluation | 2/2 | [Retrieval and evaluation](#retrieval-and-evaluation), [`docs/evaluation-notes.md`](docs/evaluation-notes.md) |
| LLM evaluation | 2/2 | [`docs/evaluation-notes.md`](docs/evaluation-notes.md), `data/answers/` |
| Interface | 2/2 | [Live Streamlit app](http://54.167.24.156:8501/), `app.py` |
| Ingestion pipeline | 1/2 | [Workflow](#workflow), [`docs/runbook.md`](docs/runbook.md), `src/download_sources.py` |
| Monitoring | 2/2 | [Live Monitoring Dashboard](http://54.167.24.156:8501/), `app.py` |
| Containerization | 2/2 | `Dockerfile`, `docker-compose.yml`, [`docs/runbook.md`](docs/runbook.md) |
| Reproducibility | 2/2 | [Setup](#setup), [Usage](#usage), [`docs/runbook.md`](docs/runbook.md), `pyproject.toml`, `uv.lock` |
| Hybrid search | +1 | `src/retrieve_hybrid.py`, [`docs/evaluation-notes.md`](docs/evaluation-notes.md) |
| Document reranking | +1 | `src/retrieve_reranked.py`, [`docs/evaluation-notes.md`](docs/evaluation-notes.md) |
| User query rewriting | +1 | `src/rewrite_query.py`, [`docs/evaluation-notes.md`](docs/evaluation-notes.md) |
| Cloud deployment | +2 | [Live Streamlit app](http://54.167.24.156:8501/), [`docs/runbook.md`](docs/runbook.md) |

The ingestion pipeline is intentionally assessed as **1/2** because it is scripted and semi-automated rather than orchestrated with a dedicated workflow tool such as Airflow, Prefect, dlt, or Kestra.

## Project includes

- A curated ACSC AI security corpus with source provenance and audience metadata
- Evaluated text, vector, reranked-vector, and hybrid retrieval
- Evaluated grounded answer-generation variants with an LLM-as-a-judge layer
- An interactive Streamlit UI with evidence inspection and feedback capture
- A monitoring dashboard with telemetry and charts
- A reproducible `uv`-based workflow and Docker Compose runtime
- A [live EC2 deployment](http://54.167.24.156:8501/) for reviewer access
- Decision records, evaluation notes, a reproducibility runbook, and rubric-based self-assessment

---

## Problem statement

Australian organisations have access to a growing set of ACSC guidance on artificial intelligence, but the material is distributed across multiple documents, formats, and audience-specific publications. This makes it harder to quickly locate the right guidance for a specific question, such as how a small business should adopt AI securely, what supply-chain risks apply to an AI system, or what controls matter for AI-enabled cyber attacks.

A general LLM can provide broad advice, but it may miss the specific ACSC publication, audience context, and operational detail needed for a trustworthy answer. This project addresses that gap by building a retrieval-augmented assistant over a curated ACSC AI guidance corpus. Users can ask natural-language questions and receive answers grounded in retrieved ACSC source material.

The project is designed for questions where retrieval adds value over generic generation, particularly when the answer depends on document-specific guidance, organisation size, role context, or operational recommendations.

---

## Project scope

This project focuses on a small, curated ACSC AI guidance corpus rather than a broad crawl of cyber-security content. The goal is to create a retrieval flow that is narrow enough to evaluate clearly while still covering key AI security guidance for different organisation types and use contexts.

The current corpus includes:

- Core ACSC AI HTML guidance pages
- Attached ACSC PDF guidance on defending against AI-enabled cyber attacks
- A manifest-defined source list with provenance and audience metadata
- A reviewed Markdown corpus used for chunking, retrieval, and evaluation, preserved as a versioned snapshot under `data/corpus_snapshots/`

Boundary documents are recorded for possible later expansion but are excluded from the current index build.

For the current corpus description and boundaries, see:

- [`docs/dataset-notes.md`](docs/dataset-notes.md)
- [`data/source_manifest_core.csv`](data/source_manifest_core.csv)

For strict reproduction of the current corpus, restore the reviewed Markdown snapshot from `data/corpus_snapshots/v1_2026-07-25/` into `data/processed/` before running downstream steps. For a fresh corpus rebuild, rerun download, extraction, and manual review as described in [`docs/runbook.md`](docs/runbook.md).

---

## Documentation map

Use this README as the high-level project entry point. The documents below provide implementation, evaluation, and reproducibility details.

| Document | Purpose |
|---|---|
| [`docs/runbook.md`](docs/runbook.md) | Step-by-step instructions for rebuilding the corpus, index, evaluation outputs, Docker runtime, and EC2 deployment |
| [`docs/evaluation-notes.md`](docs/evaluation-notes.md) | Retrieval and answer-generation evaluation setup, metrics, results, and limitations |
| [`docs/dataset-notes.md`](docs/dataset-notes.md) | Corpus scope, source provenance, chunking, audience model, and evaluation-data design |
| [`docs/decisions.md`](docs/decisions.md) | Accepted architectural and pipeline decisions |
| [`docs/self-assessment.md`](docs/self-assessment.md) | Rubric-based self-assessment, evidence, scores, and next steps |
| [`docs/project-log.md`](docs/project-log.md) | Chronological implementation history and major changes |

---

## Audience-aware design

The project treats ACSC AI guidance as an audience-aware corpus. The source manifest separates audience context into two dimensions:

- `size_audience_tag`
  - `small_business`
  - `medium_business`
  - `large_enterprise_gov_critical`
  - `all_sizes`
- `role_audience_tags`
  - `ai_consumer`
  - `ai_builder`

These fields are propagated into each chunk and can be used as filters in retrieval and evaluation.

For the full audience model and chunk schema, see [`docs/dataset-notes.md`](docs/dataset-notes.md).

---

## Retrieval and evaluation

The project includes an evaluation-data pipeline based on curated seed passages and synthetic question generation:

1. Define a curated seed manifest in `data/ground_truth_seed_draft.json` describing important passages and audience slices to test.
2. Match each seed to a concrete chunk in `data/chunks/chunks.jsonl`.
3. Vet matched chunks with an LLM judge to produce a vetted seed file.
4. Generate synthetic evaluation questions from vetted passages and store them in `data/ground_truth_synthetic.jsonl`.

This keeps the evaluation pipeline traceable: each test question can be linked back to a concrete `chunk_id`, source document, and audience slice.

Retrieval is evaluated across four backends:

- Text retrieval
- Vector retrieval
- Reranked-vector retrieval
- Hybrid retrieval

On the current 27-question synthetic benchmark, **reranked-vector retrieval** is the strongest-performing backend and is used as the default for downstream RAG flows and the interactive UI.

Query rewriting was evaluated across all four primary backends. It did not improve retrieval on the current benchmark, so it is retained as an experimental helper rather than being used in the default application path.

For detailed retrieval and answer-evaluation results, see:

- [`docs/evaluation-notes.md`](docs/evaluation-notes.md)
- [`docs/runbook.md`](docs/runbook.md)
- [`docs/dataset-notes.md`](docs/dataset-notes.md)

---

## Workflow

The project supports two reproducible workflow modes:

1. **Strict baseline reproduction** — restore the reviewed Markdown snapshot from `data/corpus_snapshots/v1_2026-07-25/` into `data/processed/`, then rebuild chunks, the PostgreSQL index, embeddings, and evaluation outputs.
2. **Fresh corpus rebuild** — download current ACSC sources, extract them into Markdown, manually review the Markdown, create or update a reviewed corpus snapshot, and then rebuild downstream artefacts.

At a high level, the workflow is:

1. Define and maintain the source manifest.
2. Download source documents from public ACSC URLs.
3. Extract HTML and PDF content into local Markdown files.
4. Manually review and clean extracted content.
5. Preserve reviewed Markdown as a versioned corpus snapshot.
6. Chunk the cleaned Markdown corpus into retrieval-ready records.
7. Spot-check sampled chunks for quality assurance.
8. Create and match evaluation seeds to concrete chunks.
9. Vet candidate seed passages with an LLM judge.
10. Generate synthetic ground-truth questions.
11. Build the PostgreSQL retrieval index with full-text and pgvector support.
12. Run text, vector, reranked-vector, and hybrid retrieval plus retrieval evaluation.
13. Generate grounded answers and judge them against gold passages.
14. Expose the evaluated default path through the Streamlit UI and monitoring dashboard.

Scripts perform downloading, extraction, chunk preparation, deterministic seed matching, question generation, database loading, embedding generation, retrieval, evaluation, answer generation, and judging. For complete executable instructions, see [`docs/runbook.md`](docs/runbook.md).

---

## Repository structure

```text
.
├── data/                          # Datasets, chunks, answer artefacts, evaluation outputs
│   ├── raw/                       # Downloaded ACSC HTML and PDF sources
│   ├── processed/                 # Extracted and reviewed Markdown
│   ├── corpus_snapshots/          # Versioned reviewed-Markdown backups
│   ├── answers/                   # Generated and judged LLM answers
│   └── chunks/                    # Retrieval-ready JSONL corpus
├── docs/                          # Runbook, decisions, evaluations, and project records
│   ├── runbook.md                 # Start here for full local reproduction
│   ├── dataset-notes.md
│   ├── evaluation-notes.md
│   ├── decisions.md
│   └── self-assessment.md
├── src/                           # Python ingestion, indexing, retrieval, evaluation, and LLM scripts
├── .streamlit/                    # Streamlit configuration
├── app.py                         # Streamlit UI and monitoring dashboard
├── docker-compose.yml             # Containerised application and database runtime
├── Dockerfile                     # Application container definition
├── pyproject.toml                 # Python dependencies and project settings
├── uv.lock                        # Locked dependency versions
└── README.md
```

---

## Retrieval corpus

The retrieval-ready corpus is written to:

```text
data/chunks/chunks.jsonl
```

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

Diagnostic fields such as `chunk_chars`, `chunk_words`, and `chunk_lines` are also stored as formal database columns for QA and chunk inspection.

For full chunking behaviour, including heading-aware chunking, list and table handling, enumerated-item splitting, and document-specific patterns, see [`docs/dataset-notes.md`](docs/dataset-notes.md).

---

## Setup

This project uses Python, `uv`, PostgreSQL, and pgvector.

### Requirements

- Python 3.13
- `uv`
- PostgreSQL
- PostgreSQL `pgvector` extension
- A configured `DATABASE_URL`

### Install dependencies

```bash
uv sync
```

Dependencies and exact versions are specified in:

- `pyproject.toml`
- `uv.lock`

Create a local `.env` file in the project root:

```bash
DATABASE_URL=postgresql://<user>:<password>@localhost:<port>/<database>
```

For the complete environment, Docker Compose, and deployment instructions, see [`docs/runbook.md`](docs/runbook.md).

---

## Usage

For the complete workflow, including snapshot restore, downloading, extraction, cleanup, chunking, seed matching, question generation, database loading, embeddings, retrieval, evaluation, answer generation, and judging, see [`docs/runbook.md`](docs/runbook.md).

### Strict baseline reproduction

To reproduce the current reviewed corpus without repeating extraction and manual cleanup:

```bash
mkdir -p data/processed
cp -iv data/corpus_snapshots/v1_2026-07-25/*.md data/processed/
```

Then rebuild the retrieval corpus and index:

```bash
uv run python src/prepare_chunks.py
uv run python src/spotcheck_chunks.py
uv run python src/db_init.py
uv run python src/db_load_chunks.py
uv run python src/db_build_embeddings.py
```

### Fresh corpus rebuild

A minimal fresh rebuild looks like this:

1. Download sources:

   ```bash
   uv run python src/download_sources.py
   ```

2. Extract HTML and PDF sources:

   ```bash
   uv run python src/extract_text_html.py data/raw/html
   uv run python src/extract_text_pdf.py data/raw/pdf
   ```

3. Manually review the Markdown in `data/processed/`, then preserve the reviewed Markdown as a new corpus snapshot.

4. Prepare chunks:

   ```bash
   uv run python src/prepare_chunks.py
   ```

5. Build and load the database:

   ```bash
   uv run python src/db_init.py
   uv run python src/db_load_chunks.py
   uv run python src/db_build_embeddings.py
   ```

6. Run retrieval with a natural-language user question:

   ```bash
   uv run python src/retrieve_text.py "How can a small business reduce the risk of data leakage when using AI tools?"
   uv run python src/retrieve_vector.py "How can a small business reduce the risk of data leakage when using AI tools?"
   uv run python src/retrieve_reranked.py "How can a small business reduce the risk of data leakage when using AI tools?"
   uv run python src/retrieve_hybrid.py "How can a small business reduce the risk of data leakage when using AI tools?"
   ```

   Query rewriting is available through `src/rewrite_query.py`, but rewritten retrieval variants are experimental and are not part of the default pipeline.

7. Generate and judge answers:

   ```bash
   uv run python src/generate_answers.py
   uv run python src/judge_answers.py
   ```

---

## Interactive UI and monitoring

### Live deployment

A reviewer-facing deployment is available at:

**[http://54.167.24.156:8501/](http://54.167.24.156:8501/)**

The deployed application runs the same Docker Compose-based stack and selected default RAG path as this repository.

### Local app run

From the project root, after preparing the database:

```bash
uv run python -m streamlit run app.py
```

### Docker Compose run

The project supports a containerised application and database runtime:

```bash
docker compose up -d postgres
docker compose run --rm bootstrap
docker compose up -d app
```

The app provides:

- **AI Navigator**
  - Free-text questions about ACSC AI security guidance
  - Optional organisation-size and role filters
  - Reranked-vector retrieval as the default backend
  - Grounded answers generated using the v2 prompt-grounded answer pipeline
  - An evidence panel showing chunk IDs, titles, headings, audience tags, and retrieval metadata

- **Monitoring Dashboard**
  - Summary metrics for conversation counts, latency, estimated cost, and feedback
  - Charts for response time, cost, token usage, conversations over time, and queries by audience segment
  - A recent-conversations table with question, answer snippet, filters, latency, cost, and tokens

The application logs to PostgreSQL tables:

- `conversations` — per-interaction telemetry including question, answer, model, audience filters, tokens, latency, estimated cost, and timestamp
- `feedback` — per-conversation thumbs-up and thumbs-down feedback

These monitoring tables do not modify the underlying corpus, evaluation data, or answer artefacts.

For local and EC2 deployment details, see [`docs/runbook.md`](docs/runbook.md).

---

## Reproducibility

This project is designed to be reproducible from a clean checkout:

- Source documents are public ACSC HTML and PDF documents.
- The corpus is defined in `data/source_manifest_core.csv`.
- Dependency versions are pinned in `pyproject.toml` and `uv.lock`.
- A reviewed corpus snapshot is available for strict baseline reproduction.
- A fresh rebuild path is documented for downloading, extraction, manual review, and snapshot creation.
- Retrieval chunks propagate organisation-size and role tags from the source manifest.
- Evaluation seeds are matched deterministically before LLM-based vetting.
- Synthetic questions are generated from vetted seed passages and preserved for retrieval evaluation.
- PostgreSQL with pgvector supports text, vector, reranked-vector, and hybrid retrieval over the same chunk corpus.
- Answer-generation and judge annotations are preserved as derived artefacts.
- Docker Compose provides a reproducible runtime for the database, bootstrap process, and Streamlit app.
- A lightweight EC2 deployment provides a live environment for reviewer access.

For detailed reproduction steps, see [`docs/runbook.md`](docs/runbook.md).

---

## Status

The project currently includes:

- Corpus scoping and source-manifest definition
- Source downloading and extraction
- Manual Markdown cleanup and a reviewed corpus snapshot
- Audience-aware schema design and heading-aware chunk preparation
- Chunk spot-checking for quality assurance
- Evaluation seed design, matching, vetting, and synthetic question generation
- PostgreSQL schema initialisation, chunk loading, and MiniLM-based embeddings through pgvector
- Evaluated text, vector, reranked-vector, and hybrid retrieval over a synthetic benchmark
- Evaluated answer-generation variants with an LLM-as-a-judge layer
- A selected default path: **reranked-vector retrieval plus v2 prompt-grounded answers**
- A Streamlit-based AI Navigator and monitoring dashboard
- Conversation and feedback logging in PostgreSQL
- Docker Compose runtime for local and reproducible execution
- A live EC2 deployment for reviewer access: [http://54.167.24.156:8501/](http://54.167.24.156:8501/)

Planned work includes:

- Formal benchmark evaluation of additional retrieval variants, such as additional reranking approaches or selective query rewriting
- Potential production hardening of the cloud deployment, including HTTPS, a custom domain, and managed secrets

---

## Notes on ACSC material

This project may reference or be inspired by guidance published by the Australian Cyber Security Centre (ACSC).

Any ACSC content is used descriptively for educational and research purposes only. The project is not affiliated with, sponsored by, or endorsed by the ACSC, the Australian Signals Directorate (ASD), or the Australian Government.

Where ACSC guidance is referenced, it is attributed and linked to the original public source material.