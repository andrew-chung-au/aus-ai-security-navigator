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
  - `src/resolve_seed_draft_ids.py` matches seeds to concrete chunks in `data/chunks/chunks.jsonl`, producing `data/seed_chunk_candidates.json` with candidate chunks, scores, and debug information.
  - An LLM-based vetting step consumes these candidates and writes `data/ground_truth_seeds_vetted.jsonl`, marking which seeds to include for evaluation and assigning a seed-quality label.

- **Synthetic question generation**:
  - `src/generate_ground_truth_questions.py` generates one user-like question per vetted seed, using an A → Q* pattern.
  - The output (`data/ground_truth_synthetic.jsonl`) records, for each question:
    - `question_id`, `question`
    - `source_id`, `chunk_id`
    - `size_audience_tag`, `role_audience_tags`
    - `target_size`, `target_role`

This benchmark is small (currently 27 questions) and intentionally seed-anchored. It is primarily a tool for comparative evaluation and debugging, not a full coverage measure of ACSC guidance.

### 2.2 Retrieval methods

Five retrieval methods are evaluated over the same benchmark, including rewritten variants for comparison:

- **Text (lexical)** — `src/retrieve_text.py`:
  - uses PostgreSQL full-text search (`fts` over `search_text`),
  - ranks chunks using `ts_rank(fts, websearch_to_tsquery('english', query), 1)`,
  - filters on `score > 0` to avoid empty result sets for long questions,
  - supports optional filters on:
    - `size_audience_tag` (with `all_sizes` as a fallback),
    - `role_audience_tags` (JSONB array containment).

- **Vector (dense)** — `src/retrieve_vector.py`:
  - uses a MiniLM sentence-transformers model (`sentence-transformers/all-MiniLM-L6-v2`) to embed `chunk_text` and queries,
  - stores embeddings in a pgvector `chunk_embedding` column,
  - performs nearest-neighbour search using cosine distance (`chunk_embedding <=> query_embedding`),
  - supports the same audience filters as the text retriever,
  - returns per-chunk `cosine_distance` and a convenience `similarity` score.

- **Vector reranked** — `src/retrieve_reranked.py`:
  - first retrieves a small candidate pool with vector search,
  - then reranks those candidates with a cross-encoder (`cross-encoder/ms-marco-MiniLM-L-6-v2`),
  - preserves vector debug fields (`vector_rank`, `vector_similarity`, `vector_cosine_distance`),
  - adds `reranker_score` for final ordering.

- **Hybrid (RRF)** — `src/retrieve_hybrid.py`:
  - calls both the text and vector retrievers with the same query and audience filters,
  - collects a small candidate set from each (e.g. top-10 text and top-10 vector),
  - fuses results per `chunk_id` using reciprocal rank fusion (RRF) to produce a `hybrid_score`,
  - preserves backend-specific debug fields (`text_rank`, `vector_rank`, `text_score`, `vector_similarity`).

- **Query rewriting variants** — `src/rewrite_query.py` plus evaluator wrappers:
  - the same four retrievers are also tested with a rewritten query,
  - the rewrite is a single LLM-generated retrieval query,
  - rewritten runs are tracked separately as `text_rewritten`, `vector_rewritten`, `vector_reranked_rewritten`, and `hybrid_rewritten`.

All methods operate over the same chunk corpus (`data/chunks/chunks.jsonl`) and audience metadata.

### 2.3 Metrics

Retrieval evaluation is implemented in `src/evaluate_retrieval.py`. For each backend, it computes:

- **Strict metrics**:
  - Hit@k: whether the exact gold `chunk_id` appears in the top-k results.
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
- backend-specific scores and ranks,
- original and rewritten retrieval queries where applicable.

### 2.4 Findings

On the current 27-question synthetic benchmark:

- **Text retrieval**:
  - After loosening the full-text condition to "rank then filter on `score > 0`", strict Hit@k and MRR are non-zero (strict Hit@5: ~0.259, strict MRR: ~0.099, relaxed Hit@10: ~0.259, relaxed MRR: ~0.099).
  - However, text retrieval still struggles with long, conversational questions and nuanced AI-security phrasing.
  - Rewriting does not improve text retrieval on this benchmark and reduces both strict and relaxed scores.

