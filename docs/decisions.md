# Decisions

## D-001 — Project topic
Date: 2026-07-22  
Status: Accepted

### Decision
Use **Australian AI Security Navigator** as the project topic.

### Reason
The topic is grounded in accessible public ACSC AI guidance and has a more specific retrieval need than a generic cyber-security corpus. It focuses on helping Australian organisations navigate AI security guidance rather than attempting to cover all cyber topics.

### Alternatives considered
- Ransomware resilience navigator
- Broader Australian cyber guidance navigator

### Trade-offs
This topic is more distinctive, but requires tighter corpus curation to avoid overlapping with future AI governance or broader cyber-security projects.

### Impact
Defines the overall project scope, target users, and high-level source selection criteria for the manifest and downstream pipeline.

---

## D-002 — Initial source corpus
Date: 2026-07-22  
Status: Accepted

### Decision
Use a manually curated ACSC AI guidance corpus as the initial dataset, including:

- a core set of HTML AI guidance pages, and  
- attached PDF guidance on defending against AI-enabled cyber attacks,

rather than indexing the entire ACSC site or a broader cyber-security corpus.

### Reason
A curated corpus:

- is easier to reproduce and document,
- is easier to evaluate against a small set of test queries, and
- is more likely to produce relevant retrieval results than a broad crawl.

Including the attached PDFs in the core set adds audience-specific and operational guidance that complements the HTML pages while keeping the project manageable for the first build.

### Alternatives considered
- Index only the ACSC AI landing page
- Crawl all linked AI guidance pages
- Use only the HTML guidance pages in the first build
- Use a wider Australian cyber-security corpus

### Trade-offs
Including both HTML pages and attached PDFs improves coverage, especially for operational and audience-specific questions, but:

- introduces mixed-format extraction and cleanup work, and
- creates some overlap between documents that must be handled via metadata and chunking rather than by excluding sources.

A curated corpus still reduces noise compared with a broad crawl, but demands more deliberate manifest maintenance.

### Impact
- The source manifest distinguishes core HTML pages, core attached PDFs, and boundary documents.
- The downloader and extraction workflow support both HTML and PDF sources in the first index build.
- Boundary sources are documented but excluded from the first retrieval index.

---

## D-003 — Audience-aware corpus design (size and role)
Date: 2026-07-23  
Status: Accepted

### Decision
Represent ACSC AI guidance as an audience-aware corpus using **two explicit dimensions** at the document level:

- `size_audience_tag` for organisation size and criticality  
  (e.g. `small_business`, `medium_business`, `large_enterprise_gov_critical`, `all_sizes`)
- `role_audience_tags` for responsibility and AI usage role  
  (e.g. `ai_consumer`, `ai_builder`, or both)

These fields replace the earlier single `audience_tag` and are propagated into all chunks.

### Reason
Many ACSC AI guidance publications are explicitly segmented by audience (small businesses, medium-sized businesses, government, critical infrastructure, large enterprises, and AI system providers) and implicitly segmented by role (organisations using AI vs those building or providing AI systems).

Separating size and role makes it easier to:

- retrieve guidance that fits both an organisation’s scale and responsibility,
- explain why a particular document was selected for an answer, and
- evaluate queries that differ by both size (small vs medium vs large/gov) and role (builder vs consumer).

For a small, curated corpus, explicit document-level `size_audience_tag` and `role_audience_tags` are sufficient and avoid the complexity of inferring audience per chunk or per query in the first version.

### Alternatives considered
- Keep a single normalized `audience_tag` label per document.
- Rely only on the original free-text `audience` field in the manifest without normalized tags.
- Infer audience and role dynamically at query time using an LLM.
- Ignore audience and role segmentation and treat all guidance as general organisational content.

### Trade-offs
Normalising into two small tag vocabularies adds a one-time manual mapping step, but:

- keeps the retrieval index simple to filter, debug, and evaluate,
- reduces reliance on on-the-fly LLM categorisation for core corpus structure, and
- supports more nuanced audience-aware tests (e.g. small-business AI consumer vs large-enterprise AI builder).

Keeping a single tag would simplify the manifest but blur the distinction between organisation size and AI responsibility, making some retrieval and evaluation scenarios harder to express.

### Impact
- The source manifest includes `size_audience_tag` and `role_audience_tags` for each document, and no longer carries the legacy single `audience_tag` field.
- Chunk preparation scripts carry `size_audience_tag` and `role_audience_tags` into every chunk record in the retrieval corpus.
- Retrieval and evaluation can explicitly condition on size and role (for example, “small business AI consumer” vs “large enterprise AI builder”) when designing test queries and filters.

