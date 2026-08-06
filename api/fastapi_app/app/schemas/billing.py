from pydantic import BaseModel
from typing import Optional, List


class BillingHistoryItem(BaseModel):
    id: str
    order_id: Optional[str] = None
    amount_paid_inr: Optional[float] = None
    status: str
    timestamp: Optional[str] = None
    invoice_number: Optional[str] = None
    purchase_type: Optional[str] = None  # SUBSCRIPTION_UPGRADE or CREDIT_TOP_UP
    gst_amount: Optional[float] = None
    gst_rate: Optional[float] = None
    base_amount: Optional[float] = None
    credit_applied: Optional[float] = None
    gross_amount: Optional[float] = None
    plan_name: Optional[str] = None
    plan_key: Optional[str] = None
    user_name: Optional[str] = None
    user_email: Optional[str] = None


class BillingHistoryResponse(BaseModel):
    history: List[BillingHistoryItem]


class UsageLogItem(BaseModel):
    id: str
    action_type: str
    query_target: Optional[str] = None
    credits_spent: Optional[int] = None
    timestamp: Optional[str] = None
    description: Optional[str] = None
    triggered_by_user_id: Optional[str] = None


class UsageLogResponse(BaseModel):
    items: List[UsageLogItem]
    page: int
    limit: int
    total: int
    total_pages: int
    total_spent_this_month: int
    total_saved_by_cache: int


class ExportReportRequest(BaseModel):
    start_date: str
    end_date: str
    export_format: str = "csv"
    email_recipients: List[str] = []