- **Vector retrieval**:
  - Strict Hit@k and MRR are substantially higher than for text (strict Hit@5: ~0.852, strict MRR: 0.750, relaxed Hit@10: ~0.926, relaxed MRR: ~0.761).
  - Vector retrieval is particularly stronger on:
    - paraphrased security questions,
    - questions about risk/mitigation combinations,
    - questions using more natural, less keyword-driven language.
  - Rewriting is slightly mixed here: strict metrics fall a little, while relaxed MRR improves slightly, but the overall win is not strong enough to make rewrite the default.

- **Vector reranked retrieval**:
  - Vector reranking is the current best-performing retrieval strategy on this benchmark (strict Hit@5: ~0.926, strict MRR: ~0.889, relaxed Hit@10: ~0.963, relaxed MRR: ~0.894).
  - It improves both strict and relaxed metrics over vector-only retrieval.
  - The reranker is especially helpful when vector search finds the right topic but does not place the most exact passage at rank 1.
  - Rewriting makes this method worse on strict MRR and worse on relaxed metrics, so the rewritten variant is not preferred.

- **Hybrid retrieval**:
  - Hybrid (RRF) improves clearly over text-only (strict Hit@5: ~0.778, strict MRR: ~0.373, relaxed Hit@10: ~0.889, relaxed MRR: ~0.389).
  - On this benchmark, hybrid does **not** outperform vector-only or vector-reranked retrieval.
  - In some cases it pulls in useful lexical hits; in others it slightly dilutes strong vector rankings.
  - Rewriting also hurts hybrid performance on this benchmark.

- **Query rewriting overall**:
  - The rewritten variants are consistently weaker than the non-rewritten best backend.
  - The strongest observed backend remains `vector_reranked` without rewrite.
  - This suggests the benchmark corpus is already well matched by semantic retrieval, and prompt-only rewriting introduces enough drift to reduce lexical alignment and precision.

- **Query rewriting experiment (overall conclusion)**:
  - A dedicated LLM-based query rewrite helper (`src/rewrite_query.py`) was added and evaluated across all four main backends (`text`, `vector`, `vector_reranked`, `hybrid`).
  - On the frozen 27-question synthetic benchmark, rewriting did not improve the best-performing backend and generally reduced strict metrics or produced only marginal differences.
  - The strongest overall backend remains `vector_reranked` without rewrite.
  - As a result, query rewriting is treated as an experimental tool, not part of the default retrieval path. It is retained for future selective or gated strategies (e.g. only for clearly vague or underspecified queries).

Given this evidence, the project treats **vector-reranked retrieval without query rewriting** as the current default backend for both evaluation and the interactive application. Text, vector, hybrid, and rewritten variants remain available as evaluated baselines and debugging tools.

---

## 3. Answer-generation evaluation

> **Note on Retrieval Baseline for Answer Generation:** 
> The prompt A/B test (v1 vs. v2) was conducted and frozen using the plain `vector` retrieval baseline to ensure a strictly controlled comparison. The project has since adopted `vector_reranked` as the superior default retrieval backend for the live Streamlit UI and for new answer-generation runs. The static evaluation artifacts (`answers_vector_v1...` and `answers_vector_v2_prompt_grounded...`) are intentionally preserved to document the prompt engineering experiment, while a new reranked-vector v2 answer set and judged output have been generated using the updated generate_answers.py and judge_answers.py scripts. All answer-generation experiments use non-rewritten retrieval, consistent with the decision not to adopt query rewriting as the default.



### 3.1 Setup

Answer-generation evaluation is built on top of the synthetic retrieval benchmark:

- questions come from `data/ground_truth_synthetic.jsonl`,
- gold passages are identified by `gold_source_id` and `gold_chunk_id`,
- retrieval uses the reranked vector backend with a default `top_k` (currently 5) and audience filters derived from `target_size` and `target_role`.