---

## D-004 — Chunking strategy and QA
Date: 2026-07-22  
Status: Accepted

### Decision
Use a heading-aware, structure-preserving chunking strategy over the cleaned Markdown corpus, combined with a small manual spot-check step for sampled chunks before retrieval indexing.

The minimum chunk schema for the first build is:

- `source_file`
- `document_title`
- `heading_path`
- `size_audience_tag`
- `role_audience_tags`
- `chunk_text`

### Reason
The ACSC AI guidance corpus is small, curated, and has strong existing structure (titles, sections, lists, tables, and repeated risk / mitigation patterns). A heading-aware chunking strategy is a better fit than blind fixed-size windows because it:

- preserves document hierarchy and section context,
- keeps related content (for example, “Scope and audience” and risk / mitigation sections) together when practical, and
- avoids splitting lists and tables mid-structure when that would harm retrieval.

A lightweight manual spot-check of sampled chunks is a pragmatic QA step for a semi-manual pipeline. It helps verify that heading paths, audience metadata (size and role), and key structures (lists, tables) have survived extraction and chunking before building embeddings and retrieval indexes.

### Alternatives considered
- Fixed-size token or character windows with simple overlap
- Purely semantic chunking without respecting headings
- Relying only on automated extraction and chunking, with no manual QA step

### Trade-offs
Heading-aware chunking plus manual QA:

- improves retrieval-quality prospects for a small, structured corpus, but
- adds some implementation complexity to the chunking script and a small amount of human time for spot-checking.

Fixed-size windows would be simpler to implement and easier to reuse across very large or unstructured corpora, but would:

- ignore meaningful ACSC section boundaries,
- increase the risk of splitting tables and paired guidance (risk plus mitigation) in unhelpful ways, and
- make audience-aware and document-specific explanations harder to trace back to the original structure.

### Impact
- Chunk preparation is explicitly structure-aware and anchored to document titles and `heading_path`.
- The minimum chunk schema stays simple but supports provenance and audience-aware retrieval using both size and role metadata.
- A small script (for example, `src/spotcheck_chunks.py`) and accompanying docs (`docs/runbook.md`, `docs/dataset-notes.md`) document how sampled chunks are exported and inspected as part of the reproducible workflow.
- Evaluation and retrieval design can assume that chunk structure reflects ACSC guidance layout, not arbitrary windowing, which should improve grounded answer quality for audience-specific and document-specific queries.

---

## D-005 — Seed–chunk matching and LLM seed vetting
Date: 2026-07-23  
Status: Accepted

### Decision
Introduce an explicit **seed–chunk matching** step and a separate **LLM-based seed vetting** step before generating evaluation questions:

- Maintain a curated seed configuration file (`ground_truth_seed_draft.json`) describing which passages and audiences to test.
- Use a deterministic matching script to resolve each seed to a concrete chunk in `chunks.jsonl`, with strong precedence for numbered list items when `numbered_item_title_guess` is provided.
- Use an LLM judge to decide whether each matched chunk is a good seed passage for generating realistic evaluation questions.

### Reason
The evaluation strategy follows an A → Q* pattern: start from a passage A, generate user-like questions Q*, and later evaluate retrieval and RAG answers against that passage and the source. To make this reproducible:

- seeds must be resolved to stable `chunk_id` values, not just fuzzy heading and quote guesses, and
- passages used as seeds must be coherent, audience-appropriate, and rich enough to support realistic questions.

Giving `numbered_item_title_guess` strong precedence ensures that seeds targeting specific list items (such as “4. Leverage trusted infrastructure”) resolve to the intended chunk, rather than a generic sibling under the same section. Using an LLM judge at the seed stage filters out overly narrow, boilerplate, or off-target passages before question generation.

### Alternatives considered
- Treat the initial seed manifest as ground truth without matching or vetting.
- Match seeds to chunks using only heading-path similarity and anchor quotes, without special handling for numbered items.
- Skip seed vetting and directly generate questions from all matched chunks.

### Trade-offs
Adding a matching step and an LLM vetting step:

- increases implementation complexity and introduces an additional pipeline stage, but
- substantially improves traceability (seed → chunk_id), debuggability (via `candidate_debug`), and seed quality before generating evaluation questions.

Skipping these steps would simplify the pipeline but:

- make it harder to understand or fix misalignments between intended passages and actual chunks, and
- risk generating questions from weak, overly narrow, or mis-targeted passages.

