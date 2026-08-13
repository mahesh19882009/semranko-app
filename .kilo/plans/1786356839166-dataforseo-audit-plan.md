# RankCare SEO SaaS — DataForSEO Cost Optimization Audit

## 1. Current Architecture

| Layer | Technology | Details |
|-------|-----------|---------|
| **Frontend** | Next.js 16 (App Router), React 19, Redux Toolkit, PrimeReact, Tailwind CSS v4 | 18 view components in `rankcareapp/src/views/` |
| **Backend** | FastAPI, SQLAlchemy 2.x, PostgreSQL | 21 API route files in `api/fastapi_app/app/api/routes/` |
| **Cache** | Redis | `cache_service.py` — generic key/value with MD5 digest keys |
| **Background Jobs** | APScheduler + RQ (Redis Queue) | Weekly Sunday bulk job, Monday tracker, rank-check queue |
| **Billing** | Razorpay (INR) | Orders, subscriptions, webhooks, credit top-ups |
| **Email** | Resend | Payment confirmations |

**Key observation:** There are TWO separate DataForSEO integration layers:
- `dataforseo_client.py` — `DataForSEOClient` class with many classmethods
- `dataforseo_dashboard.py` — `DataForSeoDashboardHelper` standalone class

Both make raw `requests.post()` calls directly to DataForSEO with duplicated auth/parsing logic.

---

## 2. DataForSEO Endpoints

| Endpoint | Feature | Live/Standard | Key Parameters | Depth | AIO |
|----------|---------|---------------|----------------|-------|-----|
| `/serp/google/organic/live/advanced` | Keyword Tracking, Day-one, Refresh, Competitor Spy, Weekly jobs, Async bulk | **Live** | `depth=100`, `expand_ai_overview=true`, `device=desktop`, `language=en` | 100 | Yes |
| `/dataforseo_labs/google/keyword_overview/live` | Keyword metrics (volume, KD, CPC, backlinks, intent) | **Live** | `keywords[]`, `location_code`, `language_code=en`, `item_types=["organic","paid","ai_overview_reference"]` | N/A | N/A |
| `/dataforseo_labs/google/keyword_ideas/live` | Keyword Research | **Live** | `keywords[]`, `location_code`, `language_code=en`, `limit` | N/A | N/A |
| `/dataforseo_labs/google/competitors_domain/live` | Competitor Spy | **Live** | `target`, `location_code`, `language_code=en`, `limit` | N/A | N/A |
| `/backlinks/summary/live` | Backlinks (defined but not actively used in current flow) | **Live** | `target`, `limit` | N/A | N/A |
| `/dataforseo_labs/google/domain_rank_overview/live` | Domain metrics (defined but not actively used) | **Live** | `target`, `location_code`, `language_code=en` | N/A | N/A |
| `/dataforseo_labs/google/bulk_traffic_estimation/live` | Traffic estimation (defined but not actively used) | **Live** | `targets[]`, `location_code`, `language_code=en` | N/A | N/A |
| `/dataforseo_labs/google/keyword_suggestions/live` | Keyword suggestions (defined but not actively used) | **Live** | `keyword`, `location_code`, `language_code=en`, `limit` | N/A | N/A |
| `/dataforseo_labs/google/keywords_for_keywords/live` | Related keywords (defined but not actively used) | **Live** | `keywords[]`, `location_code`, `language_code=en`, `limit` | N/A | N/A |
| `/serp/google/organic/task_post` | Async weekly bulk rank tracking | **Async** | `keyword`, `location_code`, `language_code=en`, `device=desktop`, `depth=100`, `pingback_url` | 100 | N/A |
| `/serp/google/organic/task_get/advanced/{task_id}` | Retrieve async SERP results | **Async poll** | task_id | 100 | N/A |

---

## 3. Expensive Operations

### 3.1 Most Expensive: `serp/google/organic/live/advanced` with depth=100 + expand_ai_overview=true

**Why it's expensive:**
- This is a **Live** endpoint (highest DataForSEO cost tier)
- `depth=100` fetches 100 results per keyword instead of 10
- `expand_ai_overview=true` adds significant cost — it expands AI Overview content
- It's called **synchronously** and **repeatedly** for the same keywords

