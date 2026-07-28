from pydantic import BaseModel, Field
from typing import Optional


class PaymentOrderCreate(BaseModel):
    plan_id: int = Field(..., description="Plan ID to upgrade to")
    amount: int = Field(..., description="Amount in smallest currency unit (e.g., paise)")
    currency: str = Field(default="INR", description="Currency code")


class PaymentVerifyRequest(BaseModel):
    razorpay_order_id: str = Field(..., description="Razorpay Order ID")
    razorpay_payment_id: str = Field(..., description="Razorpay Payment ID")
    razorpay_signature: str = Field(..., description="Razorpay Signature")
    plan_id: int = Field(..., description="Plan ID that was purchased")


class PaymentOrderResponse(BaseModel):
    order_id: str
    amount: int
    currency: str
    key: str
    plan_id: int
    user_id: int
    is_mock: bool = False


class PaymentVerifyResponse(BaseModel):
    message: str
    subscription: dict


class SubscriptionResponse(BaseModel):
    plan_name: str
    plan_id: Optional[int]
    status: str
    current_period_start: Optional[str] = None
    current_period_end: Optional[str] = None
    limits: dict