### Impact
- A seed configuration file (`ground_truth_seed_draft.json`) captures human/LLM-curated ideas about “what to test” without being treated as final ground truth.
- A matching script resolves each seed to a specific chunk in `chunks.jsonl`, producing `seed_chunk_candidates.json` with:
  - `candidate_chunk`
  - `candidate_debug`
  - `match_score`, `selection_confidence`, `selection_strategy`
- An LLM judging step produces a vetted seed file (e.g. `ground_truth_seeds_vetted.jsonl`) with:
  - `seed_id`, `chunk_id`
  - `include_for_eval`
  - `seed_quality` (`high`, `medium`, `low`)
  - `suggested_passage_type`
  - `reason`
- Downstream evaluation (question generation, retrieval metrics, RAG answer scoring) can rely on:
  - stable `chunk_id`s for relevance labels, and
  - a set of seed passages that have been explicitly checked for coherence, audience fit, and question potential.

  ## D-006 — Retrieval index and PostgreSQL-backed search
Date: 2026-07-23  
Status: Accepted

### Decision
Store the chunked corpus in a PostgreSQL database and use PostgreSQL full-text search as the first retrieval mechanism over the `chunks` table, with audience-aware filters on organisation size and role.

The database layer is implemented with:

- a small helper module (`src/db.py`) exposing `get_db_connection()`, and  
- two scripts:
  - `src/db_init.py` — schema and index creation
  - `src/db_load_chunks.py` — corpus loading and upsert.

### Reason
Moving from a JSONL-only corpus to a PostgreSQL-backed index:

- makes retrieval reproducible and queryable with standard SQL,
- simplifies audience-aware filtering and debugging against concrete tables,
- aligns with course monitoring patterns while staying lightweight enough for a small project.

Using PostgreSQL’s `tsvector`/`tsquery` full-text search and ranking (`ts_rank` plus `websearch_to_tsquery`) provides:

- reasonable default search behaviour for user-style queries, and
- a clear baseline before introducing more complex embedding-based retrieval.

### Alternatives considered
- Keep retrieval purely file-based over `chunks.jsonl` using in-memory search.
- Introduce a vector database or embedding index immediately.
- Use a search engine (for example, an external SaaS index) instead of PostgreSQL.

### Trade-offs
A PostgreSQL-backed index:

- adds a small amount of setup (schema creation, loader scripts), but
- keeps deployment simple, maintains a single source of truth for chunks, and
- enables both lexical search and metadata filtering without extra infrastructure.

Jumping straight to a vector database would add more moving parts and tooling without first validating that the corpus and metadata structure support good retrieval behaviour.

### Impact
- The `chunks` table schema becomes the canonical retrieval schema, including:
  - `chunk_id` (primary key)
  - `source_id`, `source_file` (NOT NULL)
  - `chunk_index`, `chunking_version`
  - `document_title`, `heading_path` (JSONB)
  - `size_audience_tag`
  - `role_audience_tags` (JSONB)
  - `chunk_text` and diagnostics (`chunk_chars`, `chunk_words`, `chunk_lines`)
  - `search_text` and a generated `fts` `tsvector` column.
- Loader scripts (`src/db_load_chunks.py`) upsert rows so the table can be rebuilt safely when the corpus changes.
- Indexes on `fts`, `source_id`, `size_audience_tag`, and `role_audience_tags` support efficient search and audience-aware filtering.
- Future retrieval approaches (vector or hybrid) can reuse the same canonical chunk schema.

---

## D-007 — Baseline audience-aware text retrieval helper
Date: 2026-07-23  
Status: Accepted

### Decision
Implement a simple audience-aware text retrieval helper (`src/retrieve_text.py`) that:

- uses PostgreSQL full-text search (`fts @@ websearch_to_tsquery('english', query)`),
- ranks results with `ts_rank(fts, websearch_to_tsquery('english', query), 1)`,
- applies optional filters on:
  - `size_audience_tag` (with `all_sizes` as a fall-back), and
  - `role_audience_tags` (JSON array containment),
- returns top‑k chunks (default `k=5`, configurable) as dictionaries for inspection, evaluation, and answer synthesis.

### Reason
The project needs a practical, inspectable retrieval baseline before adding more complex ranking or embedding logic. A dedicated helper script:

- makes retrieval behaviour explicit and easy to test at the command line,
- supports audience-aware queries (small vs medium vs large/gov, consumer vs builder),
- provides a clear interface that can later be reused by the LLM-facing answer generation logic.

