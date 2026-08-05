import logging
from datetime import datetime

import resend

from app.core.config import get_settings

logger = logging.getLogger("uvicorn.error")


def send_verification_email(to_email: str, name: str, verification_url: str) -> bool:
    settings = get_settings()

    if not settings.RESEND_API_KEY:
        logger.info("[EMAIL DISABLED] Verification link for %s: %s", to_email, verification_url)
        return False

    resend.api_key = settings.RESEND_API_KEY
    sender = settings.EMAIL_FROM or "onboarding@resend.dev"
    subject = f"Verify your email - {datetime.utcnow().isoformat()}"

    try:
        response = resend.Emails.send({
            "from": sender,
            "to": [to_email],
            "subject": subject,
            "html": f"""
                <!DOCTYPE html>
                <html>
                <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Verify your email</title>
                </head>
                <body style="margin: 0; padding: 0; background-color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; -webkit-font-smoothing: antialiased;">
                <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color: #f8fafc; padding: 32px 16px;">
                    <tr>
                    <td align="center">
                        <!-- Main Card Container -->
                        <table width="100%" border="0" cellspacing="0" cellpadding="0" style="max-width: 440px; background-color: #ffffff; border-radius: 16px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);">
                        
                        <!-- Header Banner -->
                        <tr>
                            <td style="background-color: #0f172a; padding: 32px 24px; text-align: center;">
                            <!-- Blue Envelope Icon Wrapper -->
                            <div style="display: inline-block; background-color: #2563eb; width: 48px; height: 48px; border-radius: 50%; text-align: center; margin-bottom: 16px;">
                                <span style="color: #ffffff; font-size: 20px; line-height: 46px; font-weight: bold;">✉</span>
                            </div>
                            <h1 style="margin: 0; color: #ffffff; font-size: 20px; font-weight: 700; letter-spacing: -0.025em;">Verify Your Email</h1>
                            <p style="margin: 4px 0 0 0; color: #94a3b8; font-size: 14px;">Welcome to RankCare</p>
                            </td>
                        </tr>

                        <!-- Content Body -->
                        <tr>
                            <td style="padding: 24px;">
                            <p style="margin: 0 0 16px 0; font-size: 15px; color: #334155; line-height: 1.5;">Hi <strong>{name}</strong>,</p>
                            <p style="margin: 0 0 24px 0; font-size: 14px; color: #64748b; line-height: 1.5;">Thanks for creating an account with RankCare! Before we get started, we just need to confirm that this email address belongs to you.</p>

                            <!-- Action Button -->
                            <table width="100%" border="0" cellspacing="0" cellpadding="0" style="margin-bottom: 28px;">
                                <tr>
                                <td align="center">
                                    <a href="{verification_url}" target="_blank" style="display: inline-block; background-color: #000000; color: #ffffff; font-size: 14px; font-weight: 600; text-decoration: none; padding: 12px 32px; border-radius: 8px; box-shadow: 0 2px 4px rgba(37, 99, 235, 0.2);">Verify Email Address</a>
                                </td>
                                </tr>
                            </table>

                            <!-- Fallback URL Section -->
                            <table width="100%" border="0" cellspacing="0" cellpadding="0" style="border-top: 1px solid #e2e8f0; padding-top: 16px;">
                                <tr>
                                <td>
                                    <p style="margin: 0 0 8px 0; font-size: 12px; color: #94a3b8; line-height: 1.4;">If the button above doesn't work, copy and paste this link into your web browser:</p>
                                    <p style="margin: 0; font-size: 12px; color: #2563eb; word-break: break-all; font-family: monospace; line-height: 1.4;"><a href="{verification_url}" style="color: #2563eb; text-decoration: none;">{verification_url}</a></p>
                                </td>
                                </tr>
                            </table>
                            </td>
                        </tr>

                        <!-- Footer -->
                        <tr>
                            <td style="padding: 0 24px 24px 24px; text-align: center;">
                            <p style="margin: 0; font-size: 12px; color: #94a3b8;">If you did not sign up for this account, you can safely ignore this email.</p>
                            <p style="margin: 6px 0 0 0; font-size: 12px; color: #94a3b8;">&copy; 2026 RankCare. All rights reserved.</p>
                            </td>
                        </tr>

                        </table>
                    </td>
                    </tr>
                </table>
                </body>
                </html>
            """
        })

        logger.info("RESEND EMAIL RESPONSE: %s", response)
        logger.info("VERIFICATION URL SENT: %s", verification_url)
        return True

    except Exception as exc:
        logger.exception("FAILED TO SEND VERIFICATION EMAIL: %s", exc)
        return False


