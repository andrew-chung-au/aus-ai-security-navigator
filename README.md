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
- A reviewed Markdown corpus used for chunking, retrieval, and evaluation, preserved as a versioned snapshot under `data/corpus_snapshots/`


Boundary documents are recorded for possible later expansion, but are excluded from the current index build.


For the current corpus description and boundaries, see:


- `docs/dataset-notes.md`
- `data/source_manifest_core.csv`


For strict reproduction of the current corpus, restore the reviewed Markdown snapshot from `data/corpus_snapshots/v1_2026-07-25/` into `data/processed/` before running downstream steps. For a fresh corpus rebuild, re-run download, extraction, and manual review as described in `docs/reproducibility.md`.


---


## Documentation map


Project structure, design rationale, and reproducible execution are intentionally split across a small set of focused documents:


- `docs/dataset-notes.md` — current description of the dataset, chunking approach, audience model, and evaluation-data design
- `docs/reproducibility.md` — step-by-step runbook for rebuilding the corpus, evaluation data, retrieval index, and optional answer-generation/judge artefacts from a clean checkout
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
12. Run text, vector, and hybrid retrieval plus retrieval evaluation.
13. Optionally generate grounded answers and judge them against gold passages.
14. Add the application or interface layer.


Scripts perform downloading, extraction, chunk preparation, deterministic seed matching, question generation, database loading, embedding generation, retrieval, evaluation, and optional answer-generation/judge workflows. For the full executable runbook, see `docs/reproducibility.md`.


---


## Repository structure


