# requirements_identification.md
## 0. Purpose
Design and deliver a law-firm internal application that answers user questions and supports legal work by retrieving and citing internal documents. The system must be safe, credible, auditable, and matter-scoped. The MVP must not rely on fine-tuning.

## 1. Scope (MVP)
### 1.1 In-Scope
1) Matter-scoped Q&A over internal documents with citations (document + page/section anchors).
2) GraphRAG-based retrieval:
   - Knowledge graph (Neo4j) for entity/relationship-aware candidate selection.
   - Vector retrieval over text chunks within ACL constraints.
3) LangGraph orchestration with deterministic workflow, checkpoints, and audit logs.
4) Graph visualization for developers and (optionally) power users using Neo4j Browser/Bloom.
5) Evaluation harness:
   - Retrieval evaluation (Recall@K, MRR).
   - Grounding evaluation (citation coverage, unsupported-claim rate).
6) Security baseline:
   - Authentication (SSO/OIDC if possible).
   - Authorization (matter/document ACL enforcement pre-retrieval).
   - Audit trail, logging controls, and prompt-injection defenses.

### 1.2 Out-of-Scope (MVP)
- Fine-tuning of the base LLM or training on internal documents.
- Redlining/contract mark-up, obligation calendar, eDiscovery, billing/time-entry integration.
- Automated legal advice; system must remain an assistant with “attorney review” posture.

## 2. Users and Personas
- Associate / trainee: clause lookup, summary, citation-based answers.
- Partner: quick confirmation with citations and risk flags.
- Paralegal / staff: locate provisions, extract definitions, compile clause packs.
- Admin/IT/Knowledge team: manage ingestion, permissions, monitoring, and evaluation.

## 3. Key User Stories (MVP)
1) As a user, I can select a matter scope and ask a question; the answer includes citations and quoted supporting text.
2) As a user, I can view the retrieval trace (which documents/sections were used).
3) As an admin, I can ingest documents, validate extraction quality, and enforce access control.
4) As an evaluator, I can run benchmark questions and see retrieval/grounding metrics.
5) As a developer, I can visually inspect the knowledge graph in Neo4j and debug entity links.

## 4. Functional Requirements
### 4.1 Authentication and Authorization
- FR-ACL-1: The system SHALL authenticate users (SSO via OIDC preferred).
- FR-ACL-2: The system SHALL enforce matter-level and document-level ACL at retrieval time.
- FR-ACL-3: The system SHALL support ethical walls / restricted matters (deny access even if user guesses identifiers).
- FR-ACL-4: The system SHALL not retrieve or display any content outside the user’s authorized scope.

### 4.2 Document Ingestion and Processing
- FR-ING-1: The system SHALL ingest PDF/DOCX and retain original files in secure storage.
- FR-ING-2: The system SHALL extract text with page anchors (PDF page numbers; DOCX section/paragraph anchors).
- FR-ING-3: The system SHALL chunk documents using legal-aware structure where possible (headings/clauses/definitions).
- FR-ING-4: The system SHALL compute embeddings for chunks and store them in a vector index.
- FR-ING-5: The system SHALL extract entities and relations to populate Neo4j (GraphRAG graph).

### 4.3 Knowledge Graph (Neo4j)
- FR-GRAPH-1: The system SHALL store a knowledge graph that includes nodes and edges sufficient for legal retrieval.
- FR-GRAPH-2: The system SHALL store provenance for each node/edge (source document + anchor).
- FR-GRAPH-3: The system SHALL support Cypher queries to retrieve candidate nodes for a user query.
- FR-GRAPH-4: The system SHALL support visualization via Neo4j Browser (and optionally Bloom).

#### 4.3.1 Minimum Graph Schema (MVP)
Nodes:
- Matter, Document, Section/Clause, DefinedTerm, Party, Obligation (optional MVP), Date/Deadline (optional MVP)
Edges:
- Matter-HAS_DOCUMENT->Document
- Document-CONTAINS->Section/Clause
- Clause-DEFINES->DefinedTerm
- Clause-REFERS_TO->Party
- Clause-IMPOSES->Obligation (optional MVP)
All nodes/edges MUST include `source_doc_id` and `source_anchor` for traceability.

### 4.4 Retrieval and Answering (GraphRAG + Vector)
- FR-RAG-1: The system SHALL perform graph retrieval to identify candidate documents/clauses (multi-hop traversal as needed).
- FR-RAG-2: The system SHALL perform vector retrieval restricted to authorized scope and graph candidates.
- FR-RAG-3: The system SHALL assemble evidence snippets and generate answers grounded in those snippets.
- FR-RAG-4: The system SHALL produce citations for each substantive claim (doc + page/section).
- FR-RAG-5: The system SHALL abstain or flag uncertainty if evidence is insufficient or conflicting.