def send_payment_success_email(to_email: str, name: str, plan_name: str, amount: float, order_id: str) -> bool:
    settings = get_settings()

    if not settings.RESEND_API_KEY:
        logger.info("[EMAIL DISABLED] Payment success email for %s: plan=%s amount=%s order=%s", to_email, plan_name, amount, order_id)
        return False

    resend.api_key = settings.RESEND_API_KEY
    sender = settings.EMAIL_FROM or "onboarding@resend.dev"
    subject = f"Payment successful - {plan_name} plan activated"

    try:
        response = resend.Emails.send({
            "from": sender,
            "to": [to_email],
            "subject": subject,
            "html": f"""
                <!DOCTYPE html>
                <html>
                <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Payment Successful</title>
                </head>
                <body style="margin: 0; padding: 0; background-color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; -webkit-font-smoothing: antialiased;">
                <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color: #f8fafc; padding: 32px 16px;">
                    <tr>
                    <td align="center">
                        <!-- Main Card Container -->
                        <table width="100%" border="0" cellspacing="0" cellpadding="0" style="max-width: 440px; background-color: #ffffff; border-radius: 16px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);">
                        
                        <!-- Header Banner -->
                        <tr>
                            <td style="background-color: #0f172a; padding: 32px 24px; text-align: center;">
                            <!-- Green Check Icon Wrapper -->
                            <div style="display: inline-block; background-color: #22c55e; width: 48px; height: 48px; border-radius: 50%; text-align: center; margin-bottom: 16px;">
                                <span style="color: #ffffff; font-size: 24px; line-height: 48px; font-weight: bold;">✓</span>
                            </div>
                            <h1 style="margin: 0; color: #ffffff; font-size: 20px; font-weight: 700; letter-spacing: -0.025em;">Payment Successful</h1>
                            <p style="margin: 4px 0 0 0; color: #94a3b8; font-size: 14px;">Thank you for your business!</p>
                            </td>
                        </tr>

                        <!-- Content Body -->
                        <tr>
                            <td style="padding: 24px;">
                            <p style="margin: 0 0 16px 0; font-size: 15px; color: #334155; line-height: 1.5;">Hi <strong>{name}</strong>,</p>
                            <p style="margin: 0 0 24px 0; font-size: 14px; color: #64748b; line-height: 1.5;">Your payment for the subscription plan has been processed successfully. Your account features are now active.</p>

                            <!-- Receipt Table Box -->
                            <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color: #f8fafc; border-radius: 8px; padding: 16px; margin-bottom: 24px;">
                                <tr>
                                <td style="padding-bottom: 10px; font-size: 13px; color: #64748b;">Plan:</td>
                                <td align="right" style="padding-bottom: 10px; font-size: 14px; font-weight: 600; color: #0f172a;">{plan_name}</td>
                                </tr>
                                <tr>
                                <td style="padding-bottom: 10px; font-size: 13px; color: #64748b;">Order ID:</td>
                                <td align="right" style="padding-bottom: 10px; font-size: 13px; font-family: monospace; color: #334155;">{order_id}</td>
                                </tr>
                                <!-- Divider Line -->
                                <tr>
                                <td colspan="2" style="border-top: 1px solid #e2e8f0; padding-top: 10px;"></td>
                                </tr>
                                <tr>
                                <td style="font-size: 14px; font-weight: 600; color: #0f172a; padding-top: 4px;">Amount Paid:</td>
                                <td align="right" style="font-size: 16px; font-weight: 700; color: #0f172a; padding-top: 4px;">₹{amount:.2f}</td>
                                </tr>
                            </table>

                            <!-- Action Button -->
                            <table width="100%" border="0" cellspacing="0" cellpadding="0">
                                <tr>
                                <td align="center">
                                    <a href="https://rankcare.codmonks.com" target="_blank" style="display: inline-block; background-color: #000000; color: #ffffff; font-size: 14px; font-weight: 600; text-decoration: none; padding: 12px 32px; border-radius: 8px; box-shadow: 0 2px 4px rgba(37, 99, 235, 0.2);">Go to Dashboard</a>
                                </td>
                                </tr>
                            </table>
                            </td>
                        </tr>

                        <!-- Footer -->
                        <tr>
                            <td style="padding: 0 24px 24px 24px; text-align: center;">
                            <p style="margin: 0; font-size: 12px; color: #94a3b8;">If you have any questions, reply directly to this email.</p>
                            <p style="margin: 6px 0 0 0; font-size: 12px; color: #94a3b8;">&copy; 2026 RankCare. All rights reserved.</p>
                            </td>
                        </tr>

                        </table>
                    </td>
                    </tr>
                </table>
                </body>
                </html>
            """
        })

        logger.info("RESEND PAYMENT SUCCESS EMAIL RESPONSE: %s", response)
        return True

    except Exception as exc:
        logger.exception("FAILED TO SEND PAYMENT SUCCESS EMAIL: %s", exc)
        return False


