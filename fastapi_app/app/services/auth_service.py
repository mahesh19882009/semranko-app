from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.core.security import create_access_token, hash_password, verify_password
from app.db.models import User
from app.utils.serializers import model_to_dict


def register_user(db: Session, payload: dict) -> dict:
    name = payload.get("name")
    email = payload.get("email")
    password = payload.get("password")

    if not name or not email or not password:
        raise ApiError(400, "Name, email and password are required")

    existing = db.scalar(select(User).where(User.email == email))
    if existing:
        raise ApiError(409, "Email already registered")

    user = User(name=name.strip(), email=email.strip().lower(), passwordHash=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)

    return model_to_dict(user, exclude={"passwordHash"})


def login_user(db: Session, payload: dict) -> dict:
    email = payload.get("email")
    password = payload.get("password")

    if not email or not password:
        raise ApiError(400, "Email and password are required")

    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    if not user or not verify_password(password, user.passwordHash):
        raise ApiError(401, "Invalid credentials")

    access_token = create_access_token(user.id, user.email)
    return {
        "user": model_to_dict(user, exclude={"passwordHash"}),
        "accessToken": access_token,
    }
