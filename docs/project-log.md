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
Use a curated ACSC AI guidance corpus as the first version of the project dataset.

### Included
- An introduction to artificial intelligence
- Engaging with artificial intelligence
- AI data security
- AI and ML supply chain risks and mitigations
- Guidelines for secure AI system development
- Careful adoption of agentic AI services
- Artificial intelligence for small business

### Excluded from the first build
- Operational Technology guidance, because it broadens the project into critical infrastructure and OT environments
- Boundary AI guidance pages, which are relevant but reserved for possible later expansion

### Why
The corpus is public, accessible, and specific enough that retrieval should add value beyond a general LLM.

### Problems / uncertainties
Some pages overlap in topic, so metadata and chunking will matter.

### Next step
Create the source manifest and download script.