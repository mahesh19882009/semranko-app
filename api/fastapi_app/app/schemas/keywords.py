from typing import Optional
from pydantic import BaseModel


class KeywordMetricRequest(BaseModel):
    keyword: str
    location: str = "India"
    device: str = "desktop"


class KeywordMetricsRequest(BaseModel):
    keywords: list[KeywordMetricRequest]


class KeywordMetricResult(BaseModel):
    keyword: str
    location: str
    volume: Optional[int] = None
    kd: Optional[int] = None
    cpc: Optional[float] = None
    competition: Optional[float] = None
    intent: Optional[str] = None
    backlinks: Optional[float] = None
    referring_domains: Optional[float] = None
    cached: bool = False


class KeywordMetricsResponse(BaseModel):
    credits_charged: int
    cached_count: int
    results: list[KeywordMetricResult]


class KeywordIdeasRequest(BaseModel):
    seed_keyword: str
    location: str = "India"


class CompetitorSpyRequest(BaseModel):
    domain: str
    location: str = "India"
    limit: int = 100
