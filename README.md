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

The current first-build corpus includes:

- Core ACSC AI HTML guidance pages  
- Attached ACSC PDF guidance on defending against AI-enabled cyber attacks  
- A manifest-defined source list with provenance and audience metadata  
- A cleaned Markdown corpus used for chunking, retrieval, and evaluation  

Boundary documents are recorded for possible later expansion, but are excluded from the first index build.

---

## Dataset and decisions

The corpus is defined in `data/source_manifest_core.csv` and built from public ACSC AI guidance sources. Source selection, corpus boundaries, chunking assumptions, schema updates, retrieval design, and project decisions are documented in:

- `docs/dataset-notes.md`
- `docs/decisions.md`
- `docs/project-log.md`
- `docs/reproducibility.md`

These documents record:

- the first-build source set and core vs boundary distinction  
- the audience-aware corpus design (size and role)  
- the retrieval chunk schema  
- the seed-matching and evaluation-data design  
- the reasoning behind project scope and pipeline decisions  

---

## Audience-aware design

The project treats ACSC AI guidance as an audience-aware corpus. Instead of using a single audience label, the manifest separates audience context into two dimensions:

- `size_audience_tag`
  - `small_business`
  - `medium_business`
  - `large_enterprise_gov_critical`
  - `all_sizes`
- `role_audience_tags`
  - `ai_consumer`
  - `ai_builder`

This allows the retrieval corpus to represent both organisational scale and role/responsibility. For example, a document may apply to organisations of all sizes while still being primarily relevant to AI builders, AI consumers, or both.

These audience fields are propagated into each chunk and are available as filters in retrieval and evaluation (e.g. “small business AI consumer” vs “large enterprise AI builder”).

---

## Evaluation design

The project includes an evaluation-data pipeline based on a curated seed-passage workflow and synthetic question generation:

1. Create a curated seed manifest (`data/ground_truth_seed_draft.json`) describing important passages to test across:
   - `source_id`
   - `target_size`
   - `target_role`
   - `passage_type`
   - `why_this_passage`
   - `best_heading_path_guess`
   - optional `numbered_item_title_guess`
   - optional `anchor_quote`
2. Match each seed to a concrete chunk in `data/chunks/chunks.jsonl`.
3. Vet the matched chunk as a seed passage using an LLM judge, producing a vetted seed file.
4. Generate synthetic evaluation questions from the vetted seed passages (A → Q*), and store them in `data/ground_truth_synthetic.jsonl` for retrieval and RAG evaluation.

This keeps the evaluation pipeline traceable: each test question can be linked back to a concrete `chunk_id`, source document, and audience slice.

---

## Workflow

At a high level, the current workflow is:

1. Define and maintain the source manifest.  
2. Download source documents from public ACSC URLs.  
3. Extract HTML and PDF content into local Markdown files.  
4. Manually review and clean extracted content.  
5. Chunk the cleaned Markdown corpus into retrieval-ready records.  
6. Spot-check sampled chunks for quality assurance.  
7. Create a seed manifest for important passages to test.  
8. Match seeds to concrete chunks.  
9. Vet candidate seed passages with an LLM judge.  
10. Generate synthetic ground-truth questions from vetted passages.  
11. Build the retrieval index and baseline retrieval helper.  
12. Run retrieval and evaluation scripts, and later the application interface.

Scripts perform downloading, extraction, chunk preparation, deterministic seed matching, question generation, and database loading. Manual review is used once to correct extraction artefacts, and an LLM-assisted step checks seed suitability before evaluation.