**Who calls it:**
- `DataForSeoDashboardHelper.fetch_cheapest_dashboard_data()` — called by:
  - `_apply_day_one_tracking()` in `keyword_service.py` (single keyword add)
  - `_apply_day_one_tracking_bulk()` in `keyword_research_service.py` (bulk add)
  - `refresh_keyword_data()` in `keyword_update_service.py` (manual refresh)
  - `DataForSEOClient.get_rank_batch()` → `get_serp_data_batch()` — called by:
    - `process_rank_check_job()` in workers (weekly + manual rank checks)
    - `process_competitor_rank_job()` in workers (competitor tracking)

**Estimated cost per keyword:** ~$0.024 (from `DATAFORSEO_CREDIT_COSTS["serp_live_advanced"]`)

### 3.2 Second Most Expensive: `labs_keyword_overview/live`

**Why it's expensive:**
- Also a **Live** Labs endpoint
- Called in parallel with SERP live/advanced during day-one tracking
- Each call returns keyword metrics (volume, KD, CPC, backlinks, intent)

**Estimated cost per keyword:** ~$0.013 (from `DATAFORSEO_CREDIT_COSTS["labs_keyword_overview"]`)

### 3.3 Third: `labs_competitors_domain/live`

**Why it's expensive:**
- **Live** Labs endpoint
- Called once per competitor spy request
- Higher per-call cost at ~$0.132

**Estimated cost per request:** ~$0.132

### 3.4 The "Double Tap" Problem

When adding a keyword, the current code makes **two** DataForSEO calls:
1. `keyword_overview/live` for metrics
2. `serp/google/organic/live/advanced` for position + AIO

This doubles the cost for every new keyword added.

### 3.5 Weekly Rank Tracking Amplification

Every week, the system processes ALL active keywords across ALL users:
- Legacy Monday job: queues individual rank checks per project
- Sunday bulk job: submits async `task_post` with `depth=100`
- Even async jobs use depth=100, which is more than needed for basic position tracking

---

## 4. Cheaper DataForSEO Alternatives

### 4.1 SERP for Rank Tracking

**CURRENT:**
```
POST /serp/google/organic/live/advanced
depth=100, expand_ai_overview=true
```
**PROPOSED:**
```
POST /serp/google/organic/task_post
depth=10, expand_ai_overview=false
```
**WHY:**
- `task_post` is the **async** endpoint with lower cost (`serp_async_task: 0.012` vs `serp_live_advanced: 0.024`)
- `depth=10` is sufficient for position tracking (most keywords rank in top 10 if at all)
- `expand_ai_overview=false` avoids the expensive AIO expansion
- For **weekly automated tracking**, async is already used but with depth=100 — reducing to depth=10 saves ~80% on that endpoint
- **needs verification:** Confirm async task_post supports depth parameter and returns organic items needed for rank extraction

### 4.2 SERP for "Check Now" / On-Demand

**CURRENT:**
```
POST /serp/google/organic/live/advanced
depth=100, expand_ai_overview=true
```
**PROPOSED:**
```
POST /serp/google/organic/live/advanced
depth=10, expand_ai_overview=false
```
**WHY:**
- When user explicitly clicks "Check Now", fresh data is needed, but depth=100 is excessive
- Top 10 is enough for 90%+ of rank-tracking use cases
- AIO expansion should be opt-in, not default
- **Confirmed:** The code already parses organic items and extracts position/url from top results

### 4.3 AIO Badge Detection

**CURRENT:**
```
expand_ai_overview=true on every SERP request
```
**PROPOSED:**
```
1. For weekly tracking: expand_ai_overview=false, detect AIO badge from SERP items only
2. For keywords where user explicitly tracks AIO: separate lightweight AIO check
```
**WHY:**
- The current code checks for AIO in multiple places: `ai_overview` items, `item_groups`, and organic items containing target domain
- The presence of an AIO badge can often be inferred from SERP structure without full expansion
- **needs verification:** Whether DataForSEO SERP response without `expand_ai_overview=true` still contains `ai_overview` item type in the `items` array — if yes, the badge can be detected without paying for expansion

