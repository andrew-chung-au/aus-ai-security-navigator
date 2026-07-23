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


## 2026-07-22 — Corpus extraction and audience framing (v1)

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
- Confirmed the source manifest structure and, for the initial version, added an explicit single `audience_tag` field per source
- Aligned deterministic audience tags with `source_id` values in `data/source_manifest_core.csv`

### Why
- The project depends on audience-aware retrieval: many ACSC AI guidance documents are written specifically for small businesses, medium-sized businesses, or government, critical infrastructure, and large enterprises, and this context needs to be preserved through ingestion and chunking
- Mixed HTML/PDF sources can introduce extraction noise that harms retrieval, so a one-time manual review and correction step is a pragmatic quality improvement for a small curated dataset
- Freezing audience metadata at the document level in the manifest keeps the mapping simple and deterministic while still allowing chunks to carry audience metadata in the retrieval index

### Problems / uncertainties
- Some guidance pages are broad organisational documents and were initially tagged as `general_organisation` even though they may skew toward larger or more complex environments
- Joint or multi-agency guidance may imply audiences not captured perfectly by a single normalized label
- Audience tags for some documents might need refinement later if evaluation reveals mismatches between query intent and document tagging

### Next step
Use the updated manifest to prepare a retrieval-ready corpus from the cleaned Markdown files.


## 2026-07-22 — Chunk schema and heading-aware chunking

### Goal
Define the minimum retrieval chunk schema and prepare the first retrieval-ready chunked corpus.

### What was done
- Defined a minimum chunk schema for the first build (later updated after the audience refactor):
  - initial version:
    - `source_file`
    - `document_title`
    - `heading_path`
    - `audience_tag`
    - `chunk_text`
  - current version:
    - `source_file`
    - `document_title`
    - `heading_path`
    - `size_audience_tag`
    - `role_audience_tags`
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
  - audience metadata is being propagated correctly from the manifest
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
- audience-aware queries (using `size_audience_tag` and `role_audience_tags`)
- document-specific operational guidance queries
- overlapping-topic queries where multiple sources may compete
- whether the current chunking decisions hold up under actual retrieval


## 2026-07-23 — Audience metadata: size and role refactor

### Goal
Refine audience representation to separate organisation size from AI responsibility (builder vs consumer) and propagate this into the retrieval corpus.

### What was done
- Replaced the single `audience_tag` field in `data/source_manifest_core.csv` with:
  - `size_audience_tag` (e.g. `small_business`, `medium_business`, `large_enterprise_gov_critical`, `all_sizes`)
  - `role_audience_tags` (e.g. `ai_consumer`, `ai_builder`, or both)
- Updated manifest rows for all core sources to use the new two-dimensional scheme
- Updated `src/prepare_chunks.py` so each chunk record now carries:
  - `size_audience_tag`
  - `role_audience_tags`
- Updated `src/download_sources.py` so download metadata captures the new audience fields for provenance
- Updated documentation (`README.md`, `docs/dataset-notes.md`, `docs/reproducibility.md`, `docs/decisions.md`) to reflect the new audience model and chunk schema

### Why
- Many documents clearly differentiate between organisations using/adopting AI and those building or providing AI systems
- A single label could not cleanly express both organisation size and role, which limited audience-aware retrieval and evaluation
- Making size and role explicit supports more precise filtering and more transparent explanations of why particular documents are retrieved (for example, “large enterprise AI builder” vs “small business AI consumer”)

### Problems / uncertainties
- Some documents apply across all sizes and both roles; in these cases, conservative tagging (e.g. `all_sizes` plus both roles) may still be coarse
- Future evaluation may suggest further refinement (for example, more granular roles), but that is deferred to later iterations

### Next step
Regenerate `data/chunks/chunks.jsonl` with the new audience fields and confirm the updated schema via spot-checking before indexing.


## 2026-07-23 — Seed–chunk matching and seed vetting (v1)

### Goal
Connect curated evaluation seeds to concrete chunks and vet them as suitable seed passages for question generation.

### What was done
- Created `data/ground_truth_seed_draft.json` as a curated list of important passages to test, with fields:
  - `source_id`
  - `target_size`
  - `target_role`
  - `passage_type`
  - `why_this_passage`
  - `best_heading_path_guess`
  - optional `numbered_item_title_guess`
  - optional `anchor_quote`
