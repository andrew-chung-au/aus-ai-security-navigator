# Project log


## 2026-07-21 — Project start

### Goal
Choose a dataset and define the project scope.

### What was decided
- Project topic: Australian AI Security Navigator
- Corpus: ACSC AI guidance
- Initial scope: core documents only

### Why
- Public and accessible sources
- Specific enough to justify RAG
- Manageable within the timeline

### What was excluded
- Broad cyber-security corpus
- OT guidance for the first version
- Generic AI primer pages unless needed for context

### Problems / uncertainties
- Some pages overlap in theme
- Need to separate core vs boundary sources clearly

### Next step
Create the source manifest and download script.


## 2026-07-22 — Dataset / source corpus

### Goal
Choose a small, public, authoritative corpus that is specific enough to justify RAG.

### Decision
Use a curated ACSC AI guidance corpus as the first version of the project dataset, including core HTML guidance pages and the attached PDF guidance on defending against AI-enabled cyber attacks.

### Included
- Core ACSC AI guidance HTML pages
- Attached PDF guidance on defending against AI-enabled cyber attacks for:
  - small businesses
  - medium-sized businesses
  - government, critical infrastructure, and large enterprises
- Initial source manifest for the first build

### Excluded from the first build
- Operational technology guidance, because it broadens the project into critical infrastructure and OT environments
- Boundary AI guidance pages, which are relevant but reserved for possible later expansion

### Why
The corpus is public, accessible, and specific enough that retrieval should add value beyond a general LLM. The attached PDFs add more operational and audience-specific guidance than the HTML pages alone.

### Problems / uncertainties
- Some pages overlap in topic, so metadata and chunking will matter
- The mixed HTML and PDF corpus may require format-specific extraction and cleanup

### Next step
Create the source manifest, download script, and extraction workflow for both HTML and PDF sources.


## 2026-07-22 — Corpus extraction and audience framing (v1)

### Goal
Move from raw ACSC sources to a cleaned corpus and clarify how audience context will be represented.

### What was done
- Completed HTML and PDF extraction into local Markdown files
- Manually reviewed and corrected extracted text for:
  - broken headings
  - repeated headers, footers, and navigation chrome
  - missing or malformed lists
  - table structure and reading-order issues
  - duplicated paragraphs
- Confirmed the source manifest structure and, for the initial version, added an explicit single `audience_tag` field per source
- Aligned deterministic audience tags with `source_id` values in `data/source_manifest_core.csv`

### Why
- The project depends on audience-aware retrieval: many ACSC AI guidance documents are written specifically for small businesses, medium-sized businesses, or government, critical infrastructure, and large enterprises, and this context needs to be preserved through ingestion and chunking
- Mixed HTML/PDF sources can introduce extraction noise that harms retrieval, so a one-time manual review and correction step is a pragmatic quality improvement for a small curated dataset
- Freezing audience metadata at the document level in the manifest keeps the mapping simple and deterministic while still allowing chunks to carry audience metadata in the retrieval index

### Problems / uncertainties
- Some guidance pages are broad organisational documents and were initially tagged as `general_organisation` even though they may skew toward larger or more complex environments
- Joint or multi-agency guidance may imply audiences not captured perfectly by a single normalized label
- Audience tags for some documents might need refinement later if evaluation reveals mismatches between query intent and document tagging

### Next step
Use the updated manifest to prepare a retrieval-ready corpus from the cleaned Markdown files.


## 2026-07-22 — Chunk schema and heading-aware chunking

### Goal
Define the minimum retrieval chunk schema and prepare the first retrieval-ready chunked corpus.

### What was done
- Defined a minimum chunk schema for the first build (later updated after the audience refactor):
  - initial version:
    - `source_file`
    - `document_title`
    - `heading_path`
    - `audience_tag`
    - `chunk_text`
  - current version:
    - `source_file`
    - `document_title`
    - `heading_path`
    - `size_audience_tag`
    - `role_audience_tags`
    - `chunk_text`
- Implemented heading-aware chunk preparation over the cleaned Markdown corpus
- Wrote the first retrieval-ready corpus to `data/chunks/chunks.jsonl`
- Added a chunk-preparation script in `src/prepare_chunks.py`
- Updated documentation in `README.md`, `docs/dataset-notes.md`, and `docs/decisions.md` to reflect the current corpus and chunking design

### Corpus editing for chunking
To improve chunk quality before chunk preparation:

