# Dataset notes

This document is a **living snapshot** of the project’s dataset and how it is currently structured, chunked, and used for retrieval and evaluation. It is not a changelog: whenever the corpus, schema, or retrieval approach changes, this file should be updated in place so that it always describes the latest state a new practitioner will see from a fresh clone.

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

These fields are propagated into the retrieval corpus so each chunk carries both organisation size and role context. The same audience information underpins seed selection, synthetic question generation, and retrieval evaluation.

## Boundary sources

The following sources are retained for possible later expansion, but excluded from the current index build:

- Opportunities for AI in cyber defence  
- Deploying AI systems securely  
- Content credentials  
- AI primer  
- AI in OT principles  

Operational technology (OT) guidance is excluded because it broadens the project into OT and critical infrastructure environments beyond the initial scope. Keeping OT and broader cyber guidance out of v1 helps maintain a focused AI security navigator for organisational and AI-system audiences.

## Formats and extraction

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

The reviewed Markdown files form the cleaned corpus used for chunking, database loading, retrieval, and evaluation. This is a one-time quality pass for the small curated corpus rather than an ongoing editorial process.

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

## Retrieval-ready corpus

The retrieval-ready corpus is written to:

- `data/chunks/chunks.jsonl`

Each line in `data/chunks/chunks.jsonl` represents one chunk as a JSON object. This file is treated as the canonical text representation of the retrieval corpus before database loading.

### Minimum chunk schema

The minimum chunk schema is:

- `chunk_id` – a stable identifier for the chunk (for example `source_id::index`)  
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

During development, the chunking script also emits diagnostic metrics such as `chunk_chars`, `chunk_words`, and `chunk_lines` to help inspect chunk sizes and identify unusually long or short chunks. These diagnostics are useful for QA and database inspection but are treated as non-core retrieval fields.

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
- Where useful for retrieval, the heading breadcrumb may be prepended to `chunk_text` or included in a separate `search_text` field before indexing.  
- Very large sections may be split further when structure provides a natural boundary (e.g. long lists, multi-page tables, or very dense guidance blocks).

### Enumerated sections

Some sections contain long top-level numbered recommendations or best-practice lists. Where these lists are large enough to create overly broad chunks, they are split into smaller item-level chunks.

In these cases:

- any introductory text before the list may remain as its own chunk  
- each numbered item becomes its own chunk  
- the numbered item title is appended to `heading_path` to preserve the semantic focus  

This preserves the granularity of enumerated guidance without falling back to arbitrary fixed-size windows and supports seed–chunk matching when seeds reference specific numbered items.

### Lists

- Bullet lists and numbered lists are kept intact where practical rather than split mid-list.  
- Nested lists remain attached to their parent list item.  
- Action-oriented checklist sections are treated as cohesive chunk units unless there is a strong structural reason to split them.

### Risk and mitigation pairings

Some documents use repeated patterns where a risk heading is followed by a mitigation or `Managing risks` subsection. These are treated as a single logical unit where possible so that the problem and the recommended response remain together.

Examples include:

- `ai-small-business.md` – risk sections paired with `Managing risks`  
- `ai-data-security.md` – risk headings paired with mitigation content  
- `engaging-with-ai.md` – threat or risk sections paired with case studies or response guidance  
- `agentic-ai-adoption.md` – security domains paired with scenario examples and recommended best practices  

Keeping these pairings intact improves retrieval and answer grounding for evaluation questions that ask both “what is the risk?” and “what should we do about it?”.

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

## Document-specific patterns

Some source documents have recurring structures that the chunking process preserves.

### AI-enabled cyber attack PDF guides

These guides are audience-segmented (small business, medium-sized business, and government / critical infrastructure / large enterprise) and are mostly structured as a document title plus time- or action-based sections (e.g. immediate, medium-term, longer-term actions). Each major section generally stays intact with its associated action bullets so that evaluation questions about “what should a medium-sized business do immediately?” map cleanly to a single chunk.

### Guidelines for secure AI system development

Development life cycle phases contain related principles and action items. These remain tied to their parent phase context so that retrieval can return phase-specific guidance for queries about design, build, deployment, and operation.

### Careful adoption of agentic AI services

Risk and security domains contain nested scenario examples and recommended best practices. These blocks stay grouped under the relevant parent heading where practical to support queries about specific agentic AI risks and control sets.

### Artificial intelligence and machine learning: Supply chain risks and mitigations

Domain sections contain nested risks, mitigations, and supporting material. These are chunked with their parent domain context preserved so evaluations about supply chain threats and mitigations can be grounded in complete domain blocks.

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

This file captures “what to test” before synthetic questions are generated and before retrieval metrics are computed.

### Seed matching and vetting

Seeds are matched deterministically to concrete chunks in `data/chunks/chunks.jsonl`, producing candidate chunk records with match scores and debugging information.

The matching process gives strong precedence to numbered list items when `numbered_item_title_guess` is present, so list-item seeds resolve to the intended passage rather than a generic sibling under the same section.

Matched chunks are then passed through an LLM-based vetting step. The judge decides whether each chunk should be included for evaluation, assigns a seed quality label (`high`, `medium`, `low`), and may refine the passage type based on the actual chunk content.

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

## Retrieval and evaluation (current setup)

The dataset is exercised via a PostgreSQL-backed retrieval layer over the `chunks` table and an evaluation harness that computes metrics on the synthetic question set.

### Text retrieval helper

The baseline text retrieval helper (`src/retrieve_text.py`):

- uses PostgreSQL full-text search to compute a relevance score for chunks via  
  - `ts_rank(fts, websearch_to_tsquery('english', query), 1)`
- filters results on `score > 0` rather than requiring a strict boolean match on  
  - `fts @@ websearch_to_tsquery('english', query)`
- preserves optional audience filters on:  
  - `size_audience_tag` (with `all_sizes` as a fallback), and  
  - `role_audience_tags` (JSONB array containment)
- returns the top‑k chunks (default `k=5`, configurable) ordered by score, with a secondary sort on `chunk_words` for tie‑breaking  

This refactor was motivated by the observation that long, conversational questions rarely satisfied a strict boolean full-text condition, leading to empty result sets even when relevant guidance existed. Ranking first and filtering on positive scores produces a more practical lexical baseline for the current corpus.

### Evaluation harness

Using the synthetic ground-truth questions in `data/ground_truth_synthetic.jsonl` and the chunk corpus:

- strict metrics (exact `chunk_id` match within top‑k) report non‑zero Hit@k and MRR values, indicating that some gold chunks appear early in the ranked list  
- relaxed metrics (exact or same-heading match within a larger top‑k) report higher hit rates and MRR, reflecting cases where retrieval reaches the correct document and section even when the exact gold chunk is not ranked first  

A debug mode in `src/evaluate_retrieval.py` prints top‑k results per question (including `chunk_id`, `source_id`, leaf heading, and score), confirming that:

- the chunked dataset and audience metadata are being used correctly in retrieval  
- the primary remaining gaps are in lexical ranking rather than in corpus structure or schema  

These retrieval and evaluation behaviours do not alter the dataset itself:

- core and boundary sources and audience metadata in `data/source_manifest_core.csv` remain unchanged  
- the retrieval-ready corpus in `data/chunks/chunks.jsonl` retains the same minimal schema and structure-aware chunking  
- the seed manifest, vetted seeds, and synthetic question dataset continue to rely on `chunk_id`, `heading_path`, `size_audience_tag`, and `role_audience_tags`  

This document therefore continues to describe the dataset and its structure; retrieval and evaluation changes are reflected here only insofar as they explain how the existing corpus is currently searched and assessed.