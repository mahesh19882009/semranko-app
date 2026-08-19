import uuid
import logging
from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc, nullslast
from typing import Dict, Any, Optional

from app.api.deps import db_session, get_current_user
from app.schemas.common import ok
from app.schemas.credit import CreditPurchaseRequest, CreditPurchaseResponse, CreditBalanceResponse, CreditLedgerEntry
from app.schemas.billing import BillingHistoryItem, BillingHistoryResponse, UsageLogResponse
from app.services.payment_service import create_order, verify_payment_signature, activate_subscription
from app.services.credit_service import add_purchased_credits, get_credit_balance, create_pending_ledger_entry, finalize_pending_ledger_entry
from app.db.models import User, PaymentOrder, CreditLedger, TopUpPackage
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
        amount=float(requested_credits),
        action_type="CREDIT_TOP_UP",
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
        existing_ledger = db.scalar(
            select(CreditLedger).where(
                CreditLedger.relatedOrderId == order_id,
                CreditLedger.status.in_(["success", "completed"])
            )
        )
        if existing_ledger:
            return ok("Payment already verified and credits added", {
                "credits_added": existing_ledger.amount,
                "new_balance": get_credit_balance(db, current_user['id']),
            })
        logger.info(f"[verify-credit-payment] Payment paid but no successful ledger found, adding credits now")

    payment_order.status = "paid"
    payment_order.razorpayPaymentId = payment_id
    db.add(payment_order)
    db.commit()

    # Calculate credits based on multiplier (stored in planId) for credit top-ups
    if payment_order.purchaseType == "CREDIT_TOP_UP":
        package = db.scalar(select(TopUpPackage).where(TopUpPackage.id == payment_order.topUpPackageId)) if payment_order.topUpPackageId else None
        if package is None:
            # Historical multiplier orders retain their former interpretation.
            from app.core.config import get_settings
            credits_to_add = int(payment_order.planId) * get_settings().CREDIT_TOP_UP_CONFIG.get("credits_per_100_inr", 600)
        else:
            credits_to_add = package.credits
        logger.info(f"[verify-credit-payment] CREDIT_TOP_UP credits_to_add={credits_to_add}")
    else:
        credits_to_add = payment_order.credit_applied_paise / 100.0 if payment_order.credit_applied_paise else 0
        logger.info(f"[verify-credit-payment] Other payment type: credits_to_add={credits_to_add}")

    # Finalize existing pending ledger entry instead of creating a duplicate
    pending_ledger = db.scalar(
        select(CreditLedger).where(
            CreditLedger.relatedOrderId == order_id,
            CreditLedger.status == "pending",
        )
    )

    if pending_ledger and credits_to_add > 0:
        pending_ledger.status = "success"
        pending_ledger.amountPaidInr = float(payment_order.amount) / 100.0
        db.add(pending_ledger)
        db.flush()

        db.commit()
        new_balance = add_purchased_credits(
            db=db,
            user_id=pending_ledger.userId,
            amount=credits_to_add,
            description=f"Credit purchase via Razorpay order {order_id}",
            related_order_id=order_id,
        )
        logger.info(f"[verify-credit-payment] Finalized pending ledger and added {credits_to_add} credits. New balance: {new_balance}")
    elif credits_to_add > 0:
        new_balance = add_purchased_credits(
            db=db,
            user_id=current_user['id'],
            amount=credits_to_add,
            description=f"Credit purchase via Razorpay order {order_id}",
            related_order_id=order_id,
        )
        logger.info(f"[verify-credit-payment] Credits added. New balance: {new_balance}")
    else:
        logger.warning(f"[verify-credit-payment] No credits to add: credits_to_add={credits_to_add}")

    email_service.send_payment_success_email(
        to_email=current_user.get('email'),
        name=db.scalar(select(User.name).where(User.id == current_user['id'])) or "User",
        plan_name="Credit Pack",
        amount=payment_order.amount / 100.0,
        order_id=order_id,
    )

    return ok("Credits added successfully", {
        "credits_added": credits_to_add,
        "new_balance": get_credit_balance(db, current_user['id']),
    })


