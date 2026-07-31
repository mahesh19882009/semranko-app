# RankCare API — Keyword Research, Rank Tracking, AIO & Core System Implementation Plan

## 1. Scope & Goal
Implement three new product modules on top of the existing FastAPI + React codebase using **DataForSEO as the sole data provider**:
1. **Keyword Research Module** — real DataForSEO data, competitor spy, semantic clustering, keyword lists
2. **Rank Tracking Module** — onboarding wizard, historic charts, SERP feature tracker, competitor side-by-side comparison
3. **AIO Module** — AI Overview / SGE monitor, citation share of voice, all sourced from DataForSEO SERP `item_groups`
4. **Core System** — midnight cron scheduler, Redis caching layer, plan limit expansion with refresh-frequency-based pricing

**Out of scope for this plan:** Frontend redesign, payment gateway migration, email template changes.

**Environment note:** This project uses a Python virtual environment at `api/.venv`. Always use `.venv/bin/python` instead of system `python3` for backend commands like alembic, migrations, and scripts.

**No external APIs besides DataForSEO:** No SerpAPI, no OpenAI/LLM, no third-party enrichment.

---

## 2. Key Decisions

| Decision | Recommendation | Rationale |
|----------|---------------|-----------|
| **AIO data source** | DataForSEO SERP `item_groups` (`ai_overview`, `ai_answer`, `cited_domains`) | Single API source for rank + SERP features + AIO. No LLM required for monitoring or citations. |
| **Keyword refresh pricing** | Plans tiered by **refresh frequency**: Daily = higher price, Weekly = lower price. AIO usage capped per plan. | Lets users self-select cost vs freshness. Daily refresh consumes more DataForSEO credits. |
| **Cost optimization** | Rank tracking = recurring Standard queue. Keyword research (volume/CPC/intent/difficulty/suggestions) = fetched once on keyword add, cached in DB, refreshed manually. AIO = premium/capped, fetched only for selected keywords. | Keeps recurring cost dominated by cheap rank checks. Avoids re-running expensive Labs/Keyword Data endpoints every refresh cycle. |
| **Infrastructure pre-launch** | Near-zero fixed cost: Cloudflare Workers Free, Supabase Free, Resend Free, domain only (~$10-20/yr). DataForSEO pay-as-you-go with $50 minimum deposit. | Allows testing and private beta at ₹0-₹1,000/month depending on real-data usage. |
| **Implementation order** | 1. Rank tracking (core) → 2. Keyword research (cached on add) → 3. AIO (last, premium, capped) → 4. Reports/Audit | Minimizes early API spend. Validates core product before adding costlier layers. |
| **Frontend charting** | `recharts` | React-native, tree-shakeable, already used in similar SaaS dashboards. |
| **Keyword clustering** | Local TF-IDF + cosine similarity (scikit-learn) | No external API cost. Fast for <10k keywords. Avoid heavy embedding deps. |
| **Scheduler timing** | Midnight cron (`cron`, hour=0) for daily snapshots; weekly snapshots on a separate weekday schedule | Matches user-chosen refresh frequency. Reduces API cost for weekly plans. |
| **Caching strategy** | Redis TTL cache-aside on DataForSEO responses (30-day TTL for volume/KD, 1-day for SERP) | Eliminates duplicate API costs across tenants. |

---

## 3. Database Models (Alembic Migration)

Add to `app/db/models.py`:

```python
class KeywordList(Base):
    __tablename__ = "KeywordList"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_id)
    userId: Mapped[str] = mapped_column(String, ForeignKey("User.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, server_default=func.now())
    user: Mapped[User] = relationship("User", back_populates="keywordLists")
    items: Mapped[list["KeywordListItem"]] = relationship(back_populates="keywordList", cascade="all, delete-orphan")

class KeywordListItem(Base):
    __tablename__ = "KeywordListItem"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_id)
    listId: Mapped[str] = mapped_column(String, ForeignKey("KeywordList.id", ondelete="CASCADE"), nullable=False)
    keyword: Mapped[str] = mapped_column(String, nullable=False)
    keywordList: Mapped[KeywordList] = relationship(back_populates="items")

class CompetitorRank(Base):
    __tablename__ = "CompetitorRank"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_id)
    projectId: Mapped[str] = mapped_column(String, ForeignKey("Project.id", ondelete="CASCADE"), nullable=False)
    competitorId: Mapped[str] = mapped_column(String, ForeignKey("Competitor.id", ondelete="CASCADE"), nullable=False)
    keywordText: Mapped[str] = mapped_column(String, nullable=False)
    position: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    checkedAt: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, server_default=func.now())
    __table_args__ = (
        Index("CompetitorRank_projectId_idx", "projectId"),
        Index("CompetitorRank_projectId_competitor_keyword_key", "projectId", "competitorId", "keywordText", unique=True),
    )

class KeywordCluster(Base):
    __tablename__ = "KeywordCluster"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_id)
    projectId: Mapped[str] = mapped_column(String, ForeignKey("Project.id", ondelete="CASCADE"), nullable=False)
    topic: Mapped[str] = mapped_column(String, nullable=False)
    keywords: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # list of keyword strings
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, server_default=func.now())
    __table_args__ = (Index("KeywordCluster_projectId_idx", "projectId"),)

class AIOTracking(Base):
    __tablename__ = "AIOTracking"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_id)
    projectId: Mapped[str] = mapped_column(String, ForeignKey("Project.id", ondelete="CASCADE"), nullable=False)
    keywordText: Mapped[str] = mapped_column(String, nullable=False)
    hasAIOverview: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    aiOverviewText: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    citedDomains: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # {"domain.com": count}
    checkedAt: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, server_default=func.now())
    __table_args__ = (
        Index("AIOTracking_projectId_idx", "projectId"),
        Index("AIOTracking_projectId_keyword_key", "projectId", "keywordText", unique=True),
    )
```

Update `User` model back_populates:
```python
keywordLists: Mapped[list["KeywordList"]] = relationship(back_populates="user")
```

---

## 4. DataForSEO API Expansion

Extend `app/services/dataforseo_client.py` with:

| New Method | Endpoint | Purpose |
| |------------|----------|---------|
| `get_keyword_data(seed_keyword, location)` | `POST /keywords_data/google/search_volume/live` | Volume, KD, CPC, intent for seed + suggestions |
| `get_competitor_keywords(domain, location)` | `POST /keywords_data/google/competitor_site` | All keywords a competitor ranks for |
| `get_serp_data(keyword, location)` | `POST /serp/google/organic/task_post` + parse `item_groups` for `ai_overview`, `featured_snippet`, `people_also_ask`, etc. | Single source of truth for rank + SERP features + AIO. Extend existing `get_rank` to also return full SERP items. |

Add location codes to `LOCATION_MAP` for US states and major cities (DataForSEO supports granular location codes).

---

## 5. New Backend Services

### 5.1 `app/services/cache_service.py`
- `get_cached(key)` / `set_cached(key, value, ttl_seconds)` using Redis
- Decorator `@cache_response(ttl_seconds)` for service methods
- Key namespace: `rankcare:cache:{hash_of_args}`

### 5.2 `app/services/keyword_research_service.py` (rewrite)
Replace mock data with DataForSEO `search_volume/live`. Return:
```python
{
  "seed": {...},
  "suggestions": [...],
  "intent": "informational" | "commercial" | "transactional" | "navigational",
  "clusters": [...],  # optional, computed client-side or via new endpoint
}
```

### 5.3 `app/services/competitor_spy_service.py`
- `get_competitor_keywords(domain, location)` → DataForSEO `competitor_site`
- Returns: `[{keyword, position, url, volume, kd}]`

