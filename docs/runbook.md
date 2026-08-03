# Runbook

This project is designed so another person can recreate the Python environment, rebuild the ACSC corpus and PostgreSQL retrieval index, regenerate or reuse evaluation artefacts, rerun comparative retrieval evaluation, launch the interactive app locally, and reproduce the lightweight cloud deployment used for reviewer access.

The workflow combines manifest-defined source ingestion, scripted transformations, documented manual checkpoints, versioned generated artefacts, a Docker Compose runtime path, and a small AWS EC2 deployment for live demonstration. This document focuses on environment, inputs, execution steps, manual checkpoints, deployment steps, and outputs rather than re-explaining the project rationale.

---

## 1. Environment

### Requirements

- Python 3.13
- `uv` for environment and dependency management
- PostgreSQL
- The PostgreSQL `pgvector` extension
- A PostgreSQL database user with permission to create or enable the `vector` extension
- Internet access for:
  - downloading public ACSC source documents
  - downloading the configured sentence-transformers embedding model on first use, if not already cached
  - LLM-assisted seed vetting, synthetic-question generation, answer generation, and answer judging when regenerating those artefacts

### Python setup

From the project root:

```bash
uv sync
```

This creates the Python environment and installs dependencies at the pinned versions defined in:

- `pyproject.toml`
- `uv.lock`

These files are committed to the repository and should not be edited casually; they are part of the reproducibility contract.

### Database configuration

Create a local `.env` file in the project root:

```bash
DATABASE_URL=postgresql://<user>:<password>@localhost:<port>/<database>
```

Do not commit `.env` or database credentials. A `.env.example` file should be committed with the required variable name and a placeholder value.

Before running database scripts:

1. Ensure the target PostgreSQL database exists.
2. Ensure the connected user can create or enable the `vector` extension.
3. Confirm that `DATABASE_URL` points to the intended database.

The project database helper in `src/db.py` loads `DATABASE_URL` from `.env` and exposes the shared connection logic used by database scripts.

### Streamlit configuration

The repository includes a local Streamlit configuration file at:

```text
.streamlit/config.toml
```

with:

```toml
[server]
fileWatcherType = "none"
runOnSave = false
```

This disables Streamlit file watching and automatic reruns on save. The setting is included because it avoids environment-specific watcher and rerun issues observed during local development and helps keep app behaviour stable when running `app.py`.

### Embedding model

The vector retrieval pipeline uses the sentence-transformers model configured in `src/db_build_embeddings.py` and `src/retrieve_vector.py`.

Record the exact identifier used by the code here before treating a run as a strict baseline:

```text
Embedding model: sentence-transformers/all-MiniLM-L6-v2
Embedding dimension: 384
Embedding normalisation: L2-normalised before storage and query-time comparison
Distance metric: cosine distance through pgvector
```

---

## 2. Data and manifest

### Source manifest

The core dataset is defined in:

```text
data/source_manifest_core.csv
```

Each row describes one ACSC source. Fields include:

- identifiers:
  - `source_id`
  - `title`
  - `url`
- source metadata:
  - `content_type` (`html` or `pdf`)
  - `published_date`
  - `primary_use_case`
  - `topic_tags`
- corpus scope:
  - `core`
  - `boundary`
  - `notes`
- audience metadata:
  - `size_audience_tag`
  - `role_audience_tags`

The current size vocabulary is:

- `small_business`
- `medium_business`
- `large_enterprise_gov_critical`
- `all_sizes`

The current role vocabulary is:

- `ai_consumer`
- `ai_builder`
- both roles, stored as a delimited source-manifest value and normalised downstream into an array

The manifest is the single source of truth for in-scope ACSC documents and their document-level metadata.

### Source documents

- All sources are public ACSC HTML pages or PDF documents.
- A fresh clone can recreate raw inputs by downloading URLs recorded in `data/source_manifest_core.csv`.
- Boundary sources may be documented in the manifest but are deliberately excluded from the current retrieval index.

ACSC may update source pages or PDFs. A new download can therefore differ from the original project run. For strict reproduction of a prior corpus version, retain or archive the original `data/raw/` files, reviewed `data/processed/` Markdown files, and generated `data/chunks/chunks.jsonl`.

---

## 3. Pipeline and scripts

This section describes the execution path from a clean checkout to a retrieval-ready corpus, comparative retrieval evaluation, optional answer-generation evaluation, and the interactive application.

It assumes that:

```bash
uv sync
```

has already completed and `DATABASE_URL` is configured.