Using `websearch_to_tsquery` gives intuitive search semantics for human-style queries, while `ts_rank` provides a simple relevance score for ordering results. Keeping `k` tunable (default 5, but overrideable) mirrors the course pattern and allows experimentation with different top‑k settings for evaluation and answer quality.

### Alternatives considered
- Use a custom scoring function over raw text without PostgreSQL full-text search.
- Implement embedding-based semantic search first and skip lexical search.
- Hard-code a single `k` value for all retrieval use-cases.

### Trade-offs
A simple full-text helper:

- is quick to implement and easy to debug,
- leverages existing PostgreSQL features and the `fts` index, and
- provides a transparent baseline that can be inspected with SQL and CLI tools.

Starting with embeddings would add complexity and make it harder to separate corpus and schema issues from embedding quality. Hard-coding `k` without a CLI parameter would restrict experimentation during evaluation.

### Impact
- `src/retrieve_text.py` becomes the canonical interface for:
  - manual sanity checks (“does this query bring back the right guidance?”),
  - synthetic retrieval evaluation (Hit Rate, MRR) over ground-truth questions, and
  - feeding top‑k chunks into the LLM in later RAG answer flows.
- The script supports queries such as:
  - “how should a small business reduce AI data leak risk”
  - “internet-facing services patching” with `size_tag=medium_business`
  - “training data integrity and provenance” with `role_tag=ai_builder`
  - “agentic AI security controls” scoped to `large_enterprise_gov_critical` and `ai_builder`.
- Manual tests confirm that top-ranked chunks match expectations for these queries, increasing confidence in the baseline retrieval behaviour before formal evaluation.

## D-008 — Text retrieval query refactor for evaluation
Date: 2026-07-24  
Status: Accepted

### Decision
Relax the PostgreSQL full-text search query used in `src/retrieve_text.py` so that retrieval evaluation over long, natural-language questions returns meaningful candidates:

- Replace the hard boolean condition `fts @@ websearch_to_tsquery('english', query)` with a ranking-first approach that:
  - computes a relevance score for all chunks using `ts_rank(fts, websearch_to_tsquery('english', query), 1)`,
  - filters results on `score > 0`,
  - preserves optional audience filters on `size_audience_tag` and `role_audience_tags`.
- Keep the evaluation harness (`src/evaluate_retrieval.py`) and ground-truth dataset unchanged, but add a debug mode that inspects top‑k results per question.

### Reason
Initial retrieval evaluation over the synthetic question set produced zero hits (Hit@5 and MRR both 0.0), and debugging showed that almost all queries returned no rows at all, despite clearly relevant guidance in the corpus. The strict boolean `fts @@ tsquery` gate was too harsh for long, conversational questions:

- a query like “What security precautions should I consider before using a generative AI tool for my small business tasks?” can be parsed into a tsquery that no single chunk satisfies exactly, leading to empty result sets, even when partial term overlap exists.
- by ranking first and then filtering on `score > 0`, the retriever can surface best-effort lexical matches based on overlapping terms (security, generative AI, small business) instead of requiring a perfect boolean match.

After the refactor, retrieval evaluation shows:

- non‑zero strict metrics (Hit@5 and MRR),
- improved relaxed metrics (Hit@10 and relaxed MRR),
- top results that are plausibly relevant security guidance, even when the exact gold chunk is not yet ranked first.

### Alternatives considered
- Keep the strict `fts @@ websearch_to_tsquery` condition and attempt to simplify question text before search.
- Switch from `websearch_to_tsquery` to `plainto_tsquery` while retaining the boolean filter.
- Move directly to vector-based retrieval and treat the lexical baseline as optional.

### Trade-offs
Relaxing the query:

- slightly increases the computational work per query (ranking all chunks), but
- dramatically improves the usefulness of the lexical baseline for evaluation and debugging,
- makes it easier to see where text search is “close but not perfect” before introducing embeddings.

Keeping a strict boolean gate would preserve textbook full-text semantics but continue to hide whether corpus and schema are healthy, since many realistic user questions would return no hits. Jumping straight to vector search would add complexity without first confirming that the corpus and metadata structure are sound.

### Impact
- `src/retrieve_text.py` now implements a v1.5 lexical baseline:
  - ranks chunks by `ts_rank` against `websearch_to_tsquery('english', query)`,
  - filters on positive scores,
  - still supports optional audience filters (`size_audience_tag`, `role_audience_tags`).
- `src/evaluate_retrieval.py`:
  - reports strict and relaxed metrics over the synthetic question set,
  - includes a debug mode that prints top‑k results per question, making retrieval behaviour inspectable.
