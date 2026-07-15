from fastapi import Depends, HTTPException, Query, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User

# Looks for: Authorization: Bearer <token> header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def get_token_from_request(
    header_token: str = Depends(oauth2_scheme),
    query_token: str = Query(default=None, alias="token"),
) -> str | None:
    """
    Extracts JWT from either:
      - Authorization: Bearer <token>  header (standard REST calls)
      - ?token=<token>                 query param (EventSource / SSE streams)
    """
    return header_token or query_token


def get_current_user(
    db: Session = Depends(get_db),
    token: str | None = Depends(get_token_from_request),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        raise credentials_exception

    email = decode_access_token(token)
    if email is None:
        raise credentials_exception

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception

    return user
