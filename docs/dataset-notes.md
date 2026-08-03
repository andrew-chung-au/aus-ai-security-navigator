# Dataset notes

This document is a **living snapshot** of the project's dataset and how it is currently structured, chunked, and used for retrieval and evaluation. It is not a changelog: whenever the corpus, schema, retrieval approach, or evaluation defaults change, this file should be updated in place so that it always describes the latest state a new practitioner will see from a fresh clone.

---

## Core sources

### Core HTML guidance pages

- An introduction to artificial intelligence
- Engaging with artificial intelligence
- AI data security
- Artificial intelligence and machine learning: Supply chain risks and mitigations
- Guidelines for secure AI system development
- Careful adoption of agentic AI services
- Artificial intelligence for small business: Managing cyber security risks

### Core attached PDFs

- Defending against AI-enabled cyber attacks – Guidance for small businesses
- Defending against AI-enabled cyber attacks – Guidance for medium-sized businesses
- Defending against AI-enabled cyber attacks – Guidance for government, critical infrastructure and large enterprises

These core sources are defined in `data/source_manifest_core.csv`. The manifest includes audience metadata split into two dimensions:

- `size_audience_tag` (for example `small_business`, `medium_business`, `large_enterprise_gov_critical`, `all_sizes`)
- `role_audience_tags` (for example `ai_consumer`, `ai_builder`, or both)

These fields are propagated into the retrieval corpus so each chunk carries both organisation size and role context. The same audience information underpins seed selection, synthetic question generation, retrieval evaluation, and answer-generation comparisons.

---

## Boundary sources

The following sources are retained for possible later expansion, but excluded from the current index build:

- Opportunities for AI in cyber defence
- Deploying AI systems securely
- Content credentials
- AI primer
- AI in OT principles

Operational technology guidance is excluded because it broadens the project into OT and critical infrastructure environments beyond the initial scope. Keeping OT and broader cyber guidance out of v1 helps maintain a focused AI security navigator for organisational and AI-system audiences.

---

## Formats, extraction, and snapshot

- Core sources are ingested as HTML pages and attached PDFs.
- All sources are converted into local Markdown files after extraction.
- The source manifest records `content_type` (`html` or `pdf`) so the workflow can route each source to the appropriate downloader and extractor.
- The mixed HTML/PDF corpus improves coverage for audience-specific and topic-specific questions, but requires format-specific extraction and cleanup.

### Manual review

Extraction is followed by a one-time manual review and correction step. This review is limited to fixing extraction artefacts rather than rewriting guidance.

Typical corrections include:

- broken or missing headings
- repeated headers, footers, or navigation text
- duplicated paragraphs
- missing or malformed lists
- table structure problems
- PDF reading-order issues
- other extraction noise that could harm retrieval

The reviewed Markdown files form the cleaned corpus used for chunking, database loading, retrieval, evaluation, and answer generation. This is a one-time quality pass for the small curated corpus rather than an ongoing editorial process.

### Reviewed corpus snapshot

Because manual review is a semi-manual transformation, the project preserves the cleaned Markdown corpus as a versioned snapshot:

- `data/corpus_snapshots/v1_2026-07-25/`

This directory contains:

- the reviewed Markdown files
- `manifest.csv` — the source manifest associated with this snapshot
- `checksums.sha256` — file checksums for verification

For strict reproduction of the current corpus, restore the snapshot into the working processed-corpus directory:

```bash
mkdir -p data/processed
cp -iv data/corpus_snapshots/v1_2026-07-25/*.md data/processed/
```

Then continue from chunk preparation and downstream steps. The `data/processed/` directory remains the overwriteable working location for fresh extraction and manual cleanup; snapshots are treated as immutable inputs. If the corpus is updated later, a new dated snapshot should be created and this document updated accordingly.

---

## Audience-aware corpus

The project treats ACSC AI guidance as an audience-aware corpus:

- Some documents are explicitly written for small businesses, medium-sized businesses, or government, critical infrastructure, and large enterprises.
- Other documents are better understood as guidance for AI system providers or general organisations adopting or using AI systems.
- Some documents apply across organisation sizes but differ in whether they primarily target AI builders, AI consumers, or both.

