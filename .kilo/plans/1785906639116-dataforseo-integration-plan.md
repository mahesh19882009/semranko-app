# DataForSEO Integration Fix & Cost Optimization Plan

## Current State Assessment

### Verified Working
- **SERP `live/advanced`**: `POST /v3/serp/google/organic/live/advanced` returns immediate rank data. Cost: **$0.002/keyword**. Requires `language_code`.
- **Labs `keyword_overview/live`**: `POST /v3/dataforseo_labs/google/keyword_overview/live` returns volume, KD, CPC, competition, backlinks, intent. Cost: **~$0.006/keyword**.
- **Async `task_post`**: `POST /v3/serp/google/organic/task_post` queues tasks. Cost: **~$0.001/keyword**. Results come via pingback webhook. **Cannot be polled synchronously** — task_get returns "Task Not Found" or "Task Handed" until pingback fires.

### Confirmed Bugs
1. **`dataforseo_dashboard.py` sends invalid payloads**: Missing `language_code` causes DataForSEO to return `40501 Invalid Field: 'language_name'` on every request. This is why **no data is fetched**.
2. **`pingback_url` sent to Labs endpoint**: Labs `keyword_overview` does not accept `pingback_url`. Must only send it to SERP async endpoints.
3. **Wrong base URL**: Was using `https://dataforseo.com` instead of `https://api.dataforseo.com/v3`.
4. **Return values discarded**: All callers of `fetch_cheapest_dashboard_data` ignored the returned data.
5. **Monday tracker didn't process returned data**: Called the helper but never wrote results to `KeywordCache`.

### Cost Reference (per keyword)
| Endpoint | Cost | Latency | Use Case |
|---|---|---|---|
| SERP `live/advanced` | $0.002 | ~2s sync | Rank tracking, AIO detection |
| Labs `keyword_overview/live` | $0.006 | ~2s sync | Volume, KD, CPC, competition, backlinks, intent |
| SERP `task_post` (async) | $0.001 | Minutes (pingback) | Bulk weekly refresh only |
| Labs `keyword_ideas/live` | varies | ~2s sync | Keyword research |
| Labs `serp_competitors/live` | varies | ~2s sync | Competitor research |
| Backlinks `summary/live` | varies | ~2s sync | Backlink data |

---

## Implementation Plan

### Phase 1: Fix Immediate Keyword Add Flow (Priority: HIGH)

**Goal**: When a user adds a keyword, DataForSEO data is fetched and stored immediately.

**Changes**:

1. **Fix `dataforseo_dashboard.py` payloads** (`api/fastapi_app/app/services/dataforseo_dashboard.py`):
   - Base URL: `https://api.dataforseo.com/v3`
   - Labs payload: `{"keywords": [...], "location_code": N, "language_code": "en"}` — **no pingback_url**
   - SERP payload: `{"keyword": "...", "location_code": N, "language_code": "en", "depth": 100, "pingback_url": "..."}` — **pingback_url only here**
   - Parse response correctly: `result[0]["items"]` for Labs, `result[0]["items"]` for SERP
   - Return structured dicts: `{keyword, volume, kd, cpc, competition, backlinks, referring_domains, intent, position, ai_badge}`
   - Replace `print()` with `logger.*`
   - Add timeouts (60s)

2. **Fix `_apply_day_one_tracking` in both locations**:
   - `api/routes/keywords.py:60` — instantiate helper with credentials, use return value
   - `services/keyword_service.py:68` — same fix
   - After `fetch_cheapest_dashboard_data()`, if rows returned, update `Keyword` and `KeywordCache` immediately

3. **Fix `create_keyword` and `bulk_create_keywords` routes** (`api/routes/keywords.py`):
   - After keyword creation, call updated `_apply_day_one_tracking`
   - If DataForSEO call fails, refund 15 credits and return error response (not silent success)

4. **Fix `bulk_create_keywords` in `keyword_service.py`**:
   - Remove duplicate credit deduction
   - Use return value from `fetch_cheapest_dashboard_data`
   - Update `KeywordCache` for all fetched keywords

### Phase 2: Implement Cost-Aware Update Service (Priority: HIGH)

**Goal**: Centralize all keyword update logic with cache checks, credit checks, and bulk/single selection.

