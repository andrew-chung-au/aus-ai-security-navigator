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

## D-003 — Audience-aware corpus design (size and role)
Date: 2026-07-23  
Status: Accepted

### Decision
Represent ACSC AI guidance as an audience-aware corpus using **two explicit dimensions** at the document level:

- `size_audience_tag` for organisation size and criticality  
  (e.g. `small_business`, `medium_business`, `large_enterprise_gov_critical`, `all_sizes`)
- `role_audience_tags` for responsibility and AI usage role  
  (e.g. `ai_consumer`, `ai_builder`, or both)

These fields replace the earlier single `audience_tag` and are propagated into all chunks.

### Reason
Many ACSC AI guidance publications are explicitly segmented by audience (small businesses, medium-sized businesses, government, critical infrastructure, large enterprises, and AI system providers) and implicitly segmented by role (organisations using AI vs those building or providing AI systems).

Separating size and role makes it easier to:

- retrieve guidance that fits both an organisation’s scale and responsibility,
- explain why a particular document was selected for an answer, and
- evaluate queries that differ by both size (small vs medium vs large/gov) and role (builder vs consumer).

For a small, curated corpus, explicit document-level `size_audience_tag` and `role_audience_tags` are sufficient and avoid the complexity of inferring audience per chunk or per query in the first version.

### Alternatives considered
- Keep a single normalized `audience_tag` label per document.
- Rely only on the original free-text `audience` field in the manifest without normalized tags.
- Infer audience and role dynamically at query time using an LLM.
- Ignore audience and role segmentation and treat all guidance as general organisational content.

### Trade-offs
Normalising into two small tag vocabularies adds a one-time manual mapping step, but:

- keeps the retrieval index simple to filter, debug, and evaluate,
- reduces reliance on on-the-fly LLM categorisation for core corpus structure, and
- supports more nuanced audience-aware tests (e.g. small-business AI consumer vs large-enterprise AI builder).

Keeping a single tag would simplify the manifest but blur the distinction between organisation size and AI responsibility, making some retrieval and evaluation scenarios harder to express.

### Impact
- The source manifest includes `size_audience_tag` and `role_audience_tags` for each document, and no longer carries the legacy single `audience_tag` field.
- Chunk preparation scripts carry `size_audience_tag` and `role_audience_tags` into every chunk record in the retrieval corpus.
- Retrieval and evaluation can explicitly condition on size and role (for example, “small business AI consumer” vs “large enterprise AI builder”) when designing test queries and filters.


---

## D-004 — Chunking strategy and QA
Date: 2026-07-22  
Status: Accepted

### Decision
Use a heading-aware, structure-preserving chunking strategy over the cleaned Markdown corpus, combined with a small manual spot-check step for sampled chunks before retrieval indexing.

The minimum chunk schema for the first build is:

- `source_file`
- `document_title`
- `heading_path`
- `size_audience_tag`
- `role_audience_tags`
- `chunk_text`

### Reason
The ACSC AI guidance corpus is small, curated, and has strong existing structure (titles, sections, lists, tables, and repeated risk / mitigation patterns). A heading-aware chunking strategy is a better fit than blind fixed-size windows because it:

- preserves document hierarchy and section context,
- keeps related content (for example, “Scope and audience” and risk / mitigation sections) together where practical, and
- avoids splitting lists and tables mid-structure when that would harm retrieval.

A lightweight manual spot-check of sampled chunks is a pragmatic QA step for a semi-manual pipeline. It helps verify that heading paths, audience metadata (size and role), and key structures (lists, tables) have survived extraction and chunking before building embeddings and retrieval indexes.

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
- The minimum chunk schema stays simple but supports provenance and audience-aware retrieval using both size and role metadata.
- A small script (for example, `src/spotcheck_chunks.py`) and accompanying docs (`docs/reproducibility.md`, `docs/dataset-notes.md`) document how sampled chunks are exported and inspected as part of the reproducible workflow.
- Evaluation and retrieval design can assume that chunk structure reflects ACSC guidance layout, not arbitrary windowing, which should improve grounded answer quality for audience-specific and document-specific queries.


---

## D-005 — Seed–chunk matching and LLM seed vetting
Date: 2026-07-23  
Status: Accepted

### Decision
Introduce an explicit **seed–chunk matching** step and a separate **LLM-based seed vetting** step before generating evaluation questions:

- Maintain a curated seed configuration file (`ground_truth_seed_draft.json`) describing which passages and audiences to test.
- Use a deterministic matching script to resolve each seed to a concrete chunk in `chunks.jsonl`, with strong precedence for numbered list items when `numbered_item_title_guess` is provided.
- Use an LLM judge to decide whether each matched chunk is a good seed passage for generating realistic evaluation questions.

### Reason
The evaluation strategy follows an A → Q* pattern: start from a passage A, generate user-like questions Q*, and later evaluate retrieval and RAG answers against that passage and the source. To make this reproducible:

- seeds must be resolved to stable `chunk_id` values, not just fuzzy heading and quote guesses, and
- passages used as seeds must be coherent, audience-appropriate, and rich enough to support realistic questions.

Giving `numbered_item_title_guess` strong precedence ensures that seeds targeting specific list items (such as “4. Leverage trusted infrastructure”) resolve to the intended chunk, rather than a generic sibling under the same section. Using an LLM judge at the seed stage filters out overly narrow, boilerplate, or off-target passages before question generation.

### Alternatives considered
- Treat the initial seed manifest as ground truth without matching or vetting.
- Match seeds to chunks using only heading-path similarity and anchor quotes, without special handling for numbered items.
- Skip seed vetting and directly generate questions from all matched chunks.

### Trade-offs
Adding a matching step and an LLM vetting step:

- increases implementation complexity and introduces an additional pipeline stage, but
- substantially improves traceability (seed → chunk_id), debuggability (via `candidate_debug`), and seed quality before generating evaluation questions.

Skipping these steps would simplify the pipeline but:

- make it harder to understand or fix misalignments between intended passages and actual chunks, and
- risk generating questions from weak, overly narrow, or mis-targeted passages.

### Impact
- A seed configuration file (`ground_truth_seed_draft.json`) captures human/LLM-curated ideas about “what to test” without being treated as final ground truth.
- A matching script resolves each seed to a specific chunk in `chunks.jsonl`, producing `seed_chunk_candidates.json` with:
  - `candidate_chunk`
  - `candidate_debug`
  - `match_score`, `selection_confidence`, `selection_strategy`
- An LLM judging step produces a vetted seed file (e.g. `ground_truth_seeds_vetted.jsonl`) with:
  - `seed_id`, `chunk_id`
  - `include_for_eval`
  - `seed_quality` (`high`, `medium`, `low`)
  - `suggested_passage_type`
  - `reason`
- Downstream evaluation (question generation, retrieval metrics, RAG answer scoring) can rely on:
  - stable `chunk_id`s for relevance labels, and
  - a set of seed passages that have been explicitly checked for coherence, audience fit, and question potential.