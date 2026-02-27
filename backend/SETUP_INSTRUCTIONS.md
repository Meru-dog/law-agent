# Setup Instructions for Law RAG Backend

## T5: LLM Integration with Gemini API - Installation

### Install Dependencies

Run the following command to install all required dependencies including the Gemini API:

```bash
cd backend
pip install -e ".[dev]"
```

Or install just the new dependency:

```bash
pip install "google-generativeai>=0.3.0"
```

### Configure API Key

Set the Gemini API key as an environment variable:

```bash
export LAW_RAG_GEMINI_API_KEY="your-gemini-api-key-here"
```

You can get a Gemini API key from: https://makersuite.google.com/app/apikey

### Run Tests

Once dependencies are installed:

```bash
pytest tests/test_llm.py -v
```

### Test the Integration

1. Start the backend server:
   ```bash
   uvicorn app.main:app --reload
   ```

2. Upload a test document:
   ```bash
   curl -X POST http://localhost:8000/v1/documents/upload \
     -H "X-User-Id: alice" \
     -F "file=@sample.pdf" \
     -F "matter_id=matter-1"
   ```

3. Query with cited answers:
   ```bash
   curl -X POST http://localhost:8000/v1/query \
     -H "X-User-Id: alice" \
     -H "Content-Type: application/json" \
     -d '{
       "matter_id": "matter-1",
       "query": "What is the payment term?"
     }'
   ```

Expected response will include:
- `answer`: The generated answer with citations like [1], [2]
- `citations`: Array of citation objects with doc_id and anchor
- `abstained`: Boolean indicating if system abstained due to insufficient evidence
- `confidence`: Float between 0.0 and 1.0
- `retrieval_trace`: Array of retrieved chunks used as context

## Configuration Options

### Environment Variables

All configuration uses the `LAW_RAG_` prefix:

- `LAW_RAG_GEMINI_API_KEY`: Gemini API key (required for answer generation)
- `LAW_RAG_GEMINI_MODEL`: Model name (default: "gemini-1.5-pro")
- `LAW_RAG_MAX_CONTEXT_CHUNKS`: Max chunks to send to LLM (default: 10)
- `LAW_RAG_USER_MATTERS`: JSON mapping of users to authorized matters

Example:
```bash
export LAW_RAG_GEMINI_API_KEY="your-key"
export LAW_RAG_GEMINI_MODEL="gemini-1.5-pro"
export LAW_RAG_MAX_CONTEXT_CHUNKS="10"
export LAW_RAG_USER_MATTERS='{"alice":["matter-1"],"bob":["matter-2"]}'
```

## What T5 Implements

✅ **Core LLM Integration** (`app/llm.py`)
- Gemini API client with error handling
- Citation parsing from answer text (extracts [1], [2] references)
- Citation validation (ensures all citations match provided context)
- Abstain logic (returns "INSUFFICIENT EVIDENCE" when appropriate)
- Confidence scoring based on citation coverage

✅ **Prompt Engineering** (`app/prompts.py`)
- System prompt enforcing mandatory citations
- Prompt injection defense (treats documents as untrusted)
- Context formatting with numbered references
- Abstain condition handling

✅ **API Integration** (`app/main.py`)
- Updated `/v1/query` endpoint to generate cited answers
- Vector search integration (retrieves relevant chunks)
- Answer synthesis with LLM
- Citation validation and response formatting
- Audit logging for LLM steps

✅ **Comprehensive Tests** (`tests/test_llm.py`)
- Citation parsing tests (single, multiple, duplicates, invalid)
- Answer generation tests (success, abstain, errors)
- API error handling (quota, timeout, generic errors)
- Edge cases (empty contexts, invalid citations)

## Next Steps

After T5 is verified:
- **T6**: Neo4j schema + entity extraction
- **T7**: GraphRAG retrieval (graph + vector fusion)
- **T8**: LangGraph workflow orchestration
- **T9**: Evaluation harness CLI