**New file**: `api/fastapi_app/app/services/keyword_update_service.py`

**Logic**:

```python
def refresh_keyword_data(db, user_id, project_id, keyword_ids=None, force=False):
    """
    Refresh keyword data for a user's project.
    
    1. Check user credits
    2. Determine which keywords need refresh (cache miss or stale)
    3. Split into affordable batch
    4. Choose endpoint based on batch size:
       - 1-50 keywords: SERP live/advanced + Labs overview (sync, immediate)
       - 50+ keywords: SERP task_post async + pingback
    5. Deduct credits
    6. Update KeywordCache
    7. Return summary: updated, skipped, failed, remaining
    """
```

**Key decisions**:
- **Cache TTL**: 7 days (Sunday to Sunday)
- **Freshness check**: `KeywordCache.updatedAt >= last_sunday_midnight`
- **Credit cost**: 15 credits/keyword for day-one tracking (includes SERP + Labs)
- **Partial processing**: If user has 500 keywords but only credits for 100, process 100 and return alert for remaining 400

**Pricing config** (new `api/fastapi_app/app/core/config.py` additions):
```python
DATAFORSEO_CREDIT_COSTS = {
    "serp_live_advanced": 0.002,  # per keyword
    "labs_keyword_overview": 0.006,  # per keyword
    "serp_async_task": 0.001,  # per keyword
}
```

### Phase 3: Fix Sunday Night Bulk Job (Priority: MEDIUM)

**Goal**: Weekly refresh all active keywords across all users using async task_post with pingback.

**Changes**:

1. **Fix `async_bulk_service.py`** (`submit_bulk_to_dataforseo`):
   - Use correct payload: `{"keyword": "...", "location_code": N, "language_code": "en", "depth": 100, "pingback_url": "..."}`
   - Store DataForSEO task IDs in `AsyncTaskQueue.resultJson`
   - Status flow: `pending` → `processing` → `completed`/`failed`

2. **Fix webhook handler** (`api/routes/webhooks.py:166`):
   - Parse DataForSEO callback correctly
   - Update `KeywordCache` for global data
   - Update `RankResult` for user-specific positions
   - Handle partial failures gracefully

3. **Fix `run_weekly_bulk_update_job`** (`async_bulk_service.py:267`):
   - Collect all active keywords across ALL active-subscription users
   - Deduplicate by (keyword, location)
   - Credit check per user before submitting
   - Submit in batches of 1000 (DataForSEO limit)
   - Store user→keyword mapping in `AsyncTaskQueue` for webhook processing

### Phase 4: Fix Worker Jobs (Priority: MEDIUM)

**Goal**: Make rank checks, competitor tracking, and AIO tracking work.

**Changes**:

1. **`app/workers/tasks.py`**:
   - `process_rank_check_job`: Use `DataForSEOClient.get_serp_data_batch()` with live/advanced endpoint
   - `process_labs_metrics_job`: Use `DataForSEOClient._fetch_keyword_data_batch()`
   - `process_competitor_rank_job`: Use `DataForSEOClient.get_serp_data_batch()`
   - `process_aio_tracking_job`: Use `DataForSEOClient.get_serp_data_batch()`

2. **`app/workers/monday_tracker.py`**:
   - Remove duplicate logic
   - Call `keyword_update_service.refresh_keyword_data()` instead

### Phase 5: Wire Frontend to New APIs (Priority: LOW)

**Goal**: Expose new endpoints through API routes and update frontend.

**New API routes needed**:
- `POST /api/keywords/{project_id}/refresh` — manual refresh for a project
- `POST /api/keywords/refresh-bulk` — admin bulk refresh
- `GET /api/keyword-research/suggestions` — keyword suggestions
- `GET /api/keyword-research/ideas` — keyword ideas
- `GET /api/keyword-research/for-keywords` — keywords for keywords
- `GET /api/competitors/{competitor_id}/keywords` — competitor keywords

**Frontend changes**:
- Show "Last updated" timestamp from `KeywordCache.updatedAt`
- Show credit cost estimate before bulk operations
- Show partial success alerts when credits are insufficient
- Add "Refresh" button with credit cost display

### Phase 6: Error Handling & User Feedback (Priority: MEDIUM)

