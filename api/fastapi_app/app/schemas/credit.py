from typing import Optional
from pydantic import BaseModel


class CreditPurchaseRequest(BaseModel):
    credits: int


class CreditPurchaseResponse(BaseModel):
    order_id: str
    amount: int
    credits: int
    key_id: str
    is_mock: bool
    currency: str = "INR"


class CreditBalanceResponse(BaseModel):
    balance: float
    currency: str = "INR"


class CreditLedgerEntry(BaseModel):
    id: str
    amount: float
    action_type: str
    description: Optional[str]
    related_order_id: Optional[str]
    created_at: Optional[str]