The `size_audience_tag` and `role_audience_tags` fields in `data/source_manifest_core.csv` capture this segmentation at the document level and are copied into each chunk in the retrieval corpus. This supports:

- audience-aware retrieval and filtering
- evaluation of audience- and role-specific queries
- source-grounded answers that better match organisation type and responsibility

These audience fields are also used when designing seeds and synthetic questions, so evaluation can explicitly slice by organisation size and AI responsibility.

---

## Retrieval-ready corpus

The retrieval-ready corpus is written to:

- `data/chunks/chunks.jsonl`

Each line in `data/chunks/chunks.jsonl` represents one chunk as a JSON object. This file is treated as the canonical text representation of the retrieval corpus before database loading.

### Minimum chunk schema

The minimum chunk schema is:

- `chunk_id` – a stable identifier for the chunk, typically `source_id::index`
- `source_id` – the logical source identifier, aligned with the manifest
- `source_file` – the cleaned Markdown filename for the source document
- `chunk_index` – an integer index reflecting document order
- `chunking_version` – a version tag for the chunking configuration
- `document_title` – the document title, usually taken from the top-level `#` heading
- `heading_path` – the heading hierarchy for the chunk, stored as an ordered path from section to subsection
- `size_audience_tag` – the organisation size label copied from `data/source_manifest_core.csv`
- `role_audience_tags` – the list of role labels (`ai_consumer`, `ai_builder`, or both) copied from `data/source_manifest_core.csv`
- `chunk_text` – the text content used for retrieval, evaluation, and embeddings

This schema is intentionally minimal. It preserves provenance, section context, and audience metadata without adding unnecessary complexity.

During development, the chunking script also emits diagnostic metrics such as `chunk_chars`, `chunk_words`, and `chunk_lines`. These are stored as formal integer columns in the PostgreSQL database to help inspect chunk sizes and identify anomalies. They are useful for QA and database inspection but are treated as non-core retrieval fields.

---

## Chunking approach

The cleaned Markdown corpus is chunked using a heading-aware approach rather than document-wide fixed-size windows. Markdown headings, lists, and tables are treated as meaningful structural boundaries and are preserved where practical.

This approach is intended to:

- preserve document structure and semantic boundaries
- keep related material together
- reduce the risk of splitting lists, tables, or paired risk / mitigation content in unhelpful ways

### General rules

- Headings define the primary chunk boundaries.
- Chunks are anchored to the document title and `heading_path`.
- Headings are not stored as standalone chunks; they are attached to the content beneath them.
- Where useful for retrieval, the heading breadcrumb may be included in a separate `search_text` field before indexing.
- Very large sections may be split further when structure provides a natural boundary, for example long lists, multi-page tables, or very dense guidance blocks.

### Enumerated sections

Some sections contain long top-level numbered recommendations or best-practice lists. Where these lists are large enough to create overly broad chunks, they are split into smaller item-level chunks.

In these cases:

- any introductory text before the list may remain as its own chunk
- each numbered item becomes its own chunk
- the numbered item title is appended to `heading_path` to preserve the semantic focus

This preserves the granularity of enumerated guidance and supports seed–chunk matching when seeds reference specific numbered items.

### Lists

- Bullet lists and numbered lists are kept intact where practical rather than split mid-list.
- Nested lists remain attached to their parent list item.
- Action-oriented checklist sections are treated as cohesive chunk units unless there is a strong structural reason to split them.

### Risk and mitigation pairings

Some documents use repeated patterns where a risk heading is followed by a mitigation or "Managing risks" subsection. These are treated as a single logical unit where possible so that the problem and the recommended response remain together.

Examples include:

- `ai-small-business.md` – risk sections paired with "Managing risks"
- `ai-data-security.md` – risk headings paired with mitigation content
- `engaging-with-ai.md` – threat or risk sections paired with case studies or response guidance
- `agentic-ai-adoption.md` – security domains paired with scenario examples and recommended best practices

Keeping these pairings intact improves retrieval and answer grounding for evaluation questions that ask both "what is the risk?" and "what should we do about it?"