### Reproduction modes

This project supports two related, but distinct, workflows:

1. **Strict v1 baseline reproduction**  
   Restore the reviewed Markdown snapshot, then rebuild chunks, the PostgreSQL index, embeddings, and retrieval metrics. Use this path to reproduce the current evaluated corpus and retrieval baseline.

2. **Fresh corpus rebuild**  
   Download current ACSC sources, extract them, manually review the generated Markdown, and create a new reviewed corpus snapshot before rebuilding downstream artefacts. Use this path when intentionally updating the corpus.

Do not treat a fresh download and extraction as equivalent to strict v1 reproduction, because ACSC source documents, extraction outputs, and semi-manual Markdown cleanup may differ.

### 3.1 Download source documents

To build a new corpus from upstream ACSC sources, download all manifest-defined core sources:

```bash
uv run python src/download_sources.py
```

This script:

- reads `data/source_manifest_core.csv`
- downloads HTML pages into `data/raw/html/`
- downloads PDFs into `data/raw/pdf/`
- writes download provenance to:

```text
data/download_metadata.json
```

For strict v1 reproduction using the existing snapshot, you can skip this step and restore the snapshot instead.

### 3.2 Extract sources into Markdown

Extract HTML:

```bash
uv run python src/extract_text_html.py data/raw/html
```

Extract PDFs:

```bash
uv run python src/extract_text_pdf.py data/raw/pdf
```

These scripts:

- parse or extract raw source content
- write first-pass Markdown files to:

```text
data/processed/
```

At this point, all in-scope source documents should exist as Markdown files in `data/processed/`.

### 3.3 Reviewed corpus snapshot

Manual Markdown review is a semi-manual quality-control step, so a fresh extraction may not reproduce the exact reviewed corpus used for the current retrieval baseline.

The repository preserves the reviewed Markdown used by the current corpus as a versioned snapshot, for example:

```text
data/corpus_snapshots/v1_2026-07-25/
```

This snapshot contains:

- reviewed Markdown files copied from `data/processed/`
- `manifest.csv` — the source manifest associated with this snapshot
- `checksums.sha256` — file checksums for snapshot verification

To reproduce the current baseline, restore the snapshot into the working processed-corpus directory:

```bash
mkdir -p data/processed
cp -iv data/corpus_snapshots/v1_2026-07-25/*.md data/processed/
```

Then continue from chunk preparation onward.

The `data/processed/` directory remains the overwriteable working location for new extraction and manual cleanup. The snapshot directory should not be modified in place; if the corpus is updated later, create a new dated snapshot directory and document the change in `docs/project-log.md`.

### 3.4 Manual Markdown review

Perform a one-time manual review of the Markdown files in `data/processed/`.

Typical corrections include:

- broken, missing, or misplaced headings
- repeated headers, footers, page numbers, or navigation text
- duplicated paragraphs
- malformed or missing lists
- table-structure problems
- PDF reading-order artefacts
- paragraphs placed under an incorrect heading after extraction

The purpose is to remove extraction noise and restore document structure, not to rewrite ACSC guidance or alter meaning.

The reviewed Markdown files are the cleaned corpus used by `src/prepare_chunks.py`.

#### Manual-review limitation

Markdown cleanup is a documented manual checkpoint rather than a fully deterministic transformation. For strict reproduction of the current corpus, use the reviewed Markdown snapshot under:

```text
data/corpus_snapshots/
```

rather than repeating the cleanup.

If upstream ACSC documents, extraction tools, or Markdown structure change:

1. Repeat the manual review on the new `data/processed/` files.
2. Record meaningful corpus changes in `docs/project-log.md`.
3. Create a new snapshot directory under `data/corpus_snapshots/` for the updated reviewed corpus.
4. Regenerate downstream chunk, database, embedding, and evaluation artefacts.
5. Treat the result as a new corpus version rather than assuming direct metric comparability.

### 3.5 Prepare retrieval chunks

Generate the retrieval-ready corpus:

```bash
uv run python src/prepare_chunks.py
```

The script:

- reads reviewed Markdown files from `data/processed/`
- uses heading-aware, structure-preserving chunking
- propagates document-level audience metadata from the manifest
- writes retrieval-ready records to:

```text
data/chunks/chunks.jsonl
```

Each chunk includes fields such as:

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
- diagnostic fields:
  - `chunk_chars`
  - `chunk_words`
  - `chunk_lines`

`data/chunks/chunks.jsonl` is the canonical text representation of the retrieval corpus.