### 4.4 Keyword Metrics (Day-One + Refresh)

**CURRENT:**
```
POST /dataforseo_labs/google/keyword_overview/live
Called separately from SERP
```
**PROPOSED:**
```
Option A: Use Standard priority instead of Live
Option B: Extract volume/KD/CPC from SERP response where available
Option C: Cache keyword metrics for 7-30 days
```
**WHY:**
- Volume, KD, and CPC change slowly — they don't need Live data on every refresh
- **needs verification:** Whether Standard priority Labs endpoint returns the same fields as Live
- The SERP response may contain some keyword_info — check if it's sufficient

### 4.5 Keyword Research

**CURRENT:**
```
POST /dataforseo_labs/google/keyword_ideas/live
```
**PROPOSED:**
```
Keep as-is, but cache for 30-90 days
```
**WHY:**
- Keyword ideas are research data that changes slowly
- Already has `KeywordResearchCache` table with 90-day TTL
- Cost is acceptable for the value provided

### 4.6 Competitor Spy

**CURRENT:**
```
POST /dataforseo_labs/google/competitors_domain/live
```
**PROPOSED:**
```
Keep as-is, but cache for 30 days
```
**WHY:**
- Already has `CompetitorCache` table with 30-day TTL
- The `get_competitor_keywords_cached()` method already checks cache first
- No cheaper alternative endpoint exists for competitor data

---

## 5. Caching

### 5.1 Existing Cache

| Cache | Type | TTL | Used? | Notes |
|-------|------|-----|-------|-------|
| `KeywordResearchCache` | PostgreSQL table | 90 days | Yes | Per-user, per-seed-keyword |
| `CompetitorCache` | PostgreSQL table | 30 days | Yes | Per-domain, per-location |
| Redis `rankcare:cache:*` | Redis | Configurable | **Partially** | `get_cached()`/`set_cached()` exist, `get_serp_data()` reads from it but **never writes** to it |
| `UserCacheUnlock` | PostgreSQL table | N/A | Unclear | Purpose unclear from current usage |
| Frontend localStorage | Browser | Indefinite | Yes | Keyword research and spy results cached in browser |

### 5.2 What Is NOT Cached

**SERP data is NOT cached.** This is the biggest missed opportunity.
- `get_serp_data()` at line 805-808 of `dataforseo_client.py` reads from Redis cache but the cache is never populated
- Every single rank check, day-one tracking, and refresh hits DataForSEO live

### 5.3 Shared SERP Cache Opportunity

**The same keyword + location + device + depth produces identical SERP results for all users.**

Current cache key concept:
```
normalized_keyword|google|location|language|device|depth
```

**What can be shared globally:**
- Raw SERP items (organic results, positions, URLs)
- SERP features (featured snippet, PAA, AIO presence)
- Cited domains in AIO

**What must remain user-specific:**
- Whether the user's domain ranks (calculated from shared SERP)
- User's credit balance and deduction
- User's project/keyword associations
- User's AIO tracking preferences

### 5.4 Recommended Cache Strategy

| Data | Cache Location | TTL | Key |
|------|---------------|-----|-----|
| SERP raw results | Redis | 24 hours | `serp:{keyword_hash}:{location}:{device}:{depth}` |
| Keyword metrics (volume/KD/CPC) | Redis | 7 days | `kw_metrics:{keyword_hash}:{location}` |
| Competitor data | PostgreSQL (existing) | 30 days | Per-domain |
| Keyword research ideas | PostgreSQL (existing) | 90 days | Per-user+seed |

---

## 6. Duplicate API Calls

### 6.1 Day-One Tracking Double Call
**Location:** `keyword_service.py` line 122 and `keyword_research_service.py` line 87

When adding keywords:
1. `_apply_day_one_tracking()` calls `DataForSeoDashboardHelper.fetch_cheapest_dashboard_data()`
2. `fetch_cheapest_dashboard_data()` internally calls:
   - `/dataforseo_labs/google/keyword_overview/live`
   - `/serp/google/organic/live/advanced` (depth=100, expand_ai_overview=true)

Then in `refresh_keyword_data()`:
- Same helper is called again, making the same two requests