```text
.
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
│   ├── ground_truth_synthetic.jsonl
│   ├── answers_vector_v1.jsonl
│   ├── answers_vector_v1_judged.jsonl
│   ├── answers_vector_v2_prompt_grounded.jsonl
│   └── answers_vector_v2_prompt_grounded_judged.jsonl
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
│   ├── retrieve_hybrid.py
│   ├── evaluate_retrieval.py
│   ├── generate_answers.py
│   └── judge_answers.py
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


For the complete environment and pipeline runbook, see `docs/reproducibility.md`.


---


## Usage


For the complete step-by-step workflow — including snapshot restore, download, extraction, cleanup, chunking, seed matching, question generation, database loading, embeddings, retrieval, evaluation, and optional answer generation and judging — see `docs/reproducibility.md`.


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


#### 1. Download sources


```bash
uv run python src/download_sources.py
```


#### 2. Extract sources


```bash
uv run python src/extract.py data/raw/html
uv run python src/extract_pdfs.py data/raw/pdf
```


#### 3. Manually review Markdown in `data/processed/`


Correct extraction artefacts without changing source meaning, then preserve the reviewed Markdown as a new corpus snapshot.


#### 4. Prepare chunks


```bash
uv run python src/prepare_chunks.py
```


#### 5. Build and load the database


```bash
uv run python src/db_init.py
uv run python src/db_load_chunks.py
uv run python src/db_build_embeddings.py
```


#### 6. Run retrieval


```bash
uv run python src/retrieve_text.py "your query"
uv run python src/retrieve_vector.py "your query"
uv run python src/retrieve_hybrid.py "your query"
```


#### 7. Run evaluation


```bash
uv run python src/evaluate_retrieval.py
```


#### 8. Optional answer generation and judging


```bash
uv run python src/generate_answers.py
uv run python src/judge_answers.py
```


---


## Outputs


Key outputs include:


- `data/raw/html/`
- `data/raw/pdf/`
- `data/processed/`
- `data/corpus_snapshots/v1_2026-07-25/`
- `data/chunks/chunks.jsonl`
- `data/chunks/spotcheck.jsonl`
- `data/chunks/spotcheck.json`
- `data/ground_truth_seed_draft.json`
- `data/seed_chunk_candidates.json`
- `data/ground_truth_seeds_vetted.jsonl`
- `data/ground_truth_synthetic.jsonl`
- `data/answers/answers_vector_v1.jsonl`
- `data/answers/answers_vector_v1_judged.jsonl`
- `data/answers/answers_vector_v2_prompt_grounded.jsonl`
- `data/answers/answers_vector_v2_prompt_grounded_judged.json`
- `data/download_metadata.json`


Additional database-backed retrieval artefacts, including the `chunks` table with full-text and vector indexes, are documented in `docs/reproducibility.md`.


---


## Reproducibility


This project is designed to be reproducible from a clean checkout:


- Source documents are public ACSC HTML and PDF documents.
- The corpus is defined in `data/source_manifest_core.csv`.
- Dependency versions are pinned in `pyproject.toml` and `uv.lock`.
- The project supports two reproducibility modes:
  - strict baseline reproduction using the reviewed Markdown snapshot in `data/corpus_snapshots/v1_2026-07-25/`
  - fresh corpus rebuild via download, extraction, manual cleanup, and snapshot creation
- Retrieval chunks are produced from reviewed Markdown.
- The retrieval corpus propagates organisation size and role tags from the manifest into each chunk.
- Evaluation seeds are resolved deterministically before LLM-based vetting.
- Synthetic questions are generated from vetted seed passages and stored for later evaluation.
- A PostgreSQL-backed retrieval index supports text, vector, and hybrid retrieval over the same chunk corpus.
- Optional grounded answers and judge annotations are preserved as derived artefacts layered on top of the retrieval and evaluation datasets.


Treat `docs/reproducibility.md` as the primary runbook for recreating the corpus, evaluation data, retrieval setup, and optional answer-generation/judge artefacts.


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

## Answer-generation and LLM-as-judge evaluation

The project now includes two answer-generation strategies that were evaluated on the same 27-question synthetic ACSC benchmark using the same fixed judge pipeline. The comparison showed that Vector v2 Prompt Grounded is the stronger answer-generation strategy, with a 96.3% pass rate compared to 81.5% for Vector v1.

### Answer-generation datasets

A vector-based RAG pipeline generates grounded answers for the synthetic question set and writes them to:

- `data/answers/answers_vector_v1.jsonl`
- `data/answers/answers_vector_v2_prompt_grounded.jsonl`

Each record typically includes:

- `question_id`, `question`, and `seed_id`
- `target_size` and `target_role`
- `gold_source_id` and `gold_chunk_id`
- `retrieved_chunks` — metadata for the top‑k chunks returned by the vector retriever (for example: `chunk_id`, `source_id`, `document_title`, `heading_path`, and a similarity score)
- `answer_text` — an audience-aware answer structured as:
  - 1–2 summary sentences grounded in ACSC guidance, plus
  - a short set of bullet points with concrete actions or checks
- `answer_chunk_ids` — the chunk IDs explicitly used to support the answer
- `grounded` — a flag indicating whether the answer is intended to rely only on corpus content
- `model_id`, `top_k`, and `usage` diagnostics

These files are treated as derived artefacts: they can be regenerated if the retriever, prompt, or model changes, and they do not introduce new primary-source content.

### LLM-as-a-judge annotations

Answer quality is evaluated by a fixed LLM-as-a-judge pipeline that compares each generated answer with its gold ACSC passage. The judged outputs are stored in:

- `data/answers/answers_vector_v1_judged.jsonl`
- `data/answers/answers_vector_v2_prompt_grounded_judged.jsonl`

For each answer, the judge:

- looks up the gold passage text via `gold_chunk_id` in `data/chunks/chunks.jsonl`
- inspects the question, gold passage, and generated answer together
- applies a rubric that:
  - focuses on semantic equivalence rather than exact wording,
  - requires that core ideas from the gold passage are present,
  - allows extra detail if it remains consistent with the gold guidance,
  - expects specific named resources or frameworks when the question explicitly asks for “specific resources” and the gold passage names them

Each judged record adds:

- `judge_model_id`
- `judge_score` — `"good"` if the answer is materially correct and sufficiently complete for the question, `"bad"` otherwise
- `judge_reasoning` — a brief explanation of why the answer was scored that way
- `judge_gold_chunk_text` and `judge_gold_heading_path`
- `judge_usage` — token-usage diagnostics

These annotations are evaluation artefacts layered on top of the existing retrieval corpus and synthetic questions. The judge was kept constant across both answer sets so the comparison is fair. The current results show that Vector v2 is the selected answer-generation strategy.

---


## Status

The project currently includes:

- corpus scoping and manifest definition
- source downloading and extraction
- manual Markdown cleanup
- reviewed corpus snapshot preservation
- audience-aware schema design
- heading-aware chunk preparation for the retrieval corpus
- chunk spot-checking for quality assurance
- evaluation seed design, matching, and vetting
- synthetic ground-truth question generation
- PostgreSQL schema initialisation and chunk loading
- MiniLM-based embedding generation and pgvector-backed vector index
- audience-aware text retrieval
- pgvector-based vector retrieval
- hybrid retrieval via reciprocal rank fusion over text and vector results
- comparative retrieval evaluation over the synthetic question set, across text, vector, and hybrid backends
- answer-generation and LLM-as-a-judge evaluation over the synthetic question set
- a selected grounded answer-generation strategy based on judge-v3 comparison results

Current work is focused on:

- refining answer generation and evaluation documentation
- application or interface implementation
- inspecting hybrid and retrieval failure cases to inform any future ranking refinements