- The project now has a functioning text baseline for retrieval evaluation, which can be directly compared against future vector or hybrid retrieval approaches without changing the ground-truth dataset or evaluation harness.

## D-009 — Vector index and comparative retrieval evaluation
Date: 2026-07-24  
Status: Accepted

### Decision
Extend the PostgreSQL-backed retrieval index with a pgvector embedding column and introduce a parallel vector-based retriever, then use the existing evaluation harness to compare text vs vector retrieval on the same synthetic question set.

Concretely:

- add a `chunk_embedding` pgvector column to the `chunks` table and populate it using a local sentence-transformers model (MiniLM),
- implement `src/retrieve_vector.py` to perform nearest-neighbour search over `chunk_embedding`,
- update `src/evaluate_retrieval.py` so it reports strict and relaxed metrics for both text and vector retrieval in a single run.

### Reason
The lexical baseline, even after the v1.5 refactor, still struggles with some long, natural-language questions and subtle security phrasing. Dense retrieval over MiniLM embeddings is better aligned with:

- natural-security-question language (for example, “how should a small business use generative AI safely?”),
- paraphrased passages,
- concept-level matches (risks, mitigations, data leakage, provenance, agentic AI controls).

By evaluating both text and vector retrieval on the same synthetic question set (A → Q*), the project can:

- select the stronger retriever based on evidence rather than intuition,
- understand where lexical search succeeds or fails relative to embeddings,
- establish a stable baseline for future hybrid or reranking strategies.

### Alternatives considered
- Keep only the text baseline, treating embeddings as out of scope for the first version.
- Introduce a separate external vector store instead of using pgvector in PostgreSQL.
- Replace text retrieval entirely with vector retrieval, without comparative evaluation.

### Trade-offs
Adding pgvector and a vector retriever:

- increases schema and code complexity slightly (new column, embedding build script, second retrieval helper),
- introduces an embedding model dependency that must be documented and pinned,
- requires an additional step in the reproducible workflow (`db_build_embeddings.py`).

However, it:

- keeps all retrieval logic within the existing PostgreSQL instance, avoiding external infrastructure,
- preserves the canonical `chunks` schema while extending it for dense search,
- provides a clear metric-based comparison between text and vector approaches.

Keeping only text search would simplify the system but leave significant retrieval performance on the table for natural-language security questions. Introducing a separate vector store would add more operational and cognitive overhead without strong benefits for a small, single-node project.

### Impact
- The `chunks` table schema now includes `chunk_embedding` (pgvector) alongside `fts`:
  - `chunk_embedding` stores MiniLM embeddings for `chunk_text` (and related fields as configured),
  - embeddings are built by a dedicated script (`src/db_build_embeddings.py`) and can be rebuilt when the corpus changes.
- `src/retrieve_vector.py` becomes the canonical interface for:
  - semantic retrieval over ACSC guidance using nearest-neighbour search,
  - audience-aware vector retrieval via the same `size_audience_tag` and `role_audience_tags` filters used by the text retriever.
- `src/evaluate_retrieval.py`:
  - runs both retrieval approaches over `data/ground_truth_synthetic.jsonl`,
  - reports strict and relaxed Hit@k and MRR metrics for text and vector retrieval side-by-side,
  - shows that vector retrieval currently outperforms text retrieval on the project’s synthetic evaluation set.
- For the current project stage, vector retrieval is treated as the preferred baseline for downstream RAG answers, while the text baseline remains available for comparison, debugging, and potential hybrid strategies.

## D-010 — Hybrid retrieval and multi-backend evaluation
Date: 2026-07-24  
Status: Accepted

### Decision
Add a simple hybrid retriever alongside the existing text and vector retrievers and extend the shared evaluation harness so that all three backends (text, vector, hybrid) can be compared on the same synthetic question set.

Concretely:

- keep `src/retrieve_text.py` as the lexical baseline over PostgreSQL full-text search,
- keep `src/retrieve_vector.py` as the MiniLM-based semantic retriever over `chunk_embedding` (pgvector),
- implement `src/retrieve_hybrid.py` as a reciprocal-rank-fusion (RRF)–style hybrid that:
  - queries both text and vector backends with the same audience filters,
  - pulls the top 10 candidates from each backend,
  - fuses results per `chunk_id` using RRF to produce a `hybrid_score` and associated debug fields (`text_rank`, `vector_rank`, `text_score`, `vector_similarity`, etc.),
- update `src/evaluate_retrieval.py` so it:
  - runs text, vector, and hybrid retrieval for each question,
  - computes strict Hit@5 and MRR, plus relaxed Hit@10 and MRR, for each backend,
  - optionally writes per-question, per-backend debug records (including top‑k result metadata) to a JSONL file.