### Tables

Tables are treated as special chunks because naive splitting can damage structure and reduce retrieval quality.

For tables:

- small or medium tables usually remain as a single chunk under the surrounding heading context
- larger tables are only split when necessary and where row or section boundaries provide natural chunk divisions
- when a table is split, row-wise text preserves the relevant heading context and, where needed, column meaning

Manual cleanup may reposition or relabel a table within a section when this better reflects the original structure and improves chunking, provided the meaning is unchanged.

Examples include:

- the AI system lifecycle table in `ai-data-security.md`
- the glossary-style table in `ai-small-business.md`
- condensed risk/mitigation tables in the PDF guides

### Document-specific patterns

Some source documents have recurring structures that the chunking process preserves.

#### AI-enabled cyber attack PDF guides

These guides are audience-segmented and are mostly structured as a document title plus time- or action-based sections. Each major section generally stays intact with its associated action bullets so that evaluation questions about "what should a medium-sized business do immediately?" map cleanly to a single chunk.

#### Guidelines for secure AI system development

Development life cycle phases contain related principles and action items. These remain tied to their parent phase context so that retrieval can return phase-specific guidance for queries about design, build, deployment, and operation.

#### Careful adoption of agentic AI services

Risk and security domains contain nested scenario examples and recommended best practices. These blocks stay grouped under the relevant parent heading where practical to support queries about specific agentic AI risks and control sets.

#### Artificial intelligence and machine learning: Supply chain risks and mitigations

Domain sections contain nested risks, mitigations, and supporting material. These are chunked with their parent domain context preserved so evaluations about supply chain threats and mitigations can be grounded in complete domain blocks.

---

## Manual chunk QA

A small sampled subset of chunks can be exported from `data/chunks/chunks.jsonl` and manually inspected before retrieval indexing.

This spot-check is intended to verify that:

- `heading_path` reflects the cleaned Markdown structure
- `size_audience_tag` and `role_audience_tags` have been propagated correctly from the manifest
- lists and tables were not broken badly in the chunking process
- paired or closely related sections remain coherent when intended

Representative spot-checks include one or two chunks from major source types, such as:

- the small-business PDF
- the medium-business PDF
- the government / critical infrastructure / large enterprise PDF
- selected HTML guidance pages

Where used, this produces inspection files such as:

- `data/chunks/spotcheck.jsonl`
- `data/chunks/spotcheck.json`

This QA step is lightweight and manual, but it helps confirm corpus quality before embeddings, retrieval indexing, and evaluation are applied.

---

## Evaluation seed and question generation

The dataset includes an evaluation-data pipeline built around a curated seed manifest, deterministic seed–chunk matching, LLM seed vetting, and synthetic question generation.

### Seed manifest

A curated seed manifest (`data/ground_truth_seed_draft.json`) defines the passages and audience slices that should be tested. Each seed typically includes:

- `source_id`
- `target_size`
- `target_role`
- `passage_type`
- `why_this_passage`
- `best_heading_path_guess`
- optional `numbered_item_title_guess`
- optional `anchor_quote`

This file captures "what to test" before synthetic questions are generated and before retrieval metrics are computed.

### Seed matching and vetting

Seeds are matched deterministically to concrete chunks in `data/chunks/chunks.jsonl`, producing candidate chunk records with match scores and debugging information.

The matching process gives strong precedence to numbered list items when `numbered_item_title_guess` is present, so list-item seeds resolve to the intended passage rather than a generic sibling under the same section.

Matched chunks are then passed through an LLM-based vetting step. The judge decides whether each chunk should be included for evaluation, assigns a seed quality label (high, medium, low), and may refine the passage type based on the actual chunk content.

This vetting stage filters out weak, overly narrow, or off-target passages before question generation and produces a vetted seed file such as `data/ground_truth_seeds_vetted.jsonl`.

### Synthetic question generation

Vetted seed chunks are used to generate realistic synthetic evaluation questions. The generation step is A → Q* style: a passage is treated as the answer source, and the model produces user-like questions that this passage would plausibly answer.

