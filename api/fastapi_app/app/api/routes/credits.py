import uuid
import logging
from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from typing import Dict, Any, Optional

from app.api.deps import db_session, get_current_user
from app.schemas.common import ok
from app.schemas.credit import CreditPurchaseRequest, CreditPurchaseResponse, CreditBalanceResponse, CreditLedgerEntry
from app.schemas.billing import BillingHistoryItem, BillingHistoryResponse, UsageLogResponse
from app.services.payment_service import create_order, verify_payment_signature, activate_subscription
from app.services.credit_service import add_purchased_credits, get_credit_balance, create_pending_ledger_entry, finalize_pending_ledger_entry
from app.db.models import User, PaymentOrder, CreditLedger
from app.services import email_service
from app.services.plan_service import PLAN_DEFINITIONS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["billing"])


@router.post("/credit-purchase-order")
async def create_credit_purchase_order(
    request: CreditPurchaseRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    requested_credits = request.credits
    
    # Backend Validation: Must be >= 1000 and multiple of 1000
    if requested_credits < 1000:
        raise HTTPException(status_code=400, detail="Minimum 1,000 credits required")
    
    if requested_credits % 1000 != 0:
        raise HTTPException(status_code=400, detail="Please enter credit volumes only in clean multiples of 1,000")

    # Cost Math Alignment: ₹0.20 per credit
    base_amount_inr = requested_credits * 0.20
    gst_amount_inr = base_amount_inr * 0.18
    total_amount_inr = base_amount_inr + gst_amount_inr
    
    amount_paise = int(total_amount_inr * 100)

    order = create_order(amount=amount_paise, currency="INR")

    payment_order = PaymentOrder(
        userId=current_user['id'],
        razorpayOrderId=order["id"],
        planId=requested_credits // 1000,
        amount=amount_paise,
        credit_applied_paise=amount_paise,
        currency="INR",
        status="created",
        purchaseType="CREDIT_TOP_UP",
    )
    db.add(payment_order)
    db.flush()

    create_pending_ledger_entry(
        db=db,
        user_id=current_user['id'],
        owner_id=current_user['id'],
        amount=float(amount_paise) / 100.0,
        action_type="purchase",
        description=f"Credit top-up order {order['id']} ({requested_credits} credits)",
        related_order_id=order["id"],
    )

    db.commit()

    return ok("Credit purchase order created", {
        "order_id": order["id"],
        "amount": amount_paise,
        "credits": requested_credits,
        "base_amount_inr": base_amount_inr,
        "gst_amount_inr": gst_amount_inr,
        "total_amount_inr": total_amount_inr,
        "key_id": order.get("key", ""),
        "is_mock": order.get("mock", False),
        "currency": "INR",
    })


@router.get("/credits/balance")
async def get_credits_balance(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    balance = get_credit_balance(db, current_user['id'])

    entries = (
        db.query(CreditLedger)
        .filter(CreditLedger.userId == current_user['id'])
        .order_by(CreditLedger.createdAt.desc())
        .limit(50)
        .all()
    )

    history = [
        CreditLedgerEntry(
            id=e.id,
            amount=float(e.amount),
            action_type=e.actionType,
            description=e.description,
            related_order_id=e.relatedOrderId,
            created_at=e.createdAt.isoformat() if e.createdAt else None,
        )
        for e in entries
    ]

    return ok("Credit balance retrieved", {
        "balance": balance,
        "history": history,
    })


@router.post("/verify-credit-payment")
async def verify_credit_payment(
    request_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    order_id = request_data.get("razorpay_order_id")
    payment_id = request_data.get("razorpay_payment_id")
    signature = request_data.get("razorpay_signature")

    if not order_id or not payment_id or not signature:
        raise HTTPException(status_code=400, detail="Missing payment fields")

    is_valid = verify_payment_signature(order_id, payment_id, signature)
    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid payment signature")

    payment_order = db.scalar(select(PaymentOrder).where(PaymentOrder.razorpayOrderId == order_id))
    if not payment_order:
        raise HTTPException(status_code=404, detail="Payment order not found")

    if payment_order.userId != current_user['id']:
        raise HTTPException(status_code=403, detail="Not your payment order")

    if payment_order.status == "paid":
        return ok("Payment already verified", {
            "credits_added": payment_order.credit_applied_paise / 100.0 if payment_order.credit_applied_paise else 0,
        })

    payment_order.status = "paid"
    payment_order.razorpayPaymentId = payment_id
    db.add(payment_order)
    db.commit()

    credits_to_add = payment_order.credit_applied_paise / 100.0 if payment_order.credit_applied_paise else 0
    if credits_to_add > 0:
        add_purchased_credits(
            db=db,
            user_id=current_user['id'],
            amount=credits_to_add,
            description=f"Credit purchase via Razorpay order {order_id}",
            related_order_id=order_id,
        )

    email_service.send_payment_success_email(
        to_email=current_user.get('email'),
        name=db.scalar(select(User.name).where(User.id == current_user['id'])) or "User",
        plan_name="Credit Pack",
        amount=payment_order.amount / 100.0,
        order_id=order_id,
    )

    return ok("Credits added successfully", {
        "credits_added": credits_to_add,
    })


@router.get("/history", response_model=BillingHistoryResponse)
async def get_billing_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    from app.services.team_service import get_team_owner_id
    owner_id = get_team_owner_id(db, current_user['id'])
    
    payment_orders = (
        db.query(PaymentOrder)
        .filter(PaymentOrder.userId == owner_id)
        .order_by(PaymentOrder.createdAt.desc())
        .all()
    )

    history = []
    for order in payment_orders:
        ledger = db.scalar(
            select(CreditLedger).where(CreditLedger.relatedOrderId == order.razorpayOrderId)
        )
        
        amount_paid_inr = order.amount / 100.0 if order.amount else None
        status = order.status or "pending"
        order_id = order.razorpayOrderId
        purchase_type = getattr(order, "purchaseType", None)

        history.append(BillingHistoryItem(
            id=ledger.id if ledger else order.id,
            order_id=order_id,
            amount_paid_inr=amount_paid_inr,
            status=status,
            timestamp=order.createdAt.isoformat() if order.createdAt else None,
            invoice_number=(ledger.invoiceNumber if ledger else None) or f"INV-{order.id[:8].upper()}",
            purchase_type=purchase_type,
        ))

    return BillingHistoryResponse(history=history)


@router.get("/invoice/{ledger_id}/download")
async def download_invoice(
    ledger_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    from app.services.team_service import get_team_owner_id
    ledger = db.scalar(select(CreditLedger).where(CreditLedger.id == ledger_id))
    if not ledger:
        raise HTTPException(status_code=404, detail="Invoice not found")

    owner_id = get_team_owner_id(db, current_user['id'])
    if ledger.userId != owner_id:
        raise HTTPException(status_code=403, detail="Not your invoice")

    if ledger.status not in {"completed", "success"}:
        raise HTTPException(status_code=400, detail="Invoice is not available for download")

    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from io import BytesIO

    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        story.append(Paragraph("RankCare Invoice", styles["Title"]))
        story.append(Spacer(1, 0.2 * inch))

        amount = float(ledger.amount or 0)
        gst_rate = 0.18
        
        payment_order = db.scalar(
            select(PaymentOrder).where(PaymentOrder.razorpayOrderId == ledger.relatedOrderId)
        )
        
        if payment_order and payment_order.amount:
            total_inr = payment_order.amount / 100.0
        else:
            total_inr = amount
        
        base_inr = round(total_inr / (1 + gst_rate), 2)
        cgst = round(base_inr * gst_rate / 2, 2)
        sgst = round(base_inr * gst_rate / 2, 2)
        total = round(base_inr + cgst + sgst, 2)
        
        is_credit_top_up = payment_order and payment_order.purchaseType == "CREDIT_TOP_UP"
        
        if is_credit_top_up:
            credits_added = int(total_inr / 0.20) if total_inr > 0 else 0
            description = f"Premium Core Platform Add-on: {credits_added:,} Live Processing Credits (Bound to active monthly cycle)"
        else:
            description = ledger.description or "Subscription plan purchase"

        story.append(Paragraph("INVOICE", styles["Heading1"]))
        story.append(Spacer(1, 0.15 * inch))
        
        company_info = [
            [Paragraph("<b>RankCare Technologies</b>", styles["Normal"])],
            [Paragraph("SEO Rank Tracking & Competitor Analysis", styles["Normal"])],
            [Paragraph("support@rankcare.com", styles["Normal"])],
            [Paragraph("GSTIN: 27AABCR1234L1ZZ", styles["Normal"])],
        ]
        company_table = Table(company_info, colWidths=[4 * inch])
        company_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ]))
        story.append(company_table)
        story.append(Spacer(1, 0.2 * inch))

        invoice_meta = [
            ["Invoice Number:", ledger.invoiceNumber or f"INV-{ledger.id[:8].upper()}"],
            ["Date:", ledger.createdAt.strftime("%d-%m-%Y") if ledger.createdAt else "N/A"],
            ["Order ID:", ledger.relatedOrderId or "N/A"],
            ["Payment ID:", payment_order.razorpayPaymentId if payment_order else "N/A"],
        ]
        meta_table = Table(invoice_meta, colWidths=[2 * inch, 4 * inch])
        meta_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (0, -1), 10),
            ("FONTSIZE", (1, 0), (1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 0.2 * inch))

        story.append(Paragraph("Description:", styles["Heading3"]))
        story.append(Paragraph(description, styles["Normal"]))
        story.append(Spacer(1, 0.2 * inch))

        data = [
            ["Description", "Amount (INR)"],
            [description, f"₹{base_inr:.2f}"],
            ["CGST (9%)", f"₹{cgst:.2f}"],
            ["SGST (9%)", f"₹{sgst:.2f}"],
            ["Total (INR)", f"₹{total:.2f}"],
        ]

        table = Table(data, colWidths=[4 * inch, 2 * inch])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 11),
            ("BACKGROUND", (0, 1), (-1, -2), colors.HexColor("#f8fafc")),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, -1), (-1, -1), 11),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e2e8f0")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ]))
        story.append(table)
        story.append(Spacer(1, 0.3 * inch))
        
        story.append(Paragraph("Thank you for your business!", styles["Normal"]))
        story.append(Paragraph("For any queries, contact us at support@rankcare.com", styles["Normal"]))

        doc.build(story)
        buffer.seek(0)

        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=invoice-{ledger.id}.pdf"
            },
        )
    except Exception as e:
        logger.exception(f"PDF generation failed for ledger {ledger_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate PDF invoice")


