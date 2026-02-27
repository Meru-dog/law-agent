"""Authentication and matter-scoped authorization.

MVP: header-based identity (X-User-Id) with in-memory user-to-matter
mapping loaded from configuration. Deny-by-default.

Requirements: FR-ACL-1, FR-ACL-2, FR-ACL-4.
"""

from fastapi import Header, HTTPException, status

from app.config import Settings


def get_current_user(x_user_id: str | None = Header(default=None)) -> str:
    """Extract user identity from X-User-Id header.

    MVP stand-in for SSO/OIDC (FR-ACL-1). Production should replace
    this with proper token validation.

    Raises:
        HTTPException 401 if header is missing or empty.
    """
    if not x_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-User-Id header",
        )
    return x_user_id


def check_matter_access(user_id: str, matter_id: str, settings: Settings) -> bool:
    """Return True only if user is explicitly authorized for the matter.

    Deny-by-default: unknown users or unlisted matters return False.
    FR-ACL-2, FR-ACL-4.
    """
    allowed_matters = settings.user_matters.get(user_id, [])
    return matter_id in allowed_matters
