from fastapi import Header, HTTPException, status

from app.core.models import UserContext
from app.services.security import AuthService


def current_user(authorization: str = Header(default="Bearer demo-token")) -> UserContext:
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="缺少 Bearer Token")
    try:
        return AuthService().decode(token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

