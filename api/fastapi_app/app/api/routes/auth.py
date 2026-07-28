from fastapi import APIRouter, Body, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import db_session
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

    return ok("Verification email sent", result)


@router.post("/forgot-password")
def forgot_password_route(payload: dict = Body(...), db: Session = Depends(db_session)) -> dict:
    result = forgot_password(db, payload)
    return ok("If your email is registered, you will receive a password reset link", result)


@router.post("/reset-password")
def reset_password_route(payload: dict = Body(...), db: Session = Depends(db_session)) -> dict:
    result = reset_password(db, payload)
    return ok("Password reset successfully", result)