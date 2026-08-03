# Self-assessment

This document tracks the current state of the project against a set of evaluation criteria inspired by common RAG best practices. The goal is to support honest self-reflection, monitor project progression over time, and identify concrete areas for improvement, not to optimise for any particular course score.

`README.md` is the main project overview, `docs/runbook.md` is the main execution and setup guide, and `docs/evaluation-notes.md` is the main evaluation reference. This file is for reflection, progress tracking, and guiding documentation and implementation work.

---

## Problem description

- **Poor**: The problem is not described.
- **OK**: The problem is described but briefly or unclearly.
- **Good**: The problem is well-described and it's clear what problem the project solves.

---

## Retrieval flow

- **Poor**: No knowledge base or LLM is used.
- **OK**: No knowledge base is used, and the LLM is queried directly.
- **Good**: Both a knowledge base and an LLM are used in the flow.

---

## Retrieval evaluation

- **Poor**: No evaluation of retrieval is provided.
- **OK**: Only one retrieval approach is evaluated.
- **Good**: Multiple retrieval approaches are evaluated, and the best one is used.

---

## LLM evaluation

- **Poor**: No evaluation of final LLM output is provided.
- **OK**: At least one answer-generation or final-output evaluation approach is implemented.
- **Good**: Multiple answer-generation or final-output approaches are evaluated, and the best one is used.

---

## Interface

- **Poor**: No way to interact with the application at all.
- **OK**: Command line interface, a script, or a Jupyter notebook.
- **Good**: UI (e.g., Streamlit), web application (e.g., Django), or an API (e.g., built with FastAPI).

---

## Ingestion pipeline

- **Poor**: No ingestion.
- **OK**: Semi-automated ingestion of the dataset into the knowledge base, e.g., with a Jupyter notebook or a Python script.
- **Good**: Automated ingestion with a special tool (e.g., Kestra, dlt, Airflow, Prefect).

---

## Monitoring

- **Poor**: No monitoring.
- **OK**: User feedback is collected OR there's a monitoring dashboard.
- **Good**: User feedback is collected and there's a dashboard with at least 5 charts.

---

## Containerization

- **Poor**: No containerization.
- **OK**: Dockerfile is provided for the main application OR there's a docker-compose for the dependencies only.
- **Good**: Everything is in docker-compose.

---

## Reproducibility

- **Poor**: No instructions on how to run the code, the data is missing, or it's unclear how to access it.
- **OK**: Some instructions are provided but are incomplete, OR instructions are clear and complete, the code works, but the data is missing.
- **Good**: Instructions are clear, the dataset is accessible, it's easy to run the code, and the versions for all dependencies are specified.

---

## Bonus implementation categories

- Hybrid search: combining both text and vector search, at least evaluated.
- Document reranking.
- User query rewriting.
- Deployment to the cloud.

---

## Current status summary

This table is a snapshot as of 2026-08-04 and is intended to be updated as the project evolves.

| Area | State | Notes |
|---|---|---|
| Problem description | Good | Clear problem, scope, and users are documented. |
| Retrieval flow | Good | Knowledge base and retrieval backends are implemented; grounded answer-generation and judge artefacts are also present. |
| Retrieval evaluation | Good | Text, vector, reranked vector, and hybrid retrieval are evaluated on the same benchmark; reranked vector is the current default based on evidence. |
| LLM evaluation | Good | Two answer-generation variants were compared on the same synthetic benchmark using a consistent judge setup; v2 was selected as the stronger approach. |
| Interface | Good | Streamlit UI with an AI Navigator tab and a Monitoring Dashboard on top of the CLI scripts. |
| Ingestion pipeline | OK | Semi-automated ingestion with scripts plus manual cleanup; no orchestration tool yet. |
| Monitoring | Good | User feedback is logged and a monitoring dashboard with multiple charts is available in the Streamlit app. |
| Containerization | Good | Dockerfile, multi-service `docker-compose.yml`, containerised Postgres/pgvector backend, bootstrap service, and app service are now in place. |
| Reproducibility | Good | Clear instructions, accessible dataset, pinned dependencies, committed Docker config, and a committed Streamlit config. |
| Hybrid search | Good | Implemented and evaluated via reciprocal rank fusion; improves over text but not over reranked vector on the current benchmark. |
| Document reranking | Good | Implemented via `src/retrieve_reranked.py` and now the preferred retrieval baseline. |
| Query rewriting | OK | Implemented and evaluated, but not adopted as the default because it did not improve the frozen benchmark. |
| Cloud deployment | Good | Lightweight EC2 deployment for reviewer access using the same Docker Compose runtime path. |