For step-by-step execution details, see `docs/reproducibility.md`.

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
│   └── retrieve_text.py
├── pyproject.toml
├── uv.lock
└── README.md
```

---

## Retrieval corpus

The first retrieval-ready corpus is written to:

- `data/chunks/chunks.jsonl`

Each chunk in `data/chunks/chunks.jsonl` uses the following minimum schema:

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

This schema preserves source provenance, section context, and audience metadata without overcomplicating the first build. Diagnostic fields (`chunk_chars`, `chunk_words`, `chunk_lines`) may also be present for inspection.

The chunking process is heading-aware rather than based only on fixed-size windows. It preserves Markdown structure where practical, keeps lists intact, and can split long enumerated sections into item-level chunks when that improves retrieval focus.

---

## Seed matching and vetting

Before question generation, the evaluation pipeline resolves seeds to concrete chunks and vets them:

- `data/ground_truth_seed_draft.json` stores curated evaluation seeds.  
- `src/match_seeds_to_chunks.py` resolves each seed to a concrete chunk in `data/chunks/chunks.jsonl`.  
  - When `numbered_item_title_guess` is present, the resolver first narrows to chunks whose last heading matches that numbered item after loose normalization.  
  - Matching outputs are written to `data/seed_chunk_candidates.json`.  
- An LLM judge then reviews each matched `candidate_chunk` and decides whether it should be included as an evaluation seed passage, producing a vetted seed file (e.g. `data/ground_truth_seeds_vetted.jsonl`) used by the question-generation script.

This ensures that synthetic questions are grounded in passages that are coherent, audience-appropriate, and linked to stable chunk identifiers.

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

---

## Usage (high-level)

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
uv run python src/extract_pdfs.py data/raw/pdf
```

### 4. Manually review and clean extracted Markdown

Correct issues such as:

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

### 6. Spot-check sampled chunks

```bash
uv run python src/spotcheck_chunks.py
```

### 7. Match evaluation seeds to chunks

```bash
uv run python src/match_seeds_to_chunks.py
```

### 8. Vet matched seed passages

Run the LLM judging step over `data/seed_chunk_candidates.json` to produce `data/ground_truth_seeds_vetted.jsonl`.

### 9. Generate synthetic ground-truth questions

```bash
uv run python src/generate_ground_truth_questions.py
```

### 10. Initialise and load the retrieval index

```bash
uv run python src/db_init.py
uv run python src/db_load_chunks.py
```

### 11. Run baseline retrieval

```bash
uv run python src/retrieve_text.py "your query"
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

---

## Reproducibility

This project is designed to be reproducible from a clean checkout:

- Source documents are public ACSC HTML and PDF documents.  
- The first-build corpus is defined in `data/source_manifest_core.csv`.  
- Dependency versions are pinned in `pyproject.toml` and `uv.lock`.  
- Retrieval chunks are produced from reviewed Markdown.  
- The retrieval corpus propagates organisation size and role tags from the manifest into each chunk.  
- Evaluation seeds are resolved deterministically before LLM-based vetting.  
- Synthetic questions are generated from vetted seed passages and stored for later evaluation.  
- A PostgreSQL-backed retrieval index is built from the same chunk corpus and accessed via a small helper script.

See `docs/reproducibility.md` for detailed setup and execution steps.

---

## Evaluation criteria mapping

This section maps the project to the course evaluation criteria:

- **Problem description**: see `## Problem statement`  
- **Ingestion pipeline**: see `## Workflow`  
- **Corpus design and scope**: see `## Project scope` and `docs/dataset-notes.md`  
- **Project decisions**: see `docs/decisions.md` and `docs/project-log.md`  
- **Reproducibility**: see `## Reproducibility` and `docs/reproducibility.md`  
- **Evaluation design**: see `## Evaluation design`, `## Seed matching and vetting`, and `docs/project-log.md`  

Additional sections can be expanded as retrieval evaluation and the application layer are completed.

---

## Status

The project has completed:

- corpus scoping and manifest definition  
- source downloading and extraction  
- manual Markdown cleanup  
- audience-aware schema design  
- heading-aware chunk preparation for the first retrieval corpus  
- chunk spot-checking for quality assurance  
- initial seed-manifest creation for evaluation passages  
- deterministic seed-to-chunk matching and first-pass LLM seed vetting  
- synthetic ground-truth question generation  
- PostgreSQL schema initialisation and chunk loading  
- a baseline audience-aware text retrieval helper

Current work is focused on:

- retrieval evaluation (e.g. Hit Rate and MRR)  
- RAG answer evaluation  
- application / interface implementation