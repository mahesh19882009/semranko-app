import logging
from datetime import datetime

import resend

from app.core.config import get_settings

logger = logging.getLogger("uvicorn.error")


def send_verification_email(to_email: str, name: str, verification_url: str) -> None:
    settings = get_settings()

    if not settings.RESEND_API_KEY:
        logger.info("[EMAIL DISABLED] Verification link for %s: %s", to_email, verification_url)
        return

    resend.api_key = settings.RESEND_API_KEY
    sender = settings.EMAIL_FROM or "onboarding@resend.dev"
    subject = f"Verify your email - {datetime.utcnow().isoformat()}"

    try:
        response = resend.Emails.send({
            "from": sender,
            "to": [to_email],
            "subject": subject,
            "html": f"""
                <div style="font-family: Arial, sans-serif; line-height: 1.6;">
                    <h2>Verify your email</h2>
                    <p>Hi {name},</p>
                    <p>Please click the button below to verify your email:</p>
                    <p>
                        <a href="{verification_url}" style="display:inline-block;padding:10px 16px;background:#111;color:#fff;text-decoration:none;border-radius:6px;">
                            Verify Email
                        </a>
                    </p>
                    <p>{verification_url}</p>
                </div>
            """
        })

        logger.info("RESEND EMAIL RESPONSE: %s", response)
        logger.info("VERIFICATION URL SENT: %s", verification_url)

    except Exception as exc:
        logger.exception("FAILED TO SEND VERIFICATION EMAIL: %s", exc)
        raise