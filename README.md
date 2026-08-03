# aus-ai-security-navigator

A lightweight retrieval-augmented generation (RAG) project that helps Australian organisations navigate official ACSC artificial intelligence security guidance. It brings together audience-specific ACSC HTML pages and PDF guidance so users can ask natural-language questions and retrieve grounded answers from the source material.

The project includes:

- a curated ACSC AI security corpus with audience metadata
- evaluated text, vector, reranked vector, and hybrid retrieval
- evaluated answer-generation variants with an LLM-as-a-judge layer
- an interactive Streamlit UI with a monitoring dashboard
- a reproducible runbook and rubric-based self-assessment

---

## Problem statement

Australian organisations now have access to a growing set of ACSC guidance on artificial intelligence, but the material is distributed across multiple documents, formats, and audience-specific publications. This makes it harder to quickly find the right guidance for a specific question, such as how a small business should adopt AI securely, what supply chain risks apply to an AI system, or what controls matter for AI-enabled cyber attacks.

A general LLM can provide broad advice, but it may miss the specific ACSC publication, audience context, or operational detail needed for a trustworthy answer. This project addresses that gap by building a retrieval-augmented assistant over a curated ACSC AI guidance corpus, so users can ask natural-language questions and receive answers grounded in the relevant source documents.

The project is designed for questions where retrieval adds clear value over generic generation, especially when the answer depends on document-specific guidance, organisation size, role context, or operational recommendations.

---

## Project scope

This project focuses on a small, curated ACSC AI guidance corpus rather than a broad crawl of cyber security content. The aim is to build a retrieval flow that is narrow enough to evaluate clearly, but broad enough to cover key AI security guidance for different organisation types and use contexts.

The current corpus includes:

- core ACSC AI HTML guidance pages
- attached ACSC PDF guidance on defending against AI-enabled cyber attacks
- a manifest-defined source list with provenance and audience metadata
- a reviewed Markdown corpus used for chunking, retrieval, and evaluation, preserved as a versioned snapshot under `data/corpus_snapshots/`

Boundary documents are recorded for possible later expansion, but are excluded from the current index build.

For the current corpus description and boundaries, see:

- `docs/dataset-notes.md`
- `data/source_manifest_core.csv`

For strict reproduction of the current corpus, restore the reviewed Markdown snapshot from `data/corpus_snapshots/v1_2026-07-25/` into `data/processed/` before running downstream steps. For a fresh corpus rebuild, re-run download, extraction, and manual review as described in `docs/runbook.md`.

---

## Documentation map

Project structure, design rationale, evaluation, and reproducible execution are intentionally split across a small set of focused documents:

- `docs/dataset-notes.md` — corpus description, chunking approach, audience model, and evaluation-data design
- `docs/runbook.md` — step-by-step runbook for rebuilding the corpus, evaluation data, retrieval index, and optional answer-generation/judge artefacts from a clean checkout
- `docs/evaluation-notes.md` — retrieval and answer-generation evaluation setup, metrics, and key findings
- `docs/decisions.md` — accepted architectural and pipeline decisions
- `docs/project-log.md` — chronological implementation history and major changes
- `docs/self-assessment.md` — rubric-based self-assessment, current scores, evidence, and next steps

Use this README as the high-level entry point. Use the documents above as the source of truth for implementation details, evaluation evidence, reproducibility steps, and project history.

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
- `docs/runbook.md`
- `docs/evaluation-notes.md`

---

## Workflow

The project supports two related workflow modes:

1. **Strict baseline reproduction** — restore the reviewed Markdown snapshot from `data/corpus_snapshots/v1_2026-07-25/` into `data/processed/`, then rebuild chunks, the PostgreSQL index, embeddings, and evaluation outputs.
2. **Fresh corpus rebuild** — download current ACSC sources, extract them into Markdown, manually review the Markdown, create or update a reviewed corpus snapshot, and then rebuild downstream artefacts.

At a high level, the project workflow is:

1. Define and maintain the source manifest.
2. Download source documents from public ACSC URLs.
3. Extract HTML and PDF content into local Markdown files.
4. Manually review and clean extracted content.
5. Preserve the reviewed Markdown as a versioned corpus snapshot.
6. Chunk the cleaned Markdown corpus into retrieval-ready records.
7. Spot-check sampled chunks for quality assurance.
8. Create and match evaluation seeds to concrete chunks.
9. Vet candidate seed passages with an LLM judge.
10. Generate synthetic ground-truth questions.
11. Build the PostgreSQL retrieval index, including full-text and pgvector support.
12. Run text, vector, reranked vector, and hybrid retrieval plus retrieval evaluation.
13. Optionally generate grounded answers and judge them against gold passages.
14. Add the application or interface layer, such as the Streamlit UI and monitoring dashboard.