### 4.5 LangGraph Orchestration
- FR-LG-1: The system SHALL implement the runtime workflow using LangGraph with explicit state.
- FR-LG-2: The system SHALL checkpoint intermediate artifacts (query intent, entities, candidates, retrieved chunks).
- FR-LG-3: The system SHALL implement safe fallbacks:
  - If graph retrieval fails, widen to vector-only within ACL (with warning).
  - If evidence coverage is low, return “insufficient evidence” with suggestions.
- FR-LG-4: The system SHALL record an audit log of each step (without leaking sensitive content in logs by default).

### 4.6 UI / UX (MVP)
- FR-UI-1: Matter selection (required) before question answering.
- FR-UI-2: Answer panel with:
  - concise conclusion
  - cited supporting quotes
  - references list (doc/section/page)
  - “confidence/needs review” indicator
- FR-UI-3: Retrieval trace panel (documents consulted, top passages).
- FR-UI-4: Graph view:
  - developer view via Neo4j Browser/Bloom
  - optional in-app graph widget for query trace visualization

## 5. Non-Functional Requirements (Safety, Credibility, Operations)
### 5.1 Safety and Credibility Controls
- NFR-SAFE-1: System SHALL be “evidence-first”: no uncited legal assertions in default mode.
- NFR-SAFE-2: System SHALL implement prompt-injection defenses:
  - treat document text as untrusted
  - ignore instructions contained in documents
- NFR-SAFE-3: System SHALL not provide definitive legal advice; include “attorney review required” posture where appropriate.
- NFR-SAFE-4: System SHALL support versioning: identify superseded documents and prefer latest versions (if metadata available).

### 5.2 Privacy and Security
- NFR-SEC-1: Encrypt data in transit (TLS) and at rest.
- NFR-SEC-2: Logs SHALL avoid storing full document text; store IDs/anchors; optionally store short snippets with explicit admin policy.
- NFR-SEC-3: Access attempts and denials SHALL be logged for audit.
- NFR-SEC-4: Data retention policy SHALL be configurable.

### 5.3 Performance
- NFR-PERF-1: Typical Q&A response time target: <= 10–20 seconds for MVP (configurable).
- NFR-PERF-2: Ingestion should be asynchronous and resumable; large documents processed in background jobs.

### 5.4 Reliability and Maintainability
- NFR-OPS-1: Monitoring for latency, error rate, and cost per query.
- NFR-OPS-2: Automated regression evaluation run on changes to ingestion, prompts, or retrieval.
- NFR-OPS-3: Clear rollback strategy for graph and embedding index updates.

## 6. Evaluation Requirements
### 6.1 Datasets
- EV-DS-1: Create a golden set of 50–200 questions tied to specific matters/documents (sanitized as needed).
- EV-DS-2: For each question, label the controlling clause/section anchor(s).

### 6.2 Metrics
Retrieval:
- EV-M-1: Recall@K (K=5,10) for labeled controlling clauses.
- EV-M-2: MRR for ranked retrieval.

Grounding:
- EV-M-3: Citation coverage rate (% of substantive sentences with citations).
- EV-M-4: Unsupported-claim rate (manual review on sampled outputs).

Usability:
- EV-M-5: Time saved vs manual lookup (pilot study).
- EV-M-6: User satisfaction and “follow-up needed” rate.

### 6.3 Gates (Release Criteria)
- EV-G-1: Recall@10 meets threshold (define per domain; initial target 0.8+ on MVP set).
- EV-G-2: Unsupported-claim rate below threshold (e.g., <5% on reviewed samples).
- EV-G-3: No cross-matter leakage in security tests.

## 7. Architecture (Proposed)
- Backend: Python + FastAPI
- Orchestration: LangGraph
- KG: Neo4j
- Vector: pgvector or managed vector DB
- Storage: object store for originals + Postgres for metadata
- Queue: Redis/Celery for ingestion
- Frontend: React/Next.js

## 8. Data Model (Minimum Metadata)
- client_id, matter_id
- doc_id, doc_type, title, version, effective_date, supersedes_doc_id (optional)
- confidentiality level / ethical wall flags
- ACL list (users/groups)
- extraction status and quality indicators

## 9. Roadmap
### MVP (no fine-tuning)
1) Ingestion + anchors + ACL
2) Vector baseline with citations
3) Neo4j schema + entity extraction + GraphRAG retrieval
4) LangGraph workflow + audit logs + grounding checks
5) Evaluation harness + pilot

### Next Step (post-MVP)
- Retrieval tuning (reranker, embedding fine-tune on labeled clause pairs)
- Optional LLM fine-tuning for formatting/consistency ONLY (not knowledge)
- Additional workflows: obligation extraction, drafting templates, clause comparison, version diff

## 10. Risks and Mitigations
- RISK-1: Hallucinations → Mitigate with “cite-or-abstain” and grounding checks.
- RISK-2: Access leakage → Mitigate with pre-retrieval ACL filters and red-team tests.
- RISK-3: Bad extraction quality → Mitigate with extraction QA dashboards and fallback OCR.
- RISK-4: Graph noise → Mitigate with schema constraints, provenance, and evaluation-driven iteration.
