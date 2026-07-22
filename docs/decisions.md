# Decisions


## D-001 — Project topic
Date:
Status: Proposed / Accepted / Superseded

### Decision
Use "Australian AI Security Navigator" as the project topic.

### Reason
The topic has accessible public data and a more specific retrieval need than a generic cyber-security corpus.

### Alternatives considered
- Ransomware resilience navigator
- Broader Australian cyber guidance navigator

### Trade-offs
This project is more distinctive, but requires tighter corpus curation to avoid overlap with future AI governance projects.

### Impact
Defines the project scope, target users, and source selection process.


## D-002 — Initial source corpus
Date: 2026-07-22
Status: Accepted

### Decision
Use a manually curated ACSC AI guidance corpus as the initial project dataset, including a core set of HTML guidance pages and the attached PDF guidance on defending against AI-enabled cyber attacks, rather than indexing the entire related website.

### Reason
A curated corpus is easier to reproduce, easier to evaluate, and more likely to produce relevant retrieval results than a broad crawl. Including the attached PDFs in the core set adds audience-specific and operational guidance that complements the broader HTML pages while keeping the project manageable within the available timeframe.

### Alternatives considered
- Index only the ACSC AI landing page
- Crawl all linked AI guidance pages
- Use only the HTML guidance pages in the first build
- Use a broader cyber-security corpus

### Trade-offs
Including both HTML pages and attached PDFs improves coverage, especially for operational and audience-specific questions, but introduces mixed-format extraction and cleanup work. A curated corpus still reduces noise compared with a broad crawl, but some overlap between documents will need to be managed through metadata and chunking.

### Impact
The source manifest will distinguish between core HTML pages, core attached PDFs, and boundary documents. The downloader and extraction workflow will support both HTML and PDF sources in the first index build.

## D-003 — Audience-aware corpus design
Date: 2026-07-22
Status: Accepted

### Decision
Represent ACSC AI guidance as an audience-aware corpus by:
- keeping the initial dataset small and curated, and
- adding a deterministic `audience_tag` field at the document level (e.g. `small_business`, `medium_business`, `large_enterprise_gov_critical`, `ai_system_provider`, `general_organisation`) that is propagated to all chunks.

### Reason
Many ACSC AI guidance publications are explicitly segmented by audience (small businesses, medium-sized businesses, government, critical infrastructure, large enterprises, and AI system providers). Preserving this segmentation in the corpus makes it easier to:
- retrieve guidance that matches an organisation’s context, and
- explain why a particular document was selected for an answer.

A simple document-level `audience_tag` is enough for a small, curated corpus and avoids the complexity of per-chunk audience inference in the first version.

### Alternatives considered
- Rely only on the original `audience` text field in the manifest without a normalized tag.
- Infer audience dynamically at query time using an LLM.
- Ignore audience in the corpus and treat all guidance as general organisational content.

### Trade-offs
Normalising audience into a small tag vocabulary adds a one-time manual mapping step, but:
- keeps the retrieval index simple to filter and analyse, and
- reduces reliance on on-the-fly LLM categorisation for core corpus structure.

Ignoring audience would simplify ingestion, but would weaken one of the main differentiators of the project and make evaluation of audience-specific queries less meaningful.

### Impact
- The source manifest now includes a normalized `audience_tag` for each document.
- Chunk preparation scripts will carry `audience_tag` into every chunk record.
- Retrieval evaluation will include audience-specific queries (e.g. small vs medium vs large/gov) to verify that audience-aware metadata improves results.