Scripts perform downloading, extraction, chunk preparation, deterministic seed matching, question generation, database loading, embedding generation, retrieval, evaluation, and optional answer-generation/judge workflows. For the full executable runbook, see `docs/runbook.md`.

---

## Repository structure

```text
.
├── .streamlit/
│   └── config.toml
├── data/
│   ├── raw/
│   │   ├── html/
│   │   └── pdf/
│   ├── processed/
│   ├── corpus_snapshots/
│   │   └── v1_2026-07-25/
│   ├── answers/
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
│   ├── evaluation-notes.md
│   ├── project-log.md
│   ├── runbook.md
│   └── self-assessment.md
├── src/
│   ├── db.py
│   ├── db_init.py
│   ├── db_load_chunks.py
│   ├── db_build_embeddings.py
│   ├── download_sources.py
│   ├── extract_text_html.py
│   ├── extract_text_pdf.py
│   ├── prepare_chunks.py
│   ├── spotcheck_chunks.py
│   ├── resolve_seed_draft_ids.py
│   ├── generate_ground_truth_questions.py
│   ├── evaluate_retrieval.py
│   ├── retrieve_text.py
│   ├── retrieve_vector.py
│   ├── retrieve_reranked.py
│   ├── retrieve_hybrid.py
│   ├── generate_answers_v1.py
│   ├── generate_answers.py
│   ├── judge_answers_v1.py
│   ├── judge_answers_v2.py
│   ├── judge_answers.py
│   ├── llm_client.py
│   ├── pricing.py
│   └── test_structured_output.py
├── app.py
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

Diagnostic fields such as `chunk_chars`, `chunk_words`, and `chunk_lines` are also stored as formal database columns for QA and chunk inspection.

For the full chunking behaviour — including heading-aware chunking, list and table handling, enumerated item splitting, and document-specific patterns — see `docs/dataset-notes.md`.

---

## Setup

This project uses Python, `uv`, PostgreSQL, and pgvector.

### Requirements

- Python 3.13
- `uv`
- PostgreSQL
- The PostgreSQL `pgvector` extension
- A configured `DATABASE_URL`

### Install dependencies

```bash
uv sync
```

Dependencies and versions are specified in:

- `pyproject.toml`
- `uv.lock`

Create a local `.env` file in the project root:

```bash
DATABASE_URL=postgresql://<user>:<password>@localhost:<port>/<database>
```

For the complete environment and pipeline runbook, see `docs/runbook.md`.

---

## Usage

For the complete step-by-step workflow — including snapshot restore, download, extraction, cleanup, chunking, seed matching, question generation, database loading, embeddings, retrieval, evaluation, and optional answer generation and judging — see `docs/runbook.md`.

### Strict baseline reproduction

To reproduce the current reviewed corpus without redoing extraction and manual cleanup:

```bash
mkdir -p data/processed
cp -iv data/corpus_snapshots/v1_2026-07-25/*.md data/processed/
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

### Fresh corpus rebuild

A minimal fresh rebuild looks like this:

1. Download sources:

   ```bash
   uv run python src/download_sources.py
   ```

2. Extract sources:

   ```bash
   uv run python src/extract_text_html.py data/raw/html
   uv run python src/extract_text_pdf.py data/raw/pdf
   ```

3. Manually review Markdown in `data/processed/`, then preserve the reviewed Markdown as a new corpus snapshot.

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

6. Run retrieval:

   ```bash
   uv run python src/retrieve_text.py "your query"
   uv run python src/retrieve_vector.py "your query"
   uv run python src/retrieve_reranked.py "your query"
   uv run python src/retrieve_hybrid.py "your query"
   ```

7. Run evaluation:

   ```bash
   uv run python src/evaluate_retrieval.py
   ```

8. Optional answer generation and judging:

   ```bash
   uv run python src/generate_answers.py
   uv run python src/judge_answers.py
   ```

---

## Interactive UI and monitoring

In addition to CLI scripts and evaluation workflows, the project exposes the current default RAG path through a Streamlit application with a lightweight monitoring layer.

From the project root, after completing the database bootstrap sequence:

```bash
uv run python -m streamlit run app.py
```

The app provides:

- **AI Navigator**:
  - free-text question input for ACSC AI security questions
  - optional audience filters for organisation size and role
  - reranked vector retrieval as the default backend (`top_k` configurable)
  - grounded answers generated by the v2 prompt-grounded answer pipeline
  - an evidence panel showing chunk IDs, titles, headings, audience tags, and similarity/distance metadata

- **Monitoring Dashboard**:
  - summary metrics for conversation counts, latency, cost, and feedback
  - charts for response time, cost, token usage, conversations over time, and queries by audience segment
  - a recent-conversations table with question, answer snippet, filters, latency, cost, and tokens

The app logs to PostgreSQL tables:

- `conversations` — per-interaction telemetry (question, answer, model, audience filters, tokens, latency, cost, timestamp)
- `feedback` — per-conversation thumbs-up / thumbs-down feedback

These tables support monitoring and analysis but do not modify the underlying corpus, evaluation data, or answer artefacts. See `docs/runbook.md` for details.

---

## Reproducibility and evaluation criteria

This project is designed to be reproducible from a clean checkout:

- Source documents are public ACSC HTML and PDF documents.
- The corpus is defined in `data/source_manifest_core.csv`.
- Dependency versions are pinned in `pyproject.toml` and `uv.lock`.
- The project supports:
  - strict baseline reproduction using the reviewed Markdown snapshot in `data/corpus_snapshots/v1_2026-07-25/`,
  - fresh corpus rebuild via download, extraction, manual cleanup, and snapshot creation.
- Retrieval chunks propagate organisation size and role tags from the manifest.
- Evaluation seeds are resolved deterministically before LLM-based vetting.
- Synthetic questions are generated from vetted seed passages and stored for later evaluation.
- A PostgreSQL-backed retrieval index supports text, vector, reranked vector, and hybrid retrieval over the same chunk corpus.
- Answer-generation and judge annotations are preserved as derived artefacts layered on top of the retrieval and evaluation datasets.
- An interactive UI and monitoring layer expose the evaluated default path.

For the course / rubric mapping:

- **Problem description**: see `## Problem statement`.
- **Ingestion pipeline**: see `## Workflow` and `docs/runbook.md`.
- **Corpus design and scope**: see `## Project scope` and `docs/dataset-notes.md`.
- **Retrieval evaluation**: see `docs/evaluation-notes.md` and `docs/runbook.md`.
- **LLM evaluation**: see `docs/evaluation-notes.md`.
- **Interface**: see `## Interactive UI and monitoring` and `app.py`.
- **Monitoring**: see `## Interactive UI and monitoring` and `docs/runbook.md`.
- **Reproducibility**: see `## Reproducibility and evaluation criteria` and `docs/runbook.md`.
- **Self-assessment**: see `docs/self-assessment.md`.

---

## Status

The project currently includes:

- corpus scoping and manifest definition
- source downloading and extraction
- manual Markdown cleanup and a reviewed corpus snapshot
- audience-aware schema design and heading-aware chunk preparation
- chunk spot-checking for quality assurance
- evaluation seed design, matching, vetting, and synthetic question generation
- PostgreSQL schema initialisation, chunk loading, and MiniLM-based embeddings via pgvector
- evaluated text, vector, reranked vector, and hybrid retrieval over a synthetic benchmark
- evaluated answer-generation variants with an LLM-as-a-judge layer
- a selected default path: reranked vector retrieval + v2 prompt-grounded answers
- a Streamlit-based interactive UI and monitoring dashboard
- conversation and feedback logging into PostgreSQL

Planned work includes:

- containerisation and simplified local startup
- targeted retrieval enhancements such as query rewriting or additional reranking experiments, evaluated against the existing benchmark
- future cloud deployment once the local evaluation baseline and documentation are stable

## Notes on ACSC material

This project may reference or be inspired by guidance published by the Australian Cyber Security Centre (ACSC).

Any ACSC content is used descriptively for educational and research purposes only. The project is not affiliated with, sponsored by, or endorsed by the ACSC, the Australian Signals Directorate (ASD), or the Australian Government.

Where ACSC guidance is referenced, it will be attributed and linked to the original source.

Key ACSC references include publicly available guidance on artificial intelligence security, risk management, and secure system development.