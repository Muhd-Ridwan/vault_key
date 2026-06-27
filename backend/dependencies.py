from datetime import datetime, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt

from config import settings

unlock_windows: dict[str, datetime] = {}

bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256"],
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please log in again.",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Token",
        )


def require_totp_unlock(
    current_user: dict = Depends(get_current_user),
) -> dict:
    user_id = current_user["sub"]
    expiry = unlock_windows.get(user_id)
    if expiry is None or datetime.now(timezone.utc) > expiry:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="TOTP unlock required.",
            headers={"X-Require-TOTP": "true"},
        )
    return current_user