### 5.4 `app/services/keyword_clustering_service.py`
- `cluster_keywords(keywords: list[str]) → list[dict]`
- TF-IDF vectorize → cosine similarity → agglomerative clustering (threshold 0.3)
- Returns: `[{topic, keywords: [...], count}]`

### 5.5 `app/services/keyword_list_service.py`
- CRUD for `KeywordList` and `KeywordListItem`
- `add_keywords_to_list(list_id, keywords)`
- `export_list_csv(list_id)` → CSV string

### 5.6 `app/services/competitor_rank_service.py`
- `track_competitor_rankings(project_id)` → enqueue RQ job calling DataForSEO for each competitor + keyword
- `get_competitor_comparison(project_id)` → side-by-side table of user vs up to 3 competitors
- Returns: `[{keyword, user_position, comp1_position, comp2_position, comp3_position}]`

### 5.7 `app/services/aio_service.py`
- `track_aio_for_project(project_id)` → for each tracked keyword, call DataForSEO SERP (`/serp/google/organic/task_post` + `task_get`), parse `item_groups` for `ai_overview` / `ai_answer` type items
- Extract: `hasAIOverview` (bool), `aiOverviewText` (string), `citedDomains` (dict of domain → count)
- Save to `AIOTracking` model
- `get_aio_dashboard(project_id)` → keywords with/without AIO, latest snapshots
- `get_citation_share_of_voice(project_id)` → aggregate cited domains across all AIO keywords, return pie-chart data `[{domain, count, percentage}]`

### 5.8 `app/services/project_onboarding_service.py`
- `create_project_with_keywords(user_id, domain, location, keywords)` → atomic project + keyword creation

---

## 6. New API Routes

| Route File | Prefix | Endpoints |
|-----------|--------|-----------|
| `keyword_research.py` (expand) | `/api/keyword-research` | `GET /research` (real DataForSEO), `GET /competitor-spy`, `POST /cluster` |
| `keyword_lists.py` (new) | `/api/keyword-lists` | `POST /`, `GET /`, `GET /{id}`, `POST /{id}/items`, `DELETE /{id}/items/{item_id}`, `GET /{id}/export` |
| `competitor_rankings.py` (new) | `/api/competitor-rankings` | `POST /{project_id}/track`, `GET /{project_id}/comparison`, `GET /{project_id}/history` |
| `aio.py` (new) | `/api/aio` | `POST /{project_id}/track`, `GET /{project_id}/dashboard`, `GET /{project_id}/citations` |

All new routes use `get_current_user` + `db_session` deps and enforce plan limits via `enforce_limits` or manual checks.

---

## 7. Worker & Scheduler Updates

### 7.1 `app/jobs/rank_scheduler.py`
Replace the interval scheduler with two cron schedulers:
```python
# Daily refresh projects
scheduler.add_job(
    run_daily_job,
    trigger="cron",
    hour=0,
    minute=0,
    id="daily-midnight-job",
    replace_existing=True,
)

# Weekly refresh projects (e.g., every Monday)
scheduler.add_job(
    run_weekly_job,
    trigger="cron",
    day_of_week="mon",
    hour=1,
    minute=0,
    id="weekly-monday-job",
    replace_existing=True,
)
```

### 7.2 `app/jobs/daily_scheduler.py` (new)
`run_daily_job()`:
1. Iterate all active projects with **daily** refresh preference
2. Queue rank checks (existing `queue_rank_checks_for_all_projects` filtered by refresh frequency)
3. Queue competitor rank tracking for daily projects with competitors
4. Queue AIO tracking for daily projects
5. Clean up stale cache keys older than 30 days

`run_weekly_job()`: same as above but only for projects with **weekly** refresh preference.

### 7.3 `app/workers/tasks.py` (extend)
Add:
- `process_competitor_rank_job(project_id, domain, competitor_id, keywords)`
- `process_aio_tracking_job(project_id, keywords)`

---

## 8. Plan Limits Update