Generated questions are written to `data/ground_truth_synthetic.jsonl`. Each record preserves the source chunk and audience context so later retrieval and answer evaluation can be sliced by:

- `chunk_id`
- `size_audience_tag`
- `role_audience_tags`
- `target_size`
- `target_role`

Batch generation includes retry handling and a fixed delay between successful requests to stay within rate limits for the chosen model provider.

---

## Retrieval and evaluation

The dataset is exercised via a PostgreSQL-backed retrieval layer over the `chunks` table and an evaluation harness that computes metrics on the synthetic question set.

### Text retrieval helper

The baseline text retrieval helper (`src/retrieve_text.py`):

- uses PostgreSQL full-text search to compute a relevance score for chunks via `ts_rank(fts, websearch_to_tsquery('english', query), 1)`
- filters results on `score > 0` rather than requiring a strict boolean match on `fts @@ websearch_to_tsquery('english', query)`
- preserves optional audience filters on:
  - `size_audience_tag` (with `all_sizes` as a fallback), and
  - `role_audience_tags` (JSONB array containment)
- returns the top‑k chunks, default `k=5` and configurable, ordered by score with secondary tie-breaking for reproducibility

This refactor was motivated by the observation that long, conversational questions rarely satisfied a strict boolean full-text condition, leading to empty result sets even when relevant guidance existed. Ranking first and filtering on positive scores produces a more practical lexical baseline for the current corpus.

### Vector retrieval and reranking

The retrieval-ready corpus in `data/chunks/chunks.jsonl` is also used to build a dense vector index inside PostgreSQL:

- a local MiniLM sentence-transformers model encodes each chunk's embedding text into a normalised vector
- embeddings are written into a `chunk_embedding` pgvector column on the `chunks` table
- query embeddings are computed with the same model and normalisation settings, and nearest-neighbour search uses cosine distance (`chunk_embedding <=> query_embedding`), with optional audience filters on `size_audience_tag` and `role_audience_tags`

A vector retriever (`src/retrieve_vector.py`) exposes this behaviour and returns chunk dictionaries that include both `cosine_distance` and a convenience `similarity` score alongside the usual metadata.

A reranking layer (`src/retrieve_reranked.py`) is built on top of the vector retriever:

- it first retrieves a candidate set with vector search
- it then applies a cross-encoder reranker to rescore those candidates
- it returns the reranked top results for downstream evaluation and answer grounding

The evaluation harness (`src/evaluate_retrieval.py`) now runs these retrieval modes over `data/ground_truth_synthetic.jsonl`:

- text
- vector
- reranked vector
- hybrid

and computes strict Hit@k and MRR based on exact `chunk_id` matches, plus relaxed metrics where same-document / same-leaf-heading matches count as partial hits. An optional JSONL debug output contains, for each question and backend, the gold labels, per-rank relevance flags, and top‑k result metadata; this is used for manual inspection but does not alter the underlying datasets.

On the current 27-question synthetic benchmark, the measured results were:

- text: strict Hit@5 0.25925925925925924, strict MRR 0.09876543209876543, relaxed Hit@10 0.25925925925925924, relaxed MRR 0.09876543209876543
- vector: strict Hit@5 0.8518518518518519, strict MRR 0.75, relaxed Hit@10 0.9259259259259259, relaxed MRR 0.7608024691358025
- vector_reranked: strict Hit@5 0.9259259259259259, strict MRR 0.8888888888888888, relaxed Hit@10 0.9629629629629629, relaxed MRR 0.8935185185185185
- hybrid: strict Hit@5 0.7777777777777778, strict MRR 0.3728395061728395, relaxed Hit@10 0.8888888888888888, relaxed MRR 0.38893298059964726

On that benchmark, `vector_reranked` is the strongest retrieval backend and is treated as the preferred retrieval path for downstream RAG work. Plain vector retrieval remains the strongest non-reranked baseline, while text and hybrid remain useful comparative baselines and debugging tools.