### 3.6 Spot-check chunks

Export a sample of chunks for manual quality assurance:

```bash
uv run python src/spotcheck_chunks.py
```

The script reads:

```text
data/chunks/chunks.jsonl
```

and writes:

```text
data/chunks/spotcheck.jsonl
data/chunks/spotcheck.json
```

Review sampled records to confirm that:

- `heading_path` reflects the reviewed Markdown structure
- `size_audience_tag` and `role_audience_tags` are correctly propagated
- lists and tables remain sufficiently coherent
- risk/mitigation and other paired content remains together where intended
- no obvious extraction or chunking artefact has been introduced

This is a lightweight QA checkpoint between chunking and retrieval indexing. It increases confidence in corpus structure but does not replace retrieval evaluation.

### 3.7 Define evaluation seeds

Edit the curated seed configuration:

```text
data/ground_truth_seed_draft.json
```

Each seed describes an important ACSC passage and audience slice to test. Typical fields include:

- `source_id`
- `target_size`
- `target_role`
- `passage_type`
- `why_this_passage`
- `best_heading_path_guess`
- optional `numbered_item_title_guess`
- optional `anchor_quote`

Seeds are evaluation design inputs, not ground truth by themselves.

### 3.8 Resolve seed draft IDs

Resolve seed intents to concrete chunk IDs:

```bash
uv run python src/resolve_seed_draft_ids.py
```

The script:

- reads:
  - `data/chunks/chunks.jsonl`
  - `data/ground_truth_seed_draft.json`
- groups candidate chunks by `source_id`
- prefers matching a numbered item when `numbered_item_title_guess` is supplied
- otherwise ranks chunks using heading-path, leaf-heading, title, and anchor-quote signals
- writes candidate selections and debugging information to:

```text
data/seed_chunk_candidates.json
```

Output records include:

- `candidate_chunk`
- `candidate_debug`
- `match_score`
- `selection_confidence`
- `score_margin`
- `selection_strategy`

### 3.9 Vet seed passages

Vet matched seed passages with the project's LLM-assisted seed-review workflow.

The vetting process uses the selected `candidate_chunk` and records whether the passage is appropriate for synthetic question generation. The output is:

```text
data/ground_truth_seeds_vetted.jsonl
```

Vetted records include fields such as:

- `seed_id`
- `chunk_id`
- `include_for_eval`
- `seed_quality`
- `suggested_passage_type`
- `reason`

Use the exact repository entry point that performs seed vetting. If the vetting workflow is currently a one-off invocation rather than a committed script, document the exact command or add a dedicated script before describing this stage as fully reproducible.

#### LLM-assisted pipeline limitation

Seed vetting uses an external LLM service, so regenerated judgements may vary across model versions, provider behaviour, and runs.

The committed vetted-seed output is the canonical input for reproducing the current benchmark. Regenerating it should be treated as creating a new evaluation-data version, not as an expectation of byte-for-byte identical results.

### 3.10 Generate synthetic questions

Generate A → Q* synthetic retrieval questions from vetted seed passages:

```bash
uv run python src/generate_ground_truth_questions.py
```

The script:

- reads vetted seeds from:

```text
data/ground_truth_seeds_vetted.jsonl
```

- uses the matched `candidate_chunk` and audience metadata as generation context
- generates one realistic question per included seed
- writes outputs to:

```text
data/ground_truth_synthetic.jsonl
```

Generated records retain provenance and audience fields, including:

- `chunk_id`
- `source_id`
- `size_audience_tag`
- `role_audience_tags`
- `target_size`
- `target_role`
- generated question text

Batch generation uses retry handling from `src/llm_client.py` and pacing in the batch script to reduce API-rate-limit failures.

#### Synthetic-benchmark limitation

The synthetic benchmark is seed-anchored: each question is generated from a vetted ACSC passage linked to a known chunk.

It supports controlled retrieval comparison because each question has traceable gold evidence. It does not by itself establish performance on naturally phrased user questions, incomplete audience context, ambiguous requests, adversarial wording, or multi-source information needs.

The committed file:

```text
data/ground_truth_synthetic.jsonl
```

is the canonical evaluation input for reproducing the current reported retrieval baseline.

### 3.11 Initialise PostgreSQL

Create the retrieval schema and required database extension:

```bash
uv run python src/db_init.py
```

The script:

- creates the PostgreSQL `vector` extension if available
- creates the `chunks` table
- creates supporting indexes for:
  - full-text search
  - source ID
  - organisation-size metadata
  - role metadata
  - vector retrieval, where configured