**Redundancy:** If day-one tracking already fetched fresh data, refresh should use cached/stored data.

### 6.2 Two DataForSEO Clients
**Locations:**
- `app/services/dataforseo_client.py` — `DataForSEOClient` class
- `app/services/dataforseo_dashboard.py` — `DataForSeoDashboardHelper` class

Both:
- Use `requests.post()` with Basic Auth
- Parse task/result structures independently
- Have overlapping functionality for SERP and Labs endpoints

**Redundancy:** `DataForSeoDashboardHelper` is a subset of `DataForSEOClient` with different parsing. They should be merged.

### 6.3 Weekly Job Duplication
**Locations:**
- `ranking_service.py:queue_weekly_tracking_for_all_projects()` — legacy Monday job
- `async_bulk_service.py:run_weekly_bulk_update_job()` — Sunday bulk job

Both run weekly and both call DataForSEO. The Sunday bulk job already deduplicates keywords, but the Monday legacy job does not.

**Redundancy:** Both jobs are scheduled. The Monday job queues individual project jobs via RQ, while Sunday submits a single bulk async task. They may double-process keywords.

### 6.4 Competitor Spy + Rank Check Overlap
**Locations:**
- `process_rank_check_job()` fetches SERP for all project keywords
- `process_competitor_rank_job()` fetches SERP again for the same keywords

**Redundancy:** If both jobs run in the same week, the same SERP is fetched twice from DataForSEO. The competitor job could reuse the rank-check SERP.

---

## 7. Feature Data Flow

### 7.1 Keyword Tracking
```
User adds keyword
  ↓
keyword_service.py: add_keyword()
  ↓
DataForSeoDashboardHelper.fetch_cheapest_dashboard_data()
  ├── POST /dataforseo_labs/google/keyword_overview/live  → metrics
  └── POST /serp/google/organic/live/advanced (depth=100, expand_ai_overview=true) → position, AIO, URL
  ↓
Store in Keyword table
  ↓
Deduct 20 credits

Weekly tracking:
  ↓
workers/tasks.py: process_rank_check_job()
  ↓
DataForSEOClient.get_rank_batch()
  └── get_serp_data_batch() → POST /serp/google/organic/live/advanced (depth=100, expand_ai_overview=true)
  ↓
Parse position from SERP
  ↓
Store in RankResult table
  ↓
Update Keyword.visibility

Manual "Check Now":
  ↓
Same as weekly, but user-triggered
```

### 7.2 Keyword Research
```
User searches keyword
  ↓
keyword_research_service.py: research_keyword()
  ↓
Check KeywordResearchCache (90-day TTL)
  ↓ (cache miss)
DataForSEOClient.get_keyword_ideas_api()
  └── POST /dataforseo_labs/google/keyword_ideas/live
  ↓
Store in KeywordResearchCache
  ↓
Deduct 20 credits
```

### 7.3 Competitor Spy
```
User spies on domain
  ↓
competitor_spy_service.py: spy_competitor_keywords()
  ↓
Check CompetitorCache (30-day TTL)
  ↓ (cache miss)
DataForSEOClient.get_competitor_keywords()
  └── POST /dataforseo_labs/google/competitors_domain/live
  ↓
Store in CompetitorCache
  ↓
Deduct 20 credits
```

### 7.4 Dashboard
```
DashboardPage.jsx loads
  ↓
dispatch(fetchKeywordsByProject) → GET /keywords/{project_id}/table
  ↓
keyword_table_service.py: get_enriched_keywords()
  ├── SELECT Keyword WHERE projectId
  └── SELECT RankResult WHERE keywordText ORDER BY checkedAt DESC LIMIT 1
  ↓
Merge Keyword + latest RankResult
  ↓
Return to frontend — NO DataForSEO call

dispatch(fetchDashboardByProject) → GET /dashboard/{project_id}
  ↓
dashboard_service.py: get_project_dashboard()
  ├── SELECT Project + keywords + competitors
  ├── Calculate avg rank from Keyword.position
  └── build_usage_snapshot()
  ↓
NO DataForSEO call

dispatch(fetchRankingsByProject) → GET /rankings/{project_id}
  ↓
ranking_service.py: get_project_rankings()
  └── SELECT RankResult WHERE projectId ORDER BY checkedAt DESC
  ↓
NO DataForSEO call
```