### Reason
The project already had a lexical baseline and a stronger vector retriever; introducing a hybrid retriever allows testing whether combining sparse and dense signals improves retrieval quality on ACSC AI guidance for this particular corpus and evaluation setup. Evaluating all three backends through a single, shared harness ensures:

- fair metric comparison across methods,
- a clearer picture of where each backend succeeds or fails,
- better evidence for choosing a default retriever for downstream RAG answers.

The JSONL debug export makes it easier to inspect individual questions, see how each backend ranked chunks, and understand how audience filters and chunk structure affect results.

### Alternatives considered
- Use only text and vector retrieval, without a hybrid experiment.
- Adopt hybrid retrieval as the default without first measuring it against the existing baselines.
- Implement a more complex hybrid strategy (for example, learned weighting or reranking) instead of a simple RRF fusion.

### Trade-offs
Adding a hybrid retriever and multi-backend evaluation:

- introduces some extra code and evaluation complexity, and
- produces more metrics to interpret,

but:

- keeps all retrieval methods aligned on the same corpus, schema, and audience filters,
- provides concrete evidence about whether hybrid actually improves retrieval on this dataset,
- offers richer debug information for analysing retrieval behaviour.

Sticking with only text and vector would keep the system simpler but leave the question of hybrid benefits unanswered. Jumping directly to a more complex hybrid or reranking strategy would add complexity without first validating that a simple RRF fusion helps on this corpus.

### Impact
- The project now has three retrievers:
  - text (lexical),
  - vector (semantic, MiniLM),
  - hybrid (RRF over text and vector),
  all sharing the same chunk schema and audience-aware filters.
- `src/evaluate_retrieval.py` reports strict and relaxed metrics for all three backends in a single run and can emit per-question debug records for deeper analysis.
- On the current synthetic evaluation set, vector retrieval remains the strongest performer; hybrid retrieval substantially improves over text-only but does not outperform vector-only, so vector continues as the preferred baseline for downstream RAG work, with hybrid treated as an evaluated alternative and debugging aid.

## D-011 — Adopt answer-generation v2 as the default grounded answer-generation strategy
Date: 2026-07-26
Status: Accepted

### Decision
Adopt the prompt-grounded answer-generation pipeline in `src/generate_answers.py` as the default answer-generation strategy for the project, replacing the earlier v1 generation approach preserved in `src/generate_answers_v1.py`.

### Context
The project developed more than one vector-based answer-generation variant for the synthetic ACSC evaluation set. An earlier version generated `data/answers/answers_vector_v1.jsonl`. A revised version generated `data/answers/answers_vector_v2_prompt_grounded.jsonl` with stronger prompt-level grounding and more explicit retention of concrete ACSC guidance.

Earlier testing became harder to interpret because different judge configurations had been used at different points. After re-running the comparison under a consistent judge setup, the project compared v1 and v2 on the same 27-question synthetic benchmark.

### Reason
The project chose answer-generation v2 because it performed better than v1 on the current judged benchmark and produced answers that were more complete, specific, and faithful to the source material.

Under the final comparison, v2 achieved 26/27 `good` answers (96.3%) compared with 22/27 `good` answers (81.5%) for v1.

The main observed advantages of v2 were:
- better retention of named resources, frameworks, and standards,
- stronger handling of multi-part questions,
- and more explicit, actionable answer structure.

By contrast, v1 more often over-summarised the source material, omitted concrete named items, or collapsed procedural guidance into high-level generalities.

### Alternatives considered
- Keep answer-generation v1 as the default strategy.
- Preserve both v1 and v2 without selecting a preferred default.
- Delay choosing a default answer-generation variant until a larger benchmark is available.

### Trade-offs
Choosing v2 improves answer quality, but it also increases average token usage relative to v1. On the current evaluation set, that increase was modest compared with the quality improvement, so the trade-off was acceptable for the project.

The benchmark is still small, and the final comparison depends on an LLM judge rather than human-labelled evaluation. The result should therefore be treated as project-level evidence for selecting the stronger current prompt, not as a definitive production benchmark.

### Impact
- `src/generate_answers.py` becomes the default answer-generation script.
- `src/generate_answers_v1.py` is retained for provenance and comparison.
- `data/answers/answers_vector_v2_prompt_grounded.jsonl` becomes the primary generated-answer artefact.
- `data/answers/answers_vector_v2_prompt_grounded_judged.jsonl` becomes the primary judged output associated with the selected answer-generation strategy.
- README, project log, and reproducibility notes should describe v2 as the selected answer-generation approach and v1 as the earlier baseline.

