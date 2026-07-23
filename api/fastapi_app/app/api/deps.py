from fastapi import Depends, Header
from sqlalchemy.orm import Session
from typing import Optional

from app.core.errors import ApiError
from app.core.security import decode_access_token
from app.db.session import get_db


def get_current_user(authorization: Optional[str] = Header(default=None)) -> dict:
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]

    if not token:
        raise ApiError(401, "Unauthorized")

    try:
        payload = decode_access_token(token)
    except Exception as exc:  # noqa: BLE001
        raise ApiError(401, "Invalid token") from exc

    user_id = payload.get("userId")
    if not user_id:
        raise ApiError(401, "Invalid token")

    payload["id"] = user_id
    return payload


def db_session(db: Session = Depends(get_db)) -> Session:
    return db
