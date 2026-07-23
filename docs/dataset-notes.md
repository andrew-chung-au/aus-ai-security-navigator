# Dataset notes


## Core sources


### HTML pages in first build
- An introduction to artificial intelligence
- Engaging with artificial intelligence
- AI data security
- Artificial intelligence and machine learning: Supply chain risks and mitigations
- Guidelines for secure AI system development
- Careful adoption of agentic AI services
- Artificial intelligence for small business: Managing cyber security risks


### Attached PDFs in first build
- Defending against AI-enabled cyber attacks – Guidance for small businesses
- Defending against AI-enabled cyber attacks – Guidance for medium-sized businesses
- Defending against AI-enabled cyber attacks – Guidance for government, critical infrastructure and large enterprises


These core sources are defined in `data/source_manifest_core.csv`. The manifest includes audience metadata split into two dimensions:

- `size_audience_tag` (for example `small_business`, `medium_business`, `large_enterprise_gov_critical`, `all_sizes`)
- `role_audience_tags` (for example `ai_consumer`, `ai_builder`, or both)

These fields are propagated into the retrieval corpus so each chunk carries both organisation size and role context.


## Boundary sources


Retained for possible later expansion, but excluded from the first index build:

- Opportunities for AI in cyber defence
- Deploying AI systems securely
- Content credentials
- AI primer
- AI in OT principles

Operational technology (OT) guidance is excluded from the first build because it broadens the project into critical infrastructure and OT environments beyond the initial scope.


## Formats and extraction


- Core sources are ingested as HTML pages and attached PDFs.
- All first-build sources are converted into local Markdown files after extraction.
- The source manifest records `content_type` (`html` or `pdf`) so the workflow can route each source to the appropriate downloader and extractor.
- The mixed HTML/PDF corpus improves coverage for audience-specific and topic-specific questions, but it also requires format-specific extraction and cleanup.


### Manual review

Extraction is followed by a one-time manual review and correction step for the first corpus. This review is limited to extraction corrections rather than rewriting.

Typical corrections include:

- broken or missing headings
- repeated headers, footers, or navigation text
- duplicated paragraphs
- missing or malformed lists
- table structure problems
- PDF reading-order issues
- other extraction noise that could harm retrieval

The reviewed Markdown files form the cleaned corpus used for chunking, embedding, and retrieval.


## Audience-aware corpus


The project treats ACSC AI guidance as an audience-aware corpus:

- Some documents are explicitly written for small businesses, medium-sized businesses, or government, critical infrastructure, and large enterprises.
- Other documents are better understood as guidance for AI system providers or general organisations adopting or using AI systems.
- Some documents apply across organisation sizes but differ in whether they primarily target AI builders, AI consumers, or both.

The `size_audience_tag` and `role_audience_tags` fields in `data/source_manifest_core.csv` capture this segmentation at the document level and are copied into each chunk in the retrieval corpus. This supports:

- audience-aware retrieval and filtering
- evaluation of audience- and role-specific queries
- source-grounded answers that better match organisation type and responsibility


## Retrieval-ready corpus


The first retrieval-ready corpus is written to:

- `data/chunks/chunks.jsonl`

Each line in `data/chunks/chunks.jsonl` represents one chunk as a JSON object.


### Minimum chunk schema

The minimum chunk schema for the first build is:

- `chunk_id` – a stable identifier for the chunk (for example `source_id::index`)
- `source_id` – the logical source identifier, aligned with the manifest
- `source_file` – the cleaned Markdown filename for the source document
- `chunk_index` – an integer index reflecting document order
- `chunking_version` – a version tag for the chunking configuration
- `document_title` – the document title, usually taken from the top-level `#` heading
- `heading_path` – the heading hierarchy for the chunk, stored as an ordered path from section to subsection
- `size_audience_tag` – the organisation size label copied from `data/source_manifest_core.csv`
- `role_audience_tags` – the list of role labels (`ai_consumer`, `ai_builder`, or both) copied from `data/source_manifest_core.csv`
- `chunk_text` – the text content used for embedding and retrieval

This schema is intentionally minimal. It preserves provenance, section context, and audience metadata without adding unnecessary complexity in the first build.

During development, the chunking script may also emit diagnostic metrics such as chunk word count, character count, or line count to help inspect chunk sizes. These are treated as diagnostics rather than part of the core retrieval schema.


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
- Where useful for retrieval, the heading breadcrumb may be prepended to `chunk_text` before embedding.
- Very large sections may be split further when structure provides a natural boundary.


### Enumerated sections

Some sections contain long top-level numbered recommendations or best-practice lists. Where these lists are large enough to create overly broad chunks, they are split into smaller item-level chunks.

