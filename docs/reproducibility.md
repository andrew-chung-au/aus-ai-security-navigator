# Reproducibility

This project is designed so that another person can recreate the environment, rebuild the corpus, and rerun the main pipelines from a clean checkout, using a manifest-defined dataset and a small set of scripts plus documented manual steps.

The focus of this document is on environment, inputs, scripted transformations, manual checkpoints, and outputs — not on re-explaining the entire project design.

---

## 1. Environment

### Requirements

- Python 3.13
- `uv` for environment and dependency management

### Setup

From the project root:

```bash
uv sync
```

This creates the Python environment and installs all dependencies at the pinned versions defined in:

- `pyproject.toml`
- `uv.lock`

These files are committed to the repository and should not be edited casually; they are part of the reproducibility contract.

---

## 2. Data & manifest

### Source manifest

The core dataset is defined in:

- `data/source_manifest_core.csv`

Each row describes a single ACSC source with fields such as:

- identifiers: `source_id`, `title`, `url`
- metadata: `content_type` (`html` or `pdf`), `published_date`, `primary_use_case`, `topic_tags`
- scope: `core`, `boundary`, `notes`
- audience fields:
  - `size_audience_tag` (e.g. `small_business`, `medium_business`, `large_enterprise_gov_critical`, `all_sizes`)
  - `role_audience_tags` (e.g. `ai_consumer`, `ai_builder`, or both; stored as a delimited list and normalised downstream)

The manifest is the single source of truth for which ACSC documents are in scope and how they are tagged.

### Source documents

- All sources are public ACSC HTML pages and PDF documents.
- No private or local-only data is required; a fresh clone can reconstruct the dataset by downloading from the URLs in `data/source_manifest_core.csv`.

If ACSC updates the documents, a new run will reflect those updates; for strict reproduction, keep an archived copy of `data/raw/` from the original run.

---

## 3. Pipelines & scripts

This section describes how to move from a clean checkout to a retrieval-ready corpus and evaluation data. It assumes `uv sync` has already been run.

### 3.1 Download and extract sources

1. **Download HTML and PDF sources**

   ```bash
   uv run python src/download_sources.py
   ```

   - Reads `data/source_manifest_core.csv`.
   - Downloads HTML pages into `data/raw/html/`.
   - Downloads PDFs into `data/raw/pdf/`.
   - Writes `data/download_metadata.json` with basic provenance for each download.

2. **Extract HTML to Markdown**

   ```bash
   uv run python src/extract.py data/raw/html
   ```

   - Parses HTML content.
   - Writes cleaned Markdown (first pass) to `data/processed/`.

3. **Extract PDFs to Markdown**

   ```bash
   uv run python src/extract_pdfs.py data/raw/pdf
   ```

   - Extracts text from PDFs.
   - Writes cleaned Markdown (first pass) to `data/processed/`.

At this point, all core sources exist as Markdown files in `data/processed/`.

### 3.2 Manual Markdown review

After extraction, perform a one-time manual review of the processed Markdown files to correct extraction artefacts. Typical corrections:

- broken or missing headings
- repeated headers, footers, or navigation text
- duplicated paragraphs
- missing or malformed lists
- table structure problems
- PDF reading-order issues

The goal is to fix extraction noise, not to rewrite content. The reviewed files form the “cleaned corpus” used by the chunker.

### 3.3 Chunk preparation

4. **Prepare retrieval-ready chunks**

   ```bash
   uv run python src/prepare_chunks.py
   ```

   - Reads cleaned Markdown from `data/processed/`.
   - Applies a heading-aware, structure-preserving chunking strategy.
   - Builds chunk records with fields such as:
     - `chunk_id`
     - `source_id`, `source_file`
     - `chunk_index`, `chunking_version`
     - `document_title`, `heading_path`
     - `size_audience_tag`, `role_audience_tags` (copied from the manifest)
     - `chunk_text`
     - diagnostic fields (`chunk_chars`, `chunk_words`, `chunk_lines`)
   - Writes the retrieval-ready corpus to `data/chunks/chunks.jsonl`.

This JSONL file is the canonical text representation of the retrieval corpus.

### 3.4 Chunk spot-check

5. **Export sampled chunks for manual QA**

   ```bash
   uv run python src/spotcheck_chunks.py
   ```

   - Reads `data/chunks/chunks.jsonl`.
   - Writes sampled chunks to:
     - `data/chunks/spotcheck.jsonl`
     - `data/chunks/spotcheck.json`