- renamed several processed Markdown files to shorter, more consistent names
- adjusted some extracted Markdown structure so content sits under more appropriate headings
- improved long enumerated sections so they can be chunked more cleanly
- moved or regrouped paragraphs where needed to preserve more meaningful chunk boundaries
- kept document meaning unchanged while improving structure for retrieval

### Chunking behaviour
The chunker currently uses a structure-aware Markdown approach:

- headings define the primary chunk boundaries
- chunks preserve the full `heading_path`
- lists are kept intact where practical
- risk/mitigation and similar paired structures are kept together where possible
- long enumerated sections can be split into smaller item-level chunks
- tables are treated carefully so structure is not damaged by naive splitting

### Why
A structure-aware approach is a better fit for cleaned Markdown than document-wide fixed-size windows because it preserves semantic boundaries, provenance, and section context. A minimal chunk schema also keeps the first build simple while retaining the metadata needed for audience-aware retrieval and later evaluation.

### Problems / uncertainties
- Some chunks may still be too broad or too narrow for optimal retrieval
- Table handling may need further refinement depending on retrieval results
- A few document-specific structures may still need custom handling if evaluation shows weak retrieval behaviour

### Next step
Build the retrieval index over `data/chunks/chunks.jsonl` and design a small evaluation set covering:
- audience-specific queries
- topic-specific queries
- document-specific operational guidance
- cases where overlapping documents may compete in retrieval


## 2026-07-22 — Chunk QA and reproducibility update

### Goal
Add a lightweight quality check for the chunked corpus and document it as part of the reproducible workflow.

### What was done
- Spot-checked a small sample of chunks from `data/chunks/chunks.jsonl`
- Reviewed chunks from representative source types, including:
  - the small-business PDF
  - the medium-business PDF
  - the government / critical infrastructure / large enterprise PDF
  - selected HTML guidance pages
- Confirmed during inspection that:
  - `heading_path` generally reflects the cleaned Markdown structure
  - audience metadata is being propagated correctly from the manifest
  - lists and tables were not broken badly in the sampled chunks
- Added a small helper script to export sampled chunks for manual inspection:
  - `src/spotcheck_chunks.py`
- Produced spot-check outputs for easier visual review:
  - `data/chunks/spotcheck.jsonl`
  - `data/chunks/spotcheck.json`
- Updated `docs/reproducibility.md` to document chunk spot-checking as a QA step between chunk preparation and retrieval indexing

### Why
- The corpus is small and manually curated, so a lightweight manual QA step is a practical way to verify chunk quality before investing further effort in embeddings, indexing, and evaluation
- Reproducibility is stronger when intermediate outputs are not only generated by script, but also checked using a documented process
- Spot-checking helps catch structural issues early, especially around heading paths, audience metadata propagation, and list / table preservation

### Problems / uncertainties
- The spot-check increases confidence in chunk quality, but it does not replace retrieval evaluation
- Some chunking issues may only become visible once retrieval is implemented and tested against real queries
- Table-heavy or unusually structured sections may still need further refinement later if retrieval quality is weaker than expected

### Next step
Build the first retrieval index over `data/chunks/chunks.jsonl` and begin designing or running a small retrieval evaluation set to test:
- audience-aware queries (using `size_audience_tag` and `role_audience_tags`)
- document-specific operational guidance queries
- overlapping-topic queries where multiple sources may compete
- whether the current chunking decisions hold up under actual retrieval


## 2026-07-23 — Audience metadata: size and role refactor

### Goal
Refine audience representation to separate organisation size from AI responsibility (builder vs consumer) and propagate this into the retrieval corpus.

### What was done
- Replaced the single `audience_tag` field in `data/source_manifest_core.csv` with:
  - `size_audience_tag` (e.g. `small_business`, `medium_business`, `large_enterprise_gov_critical`, `all_sizes`)
  - `role_audience_tags` (e.g. `ai_consumer`, `ai_builder`, or both)
- Updated manifest rows for all core sources to use the new two-dimensional scheme
- Updated `src/prepare_chunks.py` so each chunk record now carries:
  - `size_audience_tag`
  - `role_audience_tags`
- Updated `src/download_sources.py` so download metadata captures the new audience fields for provenance
- Updated documentation (`README.md`, `docs/dataset-notes.md`, `docs/reproducibility.md`, `docs/decisions.md`) to reflect the new audience model and chunk schema

