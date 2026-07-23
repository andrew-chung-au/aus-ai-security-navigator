# Self-assessment


This document records the current state of the project against a set of evaluation criteria. Each core criterion has three states (Poor, OK, Good), plus a few separate unrated bonus implementation categories.


`README.md` remains the main explanation of the project, and `docs/reproducibility.md` remains the main runbook. This file is for personal reflection and for guiding documentation and implementation work.


### Problem description


- **Poor**: The problem is not described.
- **OK**: The problem is described but briefly or unclearly.
- **Good**: The problem is well‑described and it’s clear what problem the project solves.


### Retrieval flow


- **Poor**: No knowledge base or LLM is used.
- **OK**: No knowledge base is used, and the LLM is queried directly.
- **Good**: Both a knowledge base and an LLM are used in the flow.


### Retrieval evaluation


- **Poor**: No evaluation of retrieval is provided.
- **OK**: Only one retrieval approach is evaluated.
- **Good**: Multiple retrieval approaches are evaluated, and the best one is used.


### LLM evaluation


- **Poor**: No evaluation of final LLM output is provided.
- **OK**: Only one approach (e.g., one prompt) is evaluated.
- **Good**: Multiple approaches are evaluated, and the best one is used.


### Interface


- **Poor**: No way to interact with the application at all.
- **OK**: Command line interface, a script, or a Jupyter notebook.
- **Good**: UI (e.g., Streamlit), web application (e.g., Django), or an API (e.g., built with FastAPI).


### Ingestion pipeline


- **Poor**: No ingestion.
- **OK**: Semi‑automated ingestion of the dataset into the knowledge base, e.g., with a Jupyter notebook or a Python script.
- **Good**: Automated ingestion with a special tool (e.g., Kestra, dlt, Airflow, Prefect).


### Monitoring


- **Poor**: No monitoring.
- **OK**: User feedback is collected OR there’s a monitoring dashboard.
- **Good**: User feedback is collected and there’s a dashboard with at least 5 charts.


### Containerization


- **Poor**: No containerization.
- **OK**: Dockerfile is provided for the main application OR there’s a docker‑compose for the dependencies only.
- **Good**: Everything is in docker‑compose.


### Reproducibility


- **Poor**: No instructions on how to run the code, the data is missing, or it’s unclear how to access it.
- **OK**: Some instructions are provided but are incomplete, OR instructions are clear and complete, the code works, but the data is missing.
- **Good**: Instructions are clear, the dataset is accessible, it’s easy to run the code, and it works. The versions for all dependencies are specified.


## Bonus implementation categories


- Hybrid search: combining both text and vector search (at least evaluating it).
- Document re‑ranking.
- User query rewriting.
- Deployment to the cloud.


---


## Current status summary


| Area | State | Notes |
|------|-------|-------|
| Problem description | Good | Clear problem, scope, and users are documented. |
| Retrieval flow | Good | Knowledge base is implemented, and LLMs are already used in supporting evaluation-data workflows; final answer generation is the main missing retrieval-to-answer step. |
| Retrieval evaluation | Good | Text, vector, and hybrid retrieval are evaluated on the same benchmark; vector is chosen on evidence as the current default. |
| LLM evaluation | Poor | LLMs are used in supporting workflows, but final answers are not yet implemented and evaluated. |
| Interface | OK | CLI / scripts; no web UI or API yet. |
| Ingestion pipeline | OK | Semi‑automated ingestion with scripts plus manual cleanup. |
| Monitoring | Poor | No feedback collection or dashboard. |
| Containerization | Poor | No Docker or docker‑compose setup yet. |
| Reproducibility | Good | Clear instructions, accessible dataset, pinned dependencies. |
| Hybrid search | — | Implemented and evaluated via reciprocal rank fusion; improves over text but not over vector on the current benchmark. |
| Document reranking | — | No second‑stage reranker yet. |
| Query rewriting | — | No rewrite step yet. |
| Cloud deployment | — | No deployment; local development only. |


---


## Problem description — (Good)


The project clearly explains that it aims to help Australian organisations navigate official ACSC guidance on AI security, which is spread across multiple documents and formats. The README describes the user problem, why generic AI advice is insufficient, and how a grounded RAG tool over ACSC sources addresses that gap. This fits the “2 points / Good” rubric level: the problem is well‑described and it is clear what problem the project solves. Evidence lives mainly in `README.md`, `docs/dataset-notes.md`, and `docs/decisions.md`.


## Retrieval flow — (Good)


The project uses both a knowledge base and LLM‑supported workflow components. ACSC documents are downloaded, cleaned, chunked, stored as `data/chunks/chunks.jsonl`, and loaded into a PostgreSQL `chunks` table. Retrieval scripts implement full‑text search, pgvector‑based dense retrieval, and a hybrid fusion retriever, while the LLM helper supports seed vetting and synthetic question generation. Final answer generation over retrieved chunks is not yet implemented, but the current flow still meets the “2 points / Good” definition because both a knowledge base and LLM-supported components are part of the overall system rather than direct prompting alone. Evidence is in `src/db_init.py`, `src/db_load_chunks.py`, `src/retrieve_text.py`, `src/retrieve_vector.py`, `src/retrieve_hybrid.py`, `src/llm_client.py`, and the corpus files.


## Retrieval evaluation — (Good)