The `chunks` table is the canonical database-backed retrieval index. It contains chunk provenance, audience metadata, text-search fields, and vector embeddings after the embedding-build step.

### 3.12 Load chunks into PostgreSQL

Load the canonical JSONL corpus:

```bash
uv run python src/db_load_chunks.py
```

The script:

- reads:

```text
data/chunks/chunks.jsonl
```

- normalises `heading_path` and `role_audience_tags` into JSON arrays
- constructs `search_text` from:
  - document title
  - heading path
  - audience metadata
  - chunk text
- upserts rows into the `chunks` table using `chunk_id` as the key

The loader can be rerun safely after corpus changes. If source content, chunking, or metadata changes, rerun this step before rebuilding embeddings and evaluation baselines.

### 3.13 Build pgvector embeddings

Build or refresh vector embeddings for indexed chunks:

```bash
uv run python src/db_build_embeddings.py
```

The script:

- loads the configured local sentence-transformers model once
- reads chunk records from the PostgreSQL `chunks` table
- creates normalised embeddings from `chunk_text` and any supporting fields configured by the script
- writes vectors into the pgvector `chunk_embedding` column
- logs progress while processing chunks

Run this script whenever:

- the chunk corpus changes
- the embedded text representation changes
- the embedding model changes
- embeddings have not yet been built after a fresh database initialisation

### 3.14 Run manual retrieval checks

The repository provides four audience-aware retrieval helpers.

Text retrieval:

```bash
uv run python src/retrieve_text.py "your query"
```

Vector retrieval:

```bash
uv run python src/retrieve_vector.py "your query"
```

Reranked vector retrieval:

```bash
uv run python src/retrieve_reranked.py "your query"
```

Hybrid retrieval:

```bash
uv run python src/retrieve_hybrid.py "your query"
```

All retrieval helpers support optional audience filters:

```bash
--size-tag <size_audience_tag>
--role-tag <role_audience_tag>
```

For example:

```bash
uv run python src/retrieve_reranked.py \
  "How can a small business reduce the risk of data leakage when using AI tools?" \
  --size-tag small_business \
  --role-tag ai_consumer \
  --limit 5
```

Audience semantics are consistent across retrievers:

- a requested size returns chunks tagged with that size and chunks tagged `all_sizes`
- a requested role returns chunks containing that role in `role_audience_tags`
- no filter returns eligible chunks without applying the corresponding audience constraint

Query rewriting helper (experimental):

```bash
uv run python src/rewrite_query.py "your query"
```

This helper rewrites a user query into a single retrieval-friendly query while preserving audience constraints and expanding vague wording. The rewritten query can then be passed to any of the retrieval helpers above. Query rewriting was evaluated on the frozen 27-question benchmark but did not improve the best-performing backend, so it is not used by the default UI or evaluation path and should be treated as an experimental tool.

### 3.15 Run comparative retrieval evaluation

Evaluate text, vector, reranked vector, and hybrid retrieval against the same synthetic question set:

```bash
uv run python src/evaluate_retrieval.py
```

The evaluator:

- reads:

```text
data/ground_truth_synthetic.jsonl
```

- evaluates:
  - `src/retrieve_text.py`
  - `src/retrieve_vector.py`
  - `src/retrieve_reranked.py`
  - `src/retrieve_hybrid.py`
- calculates, for each backend:
  - strict Hit@k
  - strict MRR
  - relaxed Hit@k
  - relaxed MRR

Strict metrics require an exact `chunk_id` match.

Relaxed metrics allow partial relevance where a retrieved chunk shares:

- the same `source_id`, and
- the same leaf heading, meaning the final element of `heading_path`

The evaluator prints a backend-specific metric summary so results can be compared under the same corpus, question set, audience metadata, and relevance rules.

The evaluator focuses on the four main backends (`text`, `vector`, `vector_reranked`, `hybrid`). Rewritten variants (`text_rewritten`, `vector_rewritten`, `vector_reranked_rewritten`, `hybrid_rewritten`) were also implemented and compared in project experiments, but they are not part of the primary metric summary reported here. They remain available for inspection and future selective-rewrite experiments.

### 3.16 Export retrieval debug records

Optionally write backend-specific per-question debug output:

```bash
uv run python src/evaluate_retrieval.py \
  --debug-output data/eval/retrieval_debug.jsonl
```

Use the actual configured output path consistently across the repository. If the current script uses a different filename, update this command and all documentation to match it.