### Why
- Many documents clearly differentiate between organisations using/adopting AI and those building or providing AI systems
- A single label could not cleanly express both organisation size and role, which limited audience-aware retrieval and evaluation
- Making size and role explicit supports more precise filtering and more transparent explanations of why particular documents are retrieved (for example, “large enterprise AI builder” vs “small business AI consumer”)

### Problems / uncertainties
- Some documents apply across all sizes and both roles; in these cases, conservative tagging (e.g. `all_sizes` plus both roles) may still be coarse
- Future evaluation may suggest further refinement (for example, more granular roles), but that is deferred to later iterations

### Next step
Regenerate `data/chunks/chunks.jsonl` with the new audience fields and confirm the updated schema via spot-checking before indexing.


## 2026-07-23 — Seed–chunk matching and seed vetting (v1)

### Goal
Connect curated evaluation seeds to concrete chunks and vet them as suitable seed passages for question generation.

### What was done
- Created `data/ground_truth_seed_draft.json` as a curated list of important passages to test, with fields:
  - `source_id`
  - `target_size`
  - `target_role`
  - `passage_type`
  - `why_this_passage`
  - `best_heading_path_guess`
  - optional `numbered_item_title_guess`
  - optional `anchor_quote`
- Implemented a deterministic seed–chunk matching script (`src/match_seeds_to_chunks.py`) that:
  - groups chunks by `source_id`
  - for each seed, optionally narrows the candidate pool to chunks whose last heading matches `numbered_item_title_guess` after loose normalization
  - if such numbered-item matches exist, ranks only that subset; otherwise, uses all chunks for that `source_id`
  - computes similarity scores based on:
    - full heading-path similarity
    - last-heading similarity and an exact-match bonus
    - numbered item title similarity and exact-match bonus (when present)
    - anchor-quote similarity and containment (when present)
  - selects the best-scoring chunk and records:
    - `candidate_chunk` (compact metadata + `chunk_text`)
    - `candidate_debug` (scoring breakdown)
    - `match_score`, `selection_confidence`, `score_margin`
    - `selection_strategy` (e.g. `numbered_item_exact_subset` or `all_source_chunks`)
- Wrote the matching results to `data/seed_chunk_candidates.json`
- Designed and applied an LLM-based judging prompt that:
  - inspects each `candidate_chunk`
  - decides `include_for_eval` (true/false)
  - assigns `seed_quality` (`high`, `medium`, or `low`)
  - may adjust `suggested_passage_type` based on the actual content
  - provides a short natural-language `reason` for the judgement
- Collected the judgements in a vetted seed file (e.g. `data/ground_truth_seeds_vetted.jsonl`)
- Observed that, for the current curated seeds:
  - all inspected seeds were marked `include_for_eval: true`
  - most seeds were rated `high` quality, with some `medium` and no `low` ratings in this pass

### Why
- Mapping high-level seed intents (size, role, passage_type, heading guess, anchor quote) to concrete chunks is necessary for reproducible evaluation
- Explicit handling of `numbered_item_title_guess` ensures that list-item seeds (such as “4. Leverage trusted infrastructure”) resolve to the intended chunk rather than a generic sibling under the same section
- Using an LLM as a judge at this stage surfaces weak or overly narrow passages before investing in question generation and retrieval metrics
- Storing both `candidate_chunk` and `candidate_debug` supports later debugging and potential tuning of the matching heuristics

### Problems / uncertainties
- Matching still depends on heuristics; while numbered items now have stronger precedence, some edge cases may remain where heading paths or anchor quotes are ambiguous
- The current vetted set has no `seed_quality: "low"` entries, which reflects strong initial curation but may under-sample problematic passages; future iterations may need to add intentionally borderline seeds
- LLM judgement is stable for this small set, but future expansions may require calibration or spot-checking by humans

### Next step
- Use the vetted seeds as the basis for A → Q* question generation to build `ground_truth_questions.jsonl` for retrieval and RAG evaluation
- Begin designing evaluation metrics and harnesses (e.g. Hit Rate, MRR, LLM-as-judge for answers) that consume the vetted seeds and generated questions

## 2026-07-23 — Ground-truth question generation pipeline

### Goal
Generate synthetic evaluation questions from vetted seed chunks for the A → Q* retrieval setup.

### What was done
- Built `src/generate_ground_truth_questions.py` to generate one realistic question per vetted seed chunk.
- Used the matched `candidate_chunk` as the source of truth and the seed metadata as generation context.
- Added audience-aware provenance to each output record, including:
  - `target_size`
  - `target_role`
  - `size_audience_tag`
  - `role_audience_tags`