---

## Problem description — (Good)

The project clearly explains that it aims to help Australian organisations navigate official ACSC guidance on AI security, which is spread across multiple documents and formats. The README describes the user problem, why generic AI advice is insufficient, and how a grounded RAG tool over ACSC sources addresses that gap. This matches the Good definition for this criterion. Evidence lives mainly in `README.md`, `docs/dataset-notes.md`, and `docs/decisions.md`.

## Retrieval flow — (Good)

The project uses both a knowledge base and LLM-supported workflow components. ACSC documents are downloaded, cleaned, chunked, stored as `data/chunks/chunks.jsonl`, and loaded into a PostgreSQL `chunks` table. Retrieval scripts implement full-text search, pgvector-based dense retrieval, a reranked vector retriever, and a hybrid fusion retriever, while the LLM helper supports seed vetting, synthetic question generation, answer generation, and answer judging.

This matches the Good definition for this criterion because both a knowledge base and LLM-supported components are part of the overall system rather than direct prompting alone. Evidence is in `src/db_init.py`, `src/db_load_chunks.py`, `src/db_build_embeddings.py`, `src/retrieve_text.py`, `src/retrieve_vector.py`, `src/retrieve_reranked.py`, `src/retrieve_hybrid.py`, `src/generate_answers.py`, `src/judge_answers.py`, `src/llm_client.py`, and the corpus files.

## Retrieval evaluation — (Good)

Retrieval quality is evaluated explicitly, and multiple retrieval approaches are compared on the same synthetic benchmark. The project builds a synthetic ground-truth set and uses `src/evaluate_retrieval.py` to compare text retrieval, vector retrieval, reranked vector retrieval, and hybrid retrieval, reporting metrics such as Hit@k and MRR, both strict and relaxed.

Current results show that reranked vector retrieval substantially outperforms the text baseline and the plain vector baseline on the current benchmark, while simple hybrid retrieval improves over text but does not beat reranked vector. This matches the Good definition for this criterion: multiple retrieval approaches are evaluated and the best one is used. Evidence is in `src/evaluate_retrieval.py`, `src/retrieve_text.py`, `src/retrieve_vector.py`, `src/retrieve_reranked.py`, `src/retrieve_hybrid.py`, `data/ground_truth_synthetic.jsonl`, `docs/evaluation-notes.md`, and the recorded metrics.

## LLM evaluation — (Good)

The project includes a comparative evaluation of multiple final-answer generation approaches. Two grounded answer-generation variants were produced over the same synthetic ACSC question set: `data/answers/answers_vector_v1.jsonl` and `data/answers/answers_vector_v2_prompt_grounded.jsonl`. Both were then evaluated against gold ACSC passages using the same judging setup, producing comparable judged outputs in `data/answers/answers_vector_v1_judged.jsonl` and `data/answers/answers_vector_v2_prompt_grounded_judged.jsonl`.

On the current 27-question benchmark, answer-generation v2 outperformed v1, achieving 26/27 `good` answers (96.3%) versus 22/27 `good` answers (81.5%) for v1. The main observed advantage of v2 was better retention of named resources, frameworks, and actionable multi-step guidance, whereas v1 more often over-summarised and replaced concrete ACSC guidance with generic wording.