The debug output contains one record per question and backend, including:

- question text
- audience fields:
  - `target_size`
  - `target_role`
- gold labels:
  - `chunk_id`
  - `source_id`
  - leaf heading
- strict and relaxed relevance flags or scores
- retrieved top-k metadata

Backend-specific debug data includes:

- text:
  - rank
  - text-search score
- vector:
  - rank
  - cosine distance
  - similarity
- reranked vector:
  - rank
  - reranker score
  - vector rank
  - vector similarity, where available
- hybrid:
  - rank
  - `hybrid_score`
  - `text_rank`
  - `vector_rank`
  - `text_score`
  - `vector_similarity`, where available

Use this file to inspect cases where:

- reranking improves on vector retrieval
- vector succeeds while text or hybrid fails
- hybrid helps or harms relative to vector
- the gold chunk is missed but a same-section partial match appears
- audience metadata or source overlap affects ranking

### 3.17 Selected retrieval baseline

The current project evaluates text, vector, reranked vector, and hybrid retrieval over the same synthetic benchmark.

On the current benchmark:

- text retrieval is retained as a lexical baseline and debugging path
- hybrid reciprocal-rank fusion improves on text retrieval
- vector retrieval is strong
- reranked vector retrieval is the strongest-performing backend
- query rewriting was evaluated across all four main backends (`text`, `vector`, `vector_reranked`, `hybrid`) using a dedicated LLM-based rewrite helper (`src/rewrite_query.py`). On the frozen 27-question synthetic benchmark, rewritten variants did not improve the best-performing backend and generally reduced strict metrics or produced only marginal differences. The strongest overall backend remains `vector_reranked` without rewrite.

Accordingly, `src/retrieve_reranked.py` is the preferred retrieval baseline for the first answer-generation stage. Plain vector retrieval, text retrieval, hybrid retrieval, and rewrite-enabled variants remain available as reproducible comparison and debugging backends. Any future query rewriting, hybrid weighting, embedding-model change, or reranking change should be evaluated against the current reranked-vector baseline rather than assumed to be an improvement. Query rewriting is explicitly treated as an experimental helper, not part of the default retrieval path.

### 3.18 Vector-based answer generation and LLM-as-judge evaluation

In addition to retrieval evaluation, the project preserves a derived answer-generation and judge layer that operates on the existing retrieval corpus and synthetic question set.

The answer-generation pipeline has evolved alongside the retrieval baselines. Earlier answer artefacts were generated using plain vector retrieval to fairly compare prompt variants. The current default answer-generation path uses the reranked vector retrieval backend together with the v2 prompt-grounded strategy. All answer-generation experiments and the current default path use non-rewritten retrieval queries, consistent with the decision not to adopt query rewriting as the default retrieval step.

#### 3.18.1 Generate grounded answers (reranked vector + v2 prompt)

Generate grounded answers for the synthetic question set using the current default retrieval path (reranked vector retrieval + v2 prompt-grounded pipeline):

```bash
uv run python src/generate_answers.py
```

This script:

- reads synthetic questions from `data/ground_truth_synthetic.jsonl`
- uses the selected retrieval backend (`retrieve_reranked.py`) with `top_k=5` by default, and audience filters derived from:
  - `target_size`
  - `target_role`
- assembles a structured list of retrieved chunks per question, including reranker scores and vector ranks
- calls the LLM client helper to generate a grounded answer conditioned on:
  - the question
  - the retrieved chunk metadata and text
  - the audience intent
- writes one JSON object per question to:

```text
data/answers/answers_vector_reranked_v2_prompt_grounded.jsonl
```

This file is the current default answer-generation artefact for downstream judging and comparison.

##### Frozen baseline artefacts

The project preserves earlier answer-generation outputs as frozen baselines:

- `data/answers/answers_vector_v1.jsonl` — earlier answer-generation variant
- `data/answers/answers_vector_v2_prompt_grounded.jsonl` — plain vector retrieval + v2 prompt (frozen baseline)

These were generated using the plain vector retriever to fairly evaluate the v1 and v2 prompts against one another. They should be treated as historical reference points, not regenerated unless intentionally creating a new baseline version.

If you regenerate answers today using the live default reranked-vector path, the output metrics and contents will differ from the frozen historical benchmarks because the underlying retrieval backend has changed.

##### Output schema

Each record in `answers_vector_reranked_v2_prompt_grounded.jsonl` typically includes:

- `question_id`, `question`, `seed_id`
- `target_size`, `target_role`
- `gold_source_id`, `gold_chunk_id`
- `retrieved_chunks` — including `rank`, `chunk_id`, `source_id`, `document_title`, `heading_path`, `similarity`, `reranker_score`, `vector_rank`
- `answer_text`
- `answer_chunk_ids`
- `grounded`
- `model_id`, `top_k`, and `usage` diagnostics

#### 3.18.2 Judge answers against gold passages

Evaluate the generated answers against their gold passages using the project's fixed judge pipeline:

```bash
uv run python src/judge_answers.py
```

This script:

- loads the chunk corpus from `data/chunks/chunks.jsonl`
- builds an in-memory index keyed by `chunk_id`
- reads generated answers from the answer JSONL files
- looks up the gold passage for each answer via `gold_chunk_id`
- applies a rubric that focuses on semantic equivalence, completeness, and named-resource coverage when the question asks for specific resources
- writes judged records to the corresponding judged output files

##### Current default judged output

The current default judged output corresponds to the reranked-vector answer artefact:

- `data/answers/answers_vector_reranked_v2_prompt_grounded_judged.jsonl`

Run the judge against the new answer file:

```bash
uv run python src/judge_answers.py \
  --answers-input data/answers/answers_vector_reranked_v2_prompt_grounded.jsonl \
  --output data/answers/answers_vector_reranked_v2_prompt_grounded_judged.jsonl
```

(Adjust command-line flags to match the actual `judge_answers.py` interface.)

##### Frozen baseline judged outputs

The project preserves earlier judged outputs as frozen baselines:

- `data/answers/answers_vector_v1_judged.jsonl`
- `data/answers/answers_vector_v2_prompt_grounded_judged.jsonl`

Each judged record extends the original answer fields with:

- `judge_model_id`
- `judge_score`
- `judge_reasoning`
- `judge_gold_chunk_text`
- `judge_gold_heading_path`
- `judge_usage`

These should be treated as historical reference points tied to their respective answer-generation variants.

#### 3.18.3 Preserved script versions

Earlier scripts for this stage are preserved for provenance and comparison, including:

```text
src/generate_answers_v1.py
src/judge_answers_v1.py
src/judge_answers_v2.py
```

These files, together with the v1 and v2 JSONL outputs, document the progression of the answer-generation and judging workflow without overwriting earlier implementations.

The current `src/generate_answers.py` has been updated to use reranked vector retrieval (`retrieve_reranked.py`) and writes to the new `answers_vector_reranked_v2_prompt_grounded.jsonl` artefact. Earlier answer-generation behaviour can be inspected in the preserved scripts if needed.

#### 3.18.4 Optional analysis outputs

Aggregations over the judged files, such as the proportion of `good` answers by `target_size`, `target_role`, or `source_id`, can be computed in separate analysis scripts and regenerated as needed. These are derived outputs and are not treated as primary corpus artefacts.

When comparing across answer-generation variants, treat the plain-vector artefacts (`answers_vector_v1*` and `answers_vector_v2_prompt_grounded*`) as frozen baselines, and the reranked-vector artefacts (`answers_vector_reranked_v2_prompt_grounded*`) as the current default for evaluation and comparison.

### 3.19 Interactive Streamlit UI, Docker runtime, and EC2 deployment

In addition to CLI scripts and notebooks used for evaluation, the project exposes the current default RAG path through a Streamlit application with a lightweight monitoring layer. The same Docker Compose runtime path is used both for local execution and for the lightweight EC2 deployment used to provide live reviewer access.

#### 3.19.1 First-time application bootstrap

From the project root, the standard reproducible runtime path for the application uses Docker Compose. This same Compose-based setup is used both for local execution and for the lightweight EC2 deployment used to provide live reviewer access.

1. **Start the database:**
   ```bash
   docker compose up -d postgres
   ```
   Wait until the service is healthy.

2. **Run the bootstrap service:**
   ```bash
   docker compose run --rm bootstrap
   ```
   This runs `db_init.py`, `db_load_chunks.py`, and `db_build_embeddings.py` inside a containerized environment, pointing at the `postgres` service.

3. **Start the application:**
   ```bash
   docker compose up -d app
   ```

The Streamlit UI is then available at `http://localhost:8501`.

The app provides two tabs:

- **AI Navigator**
  - free-text question input
  - optional audience filters based on organisation size and role
  - reranked vector retrieval with configurable `top_k` (default 5)
  - grounded answer display using the selected v2 prompt-grounded answer-generation pipeline
  - an expandable evidence panel showing retrieved chunks, `heading_path`, audience tags, similarity or distance metadata, and chunk text

