from fastapi import APIRouter, Body, Depends, Header
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional

from app.api.deps import db_session, get_current_user
from app.core.session import generate_session_token, invalidate_session, store_session
from app.schemas.common import ok
from app.services.auth_service import (
    forgot_password,
    login_user,
    register_user,
    resend_verification_email,
    reset_password,
    verify_email_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
def register(payload: dict = Body(...), db: Session = Depends(db_session)) -> JSONResponse:
    user = register_user(db, payload)
    return JSONResponse(status_code=201, content=ok("User registered", user))


@router.post("/login")
def login(payload: dict = Body(...), db: Session = Depends(db_session)) -> dict:
    result = login_user(db, payload)
    user_id = result["user"]["id"]
    invalidate_session(user_id)
    session_token = generate_session_token()
    store_session(user_id, session_token)
    result["sessionToken"] = session_token
    return ok("Login successful", result)

@router.post("/verify-email")
def verify_email(payload: dict = Body(...), db: Session = Depends(db_session)) -> dict:
    result = verify_email_token(db, payload)
    return ok("Email verified successfully", result)


@router.post("/resend-verification")
def resend_verification(payload: dict = Body(...), db: Session = Depends(db_session)) -> dict:
    result = resend_verification_email(db, payload)

    if result.get("alreadyVerified"):
        return ok("Email is already verified", result)

    if not result.get("sent"):
        return ok("Verification email could not be sent. Please try again later or contact support.", result)

    return ok("Verification email sent", result)


@router.post("/forgot-password")
def forgot_password_route(payload: dict = Body(...), db: Session = Depends(db_session)) -> dict:
    result = forgot_password(db, payload)
    return ok("Password reset email sent if your email is registered", result)


@router.post("/reset-password")
def reset_password_route(payload: dict = Body(...), db: Session = Depends(db_session)) -> dict:
    result = reset_password(db, payload)
    return ok("Password reset successfully", result)


@router.post("/logout")
def logout(
    current_user: dict = Depends(get_current_user),
    session_token: Optional[str] = Header(default=None, alias="X-Session-Token"),
):
    invalidate_session(current_user["id"])
    return ok("Logged out")