This matches the Good definition for this criterion: multiple final-output approaches were evaluated and the better one was selected. Evidence is in `src/generate_answers.py`, `src/generate_answers_v1.py`, `src/judge_answers.py`, `src/judge_answers_v1.py`, `src/judge_answers_v2.py`, `data/answers/answers_vector_v1.jsonl`, `data/answers/answers_vector_v1_judged.jsonl`, `data/answers/answers_vector_v2_prompt_grounded.jsonl`, `data/answers/answers_vector_v2_prompt_grounded_judged.jsonl`, and `docs/evaluation-notes.md`.

## Interface — (Good)

The project now includes both CLI-based workflows and a user-facing UI. Scripts under `src/` support download, extraction, chunking, evaluation, and answer generation and judging. On top of this, `app.py` exposes a Streamlit web application with:

- an **AI Navigator** tab for interactive questions, audience filters, reranked vector retrieval, and v2 prompt-grounded answers, and
- a **Monitoring Dashboard** tab for metrics, charts, and recent conversations.

This matches the Good definition for this criterion: there is a UI (Streamlit) in addition to scripts. Evidence is in `app.py`, `.streamlit/config.toml`, `README.md`, and `docs/runbook.md`.

## Ingestion pipeline — (OK)

The ingestion pipeline is semi-automated and clearly documented. A manifest defines sources; scripts handle downloading and extraction for HTML and PDFs; manual cleanup improves the processed Markdown; chunk preparation, database loading, and embedding generation are scripted.

This matches the OK definition for this criterion: ingestion is substantially implemented and reusable, but it is still script-based rather than orchestrated through a dedicated workflow tool. Evidence is in `src/download_sources.py`, `src/extract_text_html.py`, `src/extract_text_pdf.py`, `src/prepare_chunks.py`, `docs/runbook.md`, and `docs/dataset-notes.md`.

## Monitoring — (Good)

Monitoring is present in the form of feedback collection and a dashboard with multiple charts:

- The Streamlit app logs each interaction into a `conversations` table, including question, answer, model, audience filters, tokens, latency, estimated cost, and timestamp.
- A `feedback` table records thumbs-up / thumbs-down scores per conversation.
- The Monitoring Dashboard tab shows:
  - summary metrics (total conversations, average latency, total estimated cost, feedback counts),
  - charts (response time per query, cost per query, token usage per request, conversations per hour, queries by organisation size, queries by role),
  - a recent-conversations table.

This matches the Good definition for this criterion: user feedback is collected and there is a dashboard with at least five charts. Evidence is in `app.py`, the `conversations` and `feedback` tables, `README.md`, and `docs/runbook.md`.

## Containerization — (Good)

The project is now containerised with both an application image and a multi-service Docker Compose setup. A `Dockerfile` builds the Streamlit app image, and `docker-compose.yml` defines the full local stack with:

- a `postgres` service using `pgvector/pgvector:pg17`,
- a `bootstrap` service that initialises the schema, loads chunk records, and builds embeddings,
- an `app` service that runs the Streamlit interface against the containerised database.

The Compose setup also includes health checks, named volumes for PostgreSQL data and Hugging Face model caching, and supporting `.dockerignore` and `.gitignore` updates. This matches the Good definition for this criterion: everything needed for the containerised runtime is in Docker Compose rather than only the main app or only the dependencies. Evidence is in `Dockerfile`, `docker-compose.yml`, `.dockerignore`, `.gitignore`, `README.md`, and `docs/runbook.md`.

## Reproducibility — (Good)

Reproducibility is strong. The project has clear instructions on how to run the code, a manifest-defined public dataset, pinned dependency versions, a documented local `uv` workflow, and a documented Docker Compose workflow that covers the application and database runtime. The runbook also documents downloading, extraction, cleanup, chunking, indexing, evaluation, answer generation and judging, and the Streamlit UI.

Someone else should be able to rebuild the corpus and rerun the retrieval evaluation from a clean checkout, then launch the Streamlit UI either locally or via Docker Compose. This matches the Good definition for this criterion: instructions are clear, the dataset is accessible, it's easy to run the code, and version information is specified.

Evidence is in `docs/runbook.md`, `README.md`, `pyproject.toml`, `uv.lock`, `Dockerfile`, `docker-compose.yml`, `data/source_manifest_core.csv`, and `.streamlit/config.toml`.

---

## Bonus categories and extras

These categories are not part of any formal score here, but they are useful indicators of project maturity and future learning opportunities.

### Hybrid search

Hybrid search is implemented and evaluated. The project includes a simple reciprocal-rank-fusion (RRF) hybrid retriever that combines text and vector results without directly normalising their different score scales.

On the current synthetic benchmark, hybrid retrieval improves substantially over text-only retrieval but does not outperform reranked vector retrieval, so it is retained as an evaluated alternative and debugging aid rather than the default retriever. Evidence is in `src/retrieve_hybrid.py`, `src/evaluate_retrieval.py`, and `docs/evaluation-notes.md`.

### Document re-ranking

Document or chunk reranking is now present. The current system includes `src/retrieve_reranked.py`, and the reranked vector path is the preferred retrieval baseline because it outperforms the plain vector and hybrid alternatives on the current benchmark.

### User query rewriting

Query rewriting is implemented and evaluated, but it is not the default because it did not improve the frozen benchmark. The rewrite helper (`src/rewrite_query.py`) was tested across all four main backends (`text`, `vector`, `vector_reranked`, `hybrid`) on the 27-question synthetic set. Rewritten variants were generally weaker or only marginally different, and the strongest backend remained `vector_reranked` without rewrite. The helper is retained as an experimental tool for possible future selective or gated strategies. Evidence is in `src/rewrite_query.py`, `src/evaluate_retrieval.py`, `docs/evaluation-notes.md`, `docs/decisions.md` (D-015), and `docs/project-log.md`.

### Deployment to the cloud

The project now includes a lightweight cloud deployment for reviewer access. A small Ubuntu-based AWS EC2 instance runs the same Docker Compose stack used locally:

- `postgres` service with pgvector
- `bootstrap` service for one-off schema init, chunk load, and embedding build
- `app` service running the Streamlit UI on port 8501

The deployment reuses the evaluated reranked-vector + v2 prompt-grounded pipeline and is intended as a demonstration environment rather than a hardened production setup. It does not yet include HTTPS, a custom domain, or managed secrets. Evidence is in `Dockerfile`, `docker-compose.yml`, `docs/runbook.md`, `docs/decisions.md` (D-016), and `docs/project-log.md`.

### Other extras

Additional notable features now include a containerised local runtime with a dedicated bootstrap service, a committed Streamlit runtime configuration, and lightweight monitoring over the interactive path.

---

## Strongest areas and gaps

**Strongest areas right now:**

- Problem description (Good)
- Retrieval flow (Good)
- Retrieval evaluation (Good)
- LLM evaluation (Good)
- Interface (Good)
- Monitoring (Good)
- Containerization (Good)
- Reproducibility (Good)
- Cloud deployment (Good)

**Clear gaps and next areas to improve:**

- Ingestion pipeline orchestration is still OK rather than Good
- Query rewriting is implemented but intentionally not adopted as default
- Docker usage and reset paths should remain clearly documented so a reviewer can follow them without guesswork

---

## Next steps

These priorities are chosen to improve project quality, maintainability, and learning value.

- **Ingestion pipeline maturity**: Consider a lightweight orchestrator or single entry script that sequences the main ingestion and evaluation steps for easier reuse.
- **Targeted retrieval enhancements**: Explore small, evaluation-friendly changes such as gated query rewriting or additional reranking experiments, evaluated against the existing synthetic benchmark.
- **Optional deployment hardening**: If time permits, explore minimal hardening of the EC2 deployment (HTTPS, custom domain, managed secrets) as a bonus, without overcomplicating the core project.
- **Container refinement**: Keep Docker usage clearly documented in `README.md` and `docs/runbook.md`, including first-time bootstrap, normal restart, and full reset paths.

This document is intended to evolve as those areas are implemented; the criterion definitions stay fixed, but the current states and notes for each area can be updated over time.