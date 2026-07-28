from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from app.api.deps import db_session
from app.schemas.common import ok
from app.services.email_service import send_contact_form_email

router = APIRouter(prefix="/contact", tags=["contact"])


@router.post("/submit")
def submit_contact_form(payload: dict = Body(...), db: Session = Depends(db_session)) -> dict:
    """
    Submit contact form and send email notification
    """
    name = payload.get("name")
    email = payload.get("email")
    company = payload.get("company", "")
    message = payload.get("message")

    if not name or not email or not message:
        return ok("Please fill in all required fields", {"success": False})

    # Send email notification
    send_contact_form_email(name, email, company, message)

    return ok("Thank you for your message. We'll get back to you soon.", {"success": True})