**Important:** The dashboard itself does NOT trigger DataForSEO calls. DataForSEO is only called when:
1. Keywords are first added (day-one tracking)
2. Manual refresh is triggered
3. Weekly scheduled jobs run
4. Keyword research is performed
5. Competitor spy is performed

### 7.5 Reports
```
User generates report
  ↓
reports.py: export_project_report() or stream_project_csv()
  ↓
SELECT Keyword WHERE projectId
  ↓
Generate CSV/PDF from stored data
  ↓
NO DataForSEO call (good)
  ↓
Deduct 10-20 credits for PDF
```

---

## 8. Credits and Billing

### 8.1 Credit Flow

```
Feature request
  ↓
check_credits(db, user_id, amount) → 402 if insufficient
  ↓
API/cache operation
  ↓
Success?
  ├── YES → deduct_credits(db, user_id, amount, action_type, description)
  │        ├── Update User.creditBalance
  │        └── Insert CreditLedger entry (negative amount)
  └── NO  → refund_credits() if partial deduction occurred
            └── Insert CreditLedger entry (positive amount, actionType="refund")
```

**Credit costs (USER_CREDIT_COSTS):**
- `add_keyword`: 20
- `weekly_refresh_per_keyword`: 10
- `keyword_research`: 20
- `competitor_spy`: 20
- `extra_project`: 10
- `tracked_keyword`: 20
- `download_report`: 10

### 8.2 DataForSEO API Costs (DATAFORSEO_CREDIT_COSTS)
These are separate from user credits — they represent actual DataForSEO API costs:
- `serp_live_advanced`: 0.024
- `labs_keyword_overview`: 0.013
- `labs_keyword_ideas`: 0.018
- `labs_serp_competitors`: 0.132
- `labs_domain_rank_overview`: 0.013
- `labs_bulk_traffic_estimation`: 0.132
- `labs_keyword_suggestions`: 0.018
- `labs_keywords_for_keywords`: 0.018
- `serp_async_task`: 0.012

**Note:** There is a `DataForSEOCost` table for tracking API costs per user, but it doesn't seem to be actively populated in the current code paths.

### 8.3 Billing Architecture

| Component | Description |
|-----------|-------------|
| Plans | 4 tiers: free_trial, starter (₹999/mo), pro (₹3999/mo), agency (₹9999/mo) |
| Subscriptions | Razorpay orders → webhook → activate_subscription() |
| Credit allocation | Plan credits added to User.creditBalance on activation |
| Credit reset | Monthly reset based on plan anniversary (no rollover) |
| Top-ups | CREDIT_TOP_UP_CONFIG: 600 credits per ₹100 |
| Webhooks | `/webhooks/razorpay` handles payment.captured/order.paid |
| Invoices | Generated with GST (18%) for successful transactions |

### 8.4 Credit Refund Behavior

Current behavior:
- If `_is_valid_keyword_data()` returns False after DataForSEO call → no credits deducted
- If DataForSEO call fails with exception → rollback + no credits deducted
- If DB update fails after DataForSEO success → `refund_credits()` is called

**This is correct behavior — preserve it.**

---

## 9. Database

### 9.1 Core SEO Tables

| Table | Purpose | Status |
|-------|---------|--------|
| `User` | Users, credit balance, plan, subscription | Core |
| `Project` | User's projects/domains | Core |
| `Keyword` | Tracked keywords with stored metrics | Core |
| `RankResult` | Historical rank checks | Core |
| `Competitor` | Competitor domains per project | Core |
| `CompetitorRank` | Competitor positions per keyword | Core |
| `SerpFeature` | SERP features per keyword | Low usage |
| `TrackedKeyword` | User's tracked keyword locks | Used but unclear if needed |

### 9.2 Cache Tables

| Table | Purpose | Status |
|-------|---------|--------|
| `KeywordResearchCache` | Cached keyword research ideas | Active |
| `CompetitorCache` | Cached competitor keywords | Active |
| `UserCacheUnlock` | Purpose unclear — possibly for gamification | Unclear |