- **Monitoring Dashboard**
  - summary metrics for total conversations, average latency, total estimated cost, and feedback counts
  - charts for response time per query, cost per query, token usage per request, and conversations per hour
  - audience breakdown charts for queries by organisation size and queries by role
  - a recent-conversations table with question, answer snippet, audience filters, latency, cost, and total tokens

#### 3.19.2 Normal restart and full reset

Once the database is bootstrapped, you do not need to run the bootstrap service again unless you change the underlying corpus or want to rebuild embeddings.

**To restart the application:**
```bash
docker compose up -d postgres app
```

**To shut down the application:**
```bash
docker compose down
```

**To completely wipe the database and start fresh:**
```bash
docker compose down -v
```

After a full reset, repeat the first-time bootstrap steps.

#### 3.19.3 Conversation and feedback logging

The app reuses the containerized PostgreSQL connection and writes monitoring data to two additional tables:

- `conversations`
  - stores question, answer text, model identifier, selected audience filters, prompt/completion/total token counts, response time, estimated cost, and timestamp for each interaction
- `feedback`
  - stores per-conversation thumbs-up or thumbs-down feedback and timestamps

These monitoring tables are part of the same database environment as the retrieval index, but are separate from the `chunks` corpus table.

#### 3.19.4 Reproducibility considerations

The Docker Compose setup provides a clean boundary between the offline evaluation pipeline, run locally via `uv run ...`, and the interactive runtime, run via `docker compose`.

The containerized app depends on the exact same reviewed corpus snapshot and heading-aware chunking output in `data/chunks/chunks.jsonl`. It logs conversations and feedback, but it does not modify the underlying corpus, seeds, or evaluation datasets.

Another practitioner can therefore:

1. Rebuild or restore the reviewed corpus and regenerate `data/chunks/chunks.jsonl` locally.
2. Run the Docker Compose bootstrap (`docker compose run --rm bootstrap`) to spin up the database and load the corpus into the containerized environment.
3. Start the app via Docker Compose (`docker compose up -d app`).
4. Interact with the AI Navigator knowing it is backed by the exact same reproducible reranked-vector and v2 prompt-grounded pipeline.

The live app uses the same non-rewritten reranked-vector retrieval path selected by evaluation; rewrite-enabled retrieval variants remain available only for offline experimentation and debugging.

#### 3.19.5 Lightweight EC2 deployment

For reviewer-facing demonstration, the application was also deployed to a small Ubuntu-based AWS EC2 instance using the same Docker Compose runtime path.

Typical deployment steps were:

1. Provision a small EC2 instance and allow inbound:
   - SSH
   - TCP 8501 for Streamlit

2. Install Docker and Docker Compose on the instance.

3. Clone the repository and create a `.env` file with the required secrets and database configuration.

4. Start the database service:
   ```bash
   docker compose up -d postgres
   ```

5. Run the one-off bootstrap service:
   ```bash
   docker compose run --rm bootstrap
   ```

6. Start the Streamlit app service:
   ```bash
   docker compose up -d app
   ```

7. Access the application at:
   ```text
   http://<EC2_PUBLIC_IP>:8501
   ```

During deployment, the small instance required temporary swap to handle memory spikes during build and bootstrap, and the root EBS volume was increased from 20 GB to 30 GB to accommodate Docker build cache and model downloads.

This deployment is intended as a lightweight demonstration environment rather than a production architecture. It reuses the same evaluated reranked-vector + v2 prompt-grounded pipeline, but does not yet add production hardening such as HTTPS, a custom domain, or managed secrets.

---

## 4. Outputs

Following the workflow above produces or recreates the following artefacts.

### Raw source data

```text
data/raw/html/
data/raw/pdf/
data/download_metadata.json
```

### Reviewed corpus and snapshots

```text
data/processed/
data/corpus_snapshots/v1_2026-07-25/
```

### Chunk corpus and QA artefacts

```text
data/chunks/chunks.jsonl
data/chunks/spotcheck.jsonl
data/chunks/spotcheck.json
```

### Evaluation configuration and data

```text
data/ground_truth_seed_draft.json
data/seed_chunk_candidates.json
data/ground_truth_seeds_vetted.jsonl
data/ground_truth_synthetic.jsonl
```

### Retrieval index

```text
PostgreSQL chunks table
PostgreSQL full-text-search fields and indexes
PostgreSQL pgvector chunk_embedding values
```