**Goal**: User always sees clear, actionable error messages.

**Standardized error responses**:
```python
{
    "success": False,
    "error": "INSUFFICIENT_CREDITS",
    "message": "You need 1500 credits to refresh 100 keywords. You have 500 credits.",
    "actionable": "Add credits to continue",
    "data": {"required": 1500, "available": 500, "can_process": 33}
}
```

**Error types to handle**:
- `INSUFFICIENT_CREDITS` — partial processing with clear remaining count
- `DFO_API_ERROR` — DataForSEO returned error; show status_code and message
- `DFO_TIMEOUT` — request timed out; suggest retry
- `DFO_RATE_LIMIT` — too many requests; suggest waiting
- `CACHE_STALE` — data exists but is >7 days old; offer refresh
- `NETWORK_ERROR` — connectivity issue; suggest checking internet

**Logging requirements**:
- All DataForSEO API calls: log request URL, status, cost, keyword count
- All credit deductions: log user_id, amount, reason, remaining balance
- All webhook callbacks: log task_id, processed count, errors
- All cache hits/misses: log keyword, location, cache age

---

## File Changes Summary

| File | Action | Description |
|---|---|---|
| `app/services/dataforseo_dashboard.py` | Modify | Fix payloads, add language_code, fix base URL, return structured data |
| `app/services/dataforseo_client.py` | Modify | Implement live/advanced, keyword_overview, competitor, backlinks, research endpoints |
| `app/services/keyword_update_service.py` | **Create** | Central cache/credit/bulk/single decision logic |
| `app/services/async_bulk_service.py` | Modify | Fix submit to use real task_post with pingback |
| `app/services/keyword_service.py` | Modify | Remove duplicate code, use new update service |
| `app/api/routes/keywords.py` | Modify | Fix day-one tracking, add refresh endpoints |
| `app/api/routes/webhooks.py` | Modify | Fix webhook parsing, handle partial results |
| `app/workers/tasks.py` | Modify | Use real DataForSEOClient methods |
| `app/workers/monday_tracker.py` | Modify | Use keyword_update_service |
| `app/jobs/rank_scheduler.py` | Modify | Sunday job uses new update service |
| `app/core/config.py` | Modify | Add pricing config, credit costs |

---

## Testing Plan

1. **Unit tests**: Mock DataForSEO responses, verify cache/credit logic
2. **Integration tests**: Run against DataForSEO sandbox (if available) or use recorded responses
3. **Local testing**: Verify pingback works with ngrok or similar tunnel
4. **Credit scenarios**:
   - User with 0 credits → blocked from refresh
   - User with 100 credits, 500 keywords → processes 6, returns partial alert
   - User with sufficient credits → processes all
5. **Cache scenarios**:
   - Fresh cache (<7 days) → skip API call
   - Stale cache (>7 days) → refresh
   - Cache miss → fetch from DataForSEO
6. **Error scenarios**:
   - DataForSEO 401 → clear error message
   - DataForSEO 500 → retry with backoff
   - Network timeout → retry once, then error
   - Partial DataForSEO failure → update what succeeded, report failures

---

## Rollout Strategy

1. **Deploy backend changes** with feature flag `ENABLE_DFO_REFRESH=true`
2. **Monitor logs** for 24h: watch for API errors, credit deductions, cache hits
3. **Gradual rollout**: Enable for 10% of users, then 50%, then 100%
4. **Fallback**: If DataForSEO is down, serve stale cache data with warning banner
5. **Sunday job**: Run manually first, verify results, then enable scheduler

---

## Open Questions

1. **Pingback URL for local dev**: Should we use a mock webhook handler or require ngrok? → **Recommend**: Add `DFO_MOCK_PINGBACK=true` env flag that bypasses async and uses sync fallback for local dev.
2. **Credit cost exactness**: DataForSEO costs vary by plan/volume. Should we hardcode or fetch from API? → **Recommend**: Start with hardcoded rates, add periodic sync from DataForSEO billing API later.
3. **Cache eviction**: Should we ever delete `KeywordCache` entries? → **Recommend**: Keep all entries. They serve as global cache. Delete only if `updatedAt > 90 days` and keyword is no longer in any active project.