### Notes
The corrected comparison used a consistent judging setup after earlier testing proved unreliable. That evaluation cleanup is part of the project history, but the decision recorded here is the adoption of answer-generation v2 as the preferred project approach.

## D-012 — Streamlit UI, monitoring, and DB bootstrap sequence
Date: 2026-07-26
Status: Accepted

### Context
The project had already selected vector retrieval as the preferred retrieval backend and the v2 prompt-grounded approach as the preferred answer-generation strategy. What was missing was a usable end-to-end interface that allowed interactive querying, visible grounding to retrieved ACSC content, and a simple way to inspect operational behavior during local demos and evaluation.

A second issue was reproducibility of the vector retrieval path. Initialising the database schema and loading chunk text alone was not sufficient to make vector retrieval work, because embeddings still needed to be generated and written to `chunk_embedding`. When that final step was skipped, vector retrieval returned no chunks and the UI could not produce grounded answers.

The project also needed a lightweight monitoring approach that fit the existing stack and could support rubric-facing demonstration without introducing a separate observability platform.

### Decision
Expose the selected vector-based RAG pipeline through a Streamlit UI, store conversation and feedback telemetry in PostgreSQL, and treat the three-step database bootstrap sequence as mandatory for a working system.

Concretely:

- Provide a Streamlit app (`app.py`) with:
  - an **AI Navigator** tab for interactive questions, vector retrieval, grounded answers, and expandable evidence;
  - a **Monitoring Dashboard** tab for summary metrics, per-query latency and cost charts, token usage, hourly conversation volume, feedback counts, and audience breakdowns.
- Log interactions into PostgreSQL via:
  - a `conversations` table for question, answer, model, audience filters, token counts, latency, cost, and timestamp;
  - a `feedback` table for per-conversation thumbs up/down feedback and timestamp.
- Standardise the required DB bootstrap sequence as:
  - `uv run python src/db_init.py`
  - `uv run python src/db_load_chunks.py`
  - `uv run python src/db_build_embeddings.py`

### Alternatives considered
- Keep the project as script-first only, using CLI commands or notebooks instead of a dedicated UI.
- Store conversation and feedback logs in flat files rather than PostgreSQL.
- Leave database setup implicit and rely on ad hoc command order rather than documenting a required three-step bootstrap path.
- Introduce a separate monitoring or observability stack instead of extending the existing PostgreSQL-based setup.

### Consequences
- The Streamlit app becomes the primary interactive entry point for demonstrating the project end to end.
- Users and graders can issue natural-language questions, inspect grounded answers, and review retrieved evidence directly in the UI.
- The project gains lightweight operational visibility through persisted conversation logs, feedback, and dashboard views without requiring separate infrastructure.
- Reusing PostgreSQL keeps the architecture simple, but it also couples monitoring data to the same database environment as the retrieval corpus.
- Vector retrieval is now explicitly dependent on completing all three bootstrap steps; this adds one more required command, but makes failures easier to diagnose and reproduce.
- Documentation must clearly explain:
  - how to launch the Streamlit app,
  - how to initialise and populate the database in the required order,
  - and how monitoring data is captured and surfaced.

## D-013 — Docker Compose as the reproducible runtime path
Date: 2026-07-26
Status: Accepted

### Context
The project had already reached a point where the selected retrieval and answer-generation path could be demonstrated through the Streamlit UI, but the runtime setup still depended on a locally managed Python environment and an ad hoc PostgreSQL container. That made the application harder for reviewers to start consistently and left the runtime environment less reproducible than the documented data and evaluation workflow.

The project also needed to improve its containerization story under the assessment rubric without forcing every offline corpus-preparation and evaluation step into the same runtime path.

### Decision
Adopt Docker Compose as the standard reproducible runtime path for the application stack.

Concretely:

- run PostgreSQL with pgvector in a Compose-managed `postgres` service,
- run the Streamlit UI in a Compose-managed `app` service,
- use a separate one-off `bootstrap` service to initialise schema, load chunks, and build embeddings,
- keep the existing local `uv` workflow available for offline pipeline work such as download, extraction, corpus review, and evaluation.

### Alternatives considered
- Keep PostgreSQL and the Streamlit app as local-only processes with a documented `uv` workflow.
- Use Docker only for PostgreSQL and run the app outside containers.
- Attempt to containerise the full end-to-end offline pipeline and online app in one unified runtime path immediately.