### Retrieval interfaces

```text
src/retrieve_text.py
src/retrieve_vector.py
src/retrieve_reranked.py
src/retrieve_hybrid.py
```

### Retrieval-evaluation outputs

```text
Console or structured metric summary from src/evaluate_retrieval.py
Optional per-question debug output, for example:
data/eval/retrieval_debug.jsonl
```

### Answer-generation and judge outputs

```text
data/answers/answers_vector_v1.jsonl
data/answers/answers_vector_v1_judged.jsonl
data/answers/answers_vector_v2_prompt_grounded.jsonl
data/answers/answers_vector_v2_prompt_grounded_judged.jsonl
data/answers/answers_vector_reranked_v2_prompt_grounded.jsonl
data/answers/answers_vector_reranked_v2_prompt_grounded_judged.jsonl
```

### Monitoring tables and logs

```text
PostgreSQL conversations table
PostgreSQL feedback table
```

These tables store conversation-level metrics and thumbs-up or thumbs-down feedback for the interactive app, and are derived from, but do not modify, the underlying corpus and evaluation artefacts.

### Interactive UI and runtime artefacts

```text
app.py  (Streamlit AI Navigator and Monitoring Dashboard)
.streamlit/config.toml
docker-compose.yml
Dockerfile
.env.example
```

These files provide the optional Streamlit interface over the reranked vector and v2 prompt-grounded answer-generation path, plus a lightweight monitoring dashboard backed by the `conversations` and `feedback` tables.

### Cloud deployment state

```text
AWS EC2 instance running the Docker Compose application stack
Public Streamlit endpoint on port 8501
PostgreSQL + pgvector running in the Compose-managed database container
```

This deployment is operational state rather than a committed repository artefact.

---

## 5. What a reviewer can reproduce

From a clean clone, a reviewer can:

1. Create the pinned Python environment with `uv sync`.
2. Configure a PostgreSQL database connection using `DATABASE_URL`.
3. Use the committed `.streamlit/config.toml` when running the Streamlit app.
4. Choose a corpus path:
   - **Strict v1 baseline**: restore the reviewed Markdown snapshot under `data/corpus_snapshots/` into `data/processed/`.
   - **Fresh corpus rebuild**: download and extract ACSC sources and perform a new manual Markdown review for a fresh corpus.
5. Regenerate heading-aware chunks with `src/prepare_chunks.py` and inspect sampled chunk records from `data/chunks/spotcheck.*` for QA.
6. Recreate deterministic seed-to-chunk matching and candidate files with `src/resolve_seed_draft_ids.py`.
7. Reuse committed LLM-vetted seed and synthetic-question artefacts to reproduce the current benchmark, or regenerate them as a new evaluation-data version.
8. Initialise and populate the local PostgreSQL retrieval index for offline evaluation by running `db_init.py` → `db_load_chunks.py` → `db_build_embeddings.py`.
9. Build pgvector embeddings using the configured sentence-transformers model if they are not already present.
10. Run text, vector, reranked vector, and hybrid retrieval over manual queries with the same audience-filter semantics as described in this document.
11. Rerun comparative retrieval evaluation over the same synthetic question set to reproduce the reported retrieval metrics.
12. Export per-question debug records to inspect backend-specific rankings, scores, relevance labels, and audience context.
13. Reproduce the selected reranked-vector retrieval baseline, and rerun the derived answer-generation and judge stage using the preserved v1 and v2 answer artefacts and scripts.
14. Launch the interactive application using Docker Compose, executing the containerized bootstrap sequence (`docker compose up -d postgres`, `docker compose run --rm bootstrap`, `docker compose up -d app`).
15. Interact with the Streamlit AI Navigator and Monitoring Dashboard locally via `http://localhost:8501`.
16. Reproduce the lightweight reviewer-facing deployment on a small AWS EC2 instance using the same Docker Compose runtime path, including bootstrap and app startup.
17. Verify that the deployed app exposes the same reranked-vector retrieval and v2 prompt-grounded answer-generation path selected by evaluation, rather than a separate ad hoc configuration.

This runbook intentionally treats the evaluated retrieval baseline as the core reproducible path. The grounded answer-generation and judge layer, and the interactive Streamlit UI with monitoring, are derived stages built on top of the existing retrieval artefacts and can be rerun separately using the preserved v1 and v2 outputs, scripts, Docker Compose configurations, `.streamlit/config.toml`, and the EC2 deployment steps described above.