For each question, the evaluation pipeline:

1. retrieves top-k chunks via reranked vector retrieval,
2. assembles a structured context (chunks plus headings and audience metadata),
3. calls a prompt-grounded LLM to generate an answer,
4. stores the answer and provenance in JSONL.

The project currently preserves three answer datasets:

- `data/answers/answers_vector_v1.jsonl` — earlier answer-generation variant (plain vector, v1 prompt)
- `data/answers/answers_vector_v2_prompt_grounded.jsonl` — plain vector retrieval + v2 prompt (frozen baseline)
- `data/answers/answers_vector_reranked_v2_prompt_grounded.jsonl` — reranked vector retrieval + v2 prompt (current default)

The reranked-vector v2 file is the currently selected answer-generation artefact for the project’s default path. The earlier v1 and plain-vector v2 files are retained as frozen baselines for comparison.

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

- `data/answers/answers_vector_v1_judged.jsonl` — judged output for the v1 baseline
- `data/answers/answers_vector_v2_prompt_grounded_judged.jsonl` — judged output for the plain-vector v2 baseline (frozen)
- `data/answers/answers_vector_reranked_v2_prompt_grounded_judged.jsonl` — judged output for the reranked-vector v2 default (current)

The current default judged artefact is `answers_vector_reranked_v2_prompt_grounded_judged.jsonl`. The earlier judged files are preserved as frozen baselines tied to their respective answer-generation variants.

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

## 3.5 Current default

Based on these results and the updated retrieval backend:

- `src/generate_answers.py` (v2 prompt-grounded, using `retrieve_reranked.py`) is the **default answer-generation script**.
- `data/answers/answers_vector_reranked_v2_prompt_grounded.jsonl` and `data/answers/answers_vector_reranked_v2_prompt_grounded_judged.jsonl` are the **primary** answer and judged-answer artefacts for the current default path.
- `data/answers/answers_vector_v1.jsonl`, `data/answers/answers_vector_v1_judged.jsonl`, `data/answers/answers_vector_v2_prompt_grounded.jsonl`, and `data/answers/answers_vector_v2_prompt_grounded_judged.jsonl` are retained as frozen baselines for provenance and comparison, but are not used as the default.

---

## 4. UI and monitoring in relation to evaluation

The Streamlit application (`app.py`) is wired to the evaluated defaults:

- **Retrieval**:
  - the AI Navigator uses vector retrieval followed by cross-encoder reranking as its default backend,
  - audience filters in the UI map to the same `size_audience_tag` and `role_audience_tags` fields used in evaluation,
  - `top_k` defaults to 5 but can be adjusted for exploration.

- **Answer generation**:
  - the UI uses the v2 prompt-grounded pipeline, i.e. the same style used in `answers_vector_v2_prompt_grounded.jsonl`,
  - retrieved chunks and their metadata are displayed in an evidence panel, mirroring the fields used in judged evaluation.

- **Monitoring**:
  - the `conversations` and `feedback` tables store interaction-level telemetry (question, audience filters, model, tokens, latency, cost, feedback),
  - these tables are used to build the Monitoring Dashboard charts,
  - they do not alter the benchmark datasets or corpus; they simply record usage over the evaluated path.

In other words, the interactive app is an evaluated path, not a separate, ad hoc configuration: it uses the same reranked retrieval + v2 setup that performed best on the synthetic benchmark.

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
   - Optional: add `--debug-output data/eval/retrieval_debug.jsonl` to capture per-question debug records.

4. **Answer-generation evaluation**
   - Run `uv run python src/generate_answers.py` to regenerate v2 answers if needed.
   - Run `uv run python src/judge_answers.py` to re-judge v1 and v2 answers (or just v2).
   - Use a small analysis script or notebook to compute `good` rates per variant.

The rest of the project (self-assessment, runbook, dataset notes, UI) should be read as describing this evaluated setup and its current default choices, rather than separate or conflicting configurations.