# Law RAG Application

Internal, matter‑scoped Retrieval‑Augmented Generation (RAG) application for law firms.  
The system answers user questions over internal documents **with strict citations, ACL enforcement, and full auditability**, and is designed to work **without any model fine‑tuning in the MVP**, while remaining tuning‑ready for later iterations.

## Overview

This repository contains an end‑to‑end legal RAG stack:

- **Backend (`backend/`)**: FastAPI service that handles ingestion, chunking, embeddings, GraphRAG retrieval (Postgres + pgvector + Neo4j), LLM‑based answer generation with citations, LangGraph‑style workflow orchestration, and audit logging.
- **Frontend (`frontend/`)**: Next.js UI for matter selection, question input, answer display with citations, and retrieval trace visualization.
- **Infrastructure (`infra/`)**: `compose.yaml` for running Postgres (with pgvector) and Neo4j locally.
- **Evaluation (`eval/`)**: Golden set and metric thresholds for automated regression/evaluation of retrieval and grounding quality.

The application is **internal and matter‑scoped**:

- Every query is bound to a `matter_id`.
- Access control is enforced before any vector or graph retrieval.
- Every substantive statement in an answer must either:
  - Have one or more **citations** (document + page/section anchor), or
  - Be explicitly marked as **“insufficient evidence”**.

Fine‑tuning of the base LLM is **explicitly out of scope for the MVP** but is planned as a **post‑MVP enhancement** (see “Fine‑Tuning & Future Tuning” below).

## Key Capabilities

- **Matter‑scoped Q&A with citations**
  - Question answering over internal PDF/DOCX documents.
  - Each substantive sentence is backed by one or more citations (doc id + anchor).
  - The system abstains when evidence is insufficient.

- **Document ingestion and anchored extraction**
  - Upload endpoint stores original files and extracted text with page/section anchors.
  - Documents are chunked along legal structure where possible (headings, clauses, definitions).
  - Embeddings are computed for chunks and stored in a pgvector index.

- **GraphRAG retrieval**
  - Neo4j knowledge graph with nodes like Matter, Document, Clause/Section, DefinedTerm, Party, etc.
  - Edges encode relationships (e.g., `Matter-HAS_DOCUMENT->Document`, `Document-CONTAINS->Clause`).
  - Graph retrieval identifies candidate documents/clauses; vector search runs within that candidate set and ACL scope.

- **LangGraph‑style workflow and auditability**
  - Deterministic workflow with explicit state and checkpoints (query intent, entities, candidates, retrieved chunks, answer).
  - Per‑step audit logs record which artifacts and sources were used (without logging raw sensitive text by default).

- **LLM‑based answer composer with safety controls**
  - Uses Google Gemini via the `google-genai` / `google-generativeai` client.
  - Prompts enforce “cite‑or‑abstain” behavior and treat document text as **untrusted** (prompt‑injection defense).
  - Citation parsing and validation ensure that answer references match the provided context.

- **Evaluation harness**
  - CLI to load a golden set of questions and measure:
    - Retrieval metrics (Recall@K, MRR).
    - Grounding metrics (citation coverage, unsupported‑claim rate).
  - Thresholds can be used as **gates** in CI/CD (fail the build if quality falls below configured limits).

## Architecture

High‑level architecture (see `requirements_identification.md` for full details):

- **Backend**
  - Language: Python 3.11+
  - Framework: FastAPI
  - Orchestration: LangGraph‑style workflow in `app/workflow.py`
  - Storage:
    - Postgres (metadata + chunks) with pgvector for similarity search
    - Object storage / filesystem for original documents
    - Neo4j for the knowledge graph and provenance
  - LLM: Google Gemini (via `google-genai` / `google-generativeai`) with custom prompts
  - Logging: structured logging via `structlog`, with IDs/anchors instead of raw text

- **Frontend**
  - Framework: Next.js (React, App Router)
  - Responsibilities:
    - Matter selection
    - Question input
    - Answer display with cited snippets
    - Retrieval trace panel (documents/sections consulted)
    - Optional graph visualization hooks (via Neo4j Browser/Bloom or in‑app widgets)

- **Infra**
  - `infra/compose.yaml` runs:
    - `postgres` with pgvector extension (`lawrag` database).
    - `neo4j` with APOC enabled.

- **Evaluation**
  - `eval/golden_set.jsonl`: labeled questions and controlling clauses/anchors.
  - `eval/thresholds.yaml`: metric thresholds for gates (e.g., Recall@10, unsupported‑claim rate).

## Repository Layout