@router.post("/razorpay-webhook")
async def razorpay_credit_webhook(
    request_data: Dict[str, Any],
    signature: str = Header(None),
    db: Session = Depends(db_session),
):
    from app.services.payment_service import handle_webhook

    if not signature:
        raise HTTPException(status_code=400, detail="Missing signature")

    try:
        event = handle_webhook(request_data, signature)
    except Exception as exc:
        logger.exception("Webhook verification failed: %s", exc)
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    if not event:
        return {"received": True}

    event_type = event.get("type")
    payment_id = event.get("payment_id")
    order_id = event.get("order_id")

    payment_order = db.scalar(select(PaymentOrder).where(PaymentOrder.razorpayOrderId == order_id))
    if not payment_order:
        logger.warning(f"Payment order not found for order_id: {order_id}")
        return {"received": True}

    user = db.scalar(select(User).where(User.id == payment_order.userId))
    if not user:
        logger.warning(f"User not found for payment_order.userId: {payment_order.userId}")
        return {"received": True}

    if event_type == "payment.captured":
        payment_order.status = "paid"
        payment_order.razorpayPaymentId = payment_id
        db.add(payment_order)
        db.commit()

        ledger = finalize_pending_ledger_entry(
            db=db,
            order_id=order_id,
            amount_paid_inr=float(payment_order.amount) / 100.0,
        )

        if ledger:
            credits_to_add = ledger.amount
            user = db.scalar(select(User).where(User.id == ledger.userId))
            if user and credits_to_add > 0:
                current = float(getattr(user, "creditBalance", 0.0) or 0.0)
                user.creditBalance = round(current + credits_to_add, 2)
                db.add(user)
                db.commit()
                db.refresh(user)
                logger.info(f"Successfully added {credits_to_add} credits to user {user.id} (top-up, no plan extension)")
        else:
            credits_to_add = payment_order.credit_applied_paise / 100.0 if payment_order.credit_applied_paise else 0
            if credits_to_add > 0:
                try:
                    add_purchased_credits(
                        db=db,
                        user_id=user.id,
                        amount=credits_to_add,
                        description=f"Credit top-up via Razorpay order {order_id} (Bound to active monthly cycle)",
                        related_order_id=order_id,
                    )
                    logger.info(f"Successfully added {credits_to_add} credits to user {user.id} (top-up, no plan extension)")
                except Exception as exc:
                    logger.exception(f"Failed to add credits to user {user.id}: {exc}")

        email_service.send_payment_success_email(
            to_email=user.email,
            name=user.name,
            plan_name="Credit Top-Up",
            amount=payment_order.amount / 100.0,
            order_id=order_id,
        )

    return {"received": True }


