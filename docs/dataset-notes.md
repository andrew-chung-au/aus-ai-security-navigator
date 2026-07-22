# Dataset notes

## Core sources

### HTML pages in first build
- An introduction to artificial intelligence
- Engaging with artificial intelligence
- AI data security
- AI and ML supply chain risks and mitigations
- Guidelines for secure AI system development
- Careful adoption of agentic AI services
- Artificial intelligence for small business

### Attached PDFs in first build
- Defending against AI-enabled cyber attacks – Guidance for small businesses
- Defending against AI-enabled cyber attacks – Guidance for medium-sized businesses
- Defending against AI-enabled cyber attacks – Guidance for government, critical infrastructure and large enterprises

These core sources are all defined in `data/source_manifest_core.csv` with a normalized `audience_tag` field (for example `small_business`, `medium_business`, `large_enterprise_gov_critical`, `ai_system_provider`, `general_organisation`) that is propagated into the retrieval corpus.

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
- All sources in the first build are converted into cleaned Markdown files after extraction.
- The source manifest records `content_type` (HTML or PDF) so the extraction workflow can route each source to the appropriate extractor.
- The mixed HTML/PDF corpus increases coverage, especially for operational and audience-specific questions, but requires format-specific extraction and cleanup.

### Manual review

Extraction is followed by a one-time manual review and correction step for the first corpus:

- broken or missing headings
- repeated headers, footers, or navigation text
- duplicated paragraphs
- missing or malformed lists
- table structure and reading-order issues
- other extraction noise that could harm retrieval

Reviewed Markdown files are used as the basis for chunking and indexing.

## Audience-aware corpus

The project treats ACSC AI guidance as an audience-aware corpus:

- Many documents are explicitly segmented for small businesses, medium-sized businesses, or government/critical infrastructure/large enterprises.
- Additional guidance targets AI system providers and general organisations using AI systems.

The `audience_tag` field in `data/source_manifest_core.csv` captures this segmentation at the document level and is copied into every chunk in the retrieval corpus so that:

- queries can be evaluated for audience-specific behaviour
- answers can be grounded in guidance that matches the organisation type

## Chunk schema

The first retrieval-ready corpus will be written to:

- `data/chunks/chunks.jsonl`

Each line in `data/chunks/chunks.jsonl` represents one chunk as a JSON object with the following minimum schema:

- `source_file` – the cleaned Markdown filename for the source document
- `document_title` – the document title, usually taken from the top-level `#` heading
- `heading_path` – the heading hierarchy for the chunk, stored as an ordered path from section to subsection
- `audience_tag` – the normalized audience label copied from `data/source_manifest_core.csv`
- `chunk_text` – the text content of the chunk used for retrieval and embedding

This minimal schema is intended to preserve provenance and audience context without adding unnecessary complexity in the first build.

## Chunking and tables

When preparing the retrieval-ready corpus from cleaned Markdown:

- Chunking is heading-aware: each chunk is anchored to a document title and a heading path rather than being split only by fixed size.
- Bullet lists under a heading should be kept intact in a single chunk rather than split mid-list.
- Risk and mitigation sections that naturally pair (for example, a risk subsection followed immediately by a mitigation subsection) can be kept in one chunk to preserve context.
- If a heading section is too large, it can be split by paragraph while preserving the same `heading_path`.

Tables are treated as special chunks because generic splitting can damage their structure and reduce retrieval quality.

For tables:

- small or medium tables should be kept as a single chunk with the surrounding heading context.
- larger tables may be split by rows only if necessary, with column headers repeated in each split chunk.
- where Markdown tables are awkward for retrieval, they may be converted into readable row-wise text while preserving the heading context.

These chunking rules are documented here to make the retrieval corpus design explicit and to support evaluation of how structure-aware chunking affects retrieval quality.

## Summary

- The first index build includes core ACSC AI HTML guidance pages and three attached PDFs on defending against AI-enabled cyber attacks.
- Boundary sources are kept for future expansion but excluded from the first version.
- Sources are extracted and cleaned into Markdown, with manual corrections for structural issues.
- Audience tags are defined deterministically at the document level and propagated into the retrieval corpus.
- The first retrieval-ready corpus will be stored as `data/chunks/chunks.jsonl`.
- Chunking rules emphasize heading-aware splits, intact lists, and special handling of tables.