In these cases:

- any introductory text before the list may remain as its own chunk
- each numbered item becomes its own chunk
- the numbered item title is appended to `heading_path`

This is used to preserve the semantic focus of enumerated guidance without falling back to arbitrary fixed-size windows.


### Lists

- Bullet lists and numbered lists should be kept intact where practical rather than split mid-list.
- Nested lists should remain attached to their parent list item.
- Action-oriented checklist sections are treated as cohesive chunk units unless there is a strong structural reason to split them.


### Risk and mitigation pairings

Some documents use repeated patterns where a risk heading is followed by a mitigation or `Managing risks` subsection. These are treated as a single logical unit where possible so that the problem and the recommended response remain together.

Examples in the first build include:

- `ai-small-business.md` – risk sections paired with `Managing risks`
- `ai-data-security.md` – risk headings paired with mitigation content
- `engaging-with-ai.md` – threat sections paired with case studies
- `agentic-ai-adoption.md` – risk or security domains paired with scenario examples and recommended best practices


### Tables

Tables are treated as special chunks because naive splitting can damage structure and reduce retrieval quality.

For tables:

- small or medium tables should usually remain as a single chunk under the surrounding heading context
- larger tables may be split only when necessary
- when a table is split, row-wise text should preserve the relevant heading context and, where needed, the column meaning
- manual cleanup may reposition or relabel a table within a section when this better reflects the original structure and improves chunking, provided the meaning is unchanged

Examples in the first build include:

- the AI system lifecycle table in `ai-data-security.md`
- the glossary table in `ai-small-business.md`


## Document-specific patterns


Some source documents have recurring structures that the chunking process should preserve.

### AI-enabled cyber attack PDF guides

These guides are audience-segmented (small business, medium-sized business, and government / critical infrastructure / large enterprise) and are mostly structured as a document title plus time- or action-based sections. Each major section should generally stay intact with its associated action bullets.

### Guidelines for secure AI system development

Development life cycle phases contain related principles and action items. These should remain tied to their parent phase context.

### Careful adoption of agentic AI services

Risk and security domains contain nested scenario examples and recommended best practices. These blocks should remain grouped under the relevant parent heading where practical.

### Artificial intelligence and machine learning: Supply chain risks and mitigations

Domain sections contain nested risks, mitigations, and supporting material. These should be chunked with their parent domain context preserved.


## Manual chunk QA


For the first build, a small sampled subset of chunks can be exported from `data/chunks/chunks.jsonl` and manually inspected before retrieval indexing.

This spot-check is intended to verify that:

- `heading_path` reflects the cleaned Markdown structure
- `size_audience_tag` and `role_audience_tags` have been propagated correctly from the manifest
- lists and tables were not broken badly
- paired or closely related sections remain coherent where intended

Representative spot-checks should include one or two chunks from major source types, such as:

- the small-business PDF
- the medium-business PDF
- the government / critical infrastructure / large enterprise PDF
- selected HTML guidance pages

Where used, this produces inspection files such as:

- `data/chunks/spotcheck.jsonl`
- `data/chunks/spotcheck.json`

This QA step is lightweight and manual, but it helps confirm corpus quality before embeddings, retrieval indexing, and evaluation are added.


## Current first-build status


For the first build:

- the dataset is manifest-defined in `data/source_manifest_core.csv`
- source files are downloaded into raw HTML and PDF folders based on `content_type`
- extracted content is manually reviewed into cleaned Markdown
- the cleaned Markdown corpus is chunked into `data/chunks/chunks.jsonl`
- each chunk carries `size_audience_tag` and `role_audience_tags` from the manifest
- heading-aware chunking is implemented
- long enumerated sections can be split into item-level chunks where needed
- diagnostic fields such as chunk word count, character count, or line count may be present for inspection, but are treated as non-core metadata
- a small sampled subset of chunks can be exported and manually inspected before retrieval indexing


## Summary


- The first index build uses a curated ACSC AI guidance corpus consisting of core HTML pages and three audience-specific PDF guides.
- Boundary sources are retained for possible later expansion but excluded from the first build.
- Sources are extracted and cleaned into Markdown, with a documented manual correction step for structural issues.
- Audience metadata is defined deterministically in the manifest via `size_audience_tag` and `role_audience_tags` and propagated into the chunked corpus.
- The first retrieval-ready corpus is stored as `data/chunks/chunks.jsonl`.
- Chunking is structure-aware and preserves headings, lists, tables, and risk / mitigation relationships where practical.
- Long enumerated guidance sections may be split into item-level chunks when that improves retrieval focus.
- A small manual spot-check step can be used to inspect sampled chunks before retrieval indexing.