- `backend/`
  - `app/main.py`: FastAPI entrypoint (health check, document upload, query endpoints, etc.).
  - `app/config.py`: Pydantic settings for environment‑driven configuration.
  - `app/database.py`: SQLAlchemy setup and pgvector initialization.
  - `app/models.py`: SQLAlchemy models for documents, chunks, extracted text, audit logs, etc.
  - `app/extraction.py`, `app/chunking.py`: Text extraction and chunking.
  - `app/embeddings.py`: Embedding generation and batch operations.
  - `app/entity_extraction.py`, `app/graph.py`: Entity extraction and Neo4j graph schema/operations.
  - `app/retrieval.py`: GraphRAG + vector retrieval logic.
  - `app/llm.py`, `app/prompts.py`: LLM integration with Gemini and prompt templates.
  - `app/workflow.py`: End‑to‑end query workflow with checkpoints.
  - `app/audit.py`, `app/logging.py`, `app/auth.py`: Audit logging, structured logging, and matter‑scoped ACL checks.
  - `app/cli_eval.py`: Evaluation harness CLI (`law-rag-eval`).
  - `tests/`: Comprehensive pytest suite (config, ingestion, embeddings, retrieval, LLM, auth, audit, etc.).
  - `pyproject.toml`: Backend project metadata and dependencies.

- `frontend/`
  - Next.js application scaffold (see `frontend/README.md` for standard Next.js commands).

- `infra/`
  - `compose.yaml`: Local Postgres + Neo4j services.

- `eval/`
  - `golden_set.jsonl`: Evaluation dataset.
  - `thresholds.yaml`: Metric thresholds for automated gates.

- `SPEC.md` / `requirements_identification.md`
  - High‑level specification, functional/non‑functional requirements, evaluation criteria, and roadmap.

## Getting Started

### Prerequisites

- Python **3.11+**
- Node.js (LTS, e.g. 18+)
- Docker + Docker Compose
- Access to a Google Gemini API key

### Start Infra (Postgres + Neo4j)

From the repo root:

```bash
docker compose -f infra/compose.yaml up -d
```

This starts:

- Postgres with pgvector on `localhost:5432`
- Neo4j on `localhost:7474` (HTTP) and `localhost:7687` (Bolt)

### Backend Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

Configure environment variables (recommended: copy `.env.example` to `.env` and adjust):

- `LAW_RAG_GEMINI_API_KEY`: Gemini API key (required for answer generation)
- `LAW_RAG_GEMINI_MODEL`: Gemini model name (e.g., `gemini-1.5-pro`)
- `LAW_RAG_MAX_CONTEXT_CHUNKS`: Max chunks to send to the LLM (default: 10)
- `LAW_RAG_USER_MATTERS`: JSON mapping of users to authorized matters, e.g.:

```bash
export LAW_RAG_GEMINI_API_KEY="your-key"
export LAW_RAG_GEMINI_MODEL="gemini-1.5-pro"
export LAW_RAG_MAX_CONTEXT_CHUNKS="10"
export LAW_RAG_USER_MATTERS='{"alice":["matter-1"],"bob":["matter-2"]}'
```

Then start the backend:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Basic smoke tests:

- Health check:

  ```bash
  curl http://localhost:8000/health
  ```

- Upload a document:

  ```bash
  curl -X POST http://localhost:8000/v1/documents/upload \
    -H "X-User-Id: alice" \
    -F "file=@sample.pdf" \
    -F "matter_id=matter-1"
  ```

- Ask a question with cited answer:

  ```bash
  curl -X POST http://localhost:8000/v1/query \
    -H "X-User-Id: alice" \
    -H "Content-Type: application/json" \
    -d '{
      "matter_id": "matter-1",
      "query": "What is the payment term?"
    }'
  ```

The response will include:

- `answer`: Generated answer with citation markers like `[1]`, `[2]`
- `citations`: Array of citation objects (`doc_id`, `anchor`, etc.)
- `abstained`: `true` if the system returned “insufficient evidence”
- `confidence`: Confidence score (0.0–1.0)
- `retrieval_trace`: Array of retrieved chunks used as context

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000` in your browser.  
If needed, configure the API base URL via a Next.js environment variable (for example, `NEXT_PUBLIC_API_BASE_URL`) so that the frontend points to the FastAPI backend at `http://localhost:8000`.

## Core Workflows

### 1. Document Ingestion

1. User uploads a PDF/DOCX to `/v1/documents/upload` with `matter_id` and identity header.
2. Backend:
   - Stores the original file.
   - Extracts text with page/section anchors.
   - Chunks the document into semantically coherent units.
   - Computes embeddings and stores chunks + vectors in Postgres/pgvector.
   - Extracts entities/relations and updates the Neo4j graph with provenance.
3. Anchors and metadata are returned so users and tools can refer to specific sections.

### 2. Question Answering with Citations