### 9.3 Billing Tables

| Table | Purpose | Status |
|-------|---------|--------|
| `PaymentOrder` | Razorpay orders | Core |
| `Subscription` | Active subscriptions | Core |
| `CreditLedger` | All credit transactions | Core |
| `ScheduledReport` | Scheduled report deliveries | Low usage |

### 9.4 Job/Async Tables

| Table | Purpose | Status |
|-------|---------|--------|
| `AsyncTaskQueue` | Bulk async DataForSEO tasks | Active |

### 9.5 Cost Tracking

| Table | Purpose | Status |
|-------|---------|--------|
| `DataForSEOCost` | Track API costs per user | Defined but not actively populated |

### 9.6 Potential Issues

1. **`RankResult` may be empty** — `dashboard_service.py` comments indicate RankResult history table is empty, so dashboard falls back to `Keyword.position`
2. **`TrackedKeyword` vs `Keyword`** — There are two keyword tracking mechanisms. `TrackedKeyword` locks keywords with credits, while `Keyword` stores actual data. Need to verify both are necessary.
3. **`SerpFeature`** — Defined but `mock_extract_serp_features_from_rank_result()` is explicitly a mock. Real extraction from DataForSEO SERP responses is not implemented.

---

## 10. Recommended Architecture

### Before
```
Frontend
  ↓
Feature Services (keyword, research, competitor)
  ↓
DataForSEOClient + DataForSeoDashboardHelper (DUPLICATED)
  ↓
Direct requests.post() to DataForSEO
  ↓
NO SERP cache → every request hits DataForSEO
  ↓
Store in Keyword/RankResult tables
  ↓
Deduct credits
```

### After
```
Frontend
  ↓
Feature Services (tracking, research, competitor)
  ↓
Shared DataForSEO Service Layer
  ↓
  ├── Check Shared SERP Cache (Redis, 24h TTL)
  │     ↓ (cache hit)
  │   Return cached SERP
  │     ↓ (cache miss)
  │   DataForSEO API
  │     ↓
  │   Store in Shared SERP Cache
  │     ↓
  │   Return SERP
  ↓
Per-user calculation:
  ├── Is user's domain in SERP? → position, URL
  ├── Does user track AIO? → AIO badge
  └── Calculate visibility
  ↓
Store user-specific results in Keyword/RankResult
  ↓
Deduct credits
```

**Key changes:**
1. One DataForSEO service layer (merge the two clients)
2. Shared SERP cache — one API call serves all users
3. Rank calculation from cached SERP — no per-domain API calls
4. Depth reduction: 100 → 10 for routine tracking
5. AIO expansion opt-in, not default

---

## 11. Implementation Plan

### Phase 1: DataForSEO Service Unification (LOW risk)
**Goal:** Eliminate duplicate DataForSEO clients

1. Merge `DataForSeoDashboardHelper` into `DataForSEOClient`
2. Standardize auth, request building, and response parsing
3. Add proper error handling and retries
4. Keep all existing endpoints and behavior

**Why first:** This is pure refactoring with zero behavior change. It reduces maintenance burden and makes caching easier.

### Phase 2: Shared SERP Cache (HIGH impact, LOW risk)
**Goal:** Cache SERP responses globally

1. Implement `fetch_serp()` with Redis cache
2. Cache key: `serp:{normalized_keyword}:{location_code}:{device}:{depth}`
3. TTL: 24 hours
4. Store raw SERP items + parsed organic results
5. Modify `get_serp_data_batch()` to check cache first
6. Add cache hit/miss logging

**Why second:** This is the highest-impact change. One cached SERP serves all users with the same keyword/location/device.

### Phase 3: SERP Optimization (HIGH impact, MEDIUM risk)
**Goal:** Reduce depth and AIO expansion costs

1. Change default depth from 100 to 10 for rank tracking
2. Set `expand_ai_overview=false` for weekly jobs
3. Only enable AIO expansion when:
   - User has `TrackedKeyword.trackAio=true`, OR
   - User explicitly requests "Check Now" with AIO
4. Update async bulk job to use depth=10