### Consequences
- Reviewers can launch the core application stack with a small set of Docker Compose commands instead of manually setting up Postgres and the Python runtime.
- The project now has a clear containerized path for the end-to-end interactive system, improving both reproducibility and the containerization story.
- The `bootstrap` step makes the required DB initialisation order explicit, but also adds a one-time startup command for fresh environments.
- The offline pipeline remains partly outside Docker for now, which keeps the project simpler while preserving the existing `uv`-based development workflow.

### Notes
This decision applies to the runtime path used to launch and demonstrate the application. It does not mean every corpus-preparation or evaluation step must run inside Docker at this stage.

## D-014 — Adopt reranked retrieval as default
Date: 2026-08-03  
Status: Accepted

### Context
The project had already selected vector retrieval as the preferred baseline, but a reranked variant was added that uses a cross-encoder to rescore the top vector candidates. On the frozen 27-question benchmark, reranked retrieval outperformed plain vector retrieval on both strict and relaxed retrieval metrics.

### Decision
Use **vector retrieval followed by cross-encoder reranking** as the default retrieval path for the project.

Concretely:

- keep `src/retrieve_vector.py` as the first-stage semantic retriever,
- use `src/retrieve_reranked.py` to rerank the top vector candidates,
- treat `vector_reranked` as the preferred backend in evaluation and downstream RAG flows,
- keep text, vector, and hybrid retrieval available as baselines and debugging alternatives.

### Reason
The reranked retriever produced the strongest results on the current synthetic benchmark and did so consistently across repeated runs. It improves the chance that the most exact relevant chunk appears at the top of the ranked list, which is especially useful for grounding answer generation.

### Alternatives considered
- Keep plain vector retrieval as the default.
- Use hybrid retrieval as the default.
- Switch back to text-only retrieval.

### Trade-offs
Reranking adds some latency relative to plain vector retrieval, but the quality gain was large enough to justify that cost for this project stage.

### Impact
- `src/evaluate_retrieval.py` should treat `vector_reranked` as the main retrieval backend for comparison and reporting.
- Documentation should describe the default path as vector search plus cross-encoder reranking.
- If answer generation is regenerated later, it should use reranked retrieval rather than plain vector retrieval.

## D-015 — Query rewriting evaluated but not adopted as the default retrieval path
Date: 2026-08-03  
Status: Accepted


### Context
After adding the cross-encoder reranker as the default retrieval path, the project tested whether a lightweight LLM-based query rewrite step would further improve retrieval quality across the existing backends. The rewrite experiment was implemented as a single-query prompt that preserves audience constraints, expands vague wording, and fixes obvious spelling issues before retrieval.


### Decision
Do **not** adopt query rewriting as the default retrieval step for the project.


Concretely:


- keep `src/rewrite_query.py` as a reusable experimental helper,
- allow rewritten retrieval variants to remain available for comparison,
- but do not route the main retrieval path through query rewriting by default,
- keep `vector_reranked` as the preferred retrieval backend.


### Reason
On the frozen 27-question synthetic benchmark, rewriting did not improve retrieval overall. The strongest backend remained `vector_reranked` without rewrite, while the rewritten variants were weaker or only marginally different:


- `text_rewritten` underperformed `text`,
- `vector_rewritten` slightly improved relaxed MRR but reduced strict Hit@5 and strict MRR,
- `vector_reranked_rewritten` performed worse than `vector_reranked` on strict MRR and relaxed metrics,
- `hybrid_rewritten` underperformed `hybrid`.


The result suggests that the benchmark corpus is already well aligned with semantic retrieval, and prompt-only rewriting introduces enough vocabulary drift to hurt precision and exact passage ranking.

### Alternatives considered
- Make query rewriting the default pre-retrieval step.
- Apply rewriting only to specific query classes, such as vague or conversational questions.
- Use multi-query rewrite fusion or a decomposition strategy instead of single-query rewrite.
- Remove the rewrite code entirely after the benchmark result.


### Trade-offs
Keeping the rewrite helper but not adopting it as the default preserves an experimental path for later work without adding latency or complexity to the main retrieval pipeline.


The main downside is that some vague user queries may still benefit from rewriting in future experiments, but the current evidence does not justify making it part of the standard path.


### Impact
- The default retrieval path remains vector retrieval followed by cross-encoder reranking.
- Query rewriting is documented as an evaluated experiment that did not improve the frozen benchmark.
- `src/rewrite_query.py` remains available for selective or future experimental use.
- Evaluation notes and project logs should record that rewritten retrieval variants were compared but not selected as the default.