Query rewriting was also evaluated across all four main backends (`text`, `vector`, `vector_reranked`, `hybrid`) using a dedicated LLM-based rewrite helper (`src/rewrite_query.py`). On the frozen 27-question synthetic benchmark, rewritten variants did not improve the best-performing backend and generally reduced strict metrics or produced only marginal differences. The strongest overall backend remains `vector_reranked` without rewrite. As a result, query rewriting is treated as an experimental tool, not part of the default retrieval path, and is retained for possible future selective or gated strategies (e.g. only for clearly vague or underspecified queries).

---

## Vector-based answer dataset and LLM-as-a-judge annotations

The current dataset also supports a vector-based answer-generation and LLM-as-a-judge evaluation pipeline.

### Answer datasets

Ground-truth synthetic questions from `data/ground_truth_synthetic.jsonl` are answered using retrieval over the chunks corpus and a grounded answer-generation prompt.

The project currently preserves three answer-generation outputs for comparison and provenance:

- `data/answers/answers_vector_v1.jsonl`
- `data/answers/answers_vector_v2_prompt_grounded.jsonl`
- `data/answers/answers_vector_reranked_v2_prompt_grounded.jsonl`

These files represent different stages of the answer-generation pipeline:

- `answers_vector_v1.jsonl` — earlier baseline answer-generation variant
- `answers_vector_v2_prompt_grounded.jsonl` — plain vector retrieval + v2 prompt-grounded strategy, preserved as a frozen baseline
- `answers_vector_reranked_v2_prompt_grounded.jsonl` — reranked vector retrieval + v2 prompt-grounded strategy, treated as the current default answer-generation artefact

The reranked-vector v2 path is the selected answer-generation approach for the project's current comparison story. The earlier v1 and plain-vector v2 files are retained as frozen baselines for provenance and historical comparison.

Each line in these files is a JSON object that typically includes:

- `question_id`
- `question`
- `seed_id`
- `target_size` and `target_role`
- `gold_source_id` and `gold_chunk_id`
- `retrieved_chunks`
- `answer_text`
- `answer_chunk_ids`
- `grounded`
- `model_id`
- `top_k`
- `usage`

For the reranked-vector artefact, `retrieved_chunks` may also include retrieval metadata such as:

- `similarity`
- `reranker_score`
- `vector_rank`

These files are derived datasets layered on top of the existing chunk corpus, seeds, and synthetic questions. When comparing answer quality across variants, treat `answers_vector_v1.jsonl` and `answers_vector_v2_prompt_grounded.jsonl` as frozen historical baselines, and treat `answers_vector_reranked_v2_prompt_grounded.jsonl` as the current default output generated by `src/generate_answers.py`.

### Judge annotations

To evaluate answer quality, separate judging steps run over the answer datasets and produce judged outputs. The project currently preserves two judged files:

- `data/answers/answers_vector_v1_judged.jsonl`
- `data/answers/answers_vector_v2_prompt_grounded_judged.jsonl`

For each answer record, the judge compares the question, gold passage, and generated answer using a rubric that focuses on semantic equivalence, core idea coverage, and inclusion of important named resources when the question explicitly asks for them.

Each judged record extends the original answer fields with:

- `judge_model_id`
- `judge_score`
- `judge_reasoning`
- `judge_gold_chunk_text`
- `judge_gold_heading_path`
- `judge_usage`

These annotations are evaluation artefacts layered on top of the existing dataset. They rely on stable `chunk_id` and `gold_chunk_id` labels, plus the audience metadata carried through the corpus.

---

## Current default retrieval and answer-generation path

For a fresh clone, the default end-to-end path for retrieval and grounded answer generation is:

### Corpus and chunking

- restore the reviewed Markdown snapshot from `data/corpus_snapshots/v1_2026-07-25/` into `data/processed/` or rerun extraction and cleanup if intentionally rebuilding,
- run `src/prepare_chunks.py` to regenerate `data/chunks/chunks.jsonl` with the current heading-aware, audience-aware chunking configuration.

### Database and retrieval index

- run `src/db_init.py` to create the PostgreSQL schema, including fts and `chunk_embedding` columns and supporting indexes,
- run `src/db_load_chunks.py` to load `data/chunks/chunks.jsonl` into the `chunks` table,
- run `src/db_build_embeddings.py` to compute MiniLM embeddings and backfill the `chunk_embedding` pgvector column.