- Wrote the generated dataset to `data/ground_truth_synthetic.jsonl`.
- Added structured-output client helpers in `src/llm_client.py`.
- Added a small structured-output smoke test in `src/test_structured_output.py`.
- Updated `README.md`, `docs/reproducibility.md`, `pyproject.toml`, and `uv.lock` to reflect the new generation workflow and dependencies.

### Why
- The evaluation workflow needs a stable, reproducible question set tied to gold chunks.
- Including both seed intent and chunk provenance makes later retrieval and slice-based evaluation easier.
- A dedicated generation script keeps the dataset creation step separate from retrieval and answer evaluation.

### Problems / uncertainties
- The generation job hit the free-tier request quota once and needed retry/backoff handling.
- A small fixed delay between requests is useful for staying under rate limits during batch generation.

### Next step
Run retrieval evaluation on the generated question set, starting with Hit Rate and MRR over `chunk_id`.

## 2026-07-23 — Batch pacing and retry handling

### Goal
Make synthetic question generation more stable under API rate limits.

### What was done
- Kept retry handling in the shared LLM client helper.
- Added the plan to pace batch generation in the question-generation script rather than in the shared client.
- Chose a fixed 4-second delay between successful requests to better respect the 15-requests-per-minute quota.

### Why
- The batch job is sequential, so a simple fixed delay reduces quota errors.
- Keeping pacing in the batch script avoids slowing down unrelated LLM calls elsewhere in the project.

### Problems / uncertainties
- Retries still may be needed if the external service is temporarily unavailable.
- If other processes share the same quota, the delay may still need adjustment.

### Next step
Commit the documentation and pipeline updates, then proceed to retrieval evaluation.

## 2026-07-23 — Retrieval index and PostgreSQL setup


### Goal
Move from a JSONL chunk corpus to a reproducible, queryable retrieval index backed by PostgreSQL.

### What was done
- Chose PostgreSQL as the retrieval database and aligned it with the monitoring lessons from the course.
- Added a small database helper module `src/db.py` that:
  - loads environment variables from `.env` (including `DATABASE_URL`)
  - exposes a single `get_db_connection()` function using `psycopg[binary]`.
- Implemented `src/db_init.py` to:
  - create the `vector` extension if it is not already present
  - create a `chunks` table with the current schema:
    - `chunk_id` (primary key)
    - `source_id` (NOT NULL)
    - `source_file` (NOT NULL)
    - `chunk_index`
    - `chunking_version`
    - `document_title`
    - `heading_path` (JSONB)
    - `size_audience_tag`
    - `role_audience_tags` (JSONB)
    - `chunk_text` (NOT NULL)
    - `chunk_chars`, `chunk_words`, `chunk_lines`
    - `search_text` (NOT NULL)
    - `fts` (generated `tsvector` from `search_text` for full-text search)
  - create supporting indexes:
    - GIN index on `fts` for text search
    - B-tree index on `source_id`
    - B-tree index on `size_audience_tag`
    - GIN index on `role_audience_tags`.
- Implemented `src/db_load_chunks.py` to:
  - read `data/chunks/chunks.jsonl`
  - normalise `heading_path` and `role_audience_tags` into JSON arrays
  - build a `search_text` field combining:
    - `document_title`
    - joined `heading_path`
    - audience tags (`size_audience_tag`, `role_audience_tags`)
    - `chunk_text`
  - upsert rows into the `chunks` table keyed by `chunk_id` (using `ON CONFLICT`).
- Ran the initial database bootstrap and load:
  - `uv run python src/db_init.py`
  - `uv run python src/db_load_chunks.py`
- Verified the database state via `psql`:
  - confirmed the presence of `chunks` (and removed an older `items` table)
  - checked that `SELECT COUNT(*) FROM chunks;` returns the expected row count
  - inspected the largest chunks by word count to keep an eye on very large passages.

### Why
- Storing the chunk corpus in PostgreSQL makes retrieval reproducible and queryable with standard SQL.
- Using `search_text` + `fts` keeps the schema simple while supporting effective full-text search.
- Upserts keyed by `chunk_id` allow rerunning the loader safely whenever the corpus changes.
- Explicit indexes on text search and audience metadata support efficient retrieval and filtering.

### Problems / uncertainties
- Some chunks remain long (hundreds of words); they work for v1 but may later need targeted splitting.
- The full-text index currently uses the default English configuration; this is acceptable for v1 but may be tuned later if retrieval behaviour suggests it.

