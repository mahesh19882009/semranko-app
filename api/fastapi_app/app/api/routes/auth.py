from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_user
from app.core.rate_limiter import rate_limit, client_ip, consume_limit, clear_limit
from app.core.errors import ApiError
from app.core.security import decode_mobile_verification_token, create_access_token, decode_access_token
from app.core.session import generate_session_token, invalidate_session, store_session
from app.schemas.common import ok
from app.services.auth_service import (
    forgot_password,
    create_mobile_verification_session,
    login_user,
    register_user,
    resend_verification_email,
    reset_password,
    verify_email_token,
)
from app.services.otp_service import send_otp, verify_otp as verify_otp_service, resend_otp as resend_otp_service
from app.services.turnstile_service import verify_turnstile
from hashlib import sha256
from app.core.auth_cookies import set_auth_cookies, clear_auth_cookies, read_auth_cookies
from app.db.models import User
from sqlalchemy import select
from app.utils.serializers import model_to_dict

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
@rate_limit(max_requests=5, window_seconds=3600)
def register(request: Request, payload: dict = Body(...), db: Session = Depends(db_session)) -> JSONResponse:
    verify_turnstile(payload.pop("turnstileToken", None), client_ip(request), "register")
    user = register_user(db, payload)
    return JSONResponse(status_code=201, content=ok("User registered", user))


@router.post("/login")
@rate_limit(max_requests=10, window_seconds=60)
def login(request: Request, response: Response, payload: dict = Body(...), db: Session = Depends(db_session)) -> dict:
    identity = sha256(str(payload.get("email") or "").strip().lower().encode()).hexdigest()
    failure_key = f"login:account:{identity}"
    challenge_required, _ = consume_limit(f"login:challenge-check:{identity}", 5, 900)
    # The check bucket deliberately escalates after repeated attempts; a valid
    # Turnstile token is then required until a successful login clears state.
    if not challenge_required:
        verify_turnstile(payload.pop("turnstileToken", None), client_ip(request), "login")
    try:
        result = login_user(db, payload)
    except ApiError as exc:
        if exc.status_code == 401:
            consume_limit(failure_key, 5, 900)
        raise
    clear_limit(failure_key)
    clear_limit(f"login:challenge-check:{identity}")
    result.pop("accessToken", None)
    result.pop("sessionToken", None)
    user_id = result["user"]["id"]
    invalidate_session(user_id)
    session_token = generate_session_token()
    store_session(user_id, session_token)
    access_token = create_access_token(str(user_id), result["user"]["email"])
    set_auth_cookies(response, access_token, session_token)
    return ok("Login successful", result)


@router.post("/mobile-verification-session")
@rate_limit(max_requests=5, window_seconds=3600)
def mobile_verification_session(request: Request, payload: dict = Body(...), db: Session = Depends(db_session)) -> dict:
    return ok("Mobile verification session created", create_mobile_verification_session(db, payload))

@router.post("/verify-email")
def verify_email(payload: dict = Body(...), db: Session = Depends(db_session)) -> dict:
    result = verify_email_token(db, payload)
    return ok("Email verified successfully", result)


@router.post("/resend-verification")
@rate_limit(max_requests=3, window_seconds=3600)
def resend_verification(request: Request, payload: dict = Body(...), db: Session = Depends(db_session)) -> dict:
    result = resend_verification_email(db, payload)

    return ok("If the account requires verification, an email will be sent", {"sent": True})


@router.post("/forgot-password")
@rate_limit(max_requests=3, window_seconds=3600)
def forgot_password_route(request: Request, payload: dict = Body(...), db: Session = Depends(db_session)) -> dict:
    verify_turnstile(payload.pop("turnstileToken", None), client_ip(request), "forgot_password")
    result = forgot_password(db, payload)
    return ok("Password reset email sent if your email is registered", result)


@router.post("/reset-password")
@rate_limit(max_requests=5, window_seconds=3600)
def reset_password_route(request: Request, payload: dict = Body(...), db: Session = Depends(db_session)) -> dict:
    result = reset_password(db, payload)
    return ok("Password reset successfully", result)


@router.get("/me")
def me(current_user: dict = Depends(get_current_user), db: Session = Depends(db_session)):
    user = db.scalar(select(User).where(User.id == current_user["id"]))
    if not user:
        raise ApiError(401, "Unauthorized")
    return ok("Authenticated", model_to_dict(user, exclude={"passwordHash", "emailVerificationToken", "passwordResetToken", "mobileVerificationOtp"}))


@router.post("/logout")
def logout(request: Request, response: Response):
    token, _ = read_auth_cookies(request)
    if token:
        try:
            user_id = decode_access_token(token).get("userId")
            if user_id:
                invalidate_session(str(user_id))
        except Exception:
            pass
    clear_auth_cookies(response)
    return ok("Logged out")


@router.post("/send-otp")
@rate_limit(max_requests=3, window_seconds=60)
def send_otp_route(
    request: Request,
    payload: dict = Body(...),
    db: Session = Depends(db_session),
):
    verification_token = payload.get("verificationToken")
    try:
        user_id = decode_mobile_verification_token(verification_token or "")
    except Exception as exc:
        raise ApiError(401, "Mobile verification session is invalid or expired. Please log in again.", {
            "error": "MOBILE_VERIFICATION_SESSION_EXPIRED", "action": "login",
        }) from exc
    mobile = payload.get("mobile")
    if not mobile:
        raise HTTPException(status_code=400, detail="Mobile number is required")
    
    verify_turnstile(payload.get("turnstileToken"), client_ip(request), "otp_send")
    result = send_otp(db, user_id, mobile, source_ip=client_ip(request))
    return ok("OTP sent successfully", result)


@router.post("/verify-otp")
@rate_limit(max_requests=5, window_seconds=60)
def verify_otp_route(
    request: Request,
    payload: dict = Body(...),
    db: Session = Depends(db_session),
):
    try:
        user_id = decode_mobile_verification_token(payload.get("verificationToken") or "")
    except Exception as exc:
        raise ApiError(401, "Mobile verification session is invalid or expired. Please log in again.", {
            "error": "MOBILE_VERIFICATION_SESSION_EXPIRED", "action": "login",
        }) from exc
    otp = payload.get("otp")
    if not otp:
        raise HTTPException(status_code=400, detail="OTP is required")
    
    result = verify_otp_service(db, user_id, otp)
    return ok("Mobile verified successfully", result)


@router.post("/resend-otp")
@rate_limit(max_requests=3, window_seconds=60)
def resend_otp_route(
    request: Request,
    payload: dict = Body(...),
    db: Session = Depends(db_session),
):
    try:
        user_id = decode_mobile_verification_token(payload.get("verificationToken") or "")
    except Exception as exc:
        raise ApiError(401, "Mobile verification session is invalid or expired. Please log in again.", {
            "error": "MOBILE_VERIFICATION_SESSION_EXPIRED", "action": "login",
        }) from exc
    verify_turnstile(payload.get("turnstileToken"), client_ip(request), "otp_send")
    result = resend_otp_service(db, user_id, source_ip=client_ip(request))
    return ok("OTP resent successfully", result)
