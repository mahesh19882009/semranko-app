from fastapi import APIRouter, Body, Depends, Header, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional

from app.api.deps import db_session, get_current_user
from app.core.rate_limiter import rate_limit
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
from app.services.otp_service import send_otp, verify_otp as verify_otp_service, resend_otp as resend_otp_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
@rate_limit(max_requests=5, window_seconds=3600)
def register(request: Request, payload: dict = Body(...), db: Session = Depends(db_session)) -> JSONResponse:
    user = register_user(db, payload)
    return JSONResponse(status_code=201, content=ok("User registered", user))


@router.post("/login")
@rate_limit(max_requests=10, window_seconds=60)
def login(request: Request, payload: dict = Body(...), db: Session = Depends(db_session)) -> dict:
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
@rate_limit(max_requests=3, window_seconds=3600)
def resend_verification(request: Request, payload: dict = Body(...), db: Session = Depends(db_session)) -> dict:
    result = resend_verification_email(db, payload)

    if result.get("alreadyVerified"):
        return ok("Email is already verified", result)

    if not result.get("sent"):
        return ok("Verification email could not be sent. Please try again later or contact support.", result)

    return ok("Verification email sent", result)


@router.post("/forgot-password")
@rate_limit(max_requests=3, window_seconds=3600)
def forgot_password_route(request: Request, payload: dict = Body(...), db: Session = Depends(db_session)) -> dict:
    result = forgot_password(db, payload)
    return ok("Password reset email sent if your email is registered", result)


@router.post("/reset-password")
@rate_limit(max_requests=5, window_seconds=3600)
def reset_password_route(request: Request, payload: dict = Body(...), db: Session = Depends(db_session)) -> dict:
    result = reset_password(db, payload)
    return ok("Password reset successfully", result)


@router.post("/logout")
def logout(
    current_user: dict = Depends(get_current_user),
    session_token: Optional[str] = Header(default=None, alias="X-Session-Token"),
):
    invalidate_session(current_user["id"])
    return ok("Logged out")


@router.post("/send-otp")
@rate_limit(max_requests=3, window_seconds=60)
def send_otp_route(
    request: Request,
    payload: dict = Body(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    mobile = payload.get("mobile")
    if not mobile:
        raise HTTPException(status_code=400, detail="Mobile number is required")
    
    result = send_otp(db, current_user["id"], mobile)
    return ok("OTP sent successfully", result)


@router.post("/verify-otp")
@rate_limit(max_requests=5, window_seconds=60)
def verify_otp_route(
    request: Request,
    payload: dict = Body(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    otp = payload.get("otp")
    if not otp:
        raise HTTPException(status_code=400, detail="OTP is required")
    
    result = verify_otp_service(db, current_user["id"], otp)
    return ok("Mobile verified successfully", result)


@router.post("/resend-otp")
@rate_limit(max_requests=3, window_seconds=60)
def resend_otp_route(
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    result = resend_otp_service(db, current_user["id"])
    return ok("OTP resent successfully", result)