1. User selects a matter and sends a query to `/v1/query`.
2. Access control checks ensure the user is authorized for the `matter_id`.
3. Workflow:
   - Graph retrieval in Neo4j to identify candidate documents/clauses.
   - Vector search over candidate chunks within ACL constraints.
   - Context formatting with numbered snippets.
   - LLM call to Gemini with prompts that:
     - Enforce citation for each substantive statement.
     - Instruct the model to abstain when evidence is insufficient.
4. Backend parses and validates citations and returns:
   - Answer text.
   - Citations list.
   - Retrieval trace.
   - Abstain flag + confidence.

### 3. Retrieval Trace and Audit

- Every step of the workflow (graph query, vector search, LLM call, etc.) produces an audit log entry.
- Logs store IDs, anchors, and metadata—not raw document text—by default.
- Retrieval traces can be surfaced in the UI to help attorneys verify how answers were constructed.

## Safety, Security, and Compliance

Key controls (see `SPEC.md` and `requirements_identification.md`):

- **Matter‑scoped ACLs**
  - All retrieval is filtered by `matter_id` and user authorization.
  - Ethical walls and restricted matters are enforced as deny‑by‑default.

- **Cite‑or‑abstain**
  - No uncited legal assertions in default mode.
  - “Insufficient evidence” responses when supporting text is missing or conflicting.

- **Prompt‑injection defense**
  - Document text is treated as untrusted content.
  - Instructions inside documents are ignored by the LLM.

- **Privacy and logging**
  - Data is encrypted in transit and at rest (via underlying infra).
  - Logs avoid full document text; they store IDs/anchors and, optionally, short snippets under explicit policy.
  - Access attempts and denials are auditable.

- **“Attorney review required” posture**
  - The system is designed as an assistant, not a source of autonomous legal advice.

## Evaluation Harness

The backend exposes a CLI entrypoint `law-rag-eval` defined in `pyproject.toml`:

```bash
cd backend
law-rag-eval --help
```

Typical usage (conceptual):

1. Populate `eval/golden_set.jsonl` with questions and labeled controlling clauses/anchors.
2. Configure thresholds in `eval/thresholds.yaml` (e.g., minimum Recall@10, maximum unsupported‑claim rate).
3. Run the CLI to compute:
   - **Retrieval metrics**: Recall@5/10, MRR.
   - **Grounding metrics**: citation coverage, unsupported‑claim rate.
4. Integrate the CLI into CI to **gate deployments**:
   - Fail the build if retrieval quality or grounding falls below thresholds.

## Fine‑Tuning & Future Tuning

**Important:** The MVP is explicitly designed to **not rely on any fine‑tuning** of the base LLM or training on internal documents. All behavior is driven by:

- Careful prompt design.
- Retrieval quality (graph + vector).
- Strict citation and abstain logic.

However, the system is **tuning‑ready** for post‑MVP improvements.

Planned/possible tuning directions (to be implemented later):

- **Retrieval tuning (recommended first)**
  - Train or configure a **reranker** on labeled clause pairs to improve ranking of retrieved chunks.
  - Experiment with **embedding model variants** or fine‑tuning embeddings on in‑domain legal clauses.
  - Use the evaluation harness (Recall@K, MRR) to quantitatively compare retrieval variants.

- **Optional LLM fine‑tuning (formatting/consistency only)**
  - If allowed by policy, fine‑tune the LLM **only for style and structure**, _not_ for encoding firm‑specific legal knowledge.
  - Goals:
    - More consistent answer formatting (headings, bullet structure, citation placement).
    - More predictable expressions of uncertainty and “insufficient evidence.”
  - All fine‑tuning should preserve:
    - Mandatory citation requirements.
    - Matter‑scoped ACL behavior.
    - Abstain‑on‑insufficient‑evidence rules.

- **Evaluation‑driven tuning loop**
  - Use `law-rag-eval` as a gate:
    - New prompt versions, retrieval configs, or fine‑tuned models must meet or exceed baselines.
  - Track:
    - Recall@10 on golden questions.
    - Citation coverage and unsupported‑claim rate.
    - Cross‑matter leakage tests.

This README documents the **intended fine‑tuning strategy**, but the actual implementation of fine‑tuning is intentionally deferred and should be performed separately, following your organization’s safety, privacy, and compliance requirements.

## Development & Testing

Run backend tests:

```bash
cd backend
pytest -v
```

During development, you can:

- Add new ingestion pipelines, graph schema extensions, or retrieval strategies.
- Adjust prompts and LLM configuration in `app/prompts.py` and `app/llm.py`.
- Extend the frontend to expose more of the retrieval trace or graph structure.

Before deploying changes that affect retrieval or generation behavior, run the evaluation harness and review logs to ensure safety, correctness, and compliance remain within acceptable bounds.

