# Save Keyword Research & Competitor Spy Results to DB

## Current State
- `GET /keyword-research/research` returns DataForSEO `keyword_ideas/live` results. No DB persistence.
- `GET /keyword-research/competitor-spy` returns DataForSEO `serp_competitors/live` results. No DB persistence.
- `GET /keyword-metrics/ideas` and `/keyword-metrics/competitor-spy` also return results without persisting.
- `CompetitorCache` table exists with read helpers (`query_cached_competitor`) but **no write** is ever called.
- No equivalent cache table exists for keyword research ideas.
- **Project location/device are NOT saved to DB** despite frontend sending them. `Project` model has no `device` column and `location` is never set in `create_project()` / `update_project()`.

## Goal
1. Persist keyword research and competitor spy results to the database. One row per search key; re-search updates the existing row.
2. Fix project location/device persistence so cascading location selector and cache keys align correctly.

## Scope
- Keyword research: save ideas list per `(userId, seed_keyword, location_code)`
- Competitor spy: save keywords list per `(userId, domain, location_code)`
- Project: persist `location`, `locationCode`, and `device` on create/update
- All write paths: always upsert to DB (no cache-hit bypass), credits deducted by existing logic

## Out of Scope
- Frontend UI changes (research/spy pages already display returned data)
- Cache-hit optimization / skipping DFS calls
- Historical versioning

## Implementation Tasks

### 1. Add `locationCode` and `device` to Project model
**File:** `api/fastapi_app/app/db/models.py`

Add to `Project` class:
```python
location: Mapped[Optional[str]] = mapped_column(String, nullable=True)
locationCode: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
device: Mapped[Optional[str]] = mapped_column(String, nullable=True)
```

### 2. Create `KeywordResearchCache` model
**File:** `api/fastapi_app/app/db/models.py`

Add new table:
```python
class KeywordResearchCache(Base):
    __tablename__ = "KeywordResearchCache"
    userId: Mapped[str] = mapped_column(String, primary_key=True)
    seedKeyword: Mapped[str] = mapped_column(String, primary_key=True)
    locationCode: Mapped[int] = mapped_column(Integer, primary_key=True)
    ideasJson: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=func.now(), server_default=func.now(), onupdate=func.now())
```

### 3. Add Alembic migration
**File:** `api/fastapi_app/alembic/versions/<next>_add_project_location_and_research_cache.py`

- Add `location`, `locationCode`, `device` columns to `Project`
- Create `KeywordResearchCache` table
- No data backfill required

### 4. Persist project location/device
**File:** `api/fastapi_app/app/services/project_service.py`

Update `create_project()`:
```python
project = Project(
    name=name.strip(),
    domain=_normalize_domain(domain),
    userId=user_id,
    location=payload.get("location"),
    locationCode=payload.get("locationCode"),
    device=payload.get("device"),
)
```

Update `update_project()`:
```python
if "location" in payload:
    project.location = payload["location"]
if "locationCode" in payload:
    project.locationCode = payload["locationCode"]
if "device" in payload:
    project.device = payload["device"]
```

### 5. Add keyword research cache service
**File:** `api/fastapi_app/app/services/keyword_research_cache_service.py` (new)

```python
import json
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db.models import KeywordResearchCache

def save_research_cache(db: Session, user_id: str, seed_keyword: str, location_code: int, ideas: list[dict]) -> None:
    payload = {"ideasJson": json.dumps(ideas)}
    row = db.scalar(
        select(KeywordResearchCache).where(
            KeywordResearchCache.userId == user_id,
            KeywordResearchCache.seedKeyword == seed_keyword,
            KeywordResearchCache.locationCode == location_code,
        )
    )
    if row:
        for key, value in payload.items():
            setattr(row, key, value)
        row.updatedAt = datetime.utcnow()
        db.add(row)
    else:
        row = KeywordResearchCache(userId=user_id, seedKeyword=seed_keyword, locationCode=location_code, **payload)
        db.add(row)
```

### 6. Persist keyword research results
**File:** `api/fastapi_app/app/services/keyword_research_service.py`

Update `research_keyword()`:
```python
def research_keyword(db: Session, user_id: str, keyword: str, location_code: int = 2840) -> dict:
    ideas = DataForSEOClient.get_keyword_ideas_api(keyword, location_code, limit=50)
    from app.services.keyword_research_cache_service import save_research_cache
    save_research_cache(db, user_id, keyword, location_code, ideas or [])
    return {
        "seed": keyword,
        "ideas": ideas or [],
        "credits_charged": 1 if ideas else 0,
    }
```

### 7. Add competitor spy write path
**File:** `api/fastapi_app/app/services/competitor_spy_service.py`

Update `spy_competitor_keywords()`:
```python
def spy_competitor_keywords(db: Session, user_id: str, domain: str, location_code: int = 2840, limit: int = 100) -> list:
    try:
        result = DataForSEOClient.get_competitor_keywords_cached(db, user_id, domain, location_code, limit)
        keywords = result.get("keywords", [])

        if not keywords:
            raise ApiError(502, "Competitor keywords lookup returned no results...")

        from app.services.competitor_cache_service import save_cached_competitor
        save_cached_competitor(db, domain, str(location_code), keywords)

        from datetime import datetime
        month_key = datetime.utcnow().strftime("%Y-%m")
        increment_usage(f"competitor_spy:{user_id}:{month_key}")

        return keywords
    except ApiError:
        raise
    except Exception as exc:
        db.rollback()
        logger.error(f"Competitor spy failed for {domain}: {exc}")
        raise ApiError(502, f"Competitor spy failed: {exc}") from exc
```

### 8. Ensure alternate metrics endpoints also persist
**File:** `api/fastapi_app/app/api/routes/keyword_metrics.py`

- `/ideas`: after `DataForSEOClient.get_keyword_ideas()`, call `save_research_cache()`
- `/competitor-spy`: after `DataForSEOClient.get_competitor_keywords_cached()`, call `save_cached_competitor()`

### 9. Data-shape note (no frontend change required)
- Frontend `KeywordResearchPage.jsx` reads `result.data` from `/keyword-research/research` and `result.data.keywords` from `/keyword-research/competitor-spy`. Both shapes remain unchanged.

## Validation Steps
1. Run Alembic migration
2. Create project with location/device → verify saved
3. Update project location → verify updated
4. `GET /keyword-research/research?keyword=seo&location_code=2356` → verify row in `KeywordResearchCache` with correct `userId`
5. Re-run same request → verify row is updated, `updatedAt` changes
6. `GET /keyword-research/competitor-spy?domain=example.com&location_code=2840` → verify row in `CompetitorCache`
7. Re-run same request → verify existing row is updated
8. Verify credits deducted on every call

## Risks
- **Duplicate writes:** Both `keyword_research.py` and `keyword_metrics.py` endpoints may write for the same search. Upserts by PK, last write wins.
- **JSON size:** Limited by DataForSEO caps (`limit=50` ideas, `limit=100` competitors).
- **Credit double-charge:** Pre-existing routing duplication, not introduced by persistence.