### Next step
Add a small retrieval helper script over the `chunks` table and then run retrieval evaluation over the synthetic question set.


## 2026-07-23 — Baseline text retrieval helper


### Goal
Implement a simple, audience-aware text retrieval script over the PostgreSQL `chunks` table.

### What was done
- Created `src/retrieve_text.py` as the first retrieval helper.
- Implemented a function `retrieve_chunks(query, limit=5, size_tag=None, role_tag=None)` that:
  - uses PostgreSQL full-text search:
    - `fts @@ websearch_to_tsquery('english', %(query)s)`
    - ranks results with `ts_rank(fts, websearch_to_tsquery('english', %(query)s), 1)`
  - applies optional audience filters when provided:
    - size:
      - `(size_audience_tag = %(size_tag)s OR size_audience_tag = 'all_sizes')`
    - role:
      - `role_audience_tags @> %(role_tag_json)s::jsonb` (JSON array containment)
  - returns rows as Python dictionaries using psycopg’s dict-row factory.
- Implemented a small CLI wrapper using `argparse` so the script can be run as:
  - `uv run python src/retrieve_text.py "query text"`
  - `uv run python src/retrieve_text.py "query text" --size-tag medium_business`
  - `uv run python src/retrieve_text.py "query text" --role-tag ai_builder`
  - `uv run python src/retrieve_text.py "query text" --size-tag large_enterprise_gov_critical --role-tag ai_builder --limit 8`.
- Added a human-readable result printer that shows:
  - `chunk_id`, score
  - `source_file`
  - `document_title`
  - `heading_path` (joined with ` > `)
  - audience tags (`size_audience_tag`, `role_audience_tags`)
  - `chunk_words`
  - a truncated preview of `chunk_text`.

### Why
- Using `websearch_to_tsquery` gives user-style text search semantics (phrases, AND/OR, etc.) without complex query syntax.
- `ts_rank` provides a simple relevance score to order results.
- Audience filters make it easy to retrieve:
  - small vs medium vs large/gov guidance
  - AI consumer vs AI builder guidance.
- A CLI wrapper allows quick manual tests and supports later batch evaluation over synthetic questions.

### Problems / uncertainties
- The baseline is purely lexical; no embeddings or vector search are used yet.
- Relevance and ranking are currently driven by text search and the `search_text` field; this may later be tuned (for example, by weighting title/heading vs body).

### Empirical behaviour (manual checks)
Manual runs showed encouraging behaviour:
- A small business data-leak query retrieves the small-business AI data-leak and privacy chunk at rank 1.
- An internet-facing services patching query with `size_tag=medium_business` retrieves the medium-sized business AI-attack guidance chunks that focus on patching and patch automation.
- A training data integrity and provenance query with `role_tag=ai_builder` retrieves AI data security chunks about data poisoning, provenance, and secure storage, plus a secure AI development chunk.
- An agentic AI security controls query with `size_tag=large_enterprise_gov_critical` and `role_tag=ai_builder` retrieves “Best practices for securing agentic AI systems” and related agentic AI control chunks (designing, deploying, input management, resilience, defence in depth, controlled context, rogue agents).

### Next step
Use this retrieval helper to:
- drive synthetic retrieval evaluation over the ground-truth question set (with configurable top‑k, e.g. 5 for answers and 10 for metrics), and
- begin wiring retrieval into the answer-generation flow via the existing LLM client helper.

## 2026-07-24 — Retrieval evaluation and text-search refactor (v1.5)

### Goal
Diagnose why initial retrieval evaluation over the synthetic question set scored zero hits and improve the baseline text retrieval behaviour.

### What was done
- Ran the first retrieval evaluation over `data/ground_truth_synthetic.jsonl` using the existing text retriever and found:
  - Hit@5 and MRR were both 0.0 across 27 questions.
- Added a debug mode to the evaluation script (`src/evaluate_retrieval.py`) that:
  - inspects top‑100 retrieval results per question,
  - prints `chunk_id`, `source_id`, leaf heading, and score for manual review.
- Discovered that for almost all questions, the retriever returned no rows at all, indicating the issue was in the text-search query shape rather than the corpus or evaluation logic.
- Refactored `src/retrieve_text.py` to:
  - compute a relevance score with `ts_rank(...)` for all chunks,
  - drop the hard boolean filter over the text-search expression,
  - keep only rows with `score > 0`,
  - preserve optional audience filters on `size_audience_tag` and `role_audience_tags`.