Update `PLAN_DEFINITIONS` in `app/services/plan_service.py`:

```python
"free_trial": {
    "key": "free_trial",
    "name": "Free Trial",
    "monthlyPrice": 0,
    "yearlyPrice": 0,
    "refreshFrequency": "weekly",
    "limits": {
        "projects": 1,
        "keywords": 5,
        "competitorsPerProject": 3,
        "reportsPerMonth": 1,
        "teamMembers": 1,
        "aioKeywordsMonitored": 0,
        "keywordResearchCreditsPerMonth": 10,
    },
},
"starter": {
    "key": "starter",
    "name": "Starter",
    "monthlyPrice": 999,
    "yearlyPrice": 9599,
    "refreshFrequency": "weekly",  # default
    "limits": {
        "projects": 1,
        "keywords": 100,
        "competitorsPerProject": 3,
        "reportsPerMonth": 1,
        "teamMembers": 1,
        "aioKeywordsMonitored": 0,
        "keywordResearchCreditsPerMonth": 50,
    },
},
"pro": {
    "key": "pro",
    "name": "Pro",
    "monthlyPrice": 2499,
    "yearlyPrice": 23999,
    "refreshFrequency": "weekly",  # default, user can upgrade to daily
    "limits": {
        "projects": 3,
        "keywords": 200,
        "competitorsPerProject": 6,
        "reportsPerMonth": 6,
        "teamMembers": 3,
        "aioKeywordsMonitored": 50,
        "keywordResearchCreditsPerMonth": 200,
    },
},
"agency": {
    "key": "agency",
    "name": "Agency",
    "monthlyPrice": 4999,
    "yearlyPrice": 47999,
    "refreshFrequency": "daily",  # default
    "limits": {
        "projects": 10,
        "keywords": 500,
        "competitorsPerProject": 10,
        "reportsPerMonth": 25,
        "teamMembers": 5,
        "aioKeywordsMonitored": 200,
        "keywordResearchCreditsPerMonth": 500,
    },
},
```

**Refresh frequency pricing rule:**
- `weekly` refresh = base plan price
- `daily` refresh = base plan price + 40% surcharge (or fixed add-on)

**Keyword research credits:** Count of `search_volume/live` or `labs` API calls per month. Reset on billing cycle. Used when user manually refreshes keyword data or adds new keywords.

**AIO tracking:** Uses DataForSEO SERP AIO Mode Standard Queue at ~$0.0012 per SERP page. Capped per plan. Scheduler only tracks AIO for projects within their cap.

Add enforcement helpers:
- `ensure_keyword_research_limit(db, user_id)` — deducts from `keywordResearchCreditsPerMonth`
- `ensure_aio_tracking_limit(db, user_id)` — limits DataForSEO AIO tracking calls based on `aioKeywordsMonitored`

Mirror in `web/src/config/pricing.js`.

---

## 8.1 DataForSEO Cost Model

| Feature | DataForSEO Endpoint | Pricing (approx) | Refresh Strategy |
|---------|---------------------|------------------|------------------|
| Rank tracking (SERP organic) | `/serp/google/organic/task_post` | Standard queue: ~$0.0006/query | Recurring: weekly or daily per plan |
| AIO / SGE tracking | `/serp/google/organic/task_post` (AI mode) | Standard queue: ~$0.0012/SERP page | Premium/capped, on-demand or limited scheduler |
| Search volume | `/keywords_data/google/search_volume/live` | Bulk clickstream: ~$0.01/task + $0.0001/item | One-time on keyword add, cached |
| Keyword difficulty | `/keywords_data/google/lab/keyword_difficulty` | ~$0.0012/task + $0.00012/item | One-time on keyword add, cached |
| Search intent | `/keywords_data/google/lab/search_intent` | ~$0.0012/task + $0.00012/item | One-time on keyword add, cached |
| Suggested keywords | `/keywords_data/google/lab/related_keywords` | ~$0.0012/task + $0.00012/item | One-time on keyword add, cached |
| Competitor keywords | `/keywords_data/google/competitor_site` | ~$0.0012/task + $0.00012/item | On-demand only |

