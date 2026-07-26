# Evaluation notes

This document records how retrieval and answer-generation are evaluated in the project, what benchmarks and metrics are used, and which approaches are currently selected as defaults. It is intended for reviewers and future contributors who want to understand the evaluation setup and findings without digging through code or logs.

---

## 1. Evaluation goals

The evaluation setup is designed to answer three main questions:

- How well does the retrieval layer find the ACSC guidance passages that were intended as ground truth for particular questions?
- How well do different answer-generation prompts convert retrieved context into grounded, concrete answers?
- Which retrieval and answer-generation paths should be treated as the current defaults for the interactive application and for future experiments?

To keep the evaluation reproducible and focused, all experiments run over a small synthetic benchmark built from vetted ACSC passages and audience slices.

---

## 2. Retrieval evaluation

### 2.1 Benchmark construction

Retrieval evaluation is based on a synthetic benchmark built in three stages:

- **Seed selection**: A curated seed manifest (`data/ground_truth_seed_draft.json`) identifies important ACSC passages and audience slices to test. Each seed encodes:
  - `source_id`
  - `target_size` (e.g. small_business, medium_business, large_enterprise_gov_critical)
  - `target_role` (ai_consumer, ai_builder, or both)
  - `passage_type` and `why_this_passage`
  - a best guess at `heading_path` and, where needed, `numbered_item_title_guess`.

- **Seed–chunk matching and vetting**:
  - `src/match_seeds_to_chunks.py` matches seeds to concrete chunks in `data/chunks/chunks.jsonl`, producing `data/seed_chunk_candidates.json` with candidate chunks, scores, and debug information.
  - An LLM-based vetting step consumes these candidates and writes `data/ground_truth_seeds_vetted.jsonl`, marking which seeds to include for evaluation and assigning a seed-quality label.

- **Synthetic question generation**:
  - `src/generate_ground_truth_questions.py` generates one user-like question per vetted seed, using an A → Q* pattern.
  - The output (`data/ground_truth_synthetic.jsonl`) records, for each question:
    - `question_id`, `question`
    - `source_id`, `chunk_id`
    - `size_audience_tag`, `role_audience_tags`
    - `target_size`, `target_role`.

This benchmark is small (currently 27 questions) and intentionally seed-anchored. It is primarily a tool for comparative evaluation and debugging, not a full coverage measure of ACSC guidance.

### 2.2 Retrieval methods

Three retrieval methods are evaluated over the same benchmark:

- **Text (lexical)** — `src/retrieve_text.py`:
  - uses PostgreSQL full-text search (`fts` over `search_text`),
  - ranks chunks using `ts_rank(fts, websearch_to_tsquery('english', query), 1)`,
  - filters on `score > 0` to avoid empty result sets for long questions,
  - supports optional filters on:
    - `size_audience_tag` (with `all_sizes` as a fallback),
    - `role_audience_tags` (JSONB array containment).

- **Vector (dense)** — `src/retrieve_vector.py`:
  - uses a MiniLM sentence-transformers model (currently `sentence-transformers/all-MiniLM-L6-v2`) to embed `chunk_text` and queries,
  - stores embeddings in a pgvector `chunk_embedding` column,
  - performs nearest-neighbour search using cosine distance (`chunk_embedding <=> query_embedding`),
  - supports the same audience filters as the text retriever,
  - returns per-chunk `cosine_distance` and a convenience `similarity` score.

- **Hybrid (RRF)** — `src/retrieve_hybrid.py`:
  - calls both the text and vector retrievers with the same query and audience filters,
  - collects a small candidate set from each (e.g. top‑10 text and top‑10 vector),
  - fuses results per `chunk_id` using reciprocal rank fusion (RRF) to produce a `hybrid_score`,
  - preserves backend-specific debug fields (`text_rank`, `vector_rank`, `text_score`, `vector_similarity`).

All three methods operate over the same chunk corpus (`data/chunks/chunks.jsonl`) and audience metadata.

### 2.3 Metrics

Retrieval evaluation is implemented in `src/evaluate_retrieval.py`. For each backend (text, vector, hybrid), it computes:

- **Strict metrics**:
  - Hit@k: whether the exact gold `chunk_id` appears in the top‑k results.
  - MRR: mean reciprocal rank of the exact gold `chunk_id`.

- **Relaxed metrics**:
  - Hit@k (relaxed): counts hits where the retrieved chunk shares:
    - the same `source_id`, and
    - the same leaf heading (final element of `heading_path`),
    - even if the `chunk_id` differs.
  - MRR (relaxed): mean reciprocal rank under the same relaxed matching rule.

An optional `--debug-output` parameter writes per-question, per-backend debug records to a JSONL file (e.g. `data/eval/retrieval_debug.jsonl`), including:

- question and audience fields,
- gold labels (source and chunk),
- strict/relaxed relevance flags per rank,
- backend-specific scores and ranks.

### 2.4 Findings

On the current 27-question synthetic benchmark:

- **Text retrieval**:
  - After loosening the full-text condition to “rank then filter on `score > 0`”, strict Hit@k and MRR are non-zero.
  - However, text retrieval still struggles with long, conversational questions and nuanced AI-security phrasing.

- **Vector retrieval**:
  - Strict Hit@k and MRR are substantially higher than for text.
  - Vector retrieval is particularly stronger on:
    - paraphrased security questions,
    - questions about risk/mitigation combinations,
    - questions using more natural, less keyword-driven language.

- **Hybrid retrieval**:
  - Hybrid (RRF) improves clearly over text-only.
  - On this benchmark, hybrid does **not** outperform vector-only.
  - In some cases it pulls in useful lexical hits; in others it slightly dilutes strong vector rankings.

Given this evidence, the project treats **vector retrieval** as the current default backend for both evaluation and the interactive application. Text and hybrid retrieval remain available as evaluated baselines and debugging tools.

---

## 3. Answer-generation evaluation

### 3.1 Setup

Answer-generation evaluation is built on top of the synthetic retrieval benchmark:

- questions come from `data/ground_truth_synthetic.jsonl`,
- gold passages are identified by `gold_source_id` and `gold_chunk_id`,
- retrieval uses the vector backend with a default `top_k` (currently 5) and audience filters derived from `target_size` and `target_role`.

For each question, the evaluation pipeline:

1. retrieves top‑k chunks via vector retrieval,
2. assembles a structured context (chunks plus headings and audience metadata),
3. calls a prompt-grounded LLM to generate an answer,
4. stores the answer and provenance in JSONL.

The project currently preserves two answer datasets:

- `data/answers/answers_vector_v1.jsonl`
- `data/answers/answers_vector_v2_prompt_grounded.jsonl`

The v2 file corresponds to the currently selected answer-generation approach.

### 3.2 Datasets

Each answer record typically includes:

- question and audience fields:
  - `question_id`, `question`
  - `seed_id`
  - `target_size`, `target_role`
- gold labels:
  - `gold_source_id`, `gold_chunk_id`
- retrieval context:
  - `retrieved_chunks` (with `chunk_id`, `source_id`, `heading_path`, audience tags, scores)
- answer fields:
  - `answer_text`
  - `answer_chunk_ids`
  - `grounded` (boolean or flag)
- model and usage diagnostics:
  - `model_id`
  - `top_k`
  - `usage` (prompt, completion, total tokens)

The v1 and v2 datasets share the same questions and retrieval setup, differing primarily in prompt design and answer style.

### 3.3 Judging and metrics

Answer quality is estimated using an LLM-as-a-judge pipeline implemented in `src/judge_answers.py`. For each answer record, the judge:

- loads the gold passage from `data/chunks/chunks.jsonl` via `gold_chunk_id`,
- considers the question, gold passage, and answer,
- applies a rubric that checks:
  - semantic equivalence against the gold passage,
  - coverage of core ideas and required named resources,
  - absence of major unsupported claims or contradictions,
- returns a structured judgement with:
  - `judge_score` (e.g. `"good"` or `"bad"`),
  - `judge_reasoning` (step-by-step justification),
  - `judge_gold_chunk_text` and `judge_gold_heading_path`,
  - `judge_model_id` and `judge_usage`.

Judged records are written to:

- `data/answers/answers_vector_v1_judged.jsonl`
- `data/answers/answers_vector_v2_prompt_grounded_judged.jsonl`

For high-level comparison, a small aggregation script (or an ad hoc analysis notebook) computes:

- overall proportion of `good` answers per variant,
- optionally: `good` rate by `target_size`, `target_role`, or `source_id`.

### 3.4 Findings

On the current 27-question synthetic benchmark:

- **Answer-generation v1**:
  - Achieves 22/27 `good` answers (approx. 81.5%).
  - Failure modes include:
    - omitting named ACSC resources when explicitly asked for,
    - collapsing multi-step guidance into vague summaries,
    - occasionally under-specifying controls compared with the gold passage.

- **Answer-generation v2 (prompt grounded)**:
  - Achieves 26/27 `good` answers (approx. 96.3%).
  - Improvements over v1 include:
    - better retention of named resources and frameworks,
    - stronger handling of multi-part questions,
    - more explicit, stepwise guidance aligned with ACSC wording and structure.

The benchmark is still small and relies on an LLM judge rather than human labels, so the numbers should be treated as **project-level evidence** rather than production-grade evaluation. Nevertheless, the difference between v1 and v2 is large enough, and qualitatively clear enough, to justify the current default choice.

### 3.5 Current default

Based on these results:

- `src/generate_answers.py` (v2 prompt-grounded) is the **default answer-generation script**.
- `data/answers/answers_vector_v2_prompt_grounded.jsonl` and  
  `data/answers/answers_vector_v2_prompt_grounded_judged.jsonl` are the **primary** answer and judged-answer artefacts.
- `src/generate_answers_v1.py` and the v1 JSONL files are retained for provenance and comparison, but not used as the default.

---

## 4. UI and monitoring in relation to evaluation

The Streamlit application (`app.py`) is wired to the evaluated defaults:

- **Retrieval**:
  - the AI Navigator uses vector retrieval as its default backend,
  - audience filters in the UI map to the same `size_audience_tag` and `role_audience_tags` fields used in evaluation,
  - `top_k` defaults to 5 but can be adjusted for exploration.

- **Answer generation**:
  - the UI uses the v2 prompt-grounded pipeline, i.e. the same style used in `answers_vector_v2_prompt_grounded.jsonl`,
  - retrieved chunks and their metadata are displayed in an evidence panel, mirroring the fields used in judged evaluation.

- **Monitoring**:
  - the `conversations` and `feedback` tables store interaction-level telemetry (question, audience filters, model, tokens, latency, cost, feedback),
  - these tables are used to build the Monitoring Dashboard charts,
  - they **do not** alter the benchmark datasets or corpus; they simply record usage over the evaluated path.

In other words, the interactive app is an evaluated path, not a separate, ad hoc configuration: it uses the same vector + v2 setup that performed best on the synthetic benchmark.

---

## 5. How to rerun evaluations

To replicate the current evaluation results from a clean clone:

1. **Corpus and chunks**  
   - Restore the reviewed Markdown snapshot (or rebuild and re-review intentionally).  
   - Run `uv run python src/prepare_chunks.py` to regenerate `data/chunks/chunks.jsonl`.

2. **Database and embeddings**  
   - Run `uv run python src/db_init.py`.  
   - Run `uv run python src/db_load_chunks.py`.  
   - Run `uv run python src/db_build_embeddings.py`.

3. **Retrieval evaluation**  
   - Ensure `data/ground_truth_synthetic.jsonl` is present (from the committed benchmark or regenerated as a new version).  
   - Run `uv run python src/evaluate_retrieval.py`.  
   - Optionally add `--debug-output data/eval/retrieval_debug.jsonl` to capture per-question debug records.

4. **Answer-generation evaluation**  
   - Run `uv run python src/generate_answers.py` to regenerate v2 answers if needed.  
   - Run `uv run python src/judge_answers.py` to re-judge v1 and v2 answers (or just v2).  
   - Use a small analysis script or notebook to compute `good` rates per variant.

The rest of the project (self-assessment, runbook, dataset notes, UI) should be read as describing this evaluated setup and its current default choices, rather than separate or conflicting configurations.