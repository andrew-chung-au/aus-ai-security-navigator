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