**Key rule:** Do NOT refresh keyword research data (volume, CPC, intent, difficulty, suggestions) on every rank-check cycle. Cache it in the database and only refresh on manual request or when keyword is first added.

**Minimum deposit:** DataForSEO requires ~$50 minimum deposit to fund pay-as-you-go usage.

---

## 8.2 Monthly Cost Estimates (Per Fully-Used Account)

| Plan | Keywords | Refresh | Rank tracking cost | Keyword research cost | AIO cost | Total data cost |
|------|----------|---------|-------------------|----------------------|----------|-----------------|
| Free Trial | 5 | Weekly | ~$0.02/mo | ~$0.01/mo (once) | $0 | ~$0.03/mo |
| Starter | 100 | Weekly | ~$0.24/mo | ~$0.05/mo (cached) | $0 | ~$0.29/mo |
| Pro | 200 | Weekly | ~$0.48/mo | ~$0.10/mo (cached) | ~$0.24/mo (50 AIO checks) | ~$0.82/mo |
| Pro (daily) | 200 | Daily | ~$3.60/mo | ~$0.10/mo (cached) | ~$0.24/mo | ~$3.94/mo |
| Agency | 500 | Daily | ~$9.00/mo | ~$0.25/mo (cached) | ~$1.20/mo (200 AIO checks) | ~$10.45/mo |

These are **direct DataForSEO costs only**. Add hosting, email, and operational overhead on top.

**Testing budget:** With 100-300 total tracked keywords across all test accounts, weekly refresh, and AIO deferred, realistic testing cost is ₹200-₹1,000/month (~$3-15/month).

---

## 8.3 Pre-Launch Infrastructure (Near-Zero Cost)

| Component | Recommended Service | Cost | Notes |
|-----------|---------------------|------|-------|
| Hosting / Frontend | Cloudflare Workers / Pages | Free tier | Good for small beta; inactivity pauses possible |
| Backend API | Cloudflare Workers or cheap VPS | Free / ~$5/mo | Workers free tier sufficient for small usage |
| Database | Supabase Free or self-hosted Postgres | Free / $0 | Supabase free: 500MB, 50K MAUs; projects pause after inactivity |
| Auth | Supabase Auth or self-hosted JWT | Free | Already implemented in current codebase |
| Email | Resend Free | Free up to 3,000/mo, 100/day | Enough for OTPs, alerts, weekly reports |
| Domain | Any registrar | ~$10-20/year | One-time cost |
| SERP Data | DataForSEO pay-as-you-go | Pay per use, $50 min deposit | Only cost that scales with usage |

**Important:** Free tiers are production-capable but have limits (inactivity pauses, daily caps, lower headroom). For a serious public launch, upgrade to paid tiers.

---

## 9. Environment Variables

No new env vars required. Remove any OpenAI/LLM references. DataForSEO is the sole data source.

`DATAFORSEO_LOGIN` and `DATAFORSEO_PASSWORD` are the only external API credentials needed.

---

## 10. Dependencies

### Backend (`api/requirements.txt`)
```
scikit-learn>=1.5.0     # TF-IDF clustering
```

### Frontend (`web/package.json`)
```
recharts>=2.15.0        # Historic charts, pie charts
```

---

## 11. Frontend Changes

### 11.1 Pages to update/create
| Page | Path | Change |
|------|------|--------|
| `KeywordResearchPage` | `web/src/pages/KeywordResearchPage.jsx` | Add Competitor Spy tab, Clustering tab, real DataForSEO results |
| `KeywordListsPage` | `web/src/pages/KeywordListsPage.jsx` | New page: list CRUD, checklist UI, CSV export, send to Rank Tracker |
| `CompetitorsPage` | `web/src/pages/CompetitorsPage.jsx` | Add side-by-side comparison table |
| `RankingsPage` | `web/src/pages/RankingsPage.jsx` | Add historic line chart (recharts) |
| `AIODashboardPage` | `web/src/pages/AIODashboardPage.jsx` | New page: AIO monitor, citation pie chart, gap analyzer |

