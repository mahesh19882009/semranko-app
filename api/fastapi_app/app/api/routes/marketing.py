from fastapi import APIRouter
from pydantic import BaseModel
from typing import List

router = APIRouter(prefix="/marketing", tags=["marketing"])


class FaqItem(BaseModel):
    q: str
    a: str


MARKETING_FAQS = [
    {
        "q": "How does the credit system work?",
        "a": "RankCare uses a pure consumption model. There are no hidden keyword limits. Every action deducts credits transparently: adding a keyword costs 25 credits, weekly refresh is 15 credits/keyword, keyword research is 20 credits, competitor spy is 20 credits, extra projects are 10 credits each (first project is free), and CSV exports are 10 credits. Unused credits do not roll over to the next month.",
    },
    {
        "q": "Why was I charged for a failed operation?",
        "a": "If an operation fails after credits are deducted, our system automatically refunds the credits to your account. You will see a green 'Credit Refund (Failed Operation)' entry in your Usage & Activity Log.",
    },
    {
        "q": "How do I add more projects?",
        "a": "Your first project is completely free. Every additional project costs 10 credits. If your credit balance is insufficient, you will see a clear message prompting you to top up credits before creating another project.",
    },
    {
        "q": "Do credits roll over month to month?",
        "a": "No. Credits reset when you subscribe to a new plan cycle. To keep pricing transparent, unused credits expire at the end of your current billing cycle. You can top up 1,000 credits anytime for a flat ₹500 on the Billing page.",
    },
    {
        "q": "What is the difference between tracked keywords and normal keywords?",
        "a": "Normal keywords are added to your project for on-demand research and weekly position updates. Tracked keywords are special entries you can enable per keyword to monitor AI Overview (AIO) appearances. You can toggle AI tracking on or off anytime from the keyword table. There is no separate 30-day lock or extra charge for AI tracking itself.",
    },
    {
        "q": "Is AI Overview tracking available on all plans?",
        "a": "AI Overview (AIO) tracking is available on Starter, Pro, and Agency plans. Free Trial users cannot access AIO tracking. You can toggle AI tracking per keyword from the keyword table.",
    },
    {
        "q": "How can I see exactly where my credits went?",
        "a": "Visit the Usage & Activity Log page. It shows every credit deduction and refund with the exact tool used, the keyword or domain queried, timestamp, and credit amount. Green entries are refunds or top-ups; red entries are deductions.",
    },
]


@router.get("/pricing-faqs", response_model=List[FaqItem])
async def get_pricing_faqs():
    return MARKETING_FAQS
