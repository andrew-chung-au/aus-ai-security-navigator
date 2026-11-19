# Project status

Written 2026-11-19 after a documentation review. It records what exists, what was and was not verified, known issues, and where to pick up. Update it when any of these change.

## Current state

| Area | State |
|---|---|
| Corpus | 10 core ACSC documents, reviewed Markdown frozen in `data/corpus_snapshots/v1_2026-07-25/` (checksums pass; identical to `data/processed/`). 5 boundary documents not indexed. |
| Chunks | 350 chunks, `chunking_version` `v1`, in `data/chunks/chunks.jsonl`. |
| Retrieval | Text, vector, vector+rerank (default), hybrid, plus rewrite variants (not default). |
| Answering | `src/generate_answers.py` (v2 grounded prompt) on reranked retrieval. Used by `app.py`. |
| App | Streamlit, two tabs, logging to PostgreSQL. |
| Runtime | Docker Compose: `postgres`, `bootstrap`, `app`. |
| Tests | None. |
| CI | None. |
| Hosted demo | None maintained. A previous EC2 instance (HTTP, port 8501) was a demo; assume offline. |

## Resuming work

1. `cp .env.example .env`, set `LLM_API_KEY`, review `LLM_BASE_URL` and `MODEL_ID`.
2. `docker compose up -d postgres && docker compose run --rm bootstrap`.
3. `uv sync`, then `uv run python -m streamlit run app.py` (uses `DATABASE_URL` on `localhost:5432`) or `docker compose up -d app`.
4. Smoke check: `uv run python src/retrieve_reranked.py "your question" --limit 3`.
5. Read [`runbook.md`](runbook.md) for the offline pipeline and [`evaluation-notes.md`](evaluation-notes.md) before changing retrieval or prompts. Compare any change against the numbers in the README.

Git history shows all work happened on `main` and `feature/reranked-answer-eval` (merged) between 2026-07-21 and 2026-08-04.

## Verification log (documentation review, 2026-11-19)

Checked by reading code and data in the repository:

- Retrieval metrics in the README and evaluation notes were recomputed from `data/eval/retrieval_debug.jsonl` and match.
- Judge counts (22/27, 26/27, 26/27) were recounted from the three judged JSONL files.
- Chunk count (350), question count (27), seed count (27), size/role distribution, and snapshot checksums were checked.
- Table definitions, default models, defaults (`top_k` 5, rerank pool 20, RRF `k` 60, fusion pool 10) were read from source.
- File names in the docs were checked against the repository.

**Not run** (no database, API key or Docker in the review environment):

- Docker Compose build and bootstrap, the Streamlit app, any `uv run` script, and the retrieval evaluation. Commands in the docs were checked against the code and Compose file, not executed.
- Corpus download from cyber.gov.au (ACSC pages may have changed since July 2026).
- The EC2 demo URL (`54.167.24.156:8501` returned HTTP 403 from the review sandbox; this does not show whether the instance is up).
- Whether `gemini-3.1-flash-lite` and the configured endpoint accept the `chat.completions.parse` structured-output call. `src/test_structured_output.py` checks this when run with a key.

## Known issues and findings

Findings 2 and 7 were fixed afterwards in `src/db_load_chunks.py` and `src/rewrite_query.py`; the rest are open.

| # | Finding | Evidence | Suggested action |
|---|---|---|---|
| 1 | Benchmark pipeline cannot be fully re-run from the repository. The seed-vetting step has no script, and `data/ground_truth_seeds_vetted.jsonl` is not committed. | `grep -rn seeds_vetted src` finds nothing. `generate_ground_truth_questions.py` reads `data/seed_chunk_candidates.json` (`INPUT_PATH`) and has no `include_for_eval` filter. The project log says all 27 seeds passed vetting, so the output is unaffected. | Commit a vetting script (or document that vetting was a one-off and skipped), and have the generator read the vetted file. |
| 2 | **Fixed 2026-11-19 (untested against a live database).** Stale embeddings after chunk changes: the upsert left `chunk_embedding` untouched and the embedding script only fills NULL rows. | `db_load_chunks.py` upsert now nulls `chunk_embedding` when title, heading path or text differs. | Still open: a change of embedding model or of `build_embedding_text` is not detected. Run `UPDATE chunks SET chunk_embedding = NULL;` first, or add a `--rebuild` flag. Existing databases loaded before the fix may hold stale vectors. |
| 3 | Three judge prompt versions, and judged files do not record which was used. | `judge_answers_v1.py`, `judge_answers_v2.py`, `judge_answers.py` have different rubric text. v2 also adds a retrieved-chunk summary to the prompt. Judged records have the same fields in all three files. D-011 says the v1/v2 comparison used a consistent judge setup. | Store a judge version in each record. Re-judge all three answer sets with the current judge for a like-for-like table. |
| 4 | Reranking improved retrieval metrics but not the judged answer score (26/27 for both). | Judged files. Failing question differs: `agentic-ai-adoption::043::q01` (vector), `ai-introduction::010::q01` (rerank). | Larger question set before claiming an answer-quality gain from reranking. |
| 5 | Selection and evaluation share one 27-question set; generator, question writer and judge are all `gemini-3.1-flash-lite`. | `model_id` and `judge_model_id` in the answer files; `.env.example`. | Add a held-out set, human-written questions, and a different judge model. |
| 6 | Hybrid MRR (0.373) is far below its Hit@5 (0.778), unlike vector (0.750 / 0.852). Not investigated. | Recomputed from the debug file. | Inspect `hybrid` rows in `data/eval/retrieval_debug.jsonl` for ranking or tie-breaking effects before treating hybrid as inherently weaker. |
| 7 | **Fixed 2026-11-19 (not run).** `rewrite_query.py` used to swallow LLM errors and return the original query, so a bad key gave rewrite results identical to the plain ones. It now raises. `evaluate_retrieval.py` still always runs the rewrite variants. | `rewrite_query.py` (try/except removed). | Check that the committed rewrite results were produced with a working key. Optionally add a flag to skip rewrite variants. |
| 8 | `.env.example` `LLM_BASE_URL` may be outdated for Gemini. The current Gemini OpenAI-compatibility documentation lists `https://generativelanguage.googleapis.com/v1beta/openai/`; the example value ends at `/v1beta/`, the form used in the original 2024 announcement. Not tested. | [Gemini API docs](https://ai.google.dev/gemini-api/docs/openai). The EC2 demo worked, so the deployed `.env` was presumably correct. | Test with a key; update `.env.example` if the `/openai/` form is required. |
| 9 | Dashboard and cost depend on `src/pricing.py`. Only `gemini-3.1-flash-lite` is listed, with prices "last checked 2026-07-26". Other models log $0.00. | `pricing.py`. | Re-check prices; add entries per model. |
| 10 | Docker image copies the whole build context and `.dockerignore` excludes `docs/`, `*.md`, `data/processed/`, `data/answers/`, `data/ground_truth_*`, `data/seed_*`. Evaluation scripts cannot run inside the app image. | `.dockerignore`. Compose comments and D-013 say the offline pipeline stays outside Docker. | Documented intent; revisit if evaluation should run in a container. `uv:latest` in the Dockerfile is unpinned. |
| 11 | Security posture is demo-grade: fixed DB credentials in `docker-compose.yml`, port 5432 published, no app authentication, user questions and answers stored in plain text. | `docker-compose.yml`, `app.py` `save_conversation`. | Before any public deployment: private DB network, secrets via environment, authentication, retention policy. |
| 12 | No vector index on `chunk_embedding`; searches are exact scans. | `db_init.py` creates GIN indexes for FTS and role tags only. | Not needed at 350 chunks. Add HNSW if the corpus grows. |
| 13 | Two debug-output files exist: `data/eval/retrieval_debug.jsonl` (8 backends, 216 rows, current) and `data/eval_retrieval_debug.jsonl` (3 backends, 81 rows, older). | File contents. | Delete the older file if no longer wanted. |
| 14 | `answers_vector_v2_judged.jsonl` is the file name in the repo, but `judge_answers_v2.py` defaults to writing `answers_vector_v2_prompt_grounded_judged.jsonl`. The file was renamed after generation. | `git log --follow`, script defaults. | Docs now use the real name. Update the script default if it is ever rerun. |
| 15 | Snapshot README referred to `v1_2026-07-25a`; the directory is `v1_2026-07-25`. | Directory listing. | Corrected in the snapshot README. |

## Backlog

See "Roadmap ideas" in the [README](../README.md#roadmap-ideas). Highest value first:

1. Tests and CI for the pure-logic parts (chunk-ID validation, cost estimate, filter SQL, chunking edge cases).
2. Finding 1 (and the remaining part of 2), which affect reproducibility.
3. A larger, partly human-written evaluation set and a re-judge under one rubric (findings 3 to 5).
4. Deployment hardening (finding 11) if the app is ever hosted again.