def send_payment_failure_email(to_email: str, name: str, plan_name: str, order_id: str, error_message: str) -> bool:
    settings = get_settings()

    if not settings.RESEND_API_KEY:
        logger.info("[EMAIL DISABLED] Payment failure email for %s: plan=%s order=%s error=%s", to_email, plan_name, order_id, error_message)
        return False

    resend.api_key = settings.RESEND_API_KEY
    sender = settings.EMAIL_FROM or "onboarding@resend.dev"
    subject = f"Payment failed - {plan_name} plan"

    try:
        response = resend.Emails.send({
            "from": sender,
            "to": [to_email],
            "subject": subject,
            "html": f"""
                <!DOCTYPE html>
                <html>
                <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Payment Failed</title>
                </head>
                <body style="margin: 0; padding: 0; background-color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; -webkit-font-smoothing: antialiased;">
                <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color: #f8fafc; padding: 32px 16px;">
                    <tr>
                    <td align="center">
                        <!-- Main Card Container -->
                        <table width="100%" border="0" cellspacing="0" cellpadding="0" style="max-width: 440px; background-color: #ffffff; border-radius: 16px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);">
                        
                        <!-- Header Banner (Warning/Red Theme) -->
                        <tr>
                            <td style="background-color: #0f172a; padding: 32px 24px; text-align: center;">
                            <!-- Red Exclamation Icon Wrapper -->
                            <div style="display: inline-block; background-color: #ef4444; width: 48px; height: 48px; border-radius: 50%; text-align: center; margin-bottom: 16px;">
                                <span style="color: #ffffff; font-size: 24px; line-height: 46px; font-weight: bold;">!</span>
                            </div>
                            <h1 style="margin: 0; color: #ffffff; font-size: 20px; font-weight: 700; letter-spacing: -0.025em;">Payment Failed</h1>
                            <p style="margin: 4px 0 0 0; color: #94a3b8; font-size: 14px;">Action required to activate your plan</p>
                            </td>
                        </tr>

                        <!-- Content Body -->
                        <tr>
                            <td style="padding: 24px;">
                            <p style="margin: 0 0 16px 0; font-size: 15px; color: #334155; line-height: 1.5;">Hi <strong>{name}</strong>,</p>
                            <p style="margin: 0 0 24px 0; font-size: 14px; color: #64748b; line-height: 1.5;">We were unable to process your payment for the subscription plan. Don't worry, your account is safe, but we need you to update your details to proceed.</p>

                            <!-- Error Information Table Box -->
                            <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color: #fff5f5; border: 1px solid #fee2e2; border-radius: 8px; padding: 16px; margin-bottom: 24px;">
                                <tr>
                                <td style="padding-bottom: 10px; font-size: 13px; color: #b91c1c; font-weight: 500;">Plan:</td>
                                <td align="right" style="padding-bottom: 10px; font-size: 14px; font-weight: 600; color: #991b1b;">{plan_name}</td>
                                </tr>
                                <tr>
                                <td style="padding-bottom: 10px; font-size: 13px; color: #b91c1c; font-weight: 500;">Order ID:</td>
                                <td align="right" style="padding-bottom: 10px; font-size: 13px; font-family: monospace; color: #991b1b;">{order_id}</td>
                                </tr>
                                <!-- Divider Line -->
                                <tr>
                                <td colspan="2" style="border-top: 1px solid #fee2e2; padding-top: 10px;"></td>
                                </tr>
                                <tr>
                                <td valign="top" style="font-size: 13px; color: #b91c1c; font-weight: 500; padding-top: 4px;">Reason:</td>
                                <td align="right" style="font-size: 13px; color: #7f1d1d; padding-top: 4px; line-height: 1.4; max-width: 200px;">{error_message}</td>
                                </tr>
                            </table>

                            <!-- Action Button -->
                            <table width="100%" border="0" cellspacing="0" cellpadding="0">
                                <tr>
                                <td align="center">
                                    <a href="https://rankcare.codmonks.com" target="_blank" style="display: inline-block; background-color: #000000; color: #ffffff; font-size: 14px; font-weight: 600; text-decoration: none; padding: 12px 32px; border-radius: 8px; box-shadow: 0 2px 4px rgba(37, 99, 235, 0.2);">Retry Payment</a>
                                </td>
                                </tr>
                            </table>
                            </td>
                        </tr>

                        <!-- Footer -->
                        <tr>
                            <td style="padding: 0 24px 24px 24px; text-align: center;">
                            <p style="margin: 0; font-size: 12px; color: #94a3b8;">Need help? Please reply directly to this email to reach support.</p>
                            <p style="margin: 6px 0 0 0; font-size: 12px; color: #94a3b8;">&copy; 2026 RankCare. All rights reserved.</p>
                            </td>
                        </tr>

                        </table>
                    </td>
                    </tr>
                </table>
                </body>
                </html>
            """
        })

        logger.info("RESEND PAYMENT FAILURE EMAIL RESPONSE: %s", response)
        return True

    except Exception as exc:
        logger.exception("FAILED TO SEND PAYMENT FAILURE EMAIL: %s", exc)
        return False


