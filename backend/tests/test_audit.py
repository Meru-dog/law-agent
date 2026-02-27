"""Tests for audit log persistence (T2).

Covers:
  FR-LG-4  – every query attempt is logged
  NFR-SEC-3 – access denials are recorded
"""

import json
import uuid

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.audit import record_audit
from app.config import Settings, get_settings
from app.main import app
from app.models import AuditEntry, Base


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db_session() -> Session:
    """In-memory SQLite session for unit tests (no HTTP, no FastAPI)."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = factory()
    yield session
    session.close()
    engine.dispose()


# ---------------------------------------------------------------------------
# Unit tests – record_audit (pure function, no HTTP)
# ---------------------------------------------------------------------------


class TestRecordAudit:
    def test_creates_entry_with_all_fields(self, db_session: Session):
        entry = record_audit(
            db_session,
            query_id="qid-1",
            user_id="alice",
            matter_id="matter-1",
            step_name="query_received",
            artifact_ids=["doc-a", "doc-b"],
        )

        assert entry.id is not None
        assert entry.query_id == "qid-1"
        assert entry.user_id == "alice"
        assert entry.matter_id == "matter-1"
        assert entry.step_name == "query_received"
        assert json.loads(entry.artifact_ids) == ["doc-a", "doc-b"]
        assert entry.created_at is not None

    def test_creates_entry_without_artifact_ids(self, db_session: Session):
        entry = record_audit(
            db_session,
            query_id="qid-2",
            user_id="bob",
            matter_id="matter-2",
            step_name="query_received",
        )

        assert entry.artifact_ids is None

    def test_multiple_steps_share_query_id(self, db_session: Session):
        shared_qid = str(uuid.uuid4())
        record_audit(
            db_session,
            query_id=shared_qid,
            user_id="alice",
            matter_id="matter-1",
            step_name="query_received",
        )
        record_audit(
            db_session,
            query_id=shared_qid,
            user_id="alice",
            matter_id="matter-1",
            step_name="retrieval_complete",
        )

        rows = db_session.execute(
            select(AuditEntry).where(AuditEntry.query_id == shared_qid)
        ).scalars().all()
        assert len(rows) == 2
        assert {r.step_name for r in rows} == {"query_received", "retrieval_complete"}

    def test_access_denied_is_logged(self, db_session: Session):
        record_audit(
            db_session,
            query_id="qid-denied",
            user_id="eve",
            matter_id="matter-secret",
            step_name="access_denied",
        )

        row = db_session.execute(
            select(AuditEntry).where(AuditEntry.query_id == "qid-denied")
        ).scalar_one()
        assert row.step_name == "access_denied"
        assert row.user_id == "eve"


# ---------------------------------------------------------------------------
# Integration tests – /v1/query endpoint
# ---------------------------------------------------------------------------


@pytest.fixture()
def _override_settings():
    """Provide a Settings instance where alice can access matter-1."""
    test_settings = Settings(user_matters={"alice": ["matter-1"]})
    app.dependency_overrides[get_settings] = lambda: test_settings
    yield
    app.dependency_overrides.clear()


async def test_query_200_returns_query_id(client, _override_settings):
    resp = await client.post(
        "/v1/query",
        json={"matter_id": "matter-1", "query": "test"},
        headers={"X-User-Id": "alice"},
    )
    assert resp.status_code == 200
    data = resp.json()
    # Validate the query_id is a valid UUID4
    uuid.UUID(data["query_id"], version=4)


async def test_successful_query_creates_audit_entry(client, _override_settings):
    resp = await client.post(
        "/v1/query",
        json={"matter_id": "matter-1", "query": "test"},
        headers={"X-User-Id": "alice"},
    )
    query_id = resp.json()["query_id"]

    session: Session = app.state.session_factory()
    try:
        row = session.execute(
            select(AuditEntry).where(AuditEntry.query_id == query_id)
        ).scalar_one()
        assert row.step_name == "query_received"
        assert row.user_id == "alice"
        assert row.matter_id == "matter-1"
    finally:
        session.close()


async def test_denied_query_creates_access_denied_entry(client, _override_settings):
    resp = await client.post(
        "/v1/query",
        json={"matter_id": "matter-99", "query": "test"},
        headers={"X-User-Id": "alice"},
    )
    assert resp.status_code == 403

    session: Session = app.state.session_factory()
    try:
        rows = session.execute(
            select(AuditEntry).where(AuditEntry.step_name == "access_denied")
        ).scalars().all()
        assert len(rows) >= 1
        row = rows[-1]
        assert row.user_id == "alice"
        assert row.matter_id == "matter-99"
    finally:
        session.close()
