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
Use a manually curated ACSC AI guidance corpus as the initial project dataset, starting with a core subset of documents rather than indexing the entire related website.

### Reason
A curated corpus is easier to reproduce, easier to evaluate, and more likely to produce relevant retrieval results than a broad crawl. It also keeps the project manageable within the available timeframe.

### Alternatives considered
- Index only the ACSC AI landing page
- Crawl all linked AI guidance pages
- Use a broader cyber-security corpus

### Trade-offs
A smaller corpus reduces noise and simplifies evaluation, but may miss some edge-case questions until later expansion.

### Impact
The source manifest will distinguish between core and boundary documents, and the downloader will initially retrieve only core sources.

