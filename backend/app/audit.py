"""Audit log recording.

Provides a single function to persist an audit entry to the database.
"""

import json

from sqlalchemy.orm import Session

from app.models import AuditEntry


def record_audit(
    session: Session,
    *,
    query_id: str,
    user_id: str,
    matter_id: str,
    step_name: str,
    artifact_ids: list[str] | None = None,
) -> AuditEntry:
    """Create and persist an audit log entry.

    Args:
        session: Active SQLAlchemy session.
        query_id: UUID identifying the query.
        user_id: Authenticated user identifier.
        matter_id: Matter the query targets.
        step_name: Pipeline step (e.g. ``"query_received"``, ``"access_denied"``).
        artifact_ids: Optional list of artifact ID strings (serialized as JSON).

    Returns:
        The persisted ``AuditEntry`` instance.
    """
    entry = AuditEntry(
        query_id=query_id,
        user_id=user_id,
        matter_id=matter_id,
        step_name=step_name,
        artifact_ids=json.dumps(artifact_ids) if artifact_ids is not None else None,
    )
    session.add(entry)
    session.commit()
    return entry
