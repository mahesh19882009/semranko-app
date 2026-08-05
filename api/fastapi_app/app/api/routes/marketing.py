from fastapi import APIRouter
from pydantic import BaseModel
from typing import List

router = APIRouter(prefix="/marketing", tags=["marketing"])


class FaqItem(BaseModel):
    q: str
    a: str


MARKETING_FAQS = [
    {
        "q": "What counts as a credit, and how are they used?",
        "a": "Credits are our internal currency. A single keyword research deep dive costs 15 credits. Pulling up to 100 bulk keywords costs 50 credits. Generating complete competitor spy or keyword idea reports costs 30 credits. If the data is already stored in our high-speed local database cache, it costs you 0 credits!",
    },
    {
        "q": "Can I add a single keyword if your plan mentions 'Bulk Uploads'?",
        "a": "Yes, absolutely! You can search for a single keyword whenever you like. The 'Bulk Upload' limit simply represents the maximum number of keywords you are allowed to paste into our tool inside a single list at one time to prevent system abuse.",
    },
    {
        "q": "What happens if I search for the same keyword twice?",
        "a": "If you search for a keyword that you or any other user processed recently, our system grabs it instantly from our local database cache. This saves your credit balance, resulting in a charge of exactly 0 credits.",
    },
    {
        "q": "Do my unused credits roll over to the next month?",
        "a": "No. To keep our operational costs minimal and passes affordable for low budgets, unused credits expire automatically at midnight on the final day of your monthly billing cycle when your balance resets.",
    },
    {
        "q": "Can I swap tracked keywords in my dashboard whenever I want?",
        "a": "Yes! You can freely delete and add tracked keywords anytime. Each new tracked keyword requires a 20-credit upfront deduction to fund the upcoming month of weekly position checks. There are no lock-in periods or swap fees.",
    },
    {
        "q": "Is AI Overview tracking available on all plans?",
        "a": "AI Overview (AIO) tracking is available on all paid plans: Starter, Pro, and Agency. Free Trial users can explore the platform but do not have access to AIO tracking. Upgrade to a paid plan to unlock real-time monitoring of your keywords inside Google AI responses.",
    },
]


@router.get("/pricing-faqs", response_model=List[FaqItem])
async def get_pricing_faqs():
    return MARKETING_FAQS