- Re-ran retrieval evaluation and observed:
  - non‑zero strict metrics (Hit@5 ≈ 0.07, MRR > 0),
  - improved relaxed metrics (Hit@10 ≈ 0.15, relaxed MRR > 0),
  - debug output now shows plausible security‑focused chunks in the top results, even when the exact gold chunk is not yet ranked first.
- Confirmed that the existing `fts` schema and chunk corpus were sound and that the main fix was relaxing the query so long, natural‑language questions can still return useful candidates.

### Why
- The earlier hard text-search condition made long, conversational questions too strict, leading to no matches even when relevant guidance existed.
- Ranking with `ts_rank` over the full corpus and filtering on positive scores produces a more realistic lexical baseline for evaluation, especially for non‑FAQ style guidance.
- Keeping the evaluation script and corpus unchanged while fixing the retrieval layer preserves reproducibility and makes later comparisons (e.g. vector vs text, hybrid approaches) more meaningful.

### Problems / uncertainties
- The lexical baseline still misses some gold chunks or ranks them lower than ideal.
- Current scores are modest and will likely be improved by:
  - tuning field weighting (title/heading vs body),
  - adding vector retrieval,
  - or hybrid text+vector search.
- Audience filters remain available but are not used in the free‑text evaluation scenario; future UX decisions may introduce guided modes that leverage size/role filtering explicitly.

### Next step
- Keep this refactored text retriever as the v1.5 lexical baseline for documentation.
- Add a parallel vector‑based retriever and run the same evaluation harness over both approaches.
- Compare which questions text vs vector retrieval succeed on and consider a hybrid strategy for the final project demo.

## 2026-07-24 — Vector index and comparative retrieval evaluation (v2)

### Goal
Extend the retrieval index with dense vector search and compare text vs vector retrieval performance on the synthetic question set.

### What was done
- Implemented `src/db_build_embeddings.py` to add a pgvector-backed dense index:
  - loaded a local sentence-transformers model (MiniLM) once at startup
  - encoded each chunk’s `chunk_text` (and supporting fields as configured) into a normalised embedding
  - wrote embeddings into a new `chunk_embedding` column in the `chunks` table using the pgvector type
  - logged progress in batches (32-chunk increments) so it is clear that all 350 chunks were embedded successfully.
- Implemented `src/retrieve_vector.py` as a parallel retrieval helper:
  - used `chunk_embedding <=> query_embedding` for exact nearest-neighbour search with cosine distance
  - ordered results by ascending cosine distance (nearest first), then by `chunk_words` for a slight tie-breaker
  - preserved audience filters (`size_audience_tag` with `all_sizes` fallback, `role_audience_tags` JSONB containment) to keep behaviour aligned with the text retriever.
- Updated `src/evaluate_retrieval.py` to compare both retrieval approaches on the same synthetic questions:
  - called the text retriever (`src/retrieve_text.py`) and the vector retriever (`src/retrieve_vector.py`) for each question
  - computed strict and relaxed metrics separately for each:
    - strict Hit@k and MRR based on exact `chunk_id` matches
    - relaxed Hit@k and MRR where exact matches score highest and same-`source_id`/same-leaf-heading matches count as partial hits
  - printed a JSON summary with two metric blocks, one for text and one for vector retrieval.

### Why
- The lexical baseline is a useful reference, but vector search over MiniLM embeddings is better suited to natural-language, security-oriented questions and passages.
- Evaluating both approaches on the same synthetic question set makes the choice of retriever evidence-based rather than intuitive.
- Storing embeddings in PostgreSQL via pgvector keeps the index reproducible with standard tooling and avoids introducing an external vector store.

### Observed retrieval behaviour
On the current synthetic ground-truth set:

- The text baseline now returns non-empty results and achieves modest strict/relaxed metrics after the v1.5 refactor.
- The vector retriever consistently finds the correct gold chunk in the top positions for most questions and achieves substantially higher Hit@k and MRR.
- For example, questions about:
  - “how should a small business use AI safely”
  - “how to reduce AI data leakage”
  - “training data integrity and provenance” (with `role_tag=ai_builder`)
  are answered by vector retrieval with ACSC passages that directly describe small-business AI risks and mitigations, AI-related data leaks and privacy controls, and AI data security / provenance guidance.

These patterns confirm that, on this corpus and benchmark, dense retrieval is a stronger default than pure text search.

