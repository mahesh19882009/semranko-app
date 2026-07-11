from fastapi import APIRouter, Body, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import db_session
from app.schemas.common import ok
from app.services.auth_service import login_user, register_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
def register(payload: dict = Body(...), db: Session = Depends(db_session)) -> JSONResponse:
    user = register_user(db, payload)
    return JSONResponse(status_code=201, content=ok("User registered", user))


@router.post("/login")
def login(payload: dict = Body(...), db: Session = Depends(db_session)) -> dict:
    result = login_user(db, payload)
    return ok("Login successful", result)