@router.get("/usage-log", response_model=UsageLogResponse)
async def get_usage_log(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    action_type: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    from app.services.team_service import get_team_owner_id
    from datetime import datetime, timezone

    owner_id = get_team_owner_id(db, current_user["id"])

    query = db.query(CreditLedger).filter(CreditLedger.ownerId == owner_id)

    if action_type:
        query = query.filter(CreditLedger.actionType == action_type)

    total = query.count()

    offset = (page - 1) * limit
    entries = (
        query.order_by(CreditLedger.timestamp.desc(), CreditLedger.createdAt.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    items = []
    for entry in entries:
        items.append({
            "id": entry.id,
            "action_type": entry.actionType,
            "query_target": entry.queryTarget,
            "credits_spent": entry.creditsSpent,
            "timestamp": entry.timestamp.isoformat() if entry.timestamp else None,
            "description": entry.description,
            "triggered_by_user_id": entry.triggeredByUserId,
        })

    now = datetime.now(timezone.utc)
    cycle_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    spent_this_month = (
        db.query(func.coalesce(func.sum(CreditLedger.creditsSpent), 0))
        .filter(CreditLedger.ownerId == owner_id)
        .filter(CreditLedger.timestamp >= cycle_start)
        .filter(CreditLedger.actionType != "TOP_UP")
        .scalar()
    )

    cache_hits = (
        db.query(func.count(CreditLedger.id))
        .filter(CreditLedger.ownerId == owner_id)
        .filter(CreditLedger.timestamp >= cycle_start)
        .filter(CreditLedger.actionType == "CACHE_HIT")
        .scalar()
    )

    total_pages = (total + limit - 1) // limit if total > 0 else 1

    return UsageLogResponse(
        items=items,
        page=page,
        limit=limit,
        total=total,
        total_pages=total_pages,
        total_spent_this_month=int(spent_this_month or 0),
        total_saved_by_cache=int(cache_hits or 0) * 15,
    )


@router.get("/ledger-history")
async def get_ledger_history(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    from app.services.team_service import get_team_owner_id

    owner_id = get_team_owner_id(db, current_user["id"])

    query = db.query(CreditLedger).filter(
        CreditLedger.ownerId == owner_id,
        CreditLedger.status == "success",
    )

    total = query.count()

    offset = (page - 1) * limit
    entries = (
        query.order_by(CreditLedger.timestamp.desc(), CreditLedger.createdAt.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    action_display_map = {
        "ON_DEMAND_ADD": "Added New Keyword to Tracker",
        "WEEKLY_REFRESH": "Automated Monday Weekly Update",
        "KEYWORD_RESEARCH": "Keyword Research Lookup",
        "COMPETITOR_SPY": "Competitor Domain Spy Check",
        "ADD_NEW_DOMAIN": "Created Extra Multi-Domain Project",
        "DOWNLOAD_REPORT": "Exported Premium CSV Data Report",
        "CREDIT_TOP_UP": "Purchased 1,000 Token Top-Up Packet (+)",
        "refund": "Credit Refund (Failed Operation)",
    }

    items = []
    for entry in entries:
        amount = float(entry.amount or 0)
        display_amount = f"{amount:+.0f}"
        color = "green" if amount > 0 else "red"

        items.append({
            "ledger_id": entry.id,
            "timestamp": entry.timestamp.strftime("%Y-%m-%d %H:%M") if entry.timestamp else None,
            "action_type": action_display_map.get(entry.actionType, entry.actionType),
            "credits_deducted": display_amount,
            "credits_color": color,
            "keyword_or_domain_queried": entry.description or entry.queryTarget or entry.actionType,
        })

    total_pages = (total + limit - 1) // limit if total > 0 else 1

    return ok("Ledger history retrieved", {
        "items": items,
        "page": page,
        "limit": limit,
        "total": total,
        "total_pages": total_pages,
    })
