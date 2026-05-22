"""Shared FastAPI dependencies."""

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.auth import decode_token

security = HTTPBearer(auto_error=False)


def _user_id_from_token(credentials: Optional[HTTPAuthorizationCredentials], db: Session) -> Optional[int]:
    if not credentials:
        return None

    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "access":
        return None

    sub = payload.get("sub")
    if sub is None:
        return None

    return int(sub)


def get_optional_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> Optional[int]:
    """Return the authenticated user id, or None for guest access."""
    return _user_id_from_token(credentials, db)


def get_required_user_id(
    user_id: Optional[int] = Depends(get_optional_user_id),
) -> int:
    """Require authentication — raise 401 if not authenticated."""
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please login to access this feature.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_id