**Why third:** After caching is in place, reducing depth/AIO parameters directly reduces per-call cost.

### Phase 4: Dashboard Optimization (MEDIUM impact, LOW risk)
**Goal:** Ensure dashboard never triggers DataForSEO

1. Verify dashboard endpoints only read from database
2. Add keyword metrics refresh as explicit user action only
3. Pre-populate keyword metrics during day-one tracking only
4. Add stale-data indicators in UI

**Why fourth:** Dashboard should be instant and free.

### Phase 5: Competitor Spy Optimization (MEDIUM impact, LOW risk)
**Goal:** Reuse SERP data for competitor ranking

1. When processing competitor ranks, check if SERP cache exists for keywords
2. If SERP cached, calculate competitor positions from cached data
3. Only fetch DataForSEO if SERP is stale/missing
4. Keep competitor_domain/live for discovery (no cheaper alternative)

**Why fifth:** Competitor tracking currently fetches SERP separately from rank tracking.

### Phase 6: Credit Flow Cleanup (LOW risk)
**Goal:** Centralize credit deduction logic

1. Create single `charge_for_feature()` function
2. All feature services use it
3. Add DataForSEOCost tracking for real API cost monitoring

**Why sixth:** Current credit logic works but is scattered.

### Phase 7: Dead Code Removal (LOW risk, AFTER verification)
**Goal:** Remove unused code

1. Remove duplicate/unused DataForSEO methods after Phase 1
2. Remove mock SERP feature extraction
3. Remove unused API routes if any
4. Clean up unused frontend components

**Why last:** Only after all above phases are verified stable.

---

## 12. Expected Cost Reduction

### Confirmed Savings

| Area | Current | Proposed | Savings |
|------|---------|----------|---------|
| **SERP depth** | depth=100 | depth=10 | ~80% per SERP call |
| **AIO expansion** | `expand_ai_overview=true` on every call | Opt-in only | ~30-50% per call where AIO not needed |
| **Shared SERP cache** | Every user/project fetches independently | One fetch per keyword/location | Up to 90% for multi-user projects |
| **Double-tap elimination** | 2 calls per new keyword | 1 call (SERP-only, extract metrics) | ~50% on keyword add |

### Estimates

| Scenario | Current Monthly API Calls | Proposed Monthly API Calls | Estimated Savings |
|----------|--------------------------|---------------------------|-------------------|
| 100 keywords, weekly tracking | ~100 SERP + 100 Labs = 200 | ~100 SERP (cached) + 100 Labs = 100-200 | 30-50% |
| 500 keywords, weekly tracking | ~500 SERP + 500 Labs = 1000 | ~500 SERP (shared cache) + 500 Labs = 500-1000 | 30-50% |
| Multi-user same keywords | N calls per user | 1 call shared | Up to 90% |

### Things Requiring DataForSEO Documentation/Testing

1. **Does `serp/google/organic/task_post` with depth=10 return enough organic items?** — Need to verify async SERP with reduced depth still returns usable organic results.
2. **Does standard SERP contain keyword_info (volume/KD)?** — If Standard SERP includes basic keyword metrics, we could eliminate Labs calls entirely for day-one tracking.
3. **Does SERP without `expand_ai_overview=true` still include `ai_overview` item type?** — If yes, we can detect AIO presence without paying for expansion.
4. **What is the actual cost difference between Live and Standard for Labs endpoints?** — DataForSEO docs should clarify if Standard Labs is available and at what cost.

### Largest Wins (Priority Order)

1. **Shared SERP cache** — eliminates redundant calls across users/projects
2. **Depth reduction 100→10** — 80% cost reduction per SERP call
3. **AIO expansion opt-in** — 30-50% reduction on non-AIO keywords
4. **Single client unification** — enables all other optimizations

---

## Open Questions

1. Is `TrackedKeyword` table still needed, or can `Keyword.isActive` + `Keyword` fields replace it?
2. What is `UserCacheUnlock` for? Is it used in production?
3. Should we keep both Monday legacy job and Sunday bulk job, or remove Monday after testing?
4. Is there a Standard-priority SERP endpoint that returns organic items cheaper than Live?
