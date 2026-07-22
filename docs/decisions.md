# Decisions

## D-001 — Project topic
Date: 2026-07-xx  
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

## D-003 — Audience-aware corpus design
Date: 2026-07-22  
Status: Accepted

### Decision
Represent ACSC AI guidance as an audience-aware corpus by:

- keeping the initial dataset small and curated, and  
- adding a deterministic `audience_tag` field at the document level (e.g. `small_business`, `medium_business`, `large_enterprise_gov_critical`, `ai_system_provider`, `general_organisation`) that is propagated into all chunks.

### Reason
Many ACSC AI guidance publications are explicitly segmented by audience (small businesses, medium-sized businesses, government, critical infrastructure, large enterprises, and AI system providers). Preserving this segmentation in the corpus makes it easier to:

- retrieve guidance that fits an organisation’s context, and
- explain why a particular document was selected for an answer.

For a small, curated corpus, a simple document-level `audience_tag` is sufficient and avoids the complexity of inferring audience per chunk or per query in the first version.

### Alternatives considered
- Rely only on the original free-text `audience` field in the manifest without a normalized tag.
- Infer audience dynamically at query time using an LLM.
- Ignore audience segmentation and treat all guidance as general organisational content.

### Trade-offs
Normalising audience into a small tag vocabulary adds a one-time manual mapping step, but:

- keeps the retrieval index simple to filter, debug, and evaluate, and
- reduces reliance on on-the-fly LLM categorisation for core corpus structure.

Ignoring audience would simplify ingestion, but would weaken one of the main differentiators of the project and make audience-specific evaluation less meaningful.

### Impact
- The source manifest includes a normalized `audience_tag` for each document.
- Chunk preparation scripts carry `audience_tag` into every chunk record in the retrieval corpus.
- Retrieval evaluation will include audience-aware queries (e.g. small vs medium vs large/gov) to verify that audience metadata improves results and supports more interpretable answers.

---

## D-004 — Chunking strategy and QA
Date: 2026-07-22  
Status: Accepted

### Decision
Use a heading-aware, structure-preserving chunking strategy over the cleaned Markdown corpus, combined with a small manual spot-check step for sampled chunks before retrieval indexing.

The minimum chunk schema for the first build remains:

- `source_file`
- `document_title`
- `heading_path`
- `audience_tag`
- `chunk_text`

### Reason
The ACSC AI guidance corpus is small, curated, and has strong existing structure (titles, sections, lists, tables, and repeated risk / mitigation patterns). A heading-aware chunking strategy is a better fit than blind fixed-size windows because it:

- preserves document hierarchy and section context,
- keeps related content (for example, “Scope and audience” and risk / mitigation sections) together where practical, and
- avoids splitting lists and tables mid-structure when that would harm retrieval.

A lightweight manual spot-check of sampled chunks is a pragmatic QA step for a semi-manual pipeline. It helps verify that heading paths, audience tags, and key structures (lists, tables) have survived extraction and chunking before building embeddings and retrieval indexes.

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
- The minimum chunk schema stays simple but supports provenance and audience-aware retrieval.
- A small script (`src/spotcheck_chunks.py`) and accompanying docs (`docs/reproducibility.md`) document how sampled chunks are exported and inspected as part of the reproducible workflow.
- Evaluation and retrieval design can assume that chunk structure reflects ACSC guidance layout, not arbitrary windowing, which should improve grounded answer quality for audience-specific and document-specific queries.