### 11.2 Components to add
| Component | Purpose |
| |-----------|---------|
| `RankHistoryChart.jsx` | Recharts line chart for historic rankings |
| `CompetitorComparisonTable.jsx` | Side-by-side rank table |
| `CitationShareOfVoice.jsx` | Recharts pie chart |
| `KeywordClusterTable.jsx` | Cluster grouping UI |
| `ProjectOnboardingWizard.jsx` | Domain, location, keyword setup flow |
| `RefreshFrequencySettings.jsx` | Toggle between daily/weekly refresh with pricing impact preview |

### 11.3 API client (`web/src/lib/api.js`)
Add methods:
- `competitorSpyApi(domain)`
- `clusterKeywordsApi(projectId, keywords)`
- `keywordListsApi` (CRUD)
- `competitorComparisonApi(projectId)`
- `aioTrackApi(projectId)`
- `aioDashboardApi(projectId)`
- `aioCitationsApi(projectId)`

---

## 12. Implementation Order

1. **Database & migrations** — add new models, generate Alembic migration using venv Python: `cd api && .venv/bin/python -m alembic revision --autogenerate -m "..."` then `.venv/bin/python -m alembic upgrade head`
2. **DataForSEO expansion** — new endpoints in `dataforseo_client.py` (SERP, Keyword Data, Labs)
3. **Cache layer** — `cache_service.py` + Redis client wrapper
4. **Core services** — `keyword_list_service`, `competitor_rank_service`, `aio_service`, `keyword_clustering_service`
5. **API routes** — wire up all new endpoints with auth + plan enforcement
6. **Worker/scheduler** — midnight/weekly cron, new RQ tasks
7. **Plan limits** — expand `PLAN_DEFINITIONS`, add enforcement helpers
8. **Frontend dependencies** — install `recharts`
9. **Frontend pages** — build in order: Keyword Research enhancements → Competitor comparison → Rank history charts → AIO Dashboard → Keyword Lists
10. **End-to-end validation** — run migrations with venv Python, test API endpoints with real DataForSEO creds, verify cron fires at correct times, verify cache hit/miss behavior

**Cost-control milestones:**
- After step 2: verify DataForSEO queue mode pricing (~$0.0006/query)
- After step 3: verify keyword research data is cached and not re-fetched on every rank check
- After step 6: verify AIO tracking is capped per plan and uses credit system
- Before launch: confirm total monthly DataForSEO spend stays under target for expected user volume

---

## 13. Validation & Rollout

- **Local dev**: `docker compose up` → run Alembic migrations with venv Python: `cd api && .venv/bin/python -m alembic upgrade head` → hit `/api/keyword-research/research?keyword=crypto+marketing`
- **Cache test**: Search same keyword twice, verify second hit hits Redis (check Redis logs or `redis-cli monitor`)
- **Cron test**: Set scheduler to 1-minute interval in dev, verify daily/weekly jobs queue rank + competitor + AIO tasks
- **AIO test**: Trigger AIO tracking, verify `AIOTracking` records are created with `hasAIOverview`, `aiOverviewText`, and `citedDomains` populated from DataForSEO `item_groups`
- **Plan gate test**: Set user to `starter`, verify AIO endpoints return 403
- **Refresh frequency test**: Switch a project from weekly to daily, verify scheduler honors the new frequency
- **Cost test**: Monitor DataForSEO dashboard during testing. 100 keywords weekly should cost ~$0.24/month. Verify actual usage matches estimate.
- **Budget cap test**: Set hard per-user keyword limits and AIO credit caps. Verify scheduler respects them.