Use these files to manually check that:

- `heading_path` matches the cleaned Markdown structure.
- `size_audience_tag` and `role_audience_tags` are correctly propagated.
- lists and tables are not badly broken.
- paired risk / mitigation sections remain coherent where intended.

This is a lightweight QA step between chunking and retrieval indexing.

### 3.5 Seed matching and vetting

6. **Define seed configuration**

   - Edit `data/ground_truth_seed_draft.json` to describe important passages and audience slices to test.
   - Each seed includes fields such as:
     - `source_id`
     - `target_size`, `target_role`
     - `passage_type`
     - `why_this_passage`
     - `best_heading_path_guess`
     - optional `numbered_item_title_guess`
     - optional `anchor_quote`

7. **Match seeds to concrete chunks**

   ```bash
   uv run python src/match_seeds_to_chunks.py
   ```

   - Reads `data/chunks/chunks.jsonl` and `data/ground_truth_seed_draft.json`.
   - Resolves each seed to a specific chunk `chunk_id`, preferring numbered list items when `numbered_item_title_guess` is present.
   - Writes candidates and debug information to `data/seed_chunk_candidates.json`.

8. **Vet seed passages with an LLM judge**

   - Run the LLM judging step (using `src/llm_client.py` and a small evaluation script) over `data/seed_chunk_candidates.json`.
   - Produce a vetted seed file such as `data/ground_truth_seeds_vetted.jsonl`, including:
     - `include_for_eval`
     - `seed_quality`
     - `suggested_passage_type`
     - `reason`.

This ensures that only coherent, audience-appropriate passages are used for synthetic question generation.

### 3.6 Synthetic question generation

9. **Generate ground-truth questions (A → Q\*)**

   ```bash
   uv run python src/generate_ground_truth_questions.py
   ```

   - Reads vetted seeds from `data/ground_truth_seeds_vetted.jsonl`.
   - Uses `candidate_chunk` content plus audience metadata to generate realistic questions.
   - Writes outputs to `data/ground_truth_synthetic.jsonl`, preserving:
     - `chunk_id`
     - `source_id`
     - `size_audience_tag`, `role_audience_tags`
     - `target_size`, `target_role`
     - generated question text.

Batch generation is paced (e.g. fixed delay between requests) and uses retry handling in the shared LLM client to respect rate limits.

### 3.7 Retrieval index (PostgreSQL)

10. **Initialise the database schema**

    ```bash
    uv run python src/db_init.py
    ```

    - Creates the `chunks` table with the current schema.
    - Adds indexes on full-text search and audience metadata.

11. **Load chunks into PostgreSQL**

    ```bash
    uv run python src/db_load_chunks.py
    ```

    - Reads `data/chunks/chunks.jsonl`.
    - Normalises `heading_path` and `role_audience_tags` into JSON arrays.
    - Builds `search_text` from titles, headings, audience tags, and `chunk_text`.
    - Upserts rows into the `chunks` table keyed by `chunk_id`.

12. **Run text retrieval**

    ```bash
    uv run python src/retrieve_text.py "your query"
    ```

    - Uses PostgreSQL full-text search and ranking.
    - Supports optional `--size-tag` and `--role-tag` filters.
    - Returns top‑k chunks (default `k=5`, configurable) for inspection and evaluation.

### 3.8 Retrieval evaluation (text retriever)

After the PostgreSQL `chunks` table is populated and the text retriever is in place, a fresh checkout can reproduce retrieval evaluation over the synthetic question set.

13. **Run retrieval evaluation over synthetic questions**

    ```bash
    uv run python src/evaluate_retrieval.py
    ```

    - Reads `data/ground_truth_synthetic.jsonl`.
    - Uses `src/retrieve_text.py` as one retrieval backend.
    - Computes strict and relaxed retrieval metrics such as:
      - strict Hit@k and MRR based on exact `chunk_id` matches,
      - relaxed Hit@k and MRR where:
        - exact `chunk_id` matches score highest,
        - chunks from the same `source_id` and final heading (leaf of `heading_path`) count as partial hits.
    - Prints metrics and, in debug mode, a top‑k listing per question showing:
      - `chunk_id`, `source_id`,
      - leaf heading,
      - text-search score.

#### Baseline text retrieval behaviour

The current text retriever (`src/retrieve_text.py`) is implemented to:

- compute a relevance score for chunks using:
  - `ts_rank(fts, websearch_to_tsquery('english', query), 1)`
- filter results on `score > 0` instead of requiring a strict boolean match on:
  - `fts @@ websearch_to_tsquery('english', query)`
- preserve optional audience filters:
  - `size_audience_tag` (with `all_sizes` as a fallback), and
  - `role_audience_tags` (JSONB array containment)
- return the top‑k ranked chunks (default `k=5`, configurable) ordered by score and chunk length.

This change makes retrieval more robust for long, conversational questions while keeping the corpus, manifest, and chunk schema unchanged.

### 3.9 Vector index and comparative retrieval evaluation

In addition to the text-based retrieval baseline, the project includes a pgvector-backed dense retrieval index and a comparative evaluation harness that reports metrics for both text and vector retrieval on the same synthetic question set.

14. **Build pgvector embeddings for all chunks**

    ```bash
    uv run python src/db_build_embeddings.py
    ```

    - Loads a local sentence-transformers model (MiniLM) once.
    - Reads all rows from the `chunks` table.
    - Computes a normalised embedding for each chunk’s `chunk_text` (plus supporting fields as configured in the script).
    - Writes the embeddings into a `chunk_embedding` column using pgvector.
    - Logs progress as chunks are embedded so another person can see that all rows have been processed.

15. **Run comparative retrieval evaluation (text vs vector)**

    ```bash
    uv run python src/evaluate_retrieval.py
    ```

    - Reads `data/ground_truth_synthetic.jsonl`.
    - Uses both retrieval helpers:
      - `src/retrieve_text.py` (PostgreSQL full-text search),
      - `src/retrieve_vector.py` (pgvector nearest neighbour search over MiniLM embeddings).
    - Computes strict and relaxed retrieval metrics separately for each retriever:
      - strict Hit@k and MRR based on exact `chunk_id` matches,
      - relaxed Hit@k and MRR where:
        - exact `chunk_id` matches score highest,
        - chunks from the same `source_id` and final heading (leaf of `heading_path`) count as partial hits.
    - Prints a JSON summary with separate metric blocks for text and vector retrieval, so their performance can be compared on the same synthetic question set.

With the vector index in place, another practitioner can run both text and vector retrievers over arbitrary queries (with the same audience filters and corpus) and rerun `src/evaluate_retrieval.py` to obtain metrics for each approach. The underlying dataset, manifest, chunking strategy, and seed/question generation pipeline remain unchanged, so all prior reproducibility guarantees still hold.

---

## 4. Outputs

By following the steps above, a fresh checkout can reproduce the main data artefacts:

- Raw downloads:
  - `data/raw/html/`
  - `data/raw/pdf/`
- Cleaned corpus:
  - `data/processed/` (Markdown)
- Chunk corpus:
  - `data/chunks/chunks.jsonl`
  - `data/chunks/spotcheck.jsonl`
  - `data/chunks/spotcheck.json`
- Evaluation configuration and data:
  - `data/ground_truth_seed_draft.json`
  - `data/seed_chunk_candidates.json`
  - `data/ground_truth_seeds_vetted.jsonl`
  - `data/ground_truth_synthetic.jsonl`
- Retrieval index:
  - PostgreSQL `chunks` table populated from `data/chunks/chunks.jsonl`
  - text retrieval behaviour via `src/retrieve_text.py`
  - vector retrieval behaviour via `src/retrieve_vector.py`

---

## 5. What another person can reproduce

From a clean clone, another practitioner can:

1. Create the same Python environment with `uv sync`.
2. Download the same ACSC sources using the manifest.
3. Extract and manually review Markdown in `data/processed/`.
4. Regenerate `data/chunks/chunks.jsonl` via heading-aware chunking.
5. Spot-check sampled chunks before indexing.
6. Recreate the seed configuration, seed–chunk matches, and vetted seeds.
7. Regenerate synthetic ground-truth questions.
8. Build and populate the PostgreSQL `chunks` table.
9. Run text and vector retrieval over the synthetic question set and manual test queries, and rerun the comparative evaluation to obtain metrics for both approaches.

Project design details (problem framing, dataset notes, decisions, and log) are documented separately in `docs/dataset-notes.md`, `docs/decisions.md`, and `docs/project-log.md` so this file can stay focused on “how to reproduce” rather than “why the project is structured this way`.