### Problems / uncertainties
- The current synthetic evaluation set is still relatively small (27 questions), so the observed metrics, while encouraging, do not replace broader qualitative testing.
- Vector retrieval depends on the chosen embedding model; future iterations could explore alternative models or multi-vector strategies if some question types remain weak.
- Text and vector retrieval succeed on slightly different edge cases; a hybrid or reranked approach may eventually outperform either alone.

### Next step
- Treat the vector retriever as the preferred baseline for the current project stage while keeping the text retriever as a comparative reference.
- Use the dual-metric evaluation output to:
  - identify questions where text succeeds and vector fails (and vice versa)
  - inform decisions about hybrid retrieval or reranking for the final demo.
- Begin wiring vector-based retrieval into the planned answer-generation workflow over retrieved chunks, using the existing LLM client helper.

## 2026-07-24 — Hybrid retrieval and comparative evaluation (v2.5)

### Goal
Add a simple hybrid retriever on top of the existing text and vector baselines and compare all three approaches on the synthetic question set.

### What was done
- Refactored `src/retrieve_vector.py` to:
  - use a consistent interface and row shape (including `similarity` and `cosine_distance`) aligned with the text retriever,
  - keep query and stored embeddings normalised for cosine-distance search in PostgreSQL via pgvector.
- Implemented `src/retrieve_hybrid.py` as a reciprocal-rank-fusion (RRF) hybrid retriever:
  - called both the text and vector retrievers with the same audience filters (`size_audience_tag`, `role_audience_tags`),
  - pulled the top 10 candidates from each backend,
  - fused results per `chunk_id` using RRF, producing a `hybrid_score` and preserving debug fields such as `text_rank`, `vector_rank`, `text_score`, and `vector_similarity`.
- Updated `src/evaluate_retrieval.py` to:
  - evaluate three backends (`text`, `vector`, `hybrid`) against the same synthetic questions,
  - compute strict Hit@5/MRR and relaxed Hit@10/MRR for each backend using the existing `chunk_id` and relaxed-heading matching logic,
  - optionally write a JSONL debug file containing, per question and backend, the gold labels, relevance scores, and top‑k result metadata for manual inspection.
- Ran the evaluation twice (with and without debug export) and observed:
  - the text baseline remains the weakest retriever on this benchmark,
  - vector retrieval achieves the highest Hit@k and MRR and remains the strongest default,
  - the hybrid RRF retriever improves substantially over text alone but does not outperform vector-only retrieval on this corpus and question set.

### Why
- Adding a hybrid retriever makes it possible to test whether combining lexical and dense signals improves retrieval quality on ACSC AI guidance, rather than assuming vector search is always best.
- Using a shared evaluation harness across text, vector, and hybrid retrieval keeps the comparison fair and reproducible.
- Per-question debug export makes it easier to understand where hybrid helps, where it hurts, and how audience filters and chunk structure influence ranking.

### Problems / uncertainties
- On the current synthetic question set (27 questions), hybrid retrieval did not beat vector retrieval, suggesting that simple RRF over top‑10 text and vector candidates may not add enough complementary signal for this corpus.
- Some questions show divergent rankings between backends; understanding these cases may inform future work on weighting schemes, query rewriting, or reranking models.
- The evaluation set remains relatively small; wider manual testing and more seeds may still shift which retriever is preferred.

### Next step
- Keep vector retrieval as the preferred baseline retriever for the next project phase, with text and hybrid as evaluated reference points.
- Use the JSONL debug output to inspect a handful of successes and failures per backend and decide whether any small hybrid or ranking tweaks are worth exploring.
- Begin wiring the vector-based retriever into the first answer-generation layer over retrieved ACSC chunks, while keeping the evaluation harness as the main way to measure retrieval changes.

## 2026-07-25 — Reviewed corpus snapshot and reproducibility modes

### Goal
Preserve the manually reviewed Markdown corpus as a versioned snapshot and clearly separate strict baseline reproduction from fresh corpus rebuilds.

### What was done
- Restored the cleaned Markdown corpus in `data/processed/` from the current `HEAD` commit.
- Created a versioned snapshot of the reviewed corpus at:
  - `data/corpus_snapshots/v1_2026-07-25/`
- Copied all reviewed Markdown files from `data/processed/` into the snapshot directory:
  - `agentic-ai-adoption.md`
  - `ai-attacks-large.md`
  - `ai-attacks-medium.md`
  - `ai-attacks-small.md`
  - `ai-data-security.md`
  - `ai-introduction.md`
  - `ai-ml-supply-chain.md`
  - `ai-small-business.md`
  - `engaging-with-ai.md`
  - `secure-ai-development.md`
