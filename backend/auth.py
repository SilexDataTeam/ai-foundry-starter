"""Authentication helpers for extracting user information from JWT tokens."""

from typing import Any

from fastapi import HTTPException, status


def get_user_email(token_payload: dict[str, Any]) -> str:
    """Extract user email from JWT token payload.

    Args:
        token_payload: Decoded JWT payload from Keycloak

    Returns:
        User email address

    Raises:
        HTTPException: If no email can be found in the token
    """
    email = token_payload.get("email")
    if email:
        return email

    # Fallback to preferred_username if email is not available
    username = token_payload.get("preferred_username")
    if username:
        return username

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No email found in token",
    )