def send_password_reset_email(to_email: str, name: str, reset_url: str) -> bool:
    settings = get_settings()

    if not settings.RESEND_API_KEY:
        logger.info("[EMAIL DISABLED] Password reset link for %s: %s", to_email, reset_url)
        return False

    resend.api_key = settings.RESEND_API_KEY
    sender = settings.EMAIL_FROM or "onboarding@resend.dev"
    subject = "Reset your password"

    try:
        response = resend.Emails.send({
            "from": sender,
            "to": [to_email],
            "subject": subject,
            "html": f"""
                <!DOCTYPE html>
                <html>
                <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Reset your password</title>
                </head>
                <body style="margin: 0; padding: 0; background-color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; -webkit-font-smoothing: antialiased;">
                <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color: #f8fafc; padding: 32px 16px;">
                    <tr>
                    <td align="center">
                        <!-- Main Card Container -->
                        <table width="100%" border="0" cellspacing="0" cellpadding="0" style="max-width: 440px; background-color: #ffffff; border-radius: 16px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);">
                        
                        <!-- Header Banner -->
                        <tr>
                            <td style="background-color: #0f172a; padding: 32px 24px; text-align: center;">
                            <!-- Key Icon Wrapper -->
                            <div style="display: inline-block; background-color: #2563eb; width: 48px; height: 48px; border-radius: 50%; text-align: center; margin-bottom: 16px;">
                                <span style="color: #ffffff; font-size: 20px; line-height: 46px; font-weight: bold;">🔑</span>
                            </div>
                            <h1 style="margin: 0; color: #ffffff; font-size: 20px; font-weight: 700; letter-spacing: -0.025em;">Reset Your Password</h1>
                            <p style="margin: 4px 0 0 0; color: #94a3b8; font-size: 14px;">RankCare Account Security</p>
                            </td>
                        </tr>

                        <!-- Content Body -->
                        <tr>
                            <td style="padding: 24px;">
                            <p style="margin: 0 0 16px 0; font-size: 15px; color: #334155; line-height: 1.5;">Hi <strong>{name}</strong>,</p>
                            <p style="margin: 0 0 24px 0; font-size: 14px; color: #64748b; line-height: 1.5;">We received a request to reset your password. If you didn't make this request, you can safely ignore this email.</p>

                            <!-- Action Button -->
                            <table width="100%" border="0" cellspacing="0" cellpadding="0" style="margin-bottom: 28px;">
                                <tr>
                                <td align="center">
                                    <a href="{reset_url}" target="_blank" style="display: inline-block; background-color: #000000; color: #ffffff; font-size: 14px; font-weight: 600; text-decoration: none; padding: 12px 32px; border-radius: 8px; box-shadow: 0 2px 4px rgba(37, 99, 235, 0.2);">Reset Password</a>
                                </td>
                                </tr>
                            </table>

                            <!-- Fallback URL Section -->
                            <table width="100%" border="0" cellspacing="0" cellpadding="0" style="border-top: 1px solid #e2e8f0; padding-top: 16px;">
                                <tr>
                                <td>
                                    <p style="margin: 0 0 8px 0; font-size: 12px; color: #94a3b8; line-height: 1.4;">If the button above doesn't work, copy and paste this link into your web browser:</p>
                                    <p style="margin: 0; font-size: 12px; color: #2563eb; word-break: break-all; font-family: monospace; line-height: 1.4;"><a href="{reset_url}" style="color: #2563eb; text-decoration: none;">{reset_url}</a></p>
                                </td>
                                </tr>
                            </table>
                            </td>
                        </tr>

                        <!-- Footer -->
                        <tr>
                            <td style="padding: 0 24px 24px 24px; text-align: center;">
                            <p style="margin: 0; font-size: 12px; color: #94a3b8;">This link will expire in 1 hour for your security.</p>
                            <p style="margin: 6px 0 0 0; font-size: 12px; color: #94a3b8;">&copy; 2026 RankCare. All rights reserved.</p>
                            </td>
                        </tr>

                        </table>
                    </td>
                    </tr>
                </table>
                </body>
                </html>
            """
        })

        logger.info("RESEND PASSWORD RESET EMAIL RESPONSE: %s", response)
        logger.info("PASSWORD RESET URL SENT: %s", reset_url)
        return True

    except Exception as exc:
        logger.exception("FAILED TO SEND PASSWORD RESET EMAIL: %s", exc)
        return False


def send_email_with_attachment(
    to_email: str,
    subject: str,
    html_body: str,
    attachment_bytes: bytes,
    attachment_filename: str,
) -> bool:
    settings = get_settings()

    if not settings.RESEND_API_KEY:
        logger.info("[EMAIL DISABLED] Attachment email for %s: %s", to_email, attachment_filename)
        return False

    resend.api_key = settings.RESEND_API_KEY
    sender = settings.EMAIL_FROM or "onboarding@resend.dev"

    try:
        response = resend.Emails.send({
            "from": sender,
            "to": [to_email],
            "subject": subject,
            "html": html_body,
            "attachments": [
                {
                    "filename": attachment_filename,
                    "content": attachment_bytes.decode("latin-1"),
                }
            ],
        })
        logger.info("RESEND ATTACHMENT EMAIL RESPONSE: %s", response)
        return True
    except Exception as exc:
        logger.exception("FAILED TO SEND ATTACHMENT EMAIL: %s", exc)
        return False