- Copied the matching manifest into the snapshot as:
  - `data/corpus_snapshots/v1_2026-07-25/manifest.csv`
- Generated file checksums for verification:
  - `data/corpus_snapshots/v1_2026-07-25/checksums.sha256`
- Updated documentation to describe two reproducibility modes:
  - **Strict v1 baseline reproduction**: restore the snapshot into `data/processed/` and rebuild chunks, index, embeddings, and metrics.
  - **Fresh corpus rebuild**: re-run download, extraction, and manual cleanup, then create a new snapshot before rebuilding downstream artefacts.
- Updated `docs/reproducibility.md` to:
  - document the snapshot directory,
  - show a non-destructive restore command,
  - clarify that `data/processed/` is a working directory and snapshots are immutable inputs.
- Updated the top-level `README.md` to:
  - mention the snapshot in the project scope and workflow,
  - link to `docs/reproducibility.md` as the source of truth for both modes.

### Why
- Manual Markdown cleanup is a semi-manual transformation; without a snapshot, a fresh extraction could overwrite the exact corpus used for current retrieval and evaluation.
- Preserving the reviewed corpus as a versioned input makes strict reproduction possible even if ACSC sources or extraction behaviour change.
- Separating “strict v1 baseline” from “fresh rebuild” avoids conflating backwards-compatible reproduction with intentional dataset evolution.

### Problems / uncertainties
- Future corpus updates will need their own dated snapshots and log entries to remain comparable.
- Snapshot size is currently manageable in Git; if it grows, Git LFS or release assets may be needed.

### Next step
Use `data/corpus_snapshots/v1_2026-07-25/` as the canonical cleaned corpus for current retrieval and evaluation baselines, and treat any future corpus changes as new versions with their own snapshots and documentation updates.

## 2026-07-25 — Vector-based answer generation, judge-v3 evaluation, and prompt comparison

### Goal
Use the vector retriever to generate grounded answers to the synthetic question set and compare answer-generation strategies under a fixed judge.

### What was done
- Implemented `src/generate_answers.py` to:
  - read `data/ground_truth_synthetic.jsonl`,
  - call the vector retriever with `top_k=5` and audience filters (`target_size`, `target_role`),
  - assemble a structured context of retrieved chunks,
  - call the structured-output LLM client to produce grounded answers,
  - write one JSONL record per question to `data/answers/answers_vector_v2_prompt_grounded.jsonl`.
- Preserved the earlier generator as `src/generate_answers_v1.py` for reproducibility and comparison.
- Implemented `src/judge_answers.py` as the fixed judge-v3 pipeline to:
  - load `data/chunks/chunks.jsonl` into memory,
  - read generated answers,
  - look up the gold chunk via `gold_chunk_id`,
  - score each answer with a structured-output schema:
    - `reasoning`: step-by-step explanation,
    - `score`: `"good"` or `"bad"`,
  - apply a rubric that:
    - focuses on semantic equivalence rather than exact wording,
    - allows extra detail if it stays consistent with the gold passage,
    - requires key named resources or frameworks when the question explicitly asks for them,
    - marks answers as `bad` if they omit central named items or introduce major unsupported claims,
  - write judged results to the corresponding judged JSONL file.
- Ran the fixed judge over both answer sets to compare generator quality under the same evaluator.
- Observed that Vector v2 Prompt Grounded outperformed Vector v1 on the 27-question synthetic set, mainly by retaining named resources, concrete controls, and multi-step guidance.

### Why
- Vector retrieval was already the strongest retrieval backend.
- Grounded answer generation is the natural next step toward a full RAG pipeline.
- A fixed judge makes the comparison between answer-generation strategies fair.
- The v2 prompt improved completeness and specificity while keeping answers corpus-grounded.

### Problems / uncertainties
- The evaluation set is still small (27 questions), so the results are directional rather than definitive.
- Some answers judged as good may draw on more detailed related ACSC guidance rather than the exact gold chunk, which is useful for end users but can complicate strict gold-chunk comparisons.
- The judge rubric is still heuristic rather than human-calibrated.

### Next step
- Add a small summarisation script to compute overall and slice-level good rates from the judged outputs.
- Update the README and reproducibility notes to describe the fixed judge-v3 comparison and the v2 answer-generation selection.