- Implemented a deterministic seed–chunk matching script (`src/match_seeds_to_chunks.py`) that:
  - groups chunks by `source_id`
  - for each seed, optionally narrows the candidate pool to chunks whose last heading matches `numbered_item_title_guess` after loose normalization
  - if such numbered-item matches exist, ranks only that subset; otherwise, uses all chunks for that `source_id`
  - computes similarity scores based on:
    - full heading-path similarity
    - last-heading similarity and an exact-match bonus
    - numbered item title similarity and exact-match bonus (when present)
    - anchor-quote similarity and containment (when present)
  - selects the best-scoring chunk and records:
    - `candidate_chunk` (compact metadata + `chunk_text`)
    - `candidate_debug` (scoring breakdown)
    - `match_score`, `selection_confidence`, `score_margin`
    - `selection_strategy` (e.g. `numbered_item_exact_subset` or `all_source_chunks`)
- Wrote the matching results to `data/seed_chunk_candidates.json`
- Designed and applied an LLM-based judging prompt that:
  - inspects each `candidate_chunk`
  - decides `include_for_eval` (true/false)
  - assigns `seed_quality` (`high`, `medium`, or `low`)
  - may adjust `suggested_passage_type` based on the actual content
  - provides a short natural-language `reason` for the judgement
- Collected the judgements in a vetted seed file (e.g. `data/ground_truth_seeds_vetted.jsonl`)
- Observed that, for the current curated seeds:
  - all inspected seeds were marked `include_for_eval: true`
  - most seeds were rated `high` quality, with some `medium` and no `low` ratings in this pass

### Why
- Mapping high-level seed intents (size, role, passage_type, heading guess, anchor quote) to concrete chunks is necessary for reproducible evaluation
- Explicit handling of `numbered_item_title_guess` ensures that list-item seeds (such as “4. Leverage trusted infrastructure”) resolve to the intended chunk rather than a generic sibling under the same section
- Using an LLM as a judge at this stage surfaces weak or overly narrow passages before investing in question generation and retrieval metrics
- Storing both `candidate_chunk` and `candidate_debug` supports later debugging and potential tuning of the matching heuristics

### Problems / uncertainties
- Matching still depends on heuristics; while numbered items now have stronger precedence, some edge cases may remain where heading paths or anchor quotes are ambiguous
- The current vetted set has no `seed_quality: "low"` entries, which reflects strong initial curation but may under-sample problematic passages; future iterations may need to add intentionally borderline seeds
- LLM judgement is stable for this small set, but future expansions may require calibration or spot-checking by humans

### Next step
- Use the vetted seeds as the basis for A → Q* question generation to build `ground_truth_questions.jsonl` for retrieval and RAG evaluation
- Begin designing evaluation metrics and harnesses (e.g. Hit Rate, MRR, LLM-as-judge for answers) that consume the vetted seeds and generated questions

## 2026-07-23 — Ground-truth question generation pipeline

### Goal
Generate synthetic evaluation questions from vetted seed chunks for the A → Q* retrieval setup.

### What was done
- Built `src/generate_ground_truth_questions.py` to generate one realistic question per vetted seed chunk.
- Used the matched `candidate_chunk` as the source of truth and the seed metadata as generation context.
- Added audience-aware provenance to each output record, including:
  - `target_size`
  - `target_role`
  - `size_audience_tag`
  - `role_audience_tags`
- Wrote the generated dataset to `data/ground_truth_synthetic.jsonl`.
- Added structured-output client helpers in `src/llm_client.py`.
- Added a small structured-output smoke test in `src/test_structured_output.py`.
- Updated `README.md`, `docs/reproducibility.md`, `pyproject.toml`, and `uv.lock` to reflect the new generation workflow and dependencies.

### Why
- The evaluation workflow needs a stable, reproducible question set tied to gold chunks.
- Including both seed intent and chunk provenance makes later retrieval and slice-based evaluation easier.
- A dedicated generation script keeps the dataset creation step separate from retrieval and answer evaluation.

### Problems / uncertainties
- The generation job hit the free-tier request quota once and needed retry/backoff handling.
- A small fixed delay between requests is useful for staying under rate limits during batch generation.

### Next step
Run retrieval evaluation on the generated question set, starting with Hit Rate and MRR over `chunk_id`.

## 2026-07-23 — Batch pacing and retry handling

### Goal
Make synthetic question generation more stable under API rate limits.

### What was done
- Kept retry handling in the shared LLM client helper.
- Added the plan to pace batch generation in the question-generation script rather than in the shared client.
- Chose a fixed 4-second delay between successful requests to better respect the 15-requests-per-minute quota.

### Why
- The batch job is sequential, so a simple fixed delay reduces quota errors.
- Keeping pacing in the batch script avoids slowing down unrelated LLM calls elsewhere in the project.

### Problems / uncertainties
- Retries still may be needed if the external service is temporarily unavailable.
- If other processes share the same quota, the delay may still need adjustment.

### Next step
Commit the documentation and pipeline updates, then proceed to retrieval evaluation.