@router.get("/history", response_model=BillingHistoryResponse)
async def get_billing_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    payment_orders = (
        db.query(PaymentOrder)
        .filter(PaymentOrder.userId == current_user['id'])
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

        # For subscription payments, check if credits were added via ledger
        if not ledger and purchase_type != "CREDIT_TOP_UP":
            ledger = db.scalar(
                select(CreditLedger).where(
                    CreditLedger.userId == current_user['id'],
                    CreditLedger.actionType == "purchase",
                    CreditLedger.relatedOrderId == order.razorpayOrderId
                )
            )

        history.append(BillingHistoryItem(
            id=order.id,
            order_id=order_id,
            amount_paid_inr=amount_paid_inr,
            status=status,
            timestamp=(order.createdAt or order.updatedAt).isoformat() if (order.createdAt or order.updatedAt) else None,
            invoice_number=(ledger.invoiceNumber if ledger else None) or f"INV-{order.id[:8].upper()}",
            purchase_type=purchase_type,
        ))

    return BillingHistoryResponse(history=history)


@router.get("/invoice/{invoice_id}/download")
async def download_invoice(
    invoice_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    owner_id = current_user['id']
    
    logger.info(f"[invoice-download] Looking for invoice_id: {invoice_id} for user: {current_user['id']}")
    
    # Handle invoice_number format like "INV-ABC12345"
    if invoice_id.startswith("INV-"):
        invoice_id = invoice_id[4:]  # Remove "INV-" prefix
        logger.info(f"[invoice-download] Stripped INV- prefix, searching for: {invoice_id}")
    
    # Try to find by CreditLedger first, then by PaymentOrder
    ledger = db.scalar(select(CreditLedger).where(CreditLedger.id == invoice_id))
    payment_order = None
    
    if not ledger:
        # Try to find by PaymentOrder ID
        payment_order = db.scalar(select(PaymentOrder).where(PaymentOrder.id == invoice_id))
        if not payment_order:
            # Try to find by razorpayOrderId
            payment_order = db.scalar(select(PaymentOrder).where(PaymentOrder.razorpayOrderId == invoice_id))
        
        if payment_order:
            ledger = db.scalar(
                select(CreditLedger).where(CreditLedger.relatedOrderId == payment_order.razorpayOrderId)
            )
    
    logger.info(f"[invoice-download] Found ledger: {ledger is not None}, payment_order: {payment_order is not None}")
    
    if not ledger and not payment_order:
        # List some available orders for debugging
        available_orders = db.scalars(
            select(PaymentOrder).where(PaymentOrder.userId == owner_id).limit(5)
        ).all()
        logger.info(f"[invoice-download] Available orders for user: {[o.id for o in available_orders]}")
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    # Check ownership
    if ledger and ledger.userId != owner_id:
        raise HTTPException(status_code=403, detail="Not your invoice")
    if payment_order and payment_order.userId != owner_id:
        raise HTTPException(status_code=403, detail="Not your invoice")
    
    # Check status - allow download if payment is paid regardless of ledger status
    if payment_order and payment_order.status not in {"paid", "captured"}:
        raise HTTPException(status_code=400, detail="Invoice is not available for download")
    
    # If no payment_order but ledger exists, check ledger status
    if not payment_order and ledger and ledger.status not in {"completed", "success"}:
        raise HTTPException(status_code=400, detail="Invoice is not available for download")
    
    # Use payment_order if we have it, otherwise get it from ledger
    if not payment_order and ledger:
        payment_order = db.scalar(
            select(PaymentOrder).where(PaymentOrder.razorpayOrderId == ledger.relatedOrderId)
        )

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

        amount = float(ledger.amount or 0)
        gst_rate = 0.18
        
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
            credits_added = int(total_inr / 0.1667) if total_inr > 0 else 0
            description = f"Credit Top-Up: {credits_added:,} Credits (600 credits per ₹100)"
            hsn_code = "9983"
        else:
            if payment_order:
                plan_key = {0: "starter", 1: "pro", 2: "agency"}.get(payment_order.planId, "starter")
                plan = PLAN_DEFINITIONS.get(plan_key, {})
                plan_name = plan.get("name", "Subscription Plan")
                description = f"Subscription: {plan_name} - Monthly Plan"
            else:
                description = ledger.description or "Subscription plan purchase"
            hsn_code = "9983"

        story.append(Paragraph("TAX INVOICE", styles["Heading1"]))
        story.append(Spacer(1, 0.1 * inch))

        from app.core.config import get_settings
        settings = get_settings()

        company_address = settings.COMPANY_ADDRESS or ""
        company_state = settings.COMPANY_STATE or ""
        company_state_code = settings.COMPANY_STATE_CODE or ""
        company_gstin = settings.GSTIN or ""
        company_name = settings.COMPANY_NAME or "Semranko Technologies"
        company_email = settings.COMPANY_EMAIL or "support@semranko.com"

        user = db.scalar(select(User).where(User.id == owner_id))
        bill_to_name = user.name if user else "Customer"
        bill_to_email = user.email if user else ""
        bill_to_gstin = user.userGstin if user else None
        bill_to_gst_name = user.userGstName if user else None
        bill_to_gst_address = user.userGstAddress if user else None
        bill_to_gst_state = user.userGstState if user else None
        bill_to_gst_state_code = user.userGstStateCode if user else None

        company_lines = [
            Paragraph(f"<b>{company_name}</b>", styles["Normal"]),
        ]
        if company_address:
            company_lines.append(Paragraph(company_address, styles["Normal"]))
        company_lines.extend([
            Paragraph(f"{company_state} - {company_state_code}", styles["Normal"]),
            Paragraph(f"GSTIN: {company_gstin}", styles["Normal"]),
            Paragraph(f"Email: {company_email}", styles["Normal"]),
        ])

        bill_lines = [
            Paragraph(f"<b>Bill To</b>", styles["Normal"]),
            Paragraph(f"<b>{bill_to_name}</b>", styles["Normal"]),
        ]
        if bill_to_email:
            bill_lines.append(Paragraph(f"Email: {bill_to_email}", styles["Normal"]))
        if bill_to_gstin:
            bill_lines.append(Paragraph(f"GSTIN: {bill_to_gstin}", styles["Normal"]))
        if bill_to_gst_name:
            bill_lines.append(Paragraph(f"Name: {bill_to_gst_name}", styles["Normal"]))
        if bill_to_gst_address:
            bill_lines.append(Paragraph(f"Address: {bill_to_gst_address}", styles["Normal"]))
        if bill_to_gst_state:
            bill_lines.append(Paragraph(f"State: {bill_to_gst_state} ({bill_to_gst_state_code})", styles["Normal"]))

        info_table_data = [
            [company_lines, bill_lines],
        ]
        info_table = Table(info_table_data, colWidths=[3.4 * inch, 3.4 * inch])
        info_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#0f172a")),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f8fafc")),
            ("BACKGROUND", (1, 0), (1, -1), colors.HexColor("#ffffff")),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 0.15 * inch))

        invoice_number = (ledger.invoiceNumber if ledger else None) or f"INV-{(payment_order.id if payment_order else invoice_id)[:8].upper()}"
        invoice_date = (ledger.createdAt if ledger else payment_order.createdAt).strftime("%d/%m/%Y") if (ledger or payment_order) else "N/A"
        order_id = payment_order.razorpayOrderId if payment_order else (ledger.relatedOrderId if ledger else "N/A")
        payment_id = payment_order.razorpayPaymentId if payment_order else "N/A"

        meta_data = [
            ["Invoice Number", invoice_number, "Date", invoice_date],
            ["Order ID", order_id, "Payment ID", payment_id],
        ]
        meta_table = Table(meta_data, colWidths=[1.5 * inch, 2.5 * inch, 1 * inch, 2 * inch])
        meta_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f1f5f9")),
            ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#f1f5f9")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 0.15 * inch))

        data = [
            ["HSN/SAC", "Description", "Amount (INR)", "GST Rate", "CGST (INR)", "SGST (INR)", "Total (INR)"],
            [hsn_code, description, f"{base_inr:.2f}", "18%", f"{cgst:.2f}", f"{sgst:.2f}", f"{total:.2f}"],
        ]

        table = Table(data, colWidths=[0.9 * inch, 2.2 * inch, 1.1 * inch, 0.9 * inch, 1 * inch, 1 * inch, 1.1 * inch])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
            ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, -1), (-1, -1), 9),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e2e8f0")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(table)
        story.append(Spacer(1, 0.15 * inch))

        summary_data = [
            ["Sub Total", f"₹{base_inr:.2f}"],
            ["CGST (9%)", f"₹{cgst:.2f}"],
            ["SGST (9%)", f"₹{sgst:.2f}"],
            ["Total", f"₹{total:.2f}"],
        ]
        summary_table = Table(summary_data, colWidths=[4 * inch, 2 * inch])
        summary_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#f1f5f9")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 0.15 * inch))

        terms_data = [
            ["Terms & Conditions:"],
            ["1. Payment is due immediately upon invoice receipt."],
            ["2. Once purchased, credits are non-refundable."],
            ["3. For any queries, contact us at support@semranko.com."],
        ]
        terms_table = Table(terms_data, colWidths=[6 * inch])
        terms_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (0, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(terms_table)
        story.append(Spacer(1, 0.15 * inch))

        story.append(Paragraph("Authorized Signatory", styles["Normal"]))
        story.append(Spacer(1, 0.4 * inch))
        story.append(Paragraph("_________________________", styles["Normal"]))
        story.append(Paragraph(f"<b>{company_name}</b>", styles["Normal"]))

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


@router.get("/usage-log", response_model=UsageLogResponse)
async def get_usage_log(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    action_type: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(db_session),
):
    from datetime import datetime, timezone

    user_id = current_user["id"]

    query = db.query(CreditLedger).filter(
        (CreditLedger.userId == user_id) | (CreditLedger.ownerId == user_id)
    )

    if action_type:
        query = query.filter(CreditLedger.actionType == action_type)

    total = query.count()

    offset = (page - 1) * limit
    entries = (
        query.order_by(CreditLedger.createdAt.desc(), CreditLedger.id.desc())
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
            "timestamp": (entry.timestamp or entry.createdAt).strftime("%Y-%m-%dT%H:%M:%SZ") if (entry.timestamp or entry.createdAt) else None,
            "description": entry.description,
            "triggered_by_user_id": entry.triggeredByUserId,
        })

    now = datetime.now(timezone.utc)
    cycle_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    spent_this_month = (
        db.query(func.coalesce(func.sum(CreditLedger.creditsSpent), 0))
        .filter((CreditLedger.userId == user_id) | (CreditLedger.ownerId == user_id))
        .filter(CreditLedger.timestamp >= cycle_start)
        .filter(CreditLedger.actionType != "TOP_UP")
        .scalar()
    )

    cache_hits = (
        db.query(func.count(CreditLedger.id))
        .filter((CreditLedger.userId == user_id) | (CreditLedger.ownerId == user_id))
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
    user_id = current_user["id"]

    query = db.query(CreditLedger).filter(
        (CreditLedger.userId == user_id) | (CreditLedger.ownerId == user_id)
    )

    total = query.count()

    offset = (page - 1) * limit
    entries = (
        query.order_by(CreditLedger.createdAt.desc(), CreditLedger.id.desc())
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
        "CREDIT_TOP_UP": "Purchased Credit Top-Up",
        "refund": "Credit Refund (Failed Operation)",
    }

    items = []
    for entry in entries:
        amount = float(entry.amount or 0)
        display_amount = f"{amount:+.0f}"
        color = "green" if amount > 0 else "red"

        items.append({
            "ledger_id": entry.id,
            "timestamp": (entry.timestamp or entry.createdAt).strftime("%Y-%m-%dT%H:%M:%SZ") if (entry.timestamp or entry.createdAt) else None,
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
