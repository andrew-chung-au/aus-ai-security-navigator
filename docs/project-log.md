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

## 2026-07-22 — Corpus extraction and audience framing

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
- Confirmed the source manifest structure and added an explicit `audience_tag` field for each source
- Aligned deterministic audience tags with `source_id` values in `data/source_manifest_core.csv`

### Why
- The project depends on audience-aware retrieval: many ACSC AI guidance documents are written specifically for small businesses, medium-sized businesses, or government, critical infrastructure, and large enterprises, and this context needs to be preserved through ingestion and chunking
- Mixed HTML/PDF sources can introduce extraction noise that harms retrieval, so a one-time manual review and correction step is a pragmatic quality improvement for a small curated dataset
- Freezing `audience_tag` at the document level in the manifest keeps the mapping simple and deterministic while still allowing chunks to carry audience metadata in the retrieval index

### Problems / uncertainties
- Some guidance pages are broad organisational documents and are tagged as `general_organisation` even though they may skew toward larger or more complex environments
- Joint or multi-agency guidance may imply audiences not captured perfectly by the normalized project vocabulary
- Audience tags for some documents may need refinement later if evaluation reveals mismatches between query intent and document tagging

### Next step
Use the updated manifest to prepare a retrieval-ready corpus from the cleaned Markdown files.

## 2026-07-22 — Chunk schema and heading-aware chunking

### Goal
Define the minimum retrieval chunk schema and prepare the first retrieval-ready chunked corpus.

### What was done
- Defined a minimum chunk schema for the first build:
  - `source_file`
  - `document_title`
  - `heading_path`
  - `audience_tag`
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
  - `audience_tag` is being propagated correctly from the manifest
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
- audience-aware queries
- document-specific operational guidance queries
- overlapping-topic queries where multiple sources may compete
- whether the current chunking decisions hold up under actual retrieval