---

## 14. Report Generation & Audit

### 14.1 Report Generation

Reports (weekly/monthly PDF/CSV) are **mostly free** to generate because they use data already stored in your database:
- Rankings history → `RankResult` table
- Keyword metrics → cached in DB
- Competitor comparisons → `CompetitorRank` table
- Charts → rendered client-side with `recharts` or server-side with a lightweight library

**Cost considerations:**
- PDF generation: use free libraries (`reportlab`, `weasyprint`) or generate CSV/HTML
- Email delivery: Resend Free tier (3,000 emails/month, 100/day) sufficient for small launch
- Scheduled jobs: use existing RQ/APScheduler, no extra cost

### 14.2 SEO Audit Tool

Build a **self-hosted crawler** to avoid paid audit APIs:
1. Start from user-provided sitemap or homepage
2. Crawl same-domain HTML pages only
3. Extract: titles, meta descriptions, headings (H1-H6), canonical tags, image alt text, status codes, redirect chains
4. Score/flags issues locally in Python
5. Store results in `Audit` and `AuditIssue` tables (already exist)

**Advantages:**
- Zero per-audit API cost
- Runs on your existing worker infrastructure
- Fully customizable scoring rules

**Limitations:**
- No external SEO authority metrics (e.g., Majestic, Ahrefs)
- No page speed/performance scores (can add Google PageSpeed Insights free tier if needed)
- Requires careful crawl throttling to avoid overwhelming user's server

---

## 15. Risks & Mitigations

| Risk | Mitigation |
| |-----------|
| DataForSEO rate limits | Use Standard queue (~$0.0006/query). Cache keyword research data. Weekly plans make 1/7th the calls of daily plans. |
| AIO credit overrun | Cap `aioKeywordsMonitored` per plan. Scheduler only tracks AIO for projects within their cap. AIO is 2x cost of standard rank check. |
| Clustering performance | Limit to 5k keywords per project; fallback to simple prefix grouping if TF-IDF is slow |
| Midnight cron overlap | Add job locking (Redis SETNX) to prevent duplicate daily/weekly runs |
| Budget overrun during testing | Set hard per-user keyword limits. Defer AIO until core is stable. Use weekly refresh by default. |
| Free tier limitations | Cloudflare/Supabase free tiers have inactivity pauses. For public launch, migrate to paid tiers. Self-host DB on managed service, not personal PC. |

---

## 16. Open Questions (Resolved)

- **AIO data source**: DataForSEO SERP `item_groups` (`ai_overview`, `ai_answer`, `cited_domains`). No LLM required for core AIO features.
- **LLM usage**: Removed entirely. No OpenAI dependency.
- **Pricing model**: Plans now include `refreshFrequency` (`daily` or `weekly`). Daily = base price + 40% surcharge (or fixed add-on). AIO usage capped per plan via `aioKeywordsMonitored`. Added `free_trial` plan (7 days, 5 keywords).
- **Keyword research cost control**: Volume/CPC/intent/difficulty/suggestions fetched once on keyword add, cached in DB, refreshed manually. NOT re-fetched on every rank cycle.
- **Clustering**: Local TF-IDF + cosine similarity via scikit-learn. No external API.
- **Charting**: `recharts` for React.
- **Scheduler**: Two cron jobs — daily at midnight, weekly on Monday at 1am. Projects are filtered by `refreshFrequency`.
- **Reports**: Generated from stored data, mostly free. Email via Resend Free tier.
- **Audit**: Self-built crawler recommended to avoid paid audit APIs.
- **Pre-launch cost**: Near-zero fixed cost possible (Cloudflare Workers Free, Supabase Free, Resend Free, DataForSEO pay-as-you-go). Domain ~$10-20/year.
- **Testing budget**: ₹200-₹1,000/month realistic for small-scale testing with real DataForSEO data. AIO deferred until core is stable.
