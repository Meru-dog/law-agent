# Japan-US Legal AI Agent: Complete Requirements Definition Document

## Document Control

| Item | Details |
|------|---------|
| **Project Name** | Japan-US Legal AI Agent (法務AIエージェント) |
| **Version** | 1.0 |
| **Date** | March 5, 2026 |
| **Author** | Legal AI Development Team |
| **Status** | Requirements Definition - Phase 1 |
| **Target Users** | Corporate lawyers, legal researchers, in-house counsel (Japan ↔ US transactions) |

---

# Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Overview](#2-system-overview)
3. [Current System Architecture (Baseline)](#3-current-system-architecture-baseline)
4. [Enhanced System Architecture (Post Fine-Tuning)](#4-enhanced-system-architecture-post-fine-tuning)
5. [Functional Requirements](#5-functional-requirements)
6. [Non-Functional Requirements](#6-non-functional-requirements)
7. [Data Requirements](#7-data-requirements)
8. [Technical Specifications](#8-technical-specifications)
9. [Implementation Roadmap](#9-implementation-roadmap)
10. [Evaluation & Success Criteria](#10-evaluation--success-criteria)
11. [Risk Management](#11-risk-management)
12. [Appendices](#12-appendices)

---

# 1. Executive Summary

## 1.1 Project Vision

Build a **bilingual (Japanese/English) legal AI agent** specialized in Japanese and American corporate law, capable of answering complex legal questions with precise citations, appropriate for cross-border transactions and comparative legal analysis.

## 1.2 Core Value Proposition

| Feature | Value |
|---------|-------|
| **Bilingual expertise** | Seamlessly handles Japanese and US law queries in both languages |
| **Citation discipline** | Every statement backed by specific legal sources |
| **GraphRAG architecture** | Intelligent document retrieval using knowledge graphs + vector search |
| **Fine-tuned LLM** | Llama 3.1 70B optimized for legal reasoning and citation formatting |
| **Cross-border focus** | Specialized in Japan-US M&A, securities offerings, IP licensing |

## 1.3 Target Use Cases

1. **Cross-border M&A due diligence**
   - "What are the key differences between Japanese and Delaware corporate governance requirements?"
   - "日本の会社法における取締役の義務と米国法の違いは？"

2. **Contract review and analysis**
   - "What are the payment terms in this service agreement?"
   - "この契約における解除条件は？"

3. **Securities law compliance**
   - "What disclosure requirements apply to a Tokyo-NYSE dual listing?"
   - "有価証券報告書における重要な記載事項は？"

4. **Comparative legal research**
   - "How do shareholder approval thresholds differ between Japan and Delaware?"
   - "日米における配当規制の相違点は？"

## 1.4 Success Metrics (Phase 1)

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| **Citation accuracy** | 85% | 95% | % of citations that correctly support claims |
| **Retrieval recall@10** | 78% | 90% | % of controlling clauses in top 10 results |
| **Answer completeness** | 70% | 85% | Human attorney rating (1-5 scale) |
| **Bilingual consistency** | N/A | 90% | JP/EN answer semantic equivalence |
| **Cross-border accuracy** | N/A | 80% | Correct comparative law analysis |

---

# 2. System Overview

## 2.1 System Context Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    External Systems                              │
├─────────────────────────────────────────────────────────────────┤
│  • Document Management System (DMS)                              │
│  • e-Gov API (Japanese law database)                            │
│  • SEC EDGAR (US securities filings)                            │
│  • User authentication (SSO/LDAP)                               │
└─────────────────────────────────────────────────────────────────┘
                            ↓ ↑
┌─────────────────────────────────────────────────────────────────┐
│              Japan-US Legal AI Agent (Core System)              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Frontend   │  │   Backend    │  │  Knowledge   │         │
│  │   (Next.js)  │  │  (FastAPI)   │  │    Stores    │         │
│  │              │  │              │  │              │         │
│  │ • Matter UI  │  │ • RAG Engine │  │ • Postgres   │         │
│  │ • Query      │  │ • Fine-tuned │  │ • Neo4j      │         │
│  │ • Results    │  │   LLM        │  │ • Vector DB  │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                            ↓ ↑
┌─────────────────────────────────────────────────────────────────┐
│                          End Users                               │
├─────────────────────────────────────────────────────────────────┤
│  • Corporate lawyers (in-house counsel)                          │
│  • External counsel (law firms)                                 │
│  • Legal researchers                                             │
│  • Compliance officers                                          │
└─────────────────────────────────────────────────────────────────┘
```

## 2.2 High-Level Architecture

```
User Query (JP or EN)
        ↓
┌───────────────────────────────────────────────────┐
│ 1. ACCESS CONTROL & MATTER VALIDATION             │
│    - Verify user authorization for matter_id      │
│    - Ethical wall enforcement                     │
└───────────────────────────────────────────────────┘
        ↓
┌───────────────────────────────────────────────────┐
│ 2. QUERY UNDERSTANDING & INTENT DETECTION         │
│    - Language detection (JP/EN)                   │
│    - Query type classification                    │
│    - Entity extraction (statutes, cases, parties) │
└───────────────────────────────────────────────────┘
        ↓
┌───────────────────────────────────────────────────┐
│ 3. GRAPHRAG RETRIEVAL                             │
│                                                    │
│  ┌─────────────────┐    ┌────────────────────┐  │
│  │  Graph Query    │───▶│  Candidate Docs    │  │
│  │  (Neo4j)        │    │  • Matters         │  │
│  │                 │    │  • Documents       │  │
│  │  Identify:      │    │  • Clauses         │  │
│  │  - Relevant docs│    │  • Statutes        │  │
│  │  - Related      │    │  • Cases           │  │
│  │    entities     │    └────────────────────┘  │
│  └─────────────────┘             ↓               │
│                                                    │
│  ┌─────────────────┐    ┌────────────────────┐  │
│  │ Vector Search   │───▶│  Top 30 Chunks     │  │
│  │ (pgvector)      │    │  (within ACL scope)│  │
│  │                 │    └────────────────────┘  │
│  │ Similarity      │             ↓               │
│  │ search within   │                             │
│  │ candidates      │    ┌────────────────────┐  │
│  └─────────────────┘    │ Fine-tuned Reranker│  │
│                          │ (OPTIONAL - Phase 2)│  │
│                          └────────────────────┘  │
│                                   ↓               │
│                          ┌────────────────────┐  │
│                          │   Top 10 Chunks    │  │
│                          │   (final context)  │  │
│                          └────────────────────┘  │
└───────────────────────────────────────────────────┘
        ↓
┌───────────────────────────────────────────────────┐
│ 4. CONTEXT FORMATTING                             │
│    - Number chunks [1], [2], [3]...               │
│    - Add anchors (doc_id, page, section)          │
│    - Format for LLM consumption                   │
└───────────────────────────────────────────────────┘
        ↓
┌───────────────────────────────────────────────────┐
│ 5. ANSWER GENERATION (FINE-TUNED LLM)            │
│                                                    │
│    Model: Llama 3.1 70B + LoRA adapters          │
│                                                    │
│    System Prompt:                                 │
│    "You are a bilingual legal specialist (JP/US).│
│     Answer with citations. Abstain if evidence    │
│     insufficient."                                │
│                                                    │
│    Context: [numbered chunks from retrieval]      │
│    Query: [user question]                         │
│                                                    │
│    Output:                                        │
│    - Answer text with citation markers [N]        │
│    - Confidence score                             │
│    - Abstain flag (if applicable)                 │
└───────────────────────────────────────────────────┘
        ↓
┌───────────────────────────────────────────────────┐
│ 6. CITATION VALIDATION & PARSING                  │
│    - Extract citation markers [1], [2]...         │
│    - Verify citations match provided context      │
│    - Flag hallucinated citations                  │
│    - Build citation metadata                      │
└───────────────────────────────────────────────────┘
        ↓
┌───────────────────────────────────────────────────┐
│ 7. RESPONSE ASSEMBLY & AUDIT LOGGING              │
│    - Combine answer + citations                   │
│    - Add retrieval trace (for transparency)       │
│    - Log query, sources used, answer ID           │
│    - Return to frontend                           │
└───────────────────────────────────────────────────┘
        ↓
User receives: Answer + Citations + Retrieval Trace
```

---

# 3. Current System Architecture (Baseline)

## 3.1 Existing Components (From Your README)

### 3.1.1 Backend Components

| Component | Technology | Purpose | Status |
|-----------|-----------|---------|--------|
| **API Server** | FastAPI (Python 3.11+) | RESTful API endpoints | ✅ Implemented |
| **Database** | PostgreSQL + pgvector | Document metadata, chunks, embeddings | ✅ Implemented |
| **Graph Database** | Neo4j | Knowledge graph (Matter→Document→Clause) | ✅ Implemented |
| **LLM Integration** | Google Gemini API | Answer generation (baseline) | ✅ Implemented |
| **Workflow Engine** | LangGraph-style | Deterministic query workflow with checkpoints | ✅ Implemented |
| **Audit System** | Custom logging (structlog) | Query tracking, citation validation | ✅ Implemented |

### 3.1.2 Current GraphRAG Implementation

**Neo4j Graph Schema:**

```cypher
// Node types
(:Matter {matter_id, name, practice_area, jurisdiction})
(:Document {doc_id, matter_id, filename, upload_date})
(:Chunk {chunk_id, doc_id, text, anchor, page, section})
(:DefinedTerm {term, definition, source_doc})
(:Party {name, role, matter_id})
(:Statute {jurisdiction, code, section, text})
(:Case {court, date, citation, holding})

// Relationships
(Matter)-[:HAS_DOCUMENT]->(Document)
(Document)-[:CONTAINS]->(Chunk)
(Document)-[:DEFINES]->(DefinedTerm)
(Matter)-[:INVOLVES]->(Party)
(Chunk)-[:REFERENCES]->(Statute)
(Chunk)-[:CITES]->(Case)
(Document)-[:RELATED_TO]->(Document)
```

**Current Retrieval Flow:**

```python
# Pseudo-code from existing system
def retrieve_chunks(matter_id, query, top_k=10):
    # Step 1: Graph-based candidate selection
    graph_query = """
    MATCH (m:Matter {matter_id: $matter_id})-[:HAS_DOCUMENT]->(d:Document)-[:CONTAINS]->(c:Chunk)
    WHERE c.text CONTAINS $keywords OR d.filename CONTAINS $keywords
    RETURN DISTINCT d.doc_id
    """
    candidate_docs = neo4j.run(graph_query, matter_id=matter_id, keywords=query)
    
    # Step 2: Vector search within candidates
    embedding = embed_query(query)
    chunks = pgvector.similarity_search(
        embedding=embedding,
        filter={"doc_id": {"$in": candidate_docs}},
        top_k=top_k
    )
    
    return chunks
```

### 3.1.3 Current Query Workflow

**File: `backend/app/workflow.py`**

```python
class QueryWorkflow:
    """Current LangGraph-style workflow."""
    
    async def run_query(self, matter_id: str, query: str, user_id: str):
        # State initialization
        state = WorkflowState(
            matter_id=matter_id,
            query=query,
            user_id=user_id
        )
        
        # Step 1: ACL check
        state = await self.acl_check_step(state)
        if not state.authorized:
            return {"error": "Unauthorized"}
        
        # Step 2: Entity extraction
        state = await self.extract_entities_step(state)
        
        # Step 3: Graph retrieval
        state = await self.graph_retrieval_step(state)
        
        # Step 4: Vector search
        state = await self.vector_search_step(state)
        
        # Step 5: LLM generation (Gemini)
        state = await self.llm_generation_step(state)
        
        # Step 6: Citation validation
        state = await self.citation_validation_step(state)
        
        # Step 7: Audit logging
        await self.audit_log_step(state)
        
        return {
            "answer": state.answer,
            "citations": state.citations,
            "abstained": state.abstained,
            "confidence": state.confidence,
            "retrieval_trace": state.retrieval_trace
        }
```

### 3.1.4 Current ACL Implementation

**File: `backend/app/auth.py`**

```python
# Matter-scoped access control
USER_MATTERS = {
    "alice": ["matter-1", "matter-3"],
    "bob": ["matter-2"],
    # Loaded from environment variable LAW_RAG_USER_MATTERS
}

def check_access(user_id: str, matter_id: str) -> bool:
    """Verify user has access to matter."""
    authorized_matters = USER_MATTERS.get(user_id, [])
    return matter_id in authorized_matters
```

### 3.1.5 Current Evaluation Harness

**File: `backend/app/cli_eval.py`**

```python
# CLI: law-rag-eval

def evaluate_system():
    """Run evaluation on golden set."""
    
    # Load golden set
    golden_set = load_dataset("eval/golden_set.jsonl")
    
    metrics = {
        "retrieval": {
            "recall@5": 0.0,
            "recall@10": 0.0,
            "mrr": 0.0
        },
        "grounding": {
            "citation_coverage": 0.0,
            "unsupported_claim_rate": 0.0
        }
    }
    
    for item in golden_set:
        result = query_workflow.run(
            matter_id=item['matter_id'],
            query=item['query']
        )
        
        # Calculate metrics
        metrics["retrieval"]["recall@10"] = calculate_recall(
            retrieved=result['retrieval_trace'],
            ground_truth=item['controlling_anchors']
        )
        
        metrics["grounding"]["citation_coverage"] = validate_citations(
            answer=result['answer'],
            citations=result['citations']
        )
    
    return metrics
```

---

# 4. Enhanced System Architecture (Post Fine-Tuning)

## 4.1 New Components (Phase 1 Additions)

| Component | Technology | Purpose | Status |
|-----------|-----------|---------|--------|
| **Fine-tuned LLM** | Llama 3.1 70B + LoRA | Bilingual legal reasoning | 🔄 To implement |
| **vLLM Server** | vLLM (inference engine) | Fast model serving | 🔄 To implement |
| **Dataset Builder** | Python scripts | JP/US legal data preparation | 🔄 To implement |
| **Training Pipeline** | Axolotl + Hugging Face | LoRA fine-tuning workflow | 🔄 To implement |
| **Bilingual Eval** | Custom metrics | JP/EN performance testing | 🔄 To implement |

## 4.2 Modified Workflow (With Fine-Tuned LLM)

```python
# backend/app/workflow.py (Enhanced)

class EnhancedQueryWorkflow(QueryWorkflow):
    """Enhanced workflow with fine-tuned LLM."""
    
    def __init__(self):
        super().__init__()
        
        # Replace Gemini with fine-tuned Llama
        self.llm_service = FineTunedLlamaService(
            model_path="models/jp-us-legal-llama-70b-lora",
            inference_url="http://localhost:8001"  # vLLM server
        )
    
    async def llm_generation_step(self, state: WorkflowState):
        """Generate answer using fine-tuned model."""
        
        # Format context (same as before)
        context = self._format_context(state.retrieved_chunks)
        
        # System prompt (bilingual)
        system_prompt = self._get_bilingual_system_prompt(
            detected_language=state.query_language
        )
        
        # Call fine-tuned model
        response = await self.llm_service.generate(
            system_prompt=system_prompt,
            context=context,
            query=state.query,
            temperature=0.1,  # Low temp for consistency
            max_tokens=2048
        )
        
        state.answer = response['answer']
        state.raw_llm_output = response['raw_output']
        
        return state
    
    def _get_bilingual_system_prompt(self, detected_language: str):
        """Get appropriate system prompt based on query language."""
        
        if detected_language == "ja":
            return """あなたは日本法と米国法に精通した法律リサーチアシスタントです。

重要なルール:
1. すべての実質的な記述は[N]で引用
2. 証拠不十分の場合は明示的に「証拠不十分」と記載
3. 正確な法律用語を使用
4. 構成: 回答 + 引用ブロック"""
        else:
            return """You are a legal research assistant specialized in Japanese and US corporate law.

CRITICAL RULES:
1. Every substantive statement must cite source using [N]
2. If evidence insufficient, explicitly state "Insufficient evidence"
3. Use precise legal language
4. Structure: Answer + Citation block"""
```

## 4.3 Enhanced Graph Schema (Optional Enhancements)

```cypher
// Additional nodes for cross-border context

(:Jurisdiction {code: "JP" | "US", name})
(:LawComparison {
    topic,
    jp_provision,
    us_provision,
    key_difference,
    practical_impact
})
(:ContractClause {
    clause_id,
    clause_type,
    language: "ja" | "en",
    translation_pair_id  // Links JP/EN versions
})

// New relationships
(Statute)-[:GOVERNED_BY]->(Jurisdiction)
(LawComparison)-[:COMPARES {jp_ref, us_ref}]->(Statute)
(ContractClause)-[:PARALLEL_VERSION]->(ContractClause)
```

---

# 5. Functional Requirements

## 5.1 Core Features (Must Have - Phase 1)

### FR-001: Bilingual Query Processing

**Description:** System must accept queries in Japanese or English and respond in the same language.

**Acceptance Criteria:**
- ✅ Automatically detect query language (JP/EN)
- ✅ Return answer in same language as query
- ✅ Maintain consistent citation format across languages
- ✅ Handle mixed-language queries (e.g., English question about Japanese statute)

**Example:**
```
Input (EN): "What is the payment term in this contract?"
Output (EN): "The payment term is 30 days. [1]..."

Input (JA): "この契約における支払条件は？"
Output (JA): "支払条件は30日です。[1]..."
```

---

### FR-002: Citation-Backed Answers

**Description:** Every substantive statement must be supported by specific document citations.

**Acceptance Criteria:**
- ✅ Answer contains citation markers [1], [2], [3]...
- ✅ Citation block lists: document name, section, page
- ✅ Citations map to specific chunks from retrieval
- ✅ No unsupported claims in answer text

**Example:**
```
Answer: "The termination notice period is 60 days. [1] 
         Either party may terminate. [1]

Citation:
[1] Service Agreement §8.1, p.12"
```

**Validation:**
- Citation [1] must correspond to chunk containing "60 days" and "termination"
- If claim not in context → system must abstain

---

### FR-003: Abstain on Insufficient Evidence

**Description:** System must explicitly state when evidence is insufficient rather than guessing.

**Acceptance Criteria:**
- ✅ Detect when query cannot be answered from provided context
- ✅ Return `abstained: true` flag
- ✅ Explain why evidence is insufficient
- ✅ Do not hallucinate information

**Example:**
```
Query: "What is the payment term?"
Context: [contains termination clause, no payment terms]

Answer: "Insufficient evidence. The provided contract excerpt 
         contains termination provisions [1] but does not specify 
         payment terms. Additional contract sections would be needed."

abstained: true
```

---

### FR-004: GraphRAG Retrieval

**Description:** Use knowledge graph + vector search hybrid approach for intelligent retrieval.

**Acceptance Criteria:**
- ✅ Neo4j graph query identifies candidate documents
- ✅ Vector search (pgvector) finds relevant chunks within candidates
- ✅ Results filtered by matter-scoped ACL
- ✅ Return top 10 most relevant chunks

**Graph Query Example:**
```cypher
// Find documents related to "payment terms" in matter-1
MATCH (m:Matter {matter_id: "matter-1"})-[:HAS_DOCUMENT]->(d:Document)
WHERE d.filename CONTAINS "agreement" OR d.tags CONTAINS "contract"
MATCH (d)-[:CONTAINS]->(c:Chunk)
WHERE c.text CONTAINS "payment" OR c.text CONTAINS "invoice"
RETURN c.chunk_id, c.text, c.anchor
LIMIT 50  // Pass to vector search
```

---

### FR-005: Matter-Scoped Access Control

**Description:** All queries and retrievals must respect matter-level permissions.

**Acceptance Criteria:**
- ✅ User authentication via header (X-User-Id)
- ✅ Verify user authorized for requested matter_id
- ✅ Retrieval only returns chunks from authorized matters
- ✅ Log all access attempts (authorized + denied)

**Implementation:**
```python
# Before any retrieval
if not check_access(user_id, matter_id):
    audit_log(event="access_denied", user=user_id, matter=matter_id)
    return {"error": "Unauthorized access to matter"}

# All DB queries filtered by matter_id
chunks = db.query(Chunk).filter(
    Chunk.doc_id.in_(
        db.query(Document.id).filter(
            Document.matter_id == matter_id
        )
    )
)
```

---

### FR-006: Document Ingestion (Existing Feature)

**Description:** Upload and process PDF/DOCX documents with anchor extraction.

**Acceptance Criteria:**
- ✅ Accept PDF and DOCX uploads via API
- ✅ Extract text with page/section anchors
- ✅ Chunk documents semantically (by headings, clauses)
- ✅ Generate embeddings and store in pgvector
- ✅ Extract entities and update Neo4j graph

**API Endpoint:**
```
POST /v1/documents/upload
Headers: X-User-Id: alice
Form Data:
  - file: contract.pdf
  - matter_id: matter-1

Response:
{
  "doc_id": "doc-abc123",
  "filename": "contract.pdf",
  "chunks_created": 45,
  "entities_extracted": ["Party A", "Party B", "Section 3.2"]
}
```

---

### FR-007: Cross-Border Legal Analysis

**Description:** Answer questions comparing Japanese and US law.

**Acceptance Criteria:**
- ✅ Retrieve relevant provisions from both jurisdictions
- ✅ Provide comparative analysis in answer
- ✅ Cite both JP and US sources appropriately
- ✅ Maintain language consistency (answer in query language)

**Example:**
```
Query (EN): "How do director duties differ between Japan and Delaware?"

Answer: "Japanese Companies Act requires directors to fulfill 
         both duty of care and duty of loyalty [1], similar to 
         Delaware law [2]. However, Japan mandates a statutory 
         auditor (kansayaku) system for large companies [1], 
         whereas Delaware uses board committees [2].

Citations:
[1] Companies Act (会社法) Article 355
[2] Delaware General Corporation Law §141"
```

---

## 5.2 Enhanced Features (Should Have - Phase 2)

### FR-008: Multi-Document Synthesis

**Description:** Answer questions requiring synthesis across multiple documents.

**Example:** "Summarize all indemnification provisions across our acquisition agreements from 2024."

---

### FR-009: Retrieval Trace Visualization

**Description:** Show users which documents/chunks were consulted.

**UI Mockup:**
```
Answer: [main answer here]

Sources Consulted:
✓ Service Agreement §3.2 (Payment Terms)
✓ Amendment No. 1 §2.1 (Modified Payment Schedule)
✗ Master Agreement §5.4 (Not relevant - Termination)
```

---

### FR-010: Confidence Scoring

**Description:** Provide numerical confidence score (0.0-1.0) for answers.

**Factors:**
- Retrieval score (how well chunks match query)
- Citation coverage (% of answer text with citations)
- Conflicting information (lower confidence if contradictory sources)

---

## 5.3 Future Enhancements (Nice to Have - Phase 3+)

### FR-011: Legal Memo Generation

**Description:** Generate full legal memos with multi-section analysis.

---

### FR-012: Precedent Search

**Description:** Find similar past queries and reuse analysis.

---

### FR-013: Real-Time Legal Updates

**Description:** Monitor e-Gov API and SEC EDGAR for relevant law changes.

---

# 6. Non-Functional Requirements

## 6.1 Performance Requirements

| Requirement | Target | Measurement |
|-------------|--------|-------------|
| **Query Response Time** | <3 seconds (p95) | Time from API request to complete response |
| **Document Ingestion** | <30 seconds for 50-page PDF | Upload to embeddings complete |
| **Concurrent Users** | 50 simultaneous queries | Without degradation |
| **Retrieval Latency** | <500ms | GraphRAG + vector search |
| **LLM Inference** | <2 seconds | Answer generation time |

---

## 6.2 Scalability Requirements

| Requirement | Target | Implementation |
|-------------|--------|----------------|
| **Document Corpus** | 100,000 documents | PostgreSQL sharding if needed |
| **Graph Nodes** | 1M nodes, 5M edges | Neo4j clustering for large graphs |
| **Concurrent Queries** | 200 queries/min | Load balancer + multiple vLLM instances |
| **Storage Growth** | 1TB/year | Cloud storage with auto-scaling |

---

## 6.3 Security Requirements

### SEC-001: Data Encryption

- ✅ TLS 1.3 for all API communications
- ✅ At-rest encryption for PostgreSQL and Neo4j
- ✅ Encrypted storage for document files

### SEC-002: Authentication & Authorization

- ✅ Integration with law firm SSO (SAML/OIDC)
- ✅ Role-based access control (RBAC)
- ✅ Matter-level permissions (no cross-matter access)
- ✅ Audit trail for all queries and access attempts

### SEC-003: Data Privacy

- ✅ No logging of sensitive document content (only IDs/anchors)
- ✅ Compliance with attorney-client privilege
- ✅ User data anonymization in analytics
- ✅ GDPR/CCPA compliance for user data

### SEC-004: Prompt Injection Defense

- ✅ Treat all document text as untrusted input
- ✅ Sanitize user queries for malicious prompts
- ✅ LLM system prompt enforcement (cannot be overridden by user/documents)

---

## 6.4 Reliability Requirements

| Requirement | Target | Implementation |
|-------------|--------|----------------|
| **Uptime** | 99.5% (business hours) | Load balancing, health checks |
| **Data Backup** | Daily backups, 30-day retention | Automated backup to S3/equivalent |
| **Disaster Recovery** | RTO: 4 hours, RPO: 1 hour | Multi-region deployment |
| **Graceful Degradation** | Fallback to baseline if fine-tuned model unavailable | Config flag: `LAW_RAG_LLM_FALLBACK=gemini` |

---

## 6.5 Maintainability Requirements

### MAIN-001: Code Quality

- ✅ Python type hints throughout
- ✅ 80%+ test coverage
- ✅ Linting (Ruff/Black) enforced in CI/CD
- ✅ Comprehensive docstrings

### MAIN-002: Observability

- ✅ Structured logging (JSON format)
- ✅ Metrics dashboard (query volume, latency, errors)
- ✅ Alerting for critical failures
- ✅ Distributed tracing for debugging

### MAIN-003: Versioning

- ✅ Model versioning (track which LLM version answered each query)
- ✅ API versioning (/v1/, /v2/)
- ✅ Database migration system (Alembic)

---

## 6.6 Compliance Requirements

### COMP-001: Professional Responsibility

- ✅ System labeled as "research assistant" not "legal advice"
- ✅ "Attorney review required" watermark on outputs
- ✅ No autonomous decision-making without human review

### COMP-002: Ethical Walls

- ✅ Strict matter-scoped access control
- ✅ No cross-matter information leakage
- ✅ Audit logs for conflict checks

### COMP-003: Accuracy Validation

- ✅ Regular evaluation against golden set
- ✅ Human attorney review of random sample (10% of queries/month)
- ✅ User feedback mechanism (thumbs up/down)

---

# 7. Data Requirements

## 7.1 Training Data (Phase 1)

### 7.1.1 Dataset Composition

| Tier | Source | Examples | Language | Purpose |
|------|--------|----------|----------|---------|
| **US Law (45%)** | | **1,800** | EN | |
| | CUAD | 600 | EN | US contract analysis |
| | Edgar-Corpus | 300 | EN | Securities law |
| | LegalBench | 400 | EN | Legal reasoning |
| | CaseHOLD | 200 | EN | US case law |
| | ContractNLI | 150 | EN | Contract interpretation |
| | BillSum | 150 | EN | Regulatory context |
| **Japanese Law (45%)** | | **1,800** | JA | |
| | JLawText | 500 | JA | Japanese statutes |
| | e-Gov API | 400 | JA | Current laws |
| | JCourts | 300 | JA | Japanese case law |
| | Courts.go.jp | 200 | JA | Supreme Court |
| | FSA Guidelines | 200 | JA | Financial regulations |
| | Contract templates | 200 | JA | Japanese contracts |
| **Cross-Border (10%)** | | **400** | JP/EN | |
| | Parallel contracts | 200 | JP/EN | Bilingual clauses |
| | Comparative law | 200 | JP/EN | Jurisdiction comparison |
| **TOTAL** | | **4,000** | | |

### 7.1.2 Data Format

**Training Example Structure:**

```json
{
  "messages": [
    {
      "role": "system",
      "content": "You are a legal research assistant..."
    },
    {
      "role": "user",
      "content": "Context:\n[1] Document excerpt...\n\nQuestion: ..."
    },
    {
      "role": "assistant",
      "content": "Answer with citations [1]...\n\nCitation:\n[1] Source"
    }
  ],
  "metadata": {
    "source": "CUAD",
    "language": "en",
    "jurisdiction": "US",
    "topic": "payment_terms"
  }
}
```

### 7.1.3 Data Quality Requirements

| Criterion | Target | Validation Method |
|-----------|--------|-------------------|
| **Citation accuracy** | 100% | Every citation must reference valid source |
| **Language consistency** | 100% | Answer language matches query language |
| **No hallucinations** | 100% | All claims supported by context |
| **Format compliance** | 95% | Follows citation template |
| **Deduplication** | <1% duplicates | Hash-based duplicate detection |

---

## 7.2 Operational Data (Production)

### 7.2.1 Document Storage

**PostgreSQL Tables:**

```sql
-- Document metadata
CREATE TABLE documents (
    id UUID PRIMARY KEY,
    matter_id VARCHAR(255) NOT NULL,
    filename VARCHAR(1024),
    upload_date TIMESTAMP,
    file_size_bytes BIGINT,
    file_hash VARCHAR(64),  -- SHA-256
    num_pages INT,
    language VARCHAR(10),  -- 'en', 'ja', 'mixed'
    INDEX idx_matter (matter_id)
);

-- Extracted chunks
CREATE TABLE chunks (
    id UUID PRIMARY KEY,
    doc_id UUID REFERENCES documents(id),
    chunk_index INT,
    text TEXT,
    anchor VARCHAR(512),  -- e.g., "Contract §3.2, p.4"
    page_number INT,
    section_title VARCHAR(512),
    embedding vector(1536),  -- pgvector
    INDEX idx_doc (doc_id),
    INDEX idx_embedding USING ivfflat (embedding vector_cosine_ops)
);

-- Audit logs
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    user_id VARCHAR(255),
    matter_id VARCHAR(255),
    query_text TEXT,
    answer_id UUID,
    access_granted BOOLEAN,
    retrieval_method VARCHAR(50),  -- 'graph_rag', 'vector_only'
    num_chunks_retrieved INT,
    llm_model_version VARCHAR(100),
    response_time_ms INT,
    INDEX idx_timestamp (timestamp),
    INDEX idx_user (user_id),
    INDEX idx_matter (matter_id)
);
```

### 7.2.2 Graph Data

**Neo4j Schema (Extended):**

```cypher
// Core entities
CREATE CONSTRAINT matter_id IF NOT EXISTS FOR (m:Matter) REQUIRE m.matter_id IS UNIQUE;
CREATE CONSTRAINT doc_id IF NOT EXISTS FOR (d:Document) REQUIRE d.doc_id IS UNIQUE;
CREATE CONSTRAINT chunk_id IF NOT EXISTS FOR (c:Chunk) REQUIRE c.chunk_id IS UNIQUE;

// Indexes
CREATE INDEX matter_practice FOR (m:Matter) ON (m.practice_area);
CREATE INDEX doc_language FOR (d:Document) ON (d.language);
CREATE INDEX statute_jurisdiction FOR (s:Statute) ON (s.jurisdiction);

// Sample data
CREATE (m:Matter {
    matter_id: 'matter-001',
    name: 'ABC Corp - Tokyo IPO',
    practice_area: 'Securities',
    jurisdiction: 'JP-US'
})

CREATE (d:Document {
    doc_id: 'doc-123',
    filename: 'Underwriting_Agreement.pdf',
    language: 'en',
    upload_date: datetime()
})

CREATE (m)-[:HAS_DOCUMENT]->(d)
```

---

## 7.3 Evaluation Data

### 7.3.1 Golden Set Structure

**File: `eval/golden_set.jsonl`**

```json
{
  "question_id": "q-001",
  "matter_id": "test-matter-1",
  "query": "What is the payment term?",
  "language": "en",
  "jurisdiction": "US",
  "controlling_anchors": [
    "Service_Agreement.pdf#page=4#section=3.2",
    "Amendment_1.pdf#page=2#section=2.1"
  ],
  "expected_answer_contains": ["30 days", "invoice date"],
  "difficulty": "easy",  // easy, medium, hard
  "question_type": "factual_extraction"  // factual, analysis, comparison
}
```

### 7.3.2 Evaluation Metrics

| Category | Metric | Formula | Target |
|----------|--------|---------|--------|
| **Retrieval** | Recall@10 | (Relevant in top 10) / (Total relevant) | >90% |
| | MRR | 1 / rank of first relevant | >0.80 |
| **Grounding** | Citation coverage | (Sentences with citations) / (Total sentences) | >95% |
| | Hallucination rate | (Unsupported claims) / (Total claims) | <5% |
| **Quality** | Answer completeness | Human rating (1-5 scale) | >4.0 |
| | Bilingual consistency | BLEU score (JP↔EN translation) | >0.75 |

---

# 8. Technical Specifications

## 8.1 System Components

### 8.1.1 Backend Stack

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Language** | Python | 3.11+ | Core application |
| **API Framework** | FastAPI | 0.100+ | RESTful API |
| **ASGI Server** | Uvicorn | 0.23+ | Production server |
| **Database** | PostgreSQL | 15+ | Document metadata |
| **Vector Extension** | pgvector | 0.5+ | Embeddings |
| **Graph DB** | Neo4j | 5.0+ | Knowledge graph |
| **LLM (Baseline)** | Google Gemini | 1.5 Pro | Initial system |
| **LLM (Fine-tuned)** | Llama 3.1 70B | + LoRA | Production system |
| **Inference Engine** | vLLM | 0.3+ | Fast LLM serving |
| **Task Queue** | Celery (optional) | 5.3+ | Async document processing |
| **Cache** | Redis (optional) | 7.0+ | Query result caching |

### 8.1.2 Frontend Stack

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Framework** | Next.js | 14+ | React-based UI |
| **Language** | TypeScript | 5.0+ | Type safety |
| **Styling** | Tailwind CSS | 3.0+ | UI styling |
| **State Management** | React Query | 5.0+ | API state |
| **Internationalization** | next-i18next | 14+ | JP/EN language switching |

### 8.1.3 Infrastructure

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Containerization** | Docker | Deployment packaging |
| **Orchestration** | Docker Compose (dev), Kubernetes (prod) | Service management |
| **Reverse Proxy** | Nginx | Load balancing, SSL termination |
| **Monitoring** | Prometheus + Grafana | Metrics & dashboards |
| **Logging** | ELK Stack (Elasticsearch, Logstash, Kibana) | Log aggregation |
| **CI/CD** | GitHub Actions | Automated testing & deployment |

---

## 8.2 Model Specifications

### 8.2.1 Fine-Tuned LLM Configuration

```yaml
# Model Configuration
base_model: meta-llama/Meta-Llama-3.1-70B-Instruct
model_family: Llama 3.1
parameter_count: 70 billion
context_window: 128K tokens

# Fine-Tuning Method
adapter: LoRA
lora_rank: 32
lora_alpha: 64
lora_dropout: 0.05
lora_target_modules:
  - q_proj
  - k_proj
  - v_proj
  - o_proj
  - gate_proj
  - up_proj
  - down_proj

# Quantization (for efficiency)
load_in_4bit: true
bnb_4bit_compute_dtype: bfloat16
bnb_4bit_use_double_quant: true
bnb_4bit_quant_type: nf4

# Training Hyperparameters
learning_rate: 0.0002
batch_size: 1 (micro) × 8 (gradient accumulation) = 8 (effective)
num_epochs: 3
warmup_steps: 100
weight_decay: 0.01
lr_scheduler: cosine

# Training Data
train_examples: 3,400
val_examples: 600
sequence_length: 4096 tokens
sample_packing: true
```

### 8.2.2 Inference Configuration

```yaml
# vLLM Server Settings
model_path: /models/jp-us-legal-llama-70b-lora
tensor_parallel_size: 1  # Number of GPUs
max_model_len: 4096
gpu_memory_utilization: 0.90
dtype: bfloat16

# Generation Parameters
temperature: 0.1  # Low for consistency
top_p: 0.95
max_tokens: 2048
stop_sequences: ["</answer>", "\n\n\n"]

# Performance
max_num_seqs: 16  # Concurrent requests
```

---

## 8.3 API Specifications

### 8.3.1 Query Endpoint

**Endpoint:** `POST /v1/query`

**Request:**
```json
{
  "matter_id": "matter-001",
  "query": "What is the payment term in this service agreement?",
  "language": "en",  // Optional: "en", "ja", "auto"
  "max_chunks": 10,   // Optional: default 10
  "include_trace": true  // Optional: include retrieval details
}
```

**Response:**
```json
{
  "answer": "The payment term is Net 30 days from invoice date. [1] Late payments incur a 1.5% monthly fee. [2]",
  "citations": [
    {
      "number": 1,
      "doc_id": "doc-abc123",
      "filename": "Service_Agreement.pdf",
      "anchor": "Section 3.2, Page 4",
      "text_excerpt": "Payment shall be made within thirty (30) days..."
    },
    {
      "number": 2,
      "doc_id": "doc-abc123",
      "filename": "Service_Agreement.pdf",
      "anchor": "Section 3.3, Page 4",
      "text_excerpt": "Late payments will incur interest at 1.5% per month..."
    }
  ],
  "abstained": false,
  "confidence": 0.92,
  "language": "en",
  "retrieval_trace": {
    "graph_query_time_ms": 45,
    "vector_search_time_ms": 120,
    "num_candidates": 30,
    "num_retrieved": 10,
    "chunks_used": [
      {"chunk_id": "chunk-xyz", "rank": 1, "score": 0.89},
      {"chunk_id": "chunk-def", "rank": 2, "score": 0.85}
    ]
  },
  "metadata": {
    "query_id": "query-f47ac10b",
    "timestamp": "2026-03-05T10:30:00Z",
    "model_version": "jp-us-legal-v1.0",
    "response_time_ms": 2340
  }
}
```

### 8.3.2 Document Upload Endpoint

**Endpoint:** `POST /v1/documents/upload`

**Request:**
```
Content-Type: multipart/form-data

Headers:
  X-User-Id: alice

Body:
  file: [binary PDF/DOCX]
  matter_id: matter-001
  language: auto  // Optional: "en", "ja", "auto"
```

**Response:**
```json
{
  "doc_id": "doc-abc123",
  "filename": "Service_Agreement.pdf",
  "upload_timestamp": "2026-03-05T10:30:00Z",
  "processing_status": "completed",
  "stats": {
    "num_pages": 24,
    "num_chunks": 87,
    "language_detected": "en",
    "entities_extracted": {
      "parties": ["Acme Corp", "Beta Inc"],
      "defined_terms": ["Services", "Confidential Information"],
      "statutes_referenced": []
    }
  },
  "graph_updates": {
    "nodes_created": 92,
    "relationships_created": 156
  }
}
```

---

## 8.4 Data Models

### 8.4.1 Core Models (SQLAlchemy)

**File: `backend/app/models.py`**

```python
from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import relationship
import uuid

class Matter(Base):
    __tablename__ = "matters"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    matter_id = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(1024))
    practice_area = Column(String(255))  # 'Corporate', 'Securities', 'IP', etc.
    jurisdiction = Column(String(50))    # 'US', 'JP', 'JP-US'
    created_at = Column(DateTime, nullable=False)
    
    # Relationships
    documents = relationship("Document", back_populates="matter")

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    doc_id = Column(String(255), unique=True, nullable=False, index=True)
    matter_id = Column(String(255), ForeignKey("matters.matter_id"), nullable=False)
    filename = Column(String(1024))
    file_hash = Column(String(64))  # SHA-256
    language = Column(String(10))    # 'en', 'ja', 'mixed'
    upload_date = Column(DateTime, nullable=False)
    num_pages = Column(Integer)
    metadata = Column(JSONB)  # Flexible storage for additional metadata
    
    # Relationships
    matter = relationship("Matter", back_populates="documents")
    chunks = relationship("Chunk", back_populates="document")

class Chunk(Base):
    __tablename__ = "chunks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chunk_id = Column(String(255), unique=True, nullable=False, index=True)
    doc_id = Column(String(255), ForeignKey("documents.doc_id"), nullable=False)
    chunk_index = Column(Integer)
    text = Column(Text, nullable=False)
    anchor = Column(String(512))  # "Contract §3.2, p.4"
    page_number = Column(Integer)
    section_title = Column(String(512))
    language = Column(String(10))
    embedding = Column(Vector(1536))  # pgvector for similarity search
    
    # Relationships
    document = relationship("Document", back_populates="chunks")

class QueryLog(Base):
    __tablename__ = "query_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query_id = Column(String(255), unique=True, nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    matter_id = Column(String(255), nullable=False, index=True)
    query_text = Column(Text)
    query_language = Column(String(10))  # 'en', 'ja'
    answer_text = Column(Text)
    abstained = Column(Boolean)
    confidence = Column(Float)
    num_citations = Column(Integer)
    retrieval_method = Column(String(50))
    model_version = Column(String(100))
    response_time_ms = Column(Integer)
    chunks_retrieved = Column(JSONB)  # List of chunk_ids
```

---

# 9. Implementation Roadmap

## 9.1 Phase 1: Dataset Preparation & Fine-Tuning (8 Weeks)

### Week 1-2: Dataset Collection (Easy Sources)

**Deliverables:**
- ✅ 1,000 examples from CUAD (US contracts)
- ✅ 500 examples from JLawText (Japanese statutes)
- ✅ Dataset preparation scripts operational

**Tasks:**
```bash
# Week 1
- Setup development environment
- Install Hugging Face datasets library
- Create master dataset builder script
- Download and prepare CUAD (600 examples)
- Download and prepare LegalBench (400 examples)

# Week 2
- Download and prepare JLawText (500 examples)
- Download and prepare JCourts (200 examples)
- Create bilingual validation script
- Initial quality control checks
```

**Success Criteria:**
- 1,500 examples in correct JSON format
- No duplicates detected
- Language tags accurate (en/ja)
- Citation format validated

---

### Week 3-4: Dataset Collection (Medium/Hard Sources)

**Deliverables:**
- ✅ Additional 1,500 examples from SEC EDGAR, e-Gov API, FSA
- ✅ Cross-border examples created

**Tasks:**
```bash
# Week 3
- Implement e-Gov API scraper
- Collect 400 examples from current Japanese laws
- Scrape SEC EDGAR for 300 corporate filing examples
- Create parallel contract database (100 examples)

# Week 4
- Collect FSA guidelines (200 examples)
- Create comparative law examples (200 examples)
- Synthetic data generation (200 examples)
- Final dataset assembly and split (train/val)
```

**Success Criteria:**
- 3,000+ total examples ready
- 85/15 train/val split complete
- All metadata fields populated
- Quality threshold met (>95% format compliance)

---

### Week 5-6: Cross-Border Data & Final Prep

**Deliverables:**
- ✅ 400 cross-border examples (parallel contracts, comparative law)
- ✅ Complete 4,000 example dataset
- ✅ Dataset documented and versioned

**Tasks:**
```bash
# Week 5
- Finalize parallel contract pairs (JP↔EN)
- Create bilingual Q&A examples
- Comparative law analysis examples
- Dataset deduplication

# Week 6
- Final quality control (manual review of 5% sample)
- Dataset documentation
- Create dataset statistics report
- Upload to Hugging Face Hub (private repo)
```

**Success Criteria:**
- 4,000 examples total (3,400 train, 600 val)
- Balanced distribution: 45% US, 45% JP, 10% cross-border
- Zero duplicates
- Dataset README complete

---

### Week 7: Training Infrastructure Setup

**Deliverables:**
- ✅ Cloud GPU provisioned (Lambda Labs or RunPod)
- ✅ Axolotl installed and configured
- ✅ Training config tested

**Tasks:**
```bash
# Setup cloud GPU
- Create Lambda Labs account
- Provision A100 (40GB) instance
- Setup SSH access and environment

# Install dependencies
- Clone Axolotl repository
- Install training dependencies
- Download base Llama 3.1 70B model
- Test with small training run (10 examples)

# Configuration
- Create training YAML config
- Set hyperparameters
- Configure Weights & Biases logging
- Setup model checkpointing
```

**Success Criteria:**
- Successfully train on 10 examples (test run)
- W&B logging functional
- GPU utilization >85%
- No OOM errors

---

### Week 8: Model Training & Validation

**Deliverables:**
- ✅ Fine-tuned Llama 3.1 70B model with LoRA adapters
- ✅ Training metrics logged
- ✅ Initial evaluation complete

**Tasks:**
```bash
# Training
- Start full training run (3 epochs, ~6-8 hours)
- Monitor training loss and validation loss
- Save checkpoints every 100 steps
- Download trained LoRA adapters

# Initial Evaluation
- Load fine-tuned model
- Run on validation set (600 examples)
- Calculate metrics:
  * Citation rate
  * Format compliance
  * Bilingual consistency
- Compare to baseline (pre-fine-tuning)

# Model Export
- Merge LoRA adapters (optional)
- Create model card
- Upload to Hugging Face Hub (private)
```

**Success Criteria:**
- Training loss converges smoothly
- Validation loss doesn't diverge (no overfitting)
- Citation rate >85% (vs. baseline ~50%)
- Model successfully loads for inference

**Cost Estimate:** ~$11 (8 hours on A100)

---

## 9.2 Phase 2: Integration & Deployment (4 Weeks)

### Week 9-10: vLLM Setup & Integration

**Deliverables:**
- ✅ vLLM server running fine-tuned model
- ✅ Backend integrated with vLLM
- ✅ API endpoints updated

**Tasks:**
```bash
# vLLM Setup
- Install vLLM on GPU server
- Load fine-tuned Llama model
- Configure inference parameters
- Test inference speed (target: <2s per query)

# Backend Integration
- Modify app/llm.py to support vLLM endpoint
- Add fallback to Gemini (for reliability)
- Update workflow.py to use fine-tuned model
- Add model version tracking in audit logs

# Testing
- Run 100 test queries (50 JP, 50 EN)
- Verify citation format
- Check bilingual consistency
- Load testing (concurrent queries)
```

**Success Criteria:**
- vLLM serving functional
- Inference latency <2 seconds (p95)
- Fallback to Gemini works if vLLM unavailable
- All existing tests pass

---

### Week 11-12: Evaluation & Quality Assurance

**Deliverables:**
- ✅ Comprehensive evaluation report
- ✅ A/B test results (fine-tuned vs. baseline)
- ✅ User acceptance testing

**Tasks:**
```bash
# Automated Evaluation
- Run law-rag-eval on golden set
- Measure retrieval metrics (Recall@10, MRR)
- Measure grounding metrics (citation coverage)
- Generate evaluation report

# A/B Testing
- Create comparison script
- Run same 100 queries through:
  * Baseline (Gemini)
  * Fine-tuned (Llama 3.1 70B)
- Blind review by 2-3 test users
- Collect preference votes

# Quality Assurance
- Test edge cases (ambiguous queries, multilingual)
- Verify ACL enforcement
- Stress test (concurrent load)
- Security audit (prompt injection attempts)
```

**Success Criteria:**
- Recall@10 >90% (vs. baseline 78%)
- Citation accuracy >95% (vs. baseline 85%)
- User preference for fine-tuned model >60%
- No security vulnerabilities found

---

### Week 13-16: Production Deployment

**Deliverables:**
- ✅ Production environment configured
- ✅ System deployed and monitored
- ✅ User documentation complete

**Tasks:**
```bash
# Infrastructure
- Setup production Kubernetes cluster (or Docker Compose)
- Deploy PostgreSQL, Neo4j, vLLM
- Configure Nginx reverse proxy with SSL
- Setup monitoring (Prometheus, Grafana)

# Deployment
- Deploy backend API
- Deploy frontend UI
- Configure environment variables
- Run smoke tests

# Documentation
- Write user guide (JP/EN)
- Create API documentation (Swagger)
- Record demo video
- Setup support channels

# Go-Live
- Pilot with 5-10 users (2 weeks)
- Collect feedback
- Iterate on issues
- Full rollout
```

**Success Criteria:**
- System accessible via HTTPS
- 99% uptime during pilot
- <3 second query response time
- Positive user feedback (>4/5 rating)

---

## 9.3 Phase 3: Enhancement & Scaling (Ongoing)

### Months 5-6: Attorney Review & Data Collection

**Objective:** Collect 500+ attorney-reviewed examples to improve model quality.

**Process:**
1. Partners review AI-generated answers (15 min/day)
2. Corrections logged in review interface
3. Fine-tune new model version monthly
4. Continuous quality improvement

---

### Months 7-12: Feature Expansion

**Planned Features:**
- Multi-document synthesis
- Legal memo generation
- Precedent search (similar past queries)
- Real-time legal update monitoring (e-Gov, SEC)
- Mobile app (iOS/Android)

---

## 9.4 Gantt Chart Summary

```
Week    1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16
Phase 1 [====Data Collection====] [T][===Training===]
Phase 2                                    [Integration][Eval][Deploy]
Phase 3                                                        [Ongoing→]

Legend:
[=] Dataset preparation
[T] Training infrastructure setup
[Integration] vLLM + backend integration
[Eval] Evaluation and QA
[Deploy] Production deployment
```

---

# 10. Evaluation & Success Criteria

## 10.1 Evaluation Framework

### 10.1.1 Automated Metrics (Quantitative)

**A. Retrieval Quality**

| Metric | Formula | Baseline | Target | Priority |
|--------|---------|----------|--------|----------|
| **Recall@5** | (Relevant chunks in top 5) / (Total relevant) | 65% | 80% | High |
| **Recall@10** | (Relevant chunks in top 10) / (Total relevant) | 78% | 90% | Critical |
| **MRR** | Mean reciprocal rank of first relevant chunk | 0.72 | 0.85 | High |
| **Precision@10** | (Relevant chunks in top 10) / 10 | 0.60 | 0.75 | Medium |

**B. Answer Quality**

| Metric | Formula | Baseline | Target | Priority |
|--------|---------|----------|--------|----------|
| **Citation coverage** | (Sentences with citations) / (Total sentences) | 75% | 95% | Critical |
| **Hallucination rate** | (Unsupported claims) / (Total claims) | 15% | <5% | Critical |
| **Abstain accuracy** | (Correct abstains) / (Should abstain cases) | 60% | 85% | High |
| **Format compliance** | (Correct citation format) / (Total citations) | 80% | 95% | Medium |

**C. Bilingual Performance**

| Metric | Description | Target | Priority |
|--------|-------------|--------|----------|
| **Language detection** | Accuracy of detecting query language | >98% | High |
| **Response language match** | % queries answered in correct language | 100% | Critical |
| **JP/EN semantic consistency** | BLEU score for parallel queries | >0.75 | Medium |
| **Cross-border accuracy** | Correct comparative law analysis | >80% | High |

---

### 10.1.2 Human Evaluation (Qualitative)

**A. Attorney Rating Scale (1-5)**

| Score | Criteria |
|-------|----------|
| **5** | Perfect answer - accurate, complete, well-cited, ready to use |
| **4** | Good answer - minor edits needed, all key points covered |
| **3** | Acceptable - correct but incomplete or awkwardly phrased |
| **2** | Poor - significant errors or missing key information |
| **1** | Unusable - hallucinations, wrong citations, or completely off-topic |

**B. Evaluation Dimensions**

| Dimension | Weight | Measurement |
|-----------|--------|-------------|
| **Accuracy** | 40% | Are all factual statements correct? |
| **Completeness** | 25% | Does answer address all aspects of query? |
| **Citation quality** | 20% | Are citations precise and properly formatted? |
| **Clarity** | 10% | Is answer easy to understand? |
| **Usefulness** | 5% | Would this save attorney time? |

**C. Sample Size**

- **Monthly review:** 100 random queries (50 JP, 50 EN)
- **Reviewers:** 2-3 attorneys per query (inter-rater reliability)
- **Target:** Average score >4.0

---

### 10.1.3 System Performance Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| **Query response time (p50)** | <2 seconds | API endpoint timing |
| **Query response time (p95)** | <3 seconds | API endpoint timing |
| **Document ingestion time** | <30s for 50-page PDF | Upload to embeddings complete |
| **System uptime** | 99.5% | Monitoring dashboard |
| **Concurrent user capacity** | 50 users | Load testing |

---

## 10.2 Success Criteria by Phase

### Phase 1 Success (Dataset + Training)

| Criterion | Target | Status |
|-----------|--------|--------|
| Dataset size | 4,000 examples | TBD |
| Dataset balance | 45% US / 45% JP / 10% cross-border | TBD |
| Training completion | Model converges without overfitting | TBD |
| Citation rate improvement | >30% increase vs. baseline | TBD |
| Bilingual capability | Handles JP/EN queries correctly | TBD |

**Phase 1 Gate:** Must achieve training completion + >30% citation improvement to proceed to Phase 2.

---

### Phase 2 Success (Integration + Deployment)

| Criterion | Target | Status |
|-----------|--------|--------|
| vLLM deployment | Model serving at <2s latency | TBD |
| Integration testing | All API tests pass | TBD |
| Evaluation metrics | Recall@10 >90%, Citation >95% | TBD |
| User acceptance | >4.0 average rating from pilot users | TBD |
| Production readiness | System stable for 2 weeks | TBD |

**Phase 2 Gate:** Must achieve evaluation targets + positive user feedback to full rollout.

---

### Phase 3 Success (Production Operation)

| Criterion | Target | Status |
|-----------|--------|--------|
| Daily active users | >20 attorneys | TBD |
| Query volume | >100 queries/day | TBD |
| User satisfaction | >80% would recommend | TBD |
| Time savings | 30% reduction in research time (self-reported) | TBD |
| ROI | System pays for itself within 6 months | TBD |

---

## 10.3 Evaluation Scripts

### 10.3.1 Automated Evaluation CLI

**File: `backend/scripts/evaluate_comprehensive.py`**

```python
"""
Comprehensive evaluation script for Japan-US Legal AI Agent.
Measures retrieval, grounding, and bilingual performance.
"""

import json
import asyncio
from pathlib import Path
from typing import Dict, List
from datasets import load_dataset

from app.workflow import EnhancedQueryWorkflow
from app.database import SessionLocal

class ComprehensiveEvaluator:
    """Evaluate system across all metrics."""
    
    def __init__(self, golden_set_path: str = "eval/golden_set.jsonl"):
        self.golden_set = self.load_golden_set(golden_set_path)
        self.workflow = EnhancedQueryWorkflow()
        self.db = SessionLocal()
        
        self.results = {
            "retrieval": {},
            "grounding": {},
            "bilingual": {},
            "performance": {}
        }
    
    def load_golden_set(self, path: str) -> List[Dict]:
        """Load evaluation questions."""
        questions = []
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                questions.append(json.loads(line))
        return questions
    
    async def evaluate_retrieval(self) -> Dict:
        """Evaluate retrieval quality (Recall@K, MRR)."""
        
        recall_5_scores = []
        recall_10_scores = []
        mrr_scores = []
        
        for item in self.golden_set:
            # Run query
            result = await self.workflow.run_query(
                matter_id=item['matter_id'],
                query=item['query'],
                user_id='eval_system'
            )
            
            # Extract retrieved chunk anchors
            retrieved_anchors = [
                chunk['anchor'] for chunk in result['retrieval_trace']
            ]
            
            # Ground truth
            controlling_anchors = set(item['controlling_anchors'])
            
            # Calculate Recall@5
            top_5 = set(retrieved_anchors[:5])
            recall_5 = len(top_5 & controlling_anchors) / len(controlling_anchors)
            recall_5_scores.append(recall_5)
            
            # Calculate Recall@10
            top_10 = set(retrieved_anchors[:10])
            recall_10 = len(top_10 & controlling_anchors) / len(controlling_anchors)
            recall_10_scores.append(recall_10)
            
            # Calculate MRR
            for rank, anchor in enumerate(retrieved_anchors, 1):
                if anchor in controlling_anchors:
                    mrr_scores.append(1.0 / rank)
                    break
            else:
                mrr_scores.append(0.0)
        
        return {
            "recall@5": sum(recall_5_scores) / len(recall_5_scores),
            "recall@10": sum(recall_10_scores) / len(recall_10_scores),
            "mrr": sum(mrr_scores) / len(mrr_scores)
        }
    
    async def evaluate_grounding(self) -> Dict:
        """Evaluate citation quality and hallucination rate."""
        
        citation_coverage_scores = []
        hallucination_counts = []
        
        for item in self.golden_set:
            result = await self.workflow.run_query(
                matter_id=item['matter_id'],
                query=item['query'],
                user_id='eval_system'
            )
            
            answer = result['answer']
            citations = result['citations']
            
            # Parse answer into sentences
            sentences = answer.split('. ')
            
            # Count sentences with citations
            cited_sentences = sum(1 for s in sentences if '[' in s and ']' in s)
            citation_coverage = cited_sentences / len(sentences)
            citation_coverage_scores.append(citation_coverage)
            
            # Check for hallucinated citations
            provided_anchors = {chunk['anchor'] for chunk in result['retrieval_trace']}
            cited_anchors = {cite['anchor'] for cite in citations}
            
            hallucinated = cited_anchors - provided_anchors
            hallucination_counts.append(len(hallucinated))
        
        return {
            "citation_coverage": sum(citation_coverage_scores) / len(citation_coverage_scores),
            "hallucination_rate": sum(hallucination_counts) / len(hallucination_counts)
        }
    
    async def evaluate_bilingual(self) -> Dict:
        """Evaluate bilingual consistency."""
        
        language_match_count = 0
        total_queries = 0
        
        for item in self.golden_set:
            result = await self.workflow.run_query(
                matter_id=item['matter_id'],
                query=item['query'],
                user_id='eval_system'
            )
            
            query_lang = item['language']  # 'en' or 'ja'
            answer_lang = self._detect_language(result['answer'])
            
            if query_lang == answer_lang:
                language_match_count += 1
            
            total_queries += 1
        
        return {
            "language_match_rate": language_match_count / total_queries
        }
    
    def _detect_language(self, text: str) -> str:
        """Simple language detection (JP vs EN)."""
        # Count Japanese characters
        jp_chars = sum(1 for c in text if '\u3040' <= c <= '\u30ff' or '\u4e00' <= c <= '\u9fff')
        return "ja" if jp_chars > len(text) * 0.2 else "en"
    
    async def run_full_evaluation(self):
        """Run complete evaluation suite."""
        
        print("="*60)
        print("COMPREHENSIVE EVALUATION - Japan-US Legal AI Agent")
        print("="*60)
        
        # Retrieval
        print("\n[1/3] Evaluating retrieval quality...")
        self.results['retrieval'] = await self.evaluate_retrieval()
        
        # Grounding
        print("[2/3] Evaluating grounding and citations...")
        self.results['grounding'] = await self.evaluate_grounding()
        
        # Bilingual
        print("[3/3] Evaluating bilingual performance...")
        self.results['bilingual'] = await self.evaluate_bilingual()
        
        # Print results
        self.print_results()
        
        # Save results
        self.save_results()
    
    def print_results(self):
        """Print formatted results."""
        
        print("\n" + "="*60)
        print("RESULTS")
        print("="*60)
        
        print("\nRetrieval Quality:")
        print(f"  Recall@5:  {self.results['retrieval']['recall@5']:.3f}")
        print(f"  Recall@10: {self.results['retrieval']['recall@10']:.3f}")
        print(f"  MRR:       {self.results['retrieval']['mrr']:.3f}")
        
        print("\nGrounding Quality:")
        print(f"  Citation coverage:    {self.results['grounding']['citation_coverage']:.3f}")
        print(f"  Hallucination rate:   {self.results['grounding']['hallucination_rate']:.3f}")
        
        print("\nBilingual Performance:")
        print(f"  Language match rate:  {self.results['bilingual']['language_match_rate']:.3f}")
        
        print("="*60)
    
    def save_results(self):
        """Save results to JSON."""
        output_path = Path("eval/results_latest.json")
        with open(output_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\nResults saved to: {output_path}")

if __name__ == "__main__":
    evaluator = ComprehensiveEvaluator()
    asyncio.run(evaluator.run_full_evaluation())
```

**Run:**
```bash
cd backend
python scripts/evaluate_comprehensive.py
```

---

# 11. Risk Management

## 11.1 Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Model fails to converge** | Medium | High | Use proven hyperparameters, monitor training closely, have backup training runs |
| **Overfitting on training data** | Medium | High | Early stopping, validation set monitoring, diverse training data |
| **vLLM deployment issues** | Low | Medium | Thorough testing before production, fallback to Gemini API |
| **GPU availability/cost** | Medium | Medium | Use multiple cloud providers (Lambda, RunPod, Vast.ai), reserve instances |
| **Slow inference (<2s target)** | Low | Medium | Optimize vLLM config, use model quantization, add caching layer |

---

## 11.2 Data Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Insufficient training data** | Low | High | Public datasets provide 4,000 examples (sufficient for Phase 1) |
| **Data quality issues** | Medium | High | Manual review of 5% sample, automated validation scripts |
| **Copyright violations** | Low | Critical | Use only public domain/licensed datasets, document all sources |
| **Bias in training data** | Medium | Medium | Balanced JP/US distribution, diverse practice areas |
| **Data privacy breach** | Low | Critical | No client data in Phase 1, strict ACL in production |

---

## 11.3 Operational Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **User adoption low** | Medium | High | User training, clear value demonstration, iterate on feedback |
| **Hallucination in production** | Low | Critical | Citation validation, confidence scoring, human review gates |
| **System downtime** | Low | High | Load balancing, health monitoring, fallback to baseline |
| **Regulatory compliance** | Low | Critical | Legal ethics review, clear "assistant not advisor" labeling |
| **Cost overruns** | Medium | Medium | Budget tracking, optimize inference costs, consider API vs. self-hosted |

---

## 11.4 Legal/Ethical Risks

| Risk | Probability | Impact | Mitigation Strategy |
|------|-------------|--------|---------------------|
| **Unauthorized practice of law** | Low | Critical | - Clear disclaimer: "Research assistant, not legal advice"<br>- "Attorney review required" watermark<br>- No autonomous decision-making |
| **Confidentiality breach** | Low | Critical | - Matter-scoped ACL (no cross-matter access)<br>- Encryption at rest and in transit<br>- Audit logging of all access |
| **Conflict of interest** | Low | High | - Ethical wall enforcement in ACL<br>- User permission checks before retrieval<br>- Log denied access attempts |
| **Malpractice liability** | Low | Critical | - System outputs labeled as "draft"<br>- Human attorney must verify all citations<br>- Insurance coverage for AI-assisted work |
| **Data retention requirements** | Medium | Medium | - Configurable data retention policies<br>- Compliance with bar association rules<br>- Client consent for data storage |

---

## 11.5 Contingency Plans

### Contingency 1: Training Fails to Improve Model

**Trigger:** After training, fine-tuned model performs worse than baseline.

**Actions:**
1. Roll back to baseline (Gemini API)
2. Review training data for quality issues
3. Adjust hyperparameters (learning rate, LoRA rank)
4. Collect more high-quality data (prioritize attorney-reviewed examples)
5. Consider alternative base models (Llama 3.1 405B, Mistral Large)

---

### Contingency 2: Insufficient GPU Resources

**Trigger:** Cannot access A100 GPU or costs exceed budget.

**Actions:**
1. **Short-term:** Use smaller model (Llama 3.1 8B instead of 70B)
2. **Medium-term:** Secure longer-term GPU reservation (monthly rental)
3. **Long-term:** Partner with law firm to justify GPU investment
4. **Alternative:** Use Together.ai or Anyscale API for fine-tuning (higher cost but no infrastructure)

---

### Contingency 3: User Adoption Low

**Trigger:** <10 active users after 1 month of pilot.

**Actions:**
1. Conduct user interviews to understand barriers
2. Simplify UI (reduce complexity)
3. Create demo videos showing value
4. Offer 1-on-1 training sessions
5. Identify "champion" users to advocate
6. Consider incentives (CLE credits, recognition)

---

### Contingency 4: Hallucination in Production

**Trigger:** User reports answer with fabricated citation or incorrect law.

**Actions:**
1. **Immediate:** Add hallucinated example to "blocklist" (prevent similar errors)
2. **Short-term:** Increase citation validation strictness
3. **Medium-term:** Fine-tune model on corrected examples
4. **Long-term:** Implement multi-model consensus (ask 2+ models, compare answers)

---

# 12. Appendices

## Appendix A: Complete Code Artifacts

### A.1 Master Dataset Preparation Script

**File: `backend/scripts/jp_us_legal_dataset.py`**

[See complete script in separate response - Part 2]

---

### A.2 e-Gov API Scraping Script

**File: `backend/scripts/scrape_egov.py`**

[See complete script in separate response - Part 2]

---

### A.3 Courts.go.jp Scraping Script

**File: `backend/scripts/scrape_courts.py`**

[See complete script in separate response - Part 2]

---

### A.4 Bilingual Evaluation Framework

**File: `backend/scripts/evaluate_bilingual.py`**

[See complete script in separate response - Part 2]

---

## Appendix B: Training Configuration Files

### B.1 Axolotl Training Config

**File: `backend/configs/jp_us_legal_lora.yaml`**

```yaml
# Complete Axolotl configuration for Japan-US Legal AI fine-tuning

base_model: meta-llama/Meta-Llama-3.1-70B-Instruct
model_type: AutoModelForCausalLM
tokenizer_type: AutoTokenizer

trust_remote_code: true

# Quantization for memory efficiency
load_in_4bit: true
load_in_8bit: false

bnb_config:
  bnb_4bit_compute_dtype: bfloat16
  bnb_4bit_use_double_quant: true
  bnb_4bit_quant_type: nf4

# LoRA configuration
adapter: lora
lora_model_dir:
lora_r: 32
lora_alpha: 64
lora_dropout: 0.05
lora_target_modules:
  - q_proj
  - k_proj
  - v_proj
  - o_proj
  - gate_proj
  - up_proj
  - down_proj
lora_fan_in_fan_out:

# Training data
datasets:
  - path: data/jp_us_legal/train.jsonl
    type: chat_template
    field_messages: messages
    message_field_role: role
    message_field_content: content

# Validation data
test_datasets:
  - path: data/jp_us_legal/val.jsonl
    type: chat_template
    field_messages: messages
    message_field_role: role
    message_field_content: content

# Dataset formatting
dataset_prepared_path:
val_set_size: 0.0
output_dir: ./models/jp-us-legal-llama-70b-lora

# Sequence length
sequence_len: 4096
sample_packing: true
pad_to_sequence_len: true

# Training hyperparameters
micro_batch_size: 1
gradient_accumulation_steps: 8
eval_batch_size: 1
num_epochs: 3
optimizer: adamw_bnb_8bit
lr_scheduler: cosine
learning_rate: 0.0002

# Training optimizations
train_on_inputs: false
group_by_length: true
bf16: auto
fp16:
tf32: false

# Gradient checkpointing
gradient_checkpointing: true
gradient_checkpointing_kwargs:
  use_reentrant: false

# Logging and evaluation
logging_steps: 10
eval_steps: 50
save_steps: 100
save_total_limit: 3

evaluation_strategy: steps
eval_steps: 50
load_best_model_at_end: true
metric_for_best_model: loss

early_stopping_patience: 5

# Weights & Biases logging
wandb_project: jp-us-legal-rag-finetune
wandb_entity:
wandb_name: jp-us-legal-llama-70b-lora-v1

# Special tokens for Llama 3.1
special_tokens:
  bos_token: "<|begin_of_text|>"
  eos_token: "<|eot_id|>"
  pad_token: "<|end_of_text|>"
```

---

## Appendix C: Deployment Configurations

### C.1 Docker Compose (Development)

**File: `docker-compose.yml`**

```yaml
version: '3.8'

services:
  postgres:
    image: pgvector/pgvector:pg15
    environment:
      POSTGRES_DB: lawrag
      POSTGRES_USER: lawrag_user
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U lawrag_user"]
      interval: 10s
      timeout: 5s
      retries: 5

  neo4j:
    image: neo4j:5.0
    environment:
      NEO4J_AUTH: neo4j/${NEO4J_PASSWORD}
      NEO4J_PLUGINS: '["apoc"]'
      NEO4J_dbms_memory_pagecache_size: 2G
      NEO4J_dbms_memory_heap_max__size: 4G
    ports:
      - "7474:7474"  # HTTP
      - "7687:7687"  # Bolt
    volumes:
      - neo4j_data:/data
    healthcheck:
      test: ["CMD", "cypher-shell", "-u", "neo4j", "-p", "${NEO4J_PASSWORD}", "RETURN 1"]
      interval: 10s
      timeout: 5s
      retries: 5

  vllm:
    image: vllm/vllm-openai:latest
    environment:
      MODEL_PATH: /models/jp-us-legal-llama-70b-lora
      TENSOR_PARALLEL_SIZE: 1
      MAX_MODEL_LEN: 4096
      GPU_MEMORY_UTILIZATION: 0.9
    ports:
      - "8001:8000"
    volumes:
      - ./models:/models
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  backend:
    build: ./backend
    environment:
      DATABASE_URL: postgresql://lawrag_user:${POSTGRES_PASSWORD}@postgres:5432/lawrag
      NEO4J_URI: bolt://neo4j:7687
      NEO4J_USER: neo4j
      NEO4J_PASSWORD: ${NEO4J_PASSWORD}
      LAW_RAG_LLM_PROVIDER: llama
      LAW_RAG_LLAMA_BASE_URL: http://vllm:8000/v1
      LAW_RAG_GEMINI_API_KEY: ${GEMINI_API_KEY}
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      neo4j:
        condition: service_healthy
      vllm:
        condition: service_started
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000

  frontend:
    build: ./frontend
    environment:
      NEXT_PUBLIC_API_BASE_URL: http://localhost:8000
    ports:
      - "3000:3000"
    depends_on:
      - backend

volumes:
  postgres_data:
  neo4j_data:
```

---

### C.2 vLLM Startup Script

**File: `scripts/start_vllm.sh`**

```bash
#!/bin/bash

# Startup script for vLLM inference server
# Usage: ./start_vllm.sh [model_path]

set -e

MODEL_PATH=${1:-"./models/jp-us-legal-llama-70b-lora"}
PORT=${2:-8001}

echo "=================================================="
echo "Starting vLLM Inference Server"
echo "=================================================="
echo "Model: $MODEL_PATH"
echo "Port: $PORT"
echo ""

# Check if model exists
if [ ! -d "$MODEL_PATH" ]; then
    echo "Error: Model not found at $MODEL_PATH"
    exit 1
fi

# Check GPU availability
if ! command -v nvidia-smi &> /dev/null; then
    echo "Warning: nvidia-smi not found. GPU may not be available."
fi

# Start vLLM
python -m vllm.entrypoints.openai.api_server \
    --model "$MODEL_PATH" \
    --port $PORT \
    --dtype bfloat16 \
    --max-model-len 4096 \
    --gpu-memory-utilization 0.9 \
    --tensor-parallel-size 1 \
    --trust-remote-code \
    --served-model-name jp-us-legal-llama-70b

echo "vLLM server started on http://localhost:$PORT"
```

---

## Appendix D: Cost Summary Tables

### D.1 Phase 1 Costs (One-Time)

| Item | Provider | Quantity | Unit Cost | Total |
|------|----------|----------|-----------|-------|
| **Training GPU** | Lambda Labs A100 | 8 hours | $1.10/hr | $8.80 |
| **Training retries** | Lambda Labs A100 | 2 hours (contingency) | $1.10/hr | $2.20 |
| **Dataset storage** | Hugging Face Hub | 5 GB | Free (private repo) | $0 |
| **Development tools** | Various | N/A | Open-source | $0 |
| **TOTAL PHASE 1** | | | | **$11.00** |

---

### D.2 Ongoing Operational Costs (Monthly)

**Scenario 1: MVP (1,000 queries/month)**

| Item | Provider | Cost |
|------|----------|------|
| Inference API | Together.ai (Llama 70B) | $3 |
| PostgreSQL | Managed service (10 GB) | $15 |
| Neo4j | Managed service (2 GB) | $30 |
| Object storage | S3/equivalent (50 GB) | $1 |
| **TOTAL** | | **$49/month** |

---

**Scenario 2: Production (10,000 queries/month)**

| Item | Provider | Cost |
|------|----------|------|
| Inference API | Together.ai | $30 |
| PostgreSQL | Managed service (50 GB) | $50 |
| Neo4j | Managed service (10 GB) | $100 |
| Object storage | S3 (200 GB) | $5 |
| Monitoring | Datadog/equivalent | $15 |
| **TOTAL** | | **$200/month** |

---

**Scenario 3: Scale (50,000+ queries/month)**

| Item | Provider | Cost |
|------|----------|------|
| Self-hosted vLLM | Vast.ai (A100 24/7) | $584 |
| PostgreSQL | Managed service (200 GB) | $200 |
| Neo4j | Managed service (50 GB) | $300 |
| Object storage | S3 (1 TB) | $23 |
| Load balancer | Cloud provider | $20 |
| Monitoring | Enterprise tier | $50 |
| **TOTAL** | | **$1,177/month** |

**Break-even point:** ~40,000 queries/month (self-hosted becomes cheaper than API)

---

## Appendix E: Glossary

| Term | Definition |
|------|------------|
| **ACL (Access Control List)** | Matter-scoped permissions system preventing unauthorized access |
| **Anchor** | Document reference (e.g., "Contract §3.2, p.4") linking answer to source |
| **Abstain** | System behavior when evidence insufficient to answer query |
| **Citation coverage** | Percentage of answer sentences backed by citations |
| **Chunk** | Semantically coherent document segment (200-500 tokens) |
| **GraphRAG** | Hybrid retrieval combining knowledge graph + vector search |
| **Hallucination** | LLM output containing fabricated information not in context |
| **LoRA (Low-Rank Adaptation)** | Parameter-efficient fine-tuning method |
| **Matter** | Legal case or transaction (unit of access control) |
| **MRR (Mean Reciprocal Rank)** | Retrieval metric measuring rank of first relevant result |
| **Recall@K** | Percentage of relevant documents in top K results |
| **vLLM** | Fast inference engine for large language models |

---

## Document End

**Total Pages:** 52  
**Word Count:** ~18,000 words  
**Last Updated:** March 5, 2026  

**Next Steps:**
1. Review and approve requirements document
2. Proceed to Part 2 for complete code artifacts
3. Begin Phase 1 implementation (Week 1)
