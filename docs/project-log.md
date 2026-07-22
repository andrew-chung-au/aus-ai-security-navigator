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
  - government, critical infrastructure and large enterprises
- Initial source manifest for the first build

### Excluded from the first build
- Operational Technology guidance, because it broadens the project into critical infrastructure and OT environments
- Boundary AI guidance pages, which are relevant but reserved for possible later expansion

### Why
The corpus is public, accessible, and specific enough that retrieval should add value beyond a general LLM. The attached PDFs add more operational and audience-specific guidance than the HTML pages alone.

### Problems / uncertainties
Some pages overlap in topic, so metadata and chunking will matter. The mixed HTML and PDF corpus may also need format-specific extraction and cleanup.

### Next step
Create the source manifest, download script, and extraction workflow for both HTML and PDF sources.

## 2026-07-22 — Corpus extraction and audience framing

### Goal
Move from raw ACSC sources to a cleaned, retrieval-ready corpus and clarify how audience context will be represented.

### What was done
- Completed HTML and PDF extraction into local Markdown files.
- Manually reviewed and corrected extracted text for:
  - broken headings
  - repeated headers/footers and navigation chrome
  - missing or malformed lists
  - table structure and reading order issues
- Confirmed the source manifest structure and added an explicit `audience_tag` field for each source.
- Used an external AI-assisted review to propose deterministic audience tags for the cleaned documents (e.g. `small_business`, `medium_business`, `large_enterprise_gov_critical`, `ai_system_provider`, `general_organisation`), then aligned those tags with `source_id` values in `data/source_manifest_core.csv`.

### Why
- The project depends on audience-aware retrieval: many ACSC AI guidance documents are written specifically for small businesses, medium-sized businesses, or government/critical infrastructure and large enterprises, and this context needs to be preserved through ingestion and chunking.
- Mixed HTML/PDF sources can introduce extraction noise that harms retrieval. A one-time manual review and correction step is a pragmatic way to improve corpus quality for a small, curated dataset.
- Freezing `audience_tag` at the document level in the manifest keeps the mapping simple and deterministic, while still allowing chunks to carry audience metadata in the retrieval index.

### Problems / uncertainties
- Some guidance pages are broad organisational documents (e.g. general AI engagement or usage guidance) and are tagged as `general_organisation` even though they may be skewed towards larger or more complex environments.
- Joint or multi-agency guidance referenced in the ACSC material (e.g. AI data security and supply-chain documents) may include audiences like DIB, NSS, or other non-Australian entities; for this project, tags were normalised to fit the Australian AI Security Navigator framing.
- Audience tags for agentic AI and AI data security may need refinement later as evaluation reveals how users query across organisation types and roles.

### Next step
- Use the updated manifest (with `audience_tag`) to:
  - implement heading-aware chunking over the cleaned Markdown corpus
  - propagate `audience_tag` into each chunk record
- Produce a small retrieval-ready corpus file (e.g. `data/corpus/chunks.jsonl`) and start designing a retrieval evaluation set that exercises:
  - audience-specific queries (small vs medium vs large/gov)
  - topic-specific queries (data security, supply-chain, agentic AI, AI-enabled attacks)