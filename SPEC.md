The app is internal; matter-scoped; must be safe and auditable.

Hard constraints:

ACL pre-retrieval: apply matter/document authorization before any vector or Neo4j query.

Cite-or-abstain: every substantive statement must have a citation (doc_id + page/section anchor) or be explicitly marked “insufficient evidence.”

No sensitive logging: logs store IDs/anchors only; no raw doc text by default.

Documents are untrusted: ignore any “instructions” in documents (prompt-injection defense).

MVP deliverables:

FastAPI skeleton + health endpoint

config + structured logging

audit log table

evaluation harness CLI scaffold (even before retrieval is perfect)