Retrieval quality is evaluated explicitly, and multiple retrieval approaches are compared on the same synthetic benchmark. The project builds a synthetic ground‑truth set and uses `src/evaluate_retrieval.py` to compare text retrieval, vector retrieval, and hybrid retrieval, reporting metrics such as hit rate and MRR. Current results show that vector retrieval substantially outperforms the text baseline, while simple hybrid retrieval improves over text but does not beat vector on the current corpus and question set. This matches the “2 points / Good” definition: multiple retrieval approaches are evaluated and the best one is used. Evidence is in `src/evaluate_retrieval.py`, `src/retrieve_text.py`, `src/retrieve_vector.py`, `src/retrieve_hybrid.py`, `data/ground_truth_synthetic.jsonl`, and the recorded metrics. [web:128]


## LLM evaluation — (Poor)


LLMs are used in the project, but mainly in supporting workflows (seed vetting, synthetic question generation) rather than in a fully evaluated answer‑generation layer over retrieved chunks. There is no implemented comparison of multiple prompts or answer‑generation strategies, and no structured assessment of final LLM outputs yet. This fits the “0 points / Poor” definition: there is currently no evaluation of final LLM output. Evidence is in `src/llm_client.py` and the evaluation‑data scripts; absence of answer‑evaluation logic is noted as a gap.


## Interface — (OK)


The project is interacted with through scripts and command‑line commands. Retrieval and evaluation workflows are runnable and documented via CLI, but there is no UI, web app, or API yet. This matches the “1 point / OK” definition: there is a command‑line interface or scripts, but not a higher‑level UI. Evidence is in the `src/` scripts and the commands included in `README.md` and `docs/reproducibility.md`.


## Ingestion pipeline (OK)


The ingestion pipeline is semi‑automated and clearly documented. A manifest defines sources; scripts handle downloading and extraction for HTML and PDFs; manual cleanup improves the processed Markdown; chunk preparation and DB loading are scripted. This fits the “1 point / OK” definition: semi‑automated ingestion via scripts, rather than fully automated orchestration with tools like Airflow or Prefect. Evidence is in `src/download_sources.py`, `src/extract.py`, `src/extract_pdfs.py`, `src/prepare_chunks.py`, and the reproducibility notes.


## Monitoring (Poor)


There is currently no monitoring: no feedback collection, no dashboard, and no charts. This matches the “0 points / Poor” definition: monitoring is simply not present yet. This is a future‑work area once the system has a user‑facing interface and answer‑generation path. Evidence is the absence of monitoring code or docs.


## Containerization (Poor)


The project can be run from a clean environment using `uv` and pinned dependencies, but there is no Dockerfile or docker‑compose setup. This corresponds to the “0 points / Poor” definition: no containerization. This is acceptable for development, but clearly identified as an improvement area for later. Evidence: repository structure and the lack of container files.


## Reproducibility (Good)


Reproducibility is strong. The project has clear instructions on how to run the code, a manifest‑defined public dataset, pinned dependency versions, and a documented pipeline that covers downloading, extraction, cleanup, chunking, indexing, and evaluation. Someone else should be able to rebuild the corpus and rerun the retrieval evaluation from a clean checkout. This meets the “2 points / Good” definition: instructions are clear, the dataset is accessible, it’s easy to run the code, and version information is specified. Evidence is in `docs/reproducibility.md`, `README.md`, `pyproject.toml`, `uv.lock`, and `data/source_manifest_core.csv`.


---


## Bonus categories — current notes


These categories are not scored in the 0/1/2 framework, but they are worth tracking for project maturity.


### Hybrid search


Hybrid search is now implemented and evaluated. The project includes a simple reciprocal-rank-fusion (RRF) hybrid retriever that combines text and vector results without directly normalising their different score scales. On the current synthetic benchmark, hybrid retrieval improves substantially over text-only retrieval but does not outperform vector-only retrieval, so it is retained as an evaluated alternative and debugging aid rather than the default retriever. Evidence is in `src/retrieve_hybrid.py`, `src/evaluate_retrieval.py`, and the recorded metrics. [web:128][web:124]


### Document re-ranking


Document or chunk reranking is not yet present. The current system relies on the primary retriever’s ranking only. A second‑stage reranker could be added later to refine results, especially after the answer-generation layer is in place.


### User query rewriting


There is no explicit query rewriting layer. Queries are currently sent to retrievers as‑is. A rewriting step might be useful later for messy user queries once the end‑to‑end flow is in place.


### Deployment to the cloud


The project is not deployed to the cloud and does not include deployment automation or production infrastructure. That is beyond the current scope, but worth noting as potential future work.


### Other extras


Any additional notable features (e.g., advanced logging, structured error handling, report generation) can be added here as the project evolves.


---


## Strongest areas and gaps


Strongest areas right now:


- Problem description (Good)
- Retrieval flow (Good)
- Retrieval evaluation (Good)
- Reproducibility (Good)


Clear gaps:


- LLM evaluation of final answers (Poor)
- Interface beyond CLI (OK)
- Monitoring (Poor)
- Containerization (Poor)
- Bonus implementation categories beyond hybrid search are not yet implemented


## Next steps


Based on this assessment, the most useful next steps are:


- Implement answer generation over retrieved chunks and evaluate at least one prompt/approach.
- Add a simple user interface (e.g., Streamlit, FastAPI) for easier interaction.
- Inspect hybrid failure cases and decide whether any small retrieval refinement is worth trying before moving fully into answer generation.
- Consider containerization and basic monitoring once the application flow is stable.


This document is intended to evolve as those areas are implemented; the rubric definitions stay fixed, but the states and notes for each criterion can be updated over time.