### Retrieval baseline for evaluation and UI

- use the reranked vector retriever (`src/retrieve_reranked.py`) as the primary retrieval backend for both:
  - synthetic evaluation over `data/ground_truth_synthetic.jsonl`, and
  - the interactive UI and answer-generation flows,
- keep the plain vector (`src/retrieve_vector.py`), text (`src/retrieve_text.py`), hybrid (`src/retrieve_hybrid.py`), and rewrite-enabled retrieval variants available as evaluated baselines and debugging tools; they operate over the same chunks corpus but are not the default for the current RAG path.
- the rewrite-enabled variants are explicitly documented as experimental: they were compared on the frozen benchmark but not adopted, and are not used by the interactive UI or the default answer-generation pipeline.

### Answer-generation and judged datasets

- treat `data/answers/answers_vector_v2_prompt_grounded.jsonl` as the main generated-answer dataset,
- treat `data/answers/answers_vector_v2_prompt_grounded_judged.jsonl` as the main judged output associated with the selected v2 prompt-grounded strategy,
- retain the v1 files (`answers_vector_v1*.jsonl`) as earlier baselines for provenance and comparison rather than as current defaults.

This reflects the project's current state: reranked vector retrieval plus the v2 prompt-grounded answer-generation pipeline is the default path for both evaluation and the interactive application, while all other retrieval modes and answer variants remain as documented, reproducible baselines layered on top of the same core dataset.

For setup, runtime commands, and reproduction workflows, see `docs/runbook.md`.

---

## 2026-07-26 — Streamlit UI and monitoring usage of the dataset

The current Streamlit application (`app.py`) exercises the existing dataset and retrieval stack without changing the underlying corpus, chunking, or evaluation artefacts described above.

Key points:

### Corpus and chunks

- The AI Navigator tab queries the same chunks corpus built from the reviewed Markdown snapshot (`data/corpus_snapshots/v1_2026-07-25/`) and heading-aware chunking pipeline.
- Audience metadata (`size_audience_tag`, `role_audience_tags`) continues to be used as filters in both backend retrieval and the interactive UI.

### Retrieval backend

- The AI Navigator uses the reranked vector retriever (`chunks.chunk_embedding` with cosine distance, then cross-encoder reranking) as its default backend.
- Optional audience filters are applied in the same way as in evaluation: organisation size tag, with `all_sizes` as a fallback, and role tags for AI builders and AI consumers.
- The plain vector, text, hybrid, and rewrite-enabled retrieval helpers remain available for evaluation and debugging, but are not wired into the default UI flow.

### Answer generation and grounding

- The evaluated answer artifacts (`answers_vector_v2_prompt_grounded.jsonl`) were generated using the plain vector baseline for historical comparison.
- However, the live AI Navigator UI dynamically uses the upgraded `vector_reranked` backend at query time alongside the winning v2 prompt to maximize final answer quality.
- At query time, retrieved chunks are passed to the v2 prompt, and the returned answer includes:
  - a groundedness flag,
  - a set of `answer_chunk_ids` for grounding,
  - token usage information.
- The evidence panel in the UI shows the retrieved chunks, including `chunk_id`, `heading_path`, and audience tags, reusing the same fields that underpin the evaluation datasets.

### Monitoring and conversation logs

- Conversation logs in the `conversations` table refer back to the dataset indirectly via:
  - the question text and selected audience filters,
  - the model ID and token counts,
  - response latency and estimated cost.
- Feedback entries in the `feedback` table are keyed by `conversation_id` and do not modify the underlying corpus or evaluation artefacts.
- Dashboard charts are derived entirely from these operational tables and metrics; they consume, but do not alter, any of:
  - `data/chunks/chunks.jsonl`,
  - `data/ground_truth_*` evaluation files,
  - answer and judged answer datasets under `data/answers/`.

In other words, the Streamlit UI and monitoring layer sit on top of the existing dataset and retrieval infrastructure. They provide an interactive and observable interface to the reranked vector + v2 prompt-grounded RAG path while leaving the core corpus, chunking strategy, seeds, synthetic questions, and judged answer datasets unchanged.