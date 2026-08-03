# Self-assessment

This document maps the current project state to the peer-review evaluation criteria. It is intended to provide an honest, easy-to-check evidence trail for reviewers and to identify remaining improvement areas.

For the project overview, live deployment, and rubric evidence map, see the [README](../README.md).  
For complete local reproduction and deployment steps, see the [runbook](runbook.md).  
For retrieval and answer-generation results, see the [evaluation notes](evaluation-notes.md).

---

## Live application

The deployed reviewer-facing application is available at:

**[AUS AI Security Navigator — Streamlit app](http://54.167.24.156:8501/)**

The live app exposes the selected default RAG path:

- Reranked-vector retrieval
- V2 prompt-grounded answer generation
- Evidence inspection with retrieved ACSC source metadata
- Organisation-size and role filters
- Conversation logging, feedback collection, and a monitoring dashboard

---

## Reviewer quick check

A reviewer can verify the main implemented capabilities without rebuilding the project:

1. Open the [live Streamlit application](http://54.167.24.156:8501/).
2. Ask an ACSC AI security question in **AI Navigator**.
3. Optionally apply organisation-size and role filters.
4. Inspect the returned answer and displayed ACSC evidence.
5. Open the **Monitoring Dashboard** to verify telemetry, feedback collection, and charts.
6. Use the [README assessment evidence map](../README.md#assessment-evidence) to locate repository evidence for each criterion.

---

## Score summary

**Self-assessed core score: 17/18**

**Implemented bonus features:**

- Hybrid search evaluation
- Document reranking
- User query rewriting evaluation
- Cloud deployment

The one core point not claimed is for ingestion orchestration: the ingestion workflow is scripted and reproducible, but it does not use a dedicated orchestration tool such as Airflow, Prefect, dlt, Kestra, or similar.

| Criterion | Self-assessed score | Summary |
|---|---:|---|
| Problem description | 2/2 | Clear problem, users, scope, and retrieval rationale |
| Retrieval flow | 2/2 | ACSC knowledge base plus grounded LLM answer generation |
| Retrieval evaluation | 2/2 | Text, vector, reranked-vector, and hybrid retrieval evaluated; best backend selected |
| LLM evaluation | 2/2 | Multiple grounded answer-generation approaches evaluated; stronger variant selected |
| Interface | 2/2 | Streamlit UI deployed for reviewer access |
| Ingestion pipeline | 1/2 | Scripted semi-automated pipeline with manual review checkpoint |
| Monitoring | 2/2 | User feedback plus dashboard with at least five charts |
| Containerization | 2/2 | Database, bootstrap, and application services run through Docker Compose |
| Reproducibility | 2/2 | Accessible source data, pinned dependencies, runbook, corpus snapshot, and Docker runtime |
| Hybrid search | +1 | Implemented and evaluated |
| Document reranking | +1 | Implemented, evaluated, and selected as default retrieval |
| User query rewriting | +1 | Implemented and evaluated; retained as experimental |
| Cloud deployment | +2 | Live EC2 deployment for reviewer access |

---

## Criterion definitions

### Problem description

- **0 points:** The problem is not described.
- **1 point:** The problem is described but briefly or unclearly.
- **2 points:** The problem is well-described and it is clear what problem the project solves.

### Retrieval flow

- **0 points:** No knowledge base or LLM is used.
- **1 point:** No knowledge base is used, and the LLM is queried directly.
- **2 points:** Both a knowledge base and an LLM are used in the flow.

### Retrieval evaluation

- **0 points:** No evaluation of retrieval is provided.
- **1 point:** Only one retrieval approach is evaluated.
- **2 points:** Multiple retrieval approaches are evaluated, and the best one is used.

### LLM evaluation

- **0 points:** No evaluation of final LLM output is provided.
- **1 point:** Only one approach, such as one prompt, is evaluated.
- **2 points:** Multiple approaches are evaluated, and the best one is used.

### Interface

- **0 points:** No way to interact with the application at all.
- **1 point:** Command line interface, a script, or a Jupyter notebook.
- **2 points:** A UI, web application, or API is available.

### Ingestion pipeline

- **0 points:** No ingestion.
- **1 point:** Semi-automated ingestion of the dataset into the knowledge base, such as with scripts or a notebook.
- **2 points:** Automated ingestion with a dedicated orchestration tool, such as Kestra, dlt, Airflow, or Prefect.

### Monitoring

- **0 points:** No monitoring.
- **1 point:** User feedback is collected or a monitoring dashboard exists.
- **2 points:** User feedback is collected and a dashboard contains at least five charts.

### Containerization

- **0 points:** No containerization.
- **1 point:** A Dockerfile is provided for the main application, or Docker Compose is used only for dependencies.
- **2 points:** The complete runtime is defined in Docker Compose.

### Reproducibility

- **0 points:** No instructions are provided, data is missing, or access is unclear.
- **1 point:** Instructions are incomplete, or code works but data is missing.
- **2 points:** Instructions are clear, the dataset is accessible, the project is easy to run, and dependency versions are specified.

---

## Problem description — 2/2

The project addresses a clear problem: official ACSC guidance on AI security is distributed across multiple documents, formats, and audience-specific publications. This makes it difficult for Australian organisations to quickly find relevant, trustworthy guidance for questions about secure AI adoption, AI supply-chain risk, AI-enabled cyber attacks, and related controls.

The project provides a retrieval-augmented assistant over a curated ACSC corpus. Rather than relying on general LLM advice alone, it retrieves relevant ACSC evidence and generates answers grounded in that material.

**Evidence:**

- [README problem statement](../README.md#problem-statement)
- [README project scope](../README.md#project-scope)
- [Dataset notes](dataset-notes.md)
- [Architecture decisions](decisions.md)

---

## Retrieval flow — 2/2

The project uses both a knowledge base and an LLM-supported answer flow.

ACSC HTML and PDF guidance is downloaded, extracted, reviewed, chunked, and stored as retrieval-ready records. Chunks are loaded into PostgreSQL with pgvector embeddings and full-text search support. The selected UI path retrieves evidence using reranked-vector retrieval, then generates a v2 prompt-grounded answer from the retrieved ACSC chunks.

The LLM is also used in supporting evaluation stages, including seed vetting, synthetic-question generation, answer generation, and answer judging.

**Evidence:**

- `data/chunks/chunks.jsonl`
- `src/db_init.py`
- `src/db_load_chunks.py`
- `src/db_build_embeddings.py`
- `src/retrieve_reranked.py`
- `src/generate_answers.py`
- `src/judge_answers.py`
- `src/llm_client.py`
- `app.py`
- [Live application](http://54.167.24.156:8501/)

---

## Retrieval evaluation — 2/2

Retrieval quality is evaluated across multiple approaches using the same synthetic 27-question benchmark:

- Text retrieval
- Vector retrieval
- Reranked-vector retrieval
- Hybrid retrieval

The benchmark is built from curated ACSC seed passages that are matched to concrete chunks, vetted, and used to generate traceable synthetic questions. Retrieval evaluation reports metrics including strict and relaxed Hit@k and MRR.

Reranked-vector retrieval performed best on the current benchmark and is therefore used as the default downstream retrieval path in the UI and answer-generation workflow. Hybrid retrieval improved on text-only retrieval but did not outperform reranked-vector retrieval.

**Evidence:**

- `src/evaluate_retrieval.py`
- `src/retrieve_text.py`
- `src/retrieve_vector.py`
- `src/retrieve_reranked.py`
- `src/retrieve_hybrid.py`
- `data/ground_truth_synthetic.jsonl`
- [Evaluation notes](evaluation-notes.md)
- [README retrieval and evaluation](../README.md#retrieval-and-evaluation)

---

## LLM evaluation — 2/2

The project compares multiple grounded answer-generation approaches using the same synthetic ACSC question set and a consistent LLM-as-a-judge setup.

The evaluated answer artefacts include:

- `data/answers/answers_vector_v1.jsonl`
- `data/answers/answers_vector_v1_judged.jsonl`
- `data/answers/answers_vector_v2_prompt_grounded.jsonl`
- `data/answers/answers_vector_v2_prompt_grounded_judged.jsonl`
- `data/answers/answers_vector_reranked_v2_prompt_grounded.jsonl`
- `data/answers/answers_vector_reranked_v2_prompt_grounded_judged.jsonl`

The v2 prompt-grounded approach outperformed the earlier v1 answer-generation approach on the benchmark. The selected live path combines the stronger v2 grounded prompt with the strongest evaluated retriever, reranked-vector retrieval.

The evaluation is synthetic and should not be interpreted as a complete measure of real-world answer quality. However, it provides a controlled, traceable comparison that informed the selected implementation.

**Evidence:**

- `src/generate_answers.py`
- `src/generate_answers_v1.py`
- `src/judge_answers.py`
- `src/judge_answers_v1.py`
- `src/judge_answers_v2.py`
- `data/answers/`
- [Evaluation notes](evaluation-notes.md)
- [README retrieval and evaluation](../README.md#retrieval-and-evaluation)

---

## Interface — 2/2

The project provides both command-line workflows and a deployed Streamlit UI.

The Streamlit application in `app.py` provides:

- **AI Navigator** for asking ACSC AI security questions
- Optional organisation-size and role filters
- Reranked-vector retrieval
- V2 prompt-grounded answers
- A source-evidence panel containing chunk IDs, document titles, headings, audience tags, and retrieval metadata
- **Monitoring Dashboard** for interaction telemetry and feedback analysis

**Evidence:**

- `app.py`
- `.streamlit/config.toml`
- [Live Streamlit application](http://54.167.24.156:8501/)
- [README interactive UI and monitoring](../README.md#interactive-ui-and-monitoring)
- [Runbook reviewer verification path](runbook.md#reviewer-verification-path)

---

## Ingestion pipeline — 1/2

The ingestion pipeline is semi-automated and reproducible:

1. A manifest defines the ACSC source documents and associated audience metadata.
2. Scripts download HTML and PDF sources.
3. Scripts extract source text into Markdown.
4. Extracted Markdown is manually reviewed and cleaned.
5. A reviewed corpus snapshot is preserved under `data/corpus_snapshots/`.
6. Scripts create chunks, initialise PostgreSQL, load chunks, and build embeddings.

This is stronger than a manual one-off workflow because ingestion and index creation are largely scripted. However, it does not use a dedicated orchestrator, and a manual review checkpoint remains intentionally part of the process. It is therefore assessed as 1/2.

**Evidence:**

- `data/source_manifest_core.csv`
- `src/download_sources.py`
- `src/extract_text_html.py`
- `src/extract_text_pdf.py`
- `src/prepare_chunks.py`
- `src/db_init.py`
- `src/db_load_chunks.py`
- `src/db_build_embeddings.py`
- [Dataset notes](dataset-notes.md)
- [Runbook](runbook.md)

---

## Monitoring — 2/2

The Streamlit application includes both user-feedback collection and a monitoring dashboard with at least five charts.

Each interaction is written to PostgreSQL in a `conversations` table, including the question, answer, model, audience filters, token counts, latency, estimated cost, and timestamp. A separate `feedback` table records thumbs-up and thumbs-down feedback per conversation.

The Monitoring Dashboard includes:

- Summary metrics for conversation count, latency, estimated cost, and feedback
- Response-time chart
- Cost-per-query chart
- Token-usage chart
- Conversations-over-time chart
- Queries-by-organisation-size chart
- Queries-by-role chart
- Recent-conversations table

**Evidence:**

- `app.py`
- `conversations` PostgreSQL table
- `feedback` PostgreSQL table
- [Live Monitoring Dashboard](http://54.167.24.156:8501/)
- [README interactive UI and monitoring](../README.md#interactive-ui-and-monitoring)
- [Runbook reviewer verification path](runbook.md#reviewer-verification-path)

---

## Containerization — 2/2

The complete application runtime is defined through Docker Compose.

The Compose configuration includes:

- `postgres` — PostgreSQL with pgvector
- `bootstrap` — one-off schema initialisation, chunk loading, and embedding generation
- `app` — Streamlit application service

The repository also includes a `Dockerfile` for the application image, named volumes for PostgreSQL and model caching, health checks, and Docker ignore rules.

The same Docker Compose approach is used locally and on the lightweight EC2 deployment.

**Evidence:**

- `Dockerfile`
- `docker-compose.yml`
- `.dockerignore`
- [Runbook Docker and deployment instructions](runbook.md)
- [README interactive UI and monitoring](../README.md#interactive-ui-and-monitoring)

---

## Reproducibility — 2/2

The project provides clear reproduction paths from a clean checkout.

Reproducibility support includes:

- Public ACSC source URLs defined in `data/source_manifest_core.csv`
- A reviewed Markdown corpus snapshot for strict baseline reproduction
- A fresh source-download and extraction path
- Pinned Python dependencies in `pyproject.toml` and `uv.lock`
- Documented `uv` commands for the local workflow
- A Docker Compose runtime for the database, bootstrap process, and application
- A committed Streamlit configuration
- Step-by-step setup, evaluation, reset, and deployment instructions

A reviewer can either use the live deployed app for quick verification or follow the runbook to reproduce the corpus, index, retrieval evaluation, and local UI runtime.

**Evidence:**

- [README setup](../README.md#setup)
- [README usage](../README.md#usage)
- [Runbook](runbook.md)
- `pyproject.toml`
- `uv.lock`
- `Dockerfile`
- `docker-compose.yml`
- `.streamlit/config.toml`
- `data/source_manifest_core.csv`
- `data/corpus_snapshots/v1_2026-07-25/`

---

## Bonus implementation categories

### Hybrid search — implemented and evaluated

Hybrid retrieval combines text and vector results through reciprocal rank fusion. It was evaluated against the same benchmark as the other retrieval backends.

Hybrid retrieval improved substantially over text-only retrieval but did not outperform reranked-vector retrieval. It is retained as an evaluated alternative and debugging aid rather than being selected as the default.

**Evidence:**

- `src/retrieve_hybrid.py`
- `src/evaluate_retrieval.py`
- [Evaluation notes](evaluation-notes.md)

### Document reranking — implemented and selected

The project implements chunk reranking through `src/retrieve_reranked.py`.

Reranked-vector retrieval outperformed text, plain vector, and hybrid alternatives on the current benchmark. It is therefore the selected default retrieval backend for the Streamlit UI and current answer-generation path.

**Evidence:**

- `src/retrieve_reranked.py`
- `src/evaluate_retrieval.py`
- `app.py`
- [Evaluation notes](evaluation-notes.md)

### User query rewriting — implemented and evaluated

Query rewriting is implemented through `src/rewrite_query.py` and was evaluated across text, vector, reranked-vector, and hybrid backends.

It was not adopted as the default because it did not improve the frozen 27-question benchmark. The helper remains available for experimentation with selective or gated rewrite strategies.

Not selecting rewriting as the production default reflects the evaluation result; the capability is still implemented and evaluated.

**Evidence:**

- `src/rewrite_query.py`
- `src/evaluate_retrieval.py`
- [Evaluation notes](evaluation-notes.md)
- [Decision D-015](decisions.md)

### Cloud deployment — implemented

The project is deployed to a lightweight Ubuntu-based AWS EC2 instance for reviewer access.

The instance runs the same Docker Compose stack used for local reproduction:

- `postgres` service with pgvector
- `bootstrap` service for schema initialisation, chunk loading, and embedding generation
- `app` service running Streamlit on port 8501

The deployment is intended as a reviewer-facing demonstration environment rather than a hardened production deployment. It does not currently include HTTPS, a custom domain, or managed secrets.

**Evidence:**

- [Live deployed application](http://54.167.24.156:8501/)
- `Dockerfile`
- `docker-compose.yml`
- [Runbook EC2 deployment instructions](runbook.md)
- [Decision D-016](decisions.md)

---

## Strengths

The strongest parts of the project are currently:

- A clearly scoped and well-documented problem
- A real knowledge-base-plus-LLM RAG flow rather than direct prompting
- Comparative retrieval evaluation across four backends
- Comparative answer-generation evaluation with judge artefacts
- Selected defaults based on recorded benchmark results
- A deployed Streamlit interface with inspectable evidence
- Feedback collection and a monitoring dashboard with more than five charts
- Full Docker Compose runtime coverage
- Reproducible local and cloud deployment documentation

---

## Remaining gaps

The main remaining limitations are:

- The ingestion workflow is script-based rather than orchestrated through a dedicated workflow platform.
- The benchmark is synthetic and relatively small, so results should not be interpreted as broad real-world performance claims.
- Query rewriting is implemented but did not improve the current benchmark and is not part of the default path.
- The EC2 deployment is intentionally lightweight and lacks production hardening such as HTTPS, a custom domain, and managed secrets.

---

## Next steps

Potential next improvements are:

- Add a lightweight orchestration layer or a single high-level pipeline command for ingestion and evaluation.
- Expand evaluation with more diverse or human-authored questions while preserving a held-out test set.
- Investigate selective query rewriting or additional reranking variants only when evaluated against the existing benchmark.
- Add optional deployment hardening, such as HTTPS, a custom domain, and managed secret handling, if needed after assessment.
- Maintain clear Docker documentation for first-time bootstrap, normal restart, and full-reset workflows.

This document should be updated when the implementation or evidence changes. The criterion definitions should remain stable so changes in project maturity are easy to track.