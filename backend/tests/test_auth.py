"""Tests for authentication and matter-scoped authorization (T1).

Covers:
  FR-ACL-1  – user identity required
  FR-ACL-2  – matter-level ACL enforcement
  FR-ACL-4  – no content outside authorized scope
"""

import pytest

from app.auth import check_matter_access, get_current_user
from app.config import Settings, get_settings
from app.main import app


# ---------------------------------------------------------------------------
# Unit tests – check_matter_access (pure function, no HTTP)
# ---------------------------------------------------------------------------


class TestCheckMatterAccess:
    """Deny-by-default authorization checks."""

    def _settings(self, mapping: dict[str, list[str]] | None = None) -> Settings:
        return Settings(user_matters=mapping or {})

    def test_allow_when_user_has_explicit_access(self):
        s = self._settings({"alice": ["matter-1", "matter-2"]})
        assert check_matter_access("alice", "matter-1", s) is True

    def test_allow_second_matter(self):
        s = self._settings({"alice": ["matter-1", "matter-2"]})
        assert check_matter_access("alice", "matter-2", s) is True

    def test_deny_when_matter_not_in_list(self):
        s = self._settings({"alice": ["matter-1"]})
        assert check_matter_access("alice", "matter-99", s) is False

    def test_deny_for_unknown_user(self):
        s = self._settings({"alice": ["matter-1"]})
        assert check_matter_access("bob", "matter-1", s) is False

    def test_deny_when_mapping_is_empty(self):
        s = self._settings({})
        assert check_matter_access("alice", "matter-1", s) is False

    def test_deny_when_user_list_is_empty(self):
        s = self._settings({"alice": []})
        assert check_matter_access("alice", "matter-1", s) is False


# ---------------------------------------------------------------------------
# Unit tests – get_current_user
# ---------------------------------------------------------------------------


class TestGetCurrentUser:
    def test_returns_user_id_when_header_present(self):
        assert get_current_user("alice") == "alice"

    def test_raises_401_when_header_is_none(self):
        with pytest.raises(Exception) as exc_info:
            get_current_user(None)
        assert exc_info.value.status_code == 401

    def test_raises_401_when_header_is_empty(self):
        with pytest.raises(Exception) as exc_info:
            get_current_user("")
        assert exc_info.value.status_code == 401


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


async def test_query_401_without_user_header(client):
    resp = await client.post(
        "/v1/query", json={"matter_id": "matter-1", "query": "q"}
    )
    assert resp.status_code == 401


async def test_query_403_for_unauthorized_matter(client, _override_settings):
    resp = await client.post(
        "/v1/query",
        json={"matter_id": "matter-99", "query": "q"},
        headers={"X-User-Id": "alice"},
    )
    assert resp.status_code == 403


async def test_query_403_for_unknown_user(client, _override_settings):
    resp = await client.post(
        "/v1/query",
        json={"matter_id": "matter-1", "query": "q"},
        headers={"X-User-Id": "unknown"},
    )
    assert resp.status_code == 403


async def test_query_200_for_authorized_user_and_matter(client, _override_settings):
    resp = await client.post(
        "/v1/query",
        json={"matter_id": "matter-1", "query": "What is clause 3?"},
        headers={"X-User-Id": "alice"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["matter_id"] == "matter-1"
    assert data["query"] == "What is clause 3?"
    assert "answer" in data
    assert "query_id" in data


async def test_query_422_when_matter_id_missing(client, _override_settings):
    resp = await client.post(
        "/v1/query",
        json={"query": "q"},
        headers={"X-User-Id": "alice"},
    )
    assert resp.status_code == 422


async def test_query_403_with_default_empty_config(client):
    """With no user_matters configured, all access is denied (deny-by-default)."""
    # No _override_settings → default Settings has user_matters={}
    test_settings = Settings(user_matters={})
    app.dependency_overrides[get_settings] = lambda: test_settings
    try:
        resp = await client.post(
            "/v1/query",
            json={"matter_id": "matter-1", "query": "q"},
            headers={"X-User-Id": "alice"},
        )
        assert resp.status_code == 403
    finally:
        app.dependency_overrides.clear()
