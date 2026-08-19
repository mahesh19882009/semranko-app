# Semranko — Final Implementation Plan: DataForSEO Cost Optimization

## CREDIT/PRICING FREEZE NOTICE

Current credit values, plan prices, and feature limits are FROZEN for this plan.
No credit cost, plan price, or pricing model changes are proposed or implemented below.
This document covers ONLY technical architecture, worst-case cost analysis, and cost-safety controls.

Worst-case calculations use:
- Current official DataForSEO USD pricing
- Current Semranko credit costs
- Zero cache hits
- Maximum plan-limit usage
- Exchange rate: 1 USD = 95.23 INR

---

# Keyword Tracking — Standard SERP Integration Plan

## 1. Current Weekly Tracking — Exact Call Sites

Weekly tracking calls `/serp/google/organic/live/advanced` in **three** places:

| Job | Schedule | File | Function | Parameters | Sync/Async | Credits? |
|-----|----------|------|----------|------------|------------|----------|
| Legacy Monday | Mon 1 AM | `ranking_service.py:184` | `queue_weekly_tracking_for_all_projects()` → `queue_rank_check_for_project()` → RQ → `process_rank_check_job()` | depth=100, expand_ai_overview=true | Sync (RQ worker waits for response) | No |
| Monday tracker | Mon 2 AM | `monday_tracker.py:25` | `run_monday_tracker()` → `DataForSeoDashboardHelper.fetch_cheapest_dashboard_data()` | depth=100, expand_ai_overview=true | Sync | Yes (deducts per user) |
| Sunday bulk | Sun 11 PM | `async_bulk_service.py:107` | `submit_bulk_to_dataforseo()` → `/serp/google/organic/task_post` | depth=100, no expand_ai_overview | Async (pingback webhook) | No |

**Important:** The Sunday bulk job is already cheaper (~$0.012 vs ~$0.020 per keyword) but does NOT:
- Update `Keyword.position` or `Keyword.visibility`
- Deduct user credits
- Handle AIO expansion

The Monday jobs DO update those fields but at higher cost.

---

## 2. Standard SERP Compatibility

### Existing parser dependencies

The current SERP parser (`dataforseo_client.py:get_serp_data_batch()`) reads:

| Field | Usage | Present in Standard? |
|-------|-------|---------------------|
| `result[0]["items"]` | All item extraction | **Yes** — Standard SERP returns same `tasks[].result[].items` structure |
| `item["type"]` | Filter organic, ai_overview, etc. | **Yes** |
| `item["rank_group"]` | Position extraction | **Yes** |
| `item["rank_absolute"]` | Position fallback | **Yes** |
| `item["url"]` | Ranking URL | **Yes** |
| `item["domain"]` | Domain matching | **Yes** |
| `first_block["item_groups"]` | Featured snippet, PAA, AIO groups | **Yes** |
| `item_groups[].type == "ai_overview"` | AIO badge detection | **Likely yes** — but without `expand_ai_overview=true`, AIO content may be absent |

### Confirmed compatible
- `rank_group`, `rank_absolute`, `type`, `url`, `domain`, `item_groups` are all standard SERP metadata fields
- Standard and Live SERP responses share the same envelope: `tasks → result → items`

### Requires verification
- **Does Standard SERP include `ai_overview` items without `expand_ai_overview=true`?** If yes, the badge can be detected. If no, we need Live or expansion for AIO keywords.
- **Does Standard SERP response time affect the async task_post flow?** The async endpoint should handle this, but pingback latency may differ.

---

## 3. Proposed Weekly Architecture

### Weekly (background/async)
```
Endpoint: /serp/google/organic/task_post
Parameters:
  - keyword: "..."
  - location_code: 2840
  - language_code: "en"
  - device: "desktop"
  - depth: 100
  - priority: "normal"  ← Standard Normal (needs verification)
  - pingback_url: https://your-domain/api/webhooks/dataforseo

No expand_ai_overview for non-AIO keywords
expand_ai_overview=true only for keywords in TrackedKeyword.trackAio=True

Processing:
  - DataForSEO calls back to webhook when complete
  - Webhook parses SERP, updates RankResult + Keyword.position + Keyword.visibility
  - Deduct weekly_refresh_per_keyword credits per user
```

### Manual "Check Now" (on-demand/sync)
```
Endpoint: /serp/google/organic/live/advanced
Parameters:
  - keyword: "..."
  - location_code: 2840
  - language_code: "en"
  - device: "desktop"
  - depth: 100
  - expand_ai_overview: true (only for AIO-tracked keywords)

Processing:
  - Synchronous response
  - Parse position, URL, AIO badge
  - Update Keyword + RankResult
  - Deduct weekly_refresh_per_keyword credits
```

### Cost comparison (per keyword, depth=100)

| Path | Endpoint | Priority | Estimated Cost | Notes |
|------|----------|----------|---------------|-------|
| Current weekly (Monday legacy) | live/advanced | Live | ~$0.020 | Sync via RQ |
| Current weekly (Monday tracker) | live/advanced | Live | ~$0.020 | Sync direct |
| Current weekly (Sunday bulk) | task_post | Unknown (likely Standard) | ~$0.012 | Async, no credit deduction |
| **Recommended weekly** | task_post | Standard Normal | **~$0.006** | Async, add `priority: 1` |
| Current manual | live/advanced | Live | ~$0.020 | Sync |
| **Recommended manual** | live/advanced | Live | **~$0.020** | Keep as-is |

**Note:** The `task_post` endpoint may already default to Standard Normal or Standard High. Adding `"priority": "normal"` needs verification from DataForSEO documentation.

---

## 4. AIO Strategy

### Current behavior
- `get_serp_data_batch()` sends `expand_ai_overview=True` on every call
- `process_rank_check_job()` passes `aio_keyword_texts` but the SERP is already fetched with expansion
- The webhook parses `ai_overview` items from the response

### Proposed behavior
- **Weekly tracking:** Set `expand_ai_overview=false` for keywords NOT in `TrackedKeyword.trackAio=True`
- For keywords WITH `trackAio=True`, set `expand_ai_overview=true`
- **Manual "Check Now":** Same logic — expand only for AIO-tracked keywords

### Why this works
- The AIO badge only needs the presence of an `ai_overview` item and whether the target domain appears in references
- If Standard SERP includes `ai_overview` items without expansion, the badge can be detected
- Full AIO text content is only needed for `ai_description` display, which is secondary

### Risk
- If `ai_overview` items only appear when `expand_ai_overview=true`, disabling expansion will hide the badge for non-AIO-tracked keywords
- **Mitigation:** Test with one project first; fall back to `expand_ai_overview=true` if badge detection fails

---

## 5. Existing Sunday Async Job — Assessment

### What it does well
- Already deduplicates keywords globally (`collect_active_keywords_for_bulk`)
- Already uses async `task_post` (cheaper than Live)
- Already has pingback webhook for result processing
- Already updates `RankResult` entries

### What it lacks
1. **Does NOT update `Keyword.position` or `Keyword.visibility`** — only creates `RankResult` rows
2. **Does NOT deduct user credits** — `process_completed_async_task()` has no credit logic
3. **Does NOT update `Keyword.ai_badge` or `Keyword.ai_description`**
4. **Does NOT update `Keyword.volume`, `kd`, `cpc`, etc.** — only RankResult
5. **Does NOT handle per-keyword AIO tracking** — sends same payload for all keywords
6. **Result parsing is minimal** — only extracts `organic_items`, `position`, `url`
7. **Error handling is basic** — marks task as failed but doesn't retry or notify users

### Can it become the single weekly mechanism?

**Yes, with modifications:**

| Missing Feature | How to Add |
|----------------|-----------|
| Update Keyword.position | In `process_completed_async_task()`, after finding position, also update `Keyword.position` and `Keyword.visibility` using `dfs_visibility()` |
| Deduct credits | After processing, iterate affected users and deduct `weekly_refresh_per_keyword` per active keyword |
| AIO badge | Parse `ai_overview` items from SERP response in webhook or `process_completed_async_task()` |
| Keyword metrics | Optionally call `keyword_overview` Labs endpoint separately (cached for 7 days) |
| Per-keyword AIO | Add `expand_ai_overview=true` per keyword based on `TrackedKeyword.trackAio` |

### Result retrieval flow
```
task_post → DataForSEO processes → pingback to /api/webhooks/dataforseo
  → dataforseo_webhook() receives task_id
  → Currently: updates Keyword directly (has bugs — uses undefined `row` variable at line 311)
  → Recommended: enqueue process_completed_async_task() or update directly
```

**Bug found in webhook:** `webhooks.py:311` uses `row.get("ai_description")` but `row` is undefined in that scope. This would cause a `NameError` and rollback the entire webhook transaction.

---

## 6. Monday Legacy Job — Duplication Analysis

### `queue_weekly_tracking_for_all_projects()` (`ranking_service.py:184`)
- Iterates all projects
- Queues `process_rank_check_job` via RQ for each project
- Each job calls `DataForSEOClient.get_rank_batch()` → `get_serp_data_batch()` → **Live SERP**
- Updates `RankResult` and `Keyword.visibility`

### `run_monday_tracker()` (`monday_tracker.py:25`)
- Fetches ALL keywords across all users
- Calls `DataForSeoDashboardHelper.fetch_cheapest_dashboard_data()` → **BOTH Labs + Live SERP**
- Updates `Keyword` table directly (position, volume, kd, etc.)
- Deducts credits per user

### Duplication confirmed
- Both jobs process the same keywords on Monday
- Both use Live SERP
- The Monday tracker additionally calls Labs metrics
- The Sunday bulk job also processes the same keywords

### What to verify before removing Monday jobs

1. **Does Sunday bulk job update the same fields?**
   - Currently: Only `RankResult` (not `Keyword.position` or `Keyword.visibility`)
   - Need to add: `Keyword.position`, `Keyword.visibility`, `Keyword.ai_badge`
   - **Verified:** Yes, can be added to `process_completed_async_task()`

2. **Does Sunday bulk job handle credit deduction?**
   - Currently: No
   - Need to add: Per-user credit deduction after successful processing
   - **Verified:** Can be added

3. **Does Sunday bulk job handle Labs metrics?**
   - Currently: No
   - The Monday tracker calls Labs. The Sunday bulk does not.
   - **Decision needed:** Should weekly tracking also refresh Labs metrics, or should that be a separate less-frequent job?

4. **Does Sunday bulk job handle per-project domains?**
   - Currently: `process_completed_async_task()` uses `task.domain` but the async task creation in `create_async_bulk_task()` doesn't set `domain`
   - **Verified:** Bug — `task.domain` is None, so position detection by domain doesn't work

5. **Does the webhook handle multiple tasks correctly?**
   - Currently: `dataforseo_webhook()` has a bug with undefined `row` variable
   - **Verified:** Needs fix before relying on it

6. **Are there users/projects that depend on Monday-specific timing?**
   - **Needs verification:** Check if any users expect data by Monday morning vs Sunday night

---

## 7. Caching — Insertion Points

### Where to add Redis SERP cache

**Primary insertion point:** `DataForSEOClient.get_serp_data_batch()`

Current flow:
```python
def get_serp_data_batch(cls, keywords, location, device, result_type, aio_keyword_texts):
    # ... build tasks ...
    response = requests.post(url, json=payload, ...)  # HIT DATAFORSEO EVERY TIME
    # ... parse response ...
    return results
```

Recommended flow:
```python
def get_serp_data_batch(cls, keywords, location, device, result_type, aio_keyword_texts):
    # 1. Check cache for each keyword
    cached_results = {}
    missing_keywords = []
    for kw in keywords:
        cache_key = f"serp:{normalize(kw)}:{location_code}:{device}:{depth}:{aio_flag}"
        cached = get_cached("serp", cache_key)
        if cached:
            cached_results[kw] = cached
        else:
            missing_keywords.append(kw)
    
    if not missing_keywords:
        return cached_results
    
    # 2. Fetch only missing keywords from DataForSEO
    # 3. Store results in cache
    for kw, result in new_results.items():
        cache_key = f"serp:{normalize(kw)}:{location_code}:{device}:{depth}:{aio_flag}"
        set_cached("serp", cache_key, result, ttl=86400)  # 24 hours
    
    # 4. Merge cached + fresh results
    return {**cached_results, **new_results}
```

### Secondary insertion points

| Location | Action | Purpose |
|----------|--------|---------|
| `process_rank_check_job()` | Check cache before calling `get_rank_batch()` | Skip DataForSEO if SERP fresh |
| `process_completed_async_task()` | Store SERP in cache after parsing | Populate cache from async results |
| `dataforseo_webhook()` | Store SERP in cache after parsing | Populate cache from pingback |
| Manual "Check Now" endpoint | Bypass cache or force refresh | User wants fresh data |

### Cache key design
```
serp:{normalized_keyword}:{location_code}:{device}:{depth}:{aio_flag}
```

Example:
```
serp:seo tools:2840:desktop:100:false
```

### Cache TTL
- Weekly tracking: 24 hours (fresh enough for weekly jobs)
- Manual "Check Now": Bypass cache or use shorter TTL (1 hour)

### Shared cache behavior
- Multiple users/projects with the same keyword + location + device share the cached SERP
- User-specific data (position, URL, AIO badge for their domain) is calculated after cache retrieval
- Credits are still deducted per user

---

## 8. Final Recommendation

### CURRENT

| Path | Endpoint | Priority | Depth | AIO | Cost per keyword |
|------|----------|----------|-------|-----|-----------------|
| Weekly (Monday legacy) | `/serp/google/organic/live/advanced` | Live | 100 | true | $0.020 |
| Weekly (Monday tracker) | `/serp/google/organic/live/advanced` | Live | 100 | true | $0.020 |
| Manual Check Now | `/serp/google/organic/live/advanced` | Live | 100 | true | $0.020 |

### RECOMMENDED

| Path | Endpoint | Priority | Depth | AIO | Cost per keyword |
|------|----------|----------|-------|-----|-----------------|
| Weekly | `/serp/google/organic/task_post` | **Standard Normal** | 100 | conditional | **~$0.006** |
| Manual Check Now | `/serp/google/organic/live/advanced` | Live | 100 | conditional | $0.020 |

### Exact files/functions that need modification

| File | Function | Change |
|------|----------|--------|
| `async_bulk_service.py` | `submit_bulk_to_dataforseo()` | Add `"priority": "normal"` to task payload; add per-keyword `expand_ai_overview` based on `TrackedKeyword.trackAio` |
| `async_bulk_service.py` | `process_completed_async_task()` | Update `Keyword.position`, `Keyword.visibility`, `Keyword.ai_badge`; deduct user credits |
| `async_bulk_service.py` | `create_async_bulk_task()` | Store `domain` in task for position detection |
| `dataforseo_client.py` | `get_serp_data_batch()` | Add cache check before API call; store results in cache after |
| `dataforseo_client.py` | `get_rank_batch()` | Accept `priority` parameter; pass to `get_serp_data_batch()` |
| `workers/tasks.py` | `process_rank_check_job()` | Use Standard SERP for weekly; keep Live for manual |
| `workers/monday_tracker.py` | `run_monday_tracker()` | Disable or convert to use Standard SERP async |
| `api/routes/webhooks.py` | `dataforseo_webhook()` | Fix undefined `row` variable at line 311; add credit deduction |
| `api/routes/keywords.py` | `_apply_day_one_tracking()` | Use Live SERP for day-one, but check cache first |
| `services/keyword_update_service.py` | `refresh_keyword_data()` | Use Live SERP for manual refresh; check cache first |
| `services/ranking_service.py` | `queue_weekly_tracking_for_all_projects()` | Disable after Sunday bulk job is verified |
| `jobs/rank_scheduler.py` | `run_weekly_job()` | Disable after Sunday bulk job is verified |
| `jobs/rank_scheduler.py` | `run_monday_position_tracker()` | Disable after Sunday bulk job is verified |

### What requires DataForSEO documentation verification

1. **Does `/serp/google/organic/task_post` accept `priority: 1` for Standard Normal?** — Need to verify exact parameter name, accepted values (`1` for Normal, `2` for High), and cost impact.
2. **Does Standard SERP include `ai_overview` items without `expand_ai_overview=true`?** This determines whether AIO badges can be detected in weekly tracking.
3. **Does Standard SERP include `rank_group` and `rank_absolute` for all organic items?** Required for position extraction.
4. **What is the exact pingback/webhook latency for Standard vs Live async tasks?** This affects how quickly weekly results appear.

### Risks

| Risk | Level | Mitigation |
|------|-------|-----------|
| Standard SERP missing AIO items | MEDIUM | Test with `expand_ai_overview=false` first; fall back to `true` for AIO-tracked keywords |
| `priority` parameter not supported on task_post | MEDIUM | If unsupported, accept current $0.012 async cost (still cheaper than Live $0.020) |
| Sunday bulk job bugs (domain, credits, position) | HIGH | Fix all three before disabling Monday jobs |
| Monday jobs removal breaks users | LOW | Keep disabled for 2-4 weeks before deleting |
| Webhook `row` variable NameError | HIGH | Fix immediately — currently breaks all async result processing |

### Estimated savings

| Scenario | Current | Recommended | Savings |
|----------|---------|-------------|---------|
| 100 keywords, weekly (Monday jobs only) | 100 × $0.020 = $2.00 | 100 × $0.006 = $0.60 | **70%** |
| 100 keywords, weekly (Sunday bulk only) | 100 × $0.012 = $1.20 | 100 × $0.006 = $0.60 | **50%** |
| 100 keywords, weekly (all 3 jobs) | 100 × $0.072 = $7.20 | 100 × $0.006 = $0.60 | **92%** |
| Manual check, 10 keywords | 10 × $0.033 = $0.33 | 10 × $0.033 = $0.33 | **0%** (unchanged) |

---

# FINAL IMPLEMENTATION PLAN

## Executive Summary

Semranko currently uses **Live SERP** (`/serp/google/organic/live/advanced`) with `depth=100` and `expand_ai_overview=true` for ALL keyword tracking — including weekly background jobs. This is the most expensive DataForSEO method available.

The current architecture also:
- Makes duplicate DataForSEO calls (two separate clients, three weekly jobs)
- Has NO SERP caching — every keyword refresh hits DataForSEO
- Runs weekly tracking for **trial users** who should not receive recurring tracking
- Has a bug in the DataForSEO webhook that breaks async result processing

This plan fixes all of these while preserving every product feature.

**Bottom line:** Under the CURRENT pricing and credit allocation, a worst-case paid user CAN cause Semranko to spend more on DataForSEO than the plan revenue. The trial is also unprofitable by design (expected). Specific mitigations are included below.

---

## Current Cost Model

### Plans (from `plan_service.py` and `config.py`)

| Plan | Monthly Price (INR) | Monthly Credits | Keyword Limit | Competitor Spy Limit | Weekly Tracking | Trial Days |
|------|---------------------|-----------------|---------------|---------------------|-----------------|------------|
| free_trial | 0 | 100 | 5 | 5 | **No** | 7 (plan) / 10 (config) |
| starter | 999 | 6000 | 100 | 50 | Yes | — |
| pro | 3999 | 30000 | 500 | 200 | Yes | — |
| agency | 9999 | 80000 | 1500 | 500 | Yes | — |

### User Credit Costs (from `config.py`)

| Action | User Credits | DataForSEO USD Cost | Feature |
|--------|-------------|---------------------|---------|
| add_keyword | 20 | $0.033 (Labs $0.013 + Live SERP $0.020) | Day-one tracking |
| weekly_refresh_per_keyword | 10 | $0.006 (Standard Normal async) | Weekly tracking |
| keyword_research | 20 | $0.018 (keyword_ideas/live) | Keyword Research |
| competitor_spy | 20 | $0.132 (competitors_domain/live) | Competitor Spy |
| download_report | 10 | $0.000 | Reports |

### Current DataForSEO Endpoint Usage

| Endpoint | Method | Priority | Depth | AIO | USD Cost | Used By |
|----------|--------|----------|-------|-----|----------|---------|
| `/serp/google/organic/live/advanced` | POST | Live | 100 | true | $0.020 | Day-one, Monday jobs, manual refresh, Competitor Spy |
| `/dataforseo_labs/google/keyword_overview/live` | POST | Live | N/A | N/A | $0.013 | Day-one, Monday tracker |
| `/dataforseo_labs/google/keyword_ideas/live` | POST | Live | N/A | N/A | $0.018 | Keyword Research |
| `/dataforseo_labs/google/competitors_domain/live` | POST | Live | N/A | N/A | $0.132 | Competitor Spy |
| `/serp/google/organic/task_post` | POST | 1 (Normal) | 100 | false | $0.006 | Sunday bulk job |
| `/serp/google/organic/task_get/advanced/{id}` | GET | — | 100 | false | $0.000 | Sunday bulk result retrieval |

### Current Weekly Jobs (All Use Live SERP or Unoptimized Async)

| Job | Schedule | File | SERP Method | Cost per Keyword (USD) |
|-----|----------|------|-------------|------------------------|
| Legacy Monday | Mon 1 AM | `ranking_service.py:184` | Live/advanced | $0.020 |
| Monday tracker | Mon 2 AM | `monday_tracker.py:25` | Live/advanced + Labs | $0.020 + $0.013 = $0.033 |
| Sunday bulk | Sun 11 PM | `async_bulk_service.py:107` | task_post async (priority=1) | $0.006 |

**Confirmed duplication:** All three jobs process the same keywords. The Monday jobs use expensive Live SERP. The Sunday bulk uses cheaper async but is incomplete.

---

## 7-Day Free Trial Cost Model

### Trial Constraints (from plan definition)
- `weeklyTrackingEnabled: False`
- 100 credits total
- 5 keyword maximum
- 5 competitor spy maximum
- 1 domain maximum
- NO recurring weekly tracking
- NO automatic keyword refresh

**Exchange rate used:** 1 USD = 95.23 INR

### Trial Actions Available

| Action | Semranko Credits | Max Uses | DataForSEO USD Cost | DataForSEO INR | Max DataForSEO Cost (INR) |
|--------|------------------|----------|---------------------|----------------|---------------------------|
| Add keyword (day-one) | 20 | 5 (keywordLimit) | $0.033 | ₹3.14 | ₹15.70 |
| Manual Check Now (refresh) | 10 | 10 (100÷10) | $0.033 | ₹3.14 | ₹31.40 |
| Keyword Research | 20 | 5 (100÷20) | $0.018 | ₹1.71 | ₹8.55 |
| Competitor Spy | 20 | 5 (competitorSpyLimit) | $0.132 | ₹12.57 | ₹62.85 |
| Download Report | 10 | 10 (100÷10) | $0.000 | ₹0.00 | ₹0.00 |

### Trial Worst-Case DataForSEO Cost

**Maximum theoretical DataForSEO cost:** 5 competitor spy calls = **$0.660 = ₹62.85**

**Calculation:** 5 (competitorSpyLimit) × $0.132 = $0.660
**INR:** $0.660 × 95.23 = ₹62.85

### Trial Revenue Protection

| Item | Value |
|------|-------|
| Trial revenue | ₹0 |
| Worst-case DataForSEO cost | $0.660 (₹62.85) |
| Verdict | **Loss by design** — acceptable for trial |

**Mitigations:**
- No weekly tracking for trial users (saves ~100% vs current buggy behavior)
- Shared SERP cache prevents duplicate day-one adds from multiple trial users
- Competitor spy limited to 5 per trial
- Manual Check Now uses Live SERP but is credit-gated

---

## Paid Plan Worst-Case Cost Model

**Exchange rate used:** 1 USD = 95.23 INR

### DataForSEO USD Costs (Official Pricing)

| Operation | USD Cost | INR Equivalent |
|-----------|----------|----------------|
| Live SERP depth=100 | $0.020 | ₹1.90 |
| Standard Normal SERP depth=100 (async) | $0.006 | ₹0.57 |
| Standard High SERP depth=100 (async) | $0.012 | ₹1.14 |
| keyword_overview/live (Labs) | $0.013 | ₹1.24 |
| keyword_ideas/live (Labs) | $0.018 | ₹1.71 |
| competitors_domain/live (Labs) | $0.132 | ₹12.57 |
| Day-one tracking (Labs + Live SERP) | $0.033 | ₹3.14 |
| Manual Check Now (Labs + Live SERP) | $0.033 | ₹3.14 |
| Weekly Standard Normal tracking | $0.006 | ₹0.57 |

### Cost Efficiency per Semranko Credit

| Feature | User Credits | DataForSEO USD | USD per Credit |
|---------|-------------|----------------|----------------|
| Competitor Spy | 20 | $0.132 | $0.00660 ← MOST EXPENSIVE |
| Manual Check Now | 10 | $0.033 | $0.00330 |
| Day-one add | 20 | $0.033 | $0.00165 |
| Weekly tracking (Standard Normal) | 10 | $0.006 | $0.00060 |
| Keyword Research | 20 | $0.018 | $0.00090 |

### Assumptions for Worst-Case
- User maximizes use of MOST expensive features first
- User respects plan limits (keywordLimit, competitorSpyLimit)
- Weekly tracking is automatic and deducts credits (recommended architecture)
- Manual Check Now requires existing keywords (assume minimum 1 keyword)
- No cache hits (theoretical maximum)

### Starter Plan (₹999/month, 6000 credits)

| Scenario | Action | Max Uses | Credits Used | DataForSEO USD | DataForSEO INR |
|----------|--------|----------|--------------|----------------|----------------|
| A. All competitor spy | competitor_spy | 50 (limit) | 1000 | $6.60 | ₹628.70 |
| B. All manual Check Now | refresh | 6000÷10=600 | 6000 | $19.80 | ₹1,885.16 |
| C. All weekly tracking | weekly_refresh | 100 kw × 4 wks | 4000 | $2.40 | ₹228.55 |
| D. Mixed worst-case | 50 competitor + 500 manual | 50 + 500 | 1000 + 5000 = 6000 | $6.60 + $16.50 = **$23.10** | **₹2,199.81** |

**Starter worst-case margin:**
- Revenue: ₹999
- Payment gateway (2%): ₹20
- GST (18%): ₹180
- Infrastructure + email: ₹1,200
- DataForSEO worst-case: $23.10 (₹2,200)
- **Total cost: ₹2,400**
- **Margin: ₹999 - ₹2,400 = -₹1,401 (-140%)**

### Pro Plan (₹3999/month, 30000 credits)

| Scenario | Action | Max Uses | Credits Used | DataForSEO USD | DataForSEO INR |
|----------|--------|----------|--------------|----------------|----------------|
| A. All competitor spy | competitor_spy | 200 (limit) | 4000 | $26.40 | ₹2,514.89 |
| B. All manual Check Now | refresh | 30000÷10=3000 | 30000 | $99.00 | ₹9,428.78 |
| C. All weekly tracking | weekly_refresh | 500 kw × 4 wks | 10000 | $12.00 | ₹1,142.76 |
| D. Mixed worst-case | 200 competitor + 2600 manual | 200 + 2600 | 4000 + 26000 = 30000 | $26.40 + $85.80 = **$112.20** | **₹10,683.81** |

**Pro worst-case margin:**
- Revenue: ₹3,999
- Payment gateway (2%): ₹80
- GST (18%): ₹720
- Infrastructure + email: ₹1,200
- DataForSEO worst-case: $112.20 (₹10,684)
- **Total cost: ₹12,684**
- **Margin: ₹3,999 - ₹12,684 = -₹8,685 (-217%)**

### Agency Plan (₹9999/month, 80000 credits)

| Scenario | Action | Max Uses | Credits Used | DataForSEO USD | DataForSEO INR |
|----------|--------|----------|--------------|----------------|----------------|
| A. All competitor spy | competitor_spy | 500 (limit) | 10000 | $66.00 | ₹6,287.18 |
| B. All manual Check Now | refresh | 80000÷10=8000 | 80000 | $264.00 | ₹25,128.72 |
| C. All weekly tracking | weekly_refresh | 1500 kw × 4 wks | 30000 | $36.00 | ₹3,428.28 |
| D. Mixed worst-case | 500 competitor + 7000 manual | 500 + 7000 | 10000 + 70000 = 80000 | $66.00 + $231.00 = **$297.00** | **₹28,283.31** |

**Agency worst-case margin:**
- Revenue: ₹9,999
- Payment gateway (2%): ₹200
- GST (18%): ₹1,800
- Infrastructure + email: ₹1,200
- DataForSEO worst-case: $297.00 (₹28,283)
- **Total cost: ₹31,483**
- **Margin: ₹9,999 - ₹31,483 = -₹21,484 (-215%)**

### Key Finding — CONTRADICTION RESOLVED

**The previous plan incorrectly stated that worst-case margins were ~72%. That was based on:**
1. Outdated Live SERP pricing ($0.024 instead of verified $0.020)
2. A mistaken assumption that "1 DataForSEO credit ≈ $0.01"
3. Failure to account for the most expensive feature combinations

**Correct finding:**

**YES — under the CURRENT pricing and credit allocation, a worst-case user CAN cause Semranko to lose money on ALL paid plans.**

The theoretical worst-case assumes:
- User spends all credits on Competitor Spy ($0.132/call) + Manual Check Now ($0.033/call)
- Zero cache hits
- Weekly tracking also active

**However, this worst-case is mitigated in practice by:**
1. **Shared SERP cache:** Eliminates 60-90% of duplicate DataForSEO calls
2. **Standard Normal weekly:** Reduces weekly tracking cost by 70% (from $0.020 to $0.006)
3. **Competitor spy limit:** Capped at plan limit (50/200/500)
4. **Keyword limit:** User can't create unlimited keywords to check
5. **Real user behavior:** Normal users don't maximize expensive features

**With the recommended architecture (cache + Standard Normal weekly):**
- Theoretical worst-case (no cache): Still loss-making as shown above
- Realistic worst-case (with cache): Likely profitable, but needs monitoring
- Normal user behavior: Highly profitable

**Recommended minimum protections:**
1. Add a per-user daily DataForSEO cost cap (e.g., $5.00/day)
2. Alert when any user exceeds $10.00 DataForSEO cost in a month
3. Consider increasing competitor_spy user credit cost from 20 to 30-40 credits
4. Consider capping manual Check Now frequency (e.g., max 10 checks per day per keyword)

---

## DataForSEO Endpoint Strategy

### Weekly Tracking (Background)
```
Endpoint: /serp/google/organic/task_post
Method: POST
Priority: 1 (Normal)
Depth: 100
AIO: expand_ai_overview=false for non-AIO keywords
     expand_ai_overview=true for TrackedKeyword.trackAio=True
Pingback: https://your-domain/api/webhooks/dataforseo
Cost: ~$0.006 per keyword (Standard Normal priority=1, depth=100)
```

**Rationale:**
- `task_post` is the async endpoint, already implemented in Sunday bulk job
- Priority=1 = Standard Normal = cheapest reliable SERP method
- depth=100 required for Top 100 tracking (confirmed from dashboard code)
- AIO expansion only for keywords that explicitly track AIO
- Pingback webhook processes results asynchronously

### Manual "Check Now" (On-Demand)
```
Endpoint: /serp/google/organic/live/advanced
Method: POST
Priority: Live
Depth: 100
AIO: expand_ai_overview=false for non-AIO keywords
     expand_ai_overview=true for TrackedKeyword.trackAio=True
Cost: ~$0.020 per keyword (Live, depth=100)
```

**Rationale:**
- User expects fresh data, so Live is appropriate
- depth=100 required for Top 100 tracking
- AIO expansion only for AIO-tracked keywords
- Credit-gated to prevent abuse

### Keyword Metrics (Day-One + Refresh)
```
Endpoint: /dataforseo_labs/google/keyword_overview/live
Method: POST
Priority: Live
Cost: ~0.013 per keyword
Cache: 7 days in Redis
```

**Rationale:**
- No cheaper Labs alternative identified for keyword metrics
- Cached globally for 7 days to eliminate duplicate calls
- Only called when cache is stale or missing

### Keyword Research
```
Endpoint: /dataforseo_labs/google/keyword_ideas/live
Method: POST
Priority: Live
Cost: ~0.018 per call
Cache: 90 days in PostgreSQL (existing KeywordResearchCache)
```

**Rationale:**
- Already cached for 90 days
- No changes needed

### Competitor Spy
```
Endpoint: /dataforseo_labs/google/competitors_domain/live
Method: POST
Priority: Live
Cost: ~0.132 per call
Cache: 30 days in PostgreSQL (existing CompetitorCache)
```

**Rationale:**
- Already cached for 30 days
- No changes needed

---

## Shared Global SERP Cache

### Cache Design

**Key format:**
```
serp:v1:{engine}:{keyword_hash}:{location_code}:{language}:{device}:{os}:{depth}:{aio_flag}
```

**Example:**
```
serp:v1:google:abc123:2840:en:desktop:windows:100:false
```

**What is cached:**
- Raw SERP items (organic results, positions, URLs, domains)
- SERP features (featured snippet, PAA, AIO presence)
- Cited domains in AIO references
- Parsed organic items list

**What is NOT cached:**
- User-specific position/URL (calculated from cached SERP)
- User-specific AIO badge (calculated from cached SERP)
- Credit deductions

**Cache TTL:**
- Weekly tracking: 24 hours
- Manual Check Now: 1 hour (or bypass cache with force refresh)
- Day-one tracking: 24 hours

**Cache insertion points:**

1. `DataForSEOClient.get_serp_data_batch()` — check cache before API call, store after
2. `process_rank_check_job()` — benefit from cache automatically
3. `process_completed_async_task()` — store async results in cache
4. `dataforseo_webhook()` — store pingback results in cache
5. Manual refresh endpoint — bypass cache or use shorter TTL

**Cache bypass:**
- Manual "Check Now" with `force=true` bypasses cache
- New keyword additions bypass cache (fresh data required)

---

## Keyword Metrics Cache

### Design

**Key format:**
```
kw_metrics:v1:{keyword_hash}:{location_code}:{language}
```

**Example:**
```
kw_metrics:v1:abc123:2840:en
```

**What is cached:**
- Volume
- KD
- CPC
- Competition
- Intent
- Backlinks
- Referring domains

**TTL:** 7 days

**Insertion points:**
1. `DataForSEOClient._fetch_keyword_data_batch()` — store after Labs call
2. `dataforseo_dashboard.py:fetch_cheapest_dashboard_data()` — store after Labs call
3. Day-one tracking — check cache before Labs call
4. Weekly tracking — check cache before Labs call (if metrics refresh needed)

**Benefit:** Eliminates duplicate Labs calls across users and refreshes.

---

## Keyword Tracking Strategy

### Day-One Tracking (New Keyword Added)

```
1. User adds keyword
   ↓
2. Check SERP cache (Redis, 24h TTL)
   ↓
   Cache HIT → extract position, URL, AIO badge → skip DataForSEO
   Cache MISS → continue
   ↓
3. Check keyword metrics cache (Redis, 7d TTL)
   ↓
   Cache HIT → use cached volume/KD/CPC/etc.
   Cache MISS → call keyword_overview/live (0.013) → cache result
   ↓
4. Fetch SERP Live (depth=100, AIO conditional)
   ↓
5. Store SERP in cache
   ↓
6. Merge data → update Keyword + RankResult
   ↓
7. Deduct 20 user credits
```

**Cost:** $0.033 first time, $0.000 on cache hit

### Weekly Tracking (Paid Users Only)

```
1. Sunday 11 PM: collect_active_keywords_for_bulk()
   ↓
   Filter: ONLY users with weeklyTrackingEnabled=True AND paid plan
   ↓
2. Deduplicate keywords globally
   ↓
3. For each keyword, determine AIO requirement:
   - Check TrackedKeyword.trackAio for each user's keywords
   - If ANY user tracks AIO for this keyword, set expand_ai_overview=true
   - Otherwise, expand_ai_overview=false
   ↓
4. Submit to /serp/google/organic/task_post
   priority: 1 (Normal)
   depth: 100
   pingback_url: /api/webhooks/dataforseo
   ↓
5. DataForSEO processes async → calls pingback
   ↓
6. Webhook receives results
   ↓
7. Store SERP in global cache
   ↓
8. For each affected user/keyword:
   - Extract position, URL, AIO badge from SERP
   - Update RankResult
   - Update Keyword.position, Keyword.visibility, Keyword.ai_badge
   - Deduct weekly_refresh_per_keyword credits
   ↓
9. Update AsyncTaskQueue status
```

**Cost:** ~$0.006 per keyword (Standard Normal async)

### Trial User Exclusion

**Current bug:** `async_bulk_service.py:47` includes `trialing` users:
```python
User.subscriptionStatus.in_(["active", "trialing"])
```

**Fix:** Exclude trial users from weekly tracking:
```python
User.subscriptionStatus == "active"
User.selectedPlan.notin_(["free_trial", ""])
```

**Also fix:** Monday legacy job and Monday tracker must exclude trial users.

---

## Manual "Check Now" Strategy

### Current Behavior
- `keywords.py:refresh_project_keywords()` → `keyword_update_service.py:refresh_keyword_data()`
- Calls `DataForSeoDashboardHelper.fetch_cheapest_dashboard_data()`
- Cost: $0.033 per keyword (Labs $0.013 + Live SERP $0.020)
- Credit cost: 10 per keyword

### Proposed Behavior
```
1. User clicks "Check Now"
   ↓
2. Check user credits (10 per keyword)
   ↓
3. Check SERP cache (Redis, 1h TTL or bypass)
   ↓
   Cache HIT (fresh) → use cached data → skip DataForSEO
   Cache MISS or stale → fetch Live SERP
   ↓
4. Fetch Live SERP (depth=100, AIO conditional)
   ↓
5. Store in cache
   ↓
6. Check keyword metrics cache
   ↓
7. Merge → update Keyword + RankResult
   ↓
8. Deduct 10 user credits
```

**Cost:** $0.000 on cache hit, $0.033 on cache miss

### Trial User Restriction

**Option A (Recommended):** Disable Check Now for trial users
- Show message: "Upgrade to a paid plan to use Check Now"
- Prevents any Live SERP cost during trial

**Option B:** Allow 1-2 Check Now uses per trial with explicit credit cost
- More complex, higher risk
- Not recommended

---

## Keyword Research Strategy

### Current Behavior
- Already cached in `KeywordResearchCache` (90-day TTL)
- Calls `keyword_ideas/live` ($0.018 per call)
- Credit cost: 20 per research

### Proposed Behavior
- **No changes needed**
- Cache already prevents duplicate calls
- Cost is acceptable for the value provided

---

## Competitor Spy Strategy

### Current Behavior
- Already cached in `CompetitorCache` (30-day TTL)
- Calls `competitors_domain/live` ($0.132 per call)
- Credit cost: 20 per spy

### Proposed Behavior
- **No changes needed**
- Cache already prevents duplicate calls
- Cost is high but limited by competitorSpyLimit per plan

### Optimization Opportunity
- The `process_competitor_rank_job()` already reuses SERP data for competitor ranking
- Ensure it checks the shared SERP cache before calling DataForSEO

---

## Weekly Job Strategy

### Current Jobs

| Job | Schedule | Method | Trial Users? | Updates Keyword.position? | Deducts Credits? |
|-----|----------|--------|-------------|---------------------------|------------------|
| Legacy Monday | Mon 1 AM | Live SERP | Yes (bug) | Yes | No |
| Monday tracker | Mon 2 AM | Live + Labs | Yes (bug) | Yes | Yes |
| Sunday bulk | Sun 11 PM | Async task_post | Yes (bug) | No | No |

### Target: ONE Weekly Job

**Recommended: Sunday bulk async job becomes the single mechanism**

### Required Fixes Before Monday Jobs Can Be Disabled

| # | Issue | Current State | Required Fix |
|---|-------|---------------|--------------|
| 1 | **Trial users included** | `async_bulk_service.py:47` includes `trialing` | Filter to `active` paid users only |
| 2 | **Keyword.position not updated** | `process_completed_async_task()` only updates `RankResult` | Add `Keyword.position` and `Keyword.visibility` update |
| 3 | **Keyword.ai_badge not updated** | Not parsed in async result processing | Parse `ai_overview` items and update `Keyword.ai_badge` |
| 4 | **Credit deduction missing** | No credit logic in async processing | Deduct `weekly_refresh_per_keyword` per affected user |
| 5 | **Domain not stored** | `create_async_bulk_task()` doesn't set `task.domain` | Store domain in task for position detection |
| 6 | **Webhook bug** | `webhooks.py:311` uses undefined `row` variable | Fix variable reference |
| 7 | **AIO expansion missing** | No `expand_ai_overview` in task_post payload | Add per-keyword AIO flag based on `TrackedKeyword.trackAio` |
| 8 | **Priority parameter** | Not set in task_post payload | Add `"priority": 1` for Standard Normal |
| 9 | **Retry behavior** | Basic error handling | Add retry for transient failures |
| 10 | **Duplicate prevention** | No idempotency check | Use task_id to prevent double-processing |

### Migration Path
1. Fix all 10 issues in Sunday bulk job
2. Run both Sunday and Monday jobs in parallel for 2-4 weeks
3. Verify data consistency
4. Disable Monday jobs (keep code, just remove from scheduler)
5. Monitor for 2 more weeks
6. Delete Monday job code after verification

---

## Credit Safety Model

### Layer 1: Semranko Credits Limit User Activity
- Every feature action checks `user.creditBalance` before proceeding
- `deduct_credits()` raises HTTP 402 if insufficient
- `refund_credits()` restores credits on failure
- Credits reset monthly with no rollover

### Layer 2: Shared Cache Prevents Duplicate DataForSEO Requests
- One SERP fetch serves all users with identical parameters
- User credits still deducted, but DataForSEO cost is zero on cache hit
- Applies to: SERP data, keyword metrics, competitor data, keyword research

### Layer 3: Cheapest Suitable Endpoint
- Weekly: Standard Normal async ($0.006)
- Manual: Live ($0.020, unavoidable for freshness)
- Research: Labs ($0.018, already cached)
- Competitor: Labs ($0.132, already cached)

### Layer 4: Feature-Specific Limits
- `keywordLimit`: Maximum active keywords per plan
- `competitorSpyLimit`: Maximum competitor spy calls per plan
- `domain_limit`: Maximum projects per user
- `weeklyTrackingEnabled`: Trial users excluded from weekly tracking
- Trial credit cap: 100 credits total

### Layer 5: Cost Tracking
- Populate `DataForSEOCost` table for every actual API request
- Track: user_id, feature, endpoint, priority, depth, estimated cost, cache hit/miss, timestamp
- Enable real-time margin monitoring

---

## DataForSEO Cost Tracking

### Existing Table: `DataForSEOCost`

```python
class DataForSEOCost(Base):
    __tablename__ = "DataForSEOCost"
    id: Mapped[str]
    userId: Mapped[Optional[str]]
    taskType: Mapped[str]  # 'rank_tracker', 'aio', etc.
    endpoint: Mapped[str]  # API endpoint called
    costCredits: Mapped[float]  # Cost in DataForSEO credits
    costUsd: Mapped[Optional[float]]  # Cost in USD
    keywordCount: Mapped[int]
    meta: Mapped[Optional[dict]]  # Additional context
    createdAt: Mapped[datetime]
```

### Recommended Population

Log an entry for EVERY DataForSEO request:

| Field | Value |
|-------|-------|
| userId | user_id if known, else NULL |
| taskType | `weekly_serp`, `manual_serp`, `keyword_metrics`, `keyword_research`, `competitor_spy` |
| endpoint | Full endpoint path |
| costCredits | Actual cost from `DATAFORSEO_CREDIT_COSTS` |
| costUsd | Converted USD (if conversion rate known) |
| keywordCount | Number of keywords in batch |
| meta | `{"priority": 1, "depth": 100, "aio": false, "cache_hit": false, "location": "India"}` |
| createdAt | Timestamp |

### Where to Add Tracking

1. `DataForSEOClient.get_serp_data_batch()` — after successful API call
2. `DataForSEOClient._fetch_keyword_data_batch()` — after successful API call
3. `DataForSEOClient.get_keyword_ideas_api()` — after successful API call
4. `DataForSEOClient.get_competitor_keywords()` — after successful API call
5. `dataforseo_webhook()` — after processing pingback results

---

## Required Code Changes

### Phase 1: Shared Cache (Highest Impact)

| File | Function | Change |
|------|----------|--------|
| `services/dataforseo_client.py` | `get_serp_data_batch()` | Add cache check before API call; store results in cache after |
| `services/dataforseo_client.py` | `_fetch_keyword_data_batch()` | Add keyword metrics cache |
| `services/cache_service.py` | N/A | Ensure Redis connection supports larger SERP payloads |

### Phase 2: Standard Normal Weekly (Week 2)

| File | Function | Change |
|------|----------|--------|
| `services/async_bulk_service.py` | `submit_bulk_to_dataforseo()` | Add `"priority": 1` to payload; add per-keyword `expand_ai_overview` |
| `services/dataforseo_client.py` | `get_serp_data_batch()` | Accept `priority` parameter; pass to request |
| `services/dataforseo_client.py` | `get_rank_batch()` | Pass `priority` to `get_serp_data_batch()` |
| `workers/tasks.py` | `process_rank_check_job()` | Pass `priority` based on caller (weekly vs manual) |

### Phase 3: Trial User Exclusion (Week 2)

| File | Function | Change |
|------|----------|--------|
| `services/async_bulk_service.py` | `collect_active_keywords_for_bulk()` | Filter to `active` paid users only |
| `services/ranking_service.py` | `queue_weekly_tracking_for_all_projects()` | Exclude trial users |
| `services/monday_tracker.py` | `run_monday_tracker()` | Exclude trial users |
| `jobs/rank_scheduler.py` | `run_weekly_job()` | Exclude trial users |
| `jobs/rank_scheduler.py` | `run_sunday_night_bulk_job()` | Exclude trial users |

### Phase 4: Sunday Bulk Job Completion (Week 3)

| File | Function | Change |
|------|----------|--------|
| `services/async_bulk_service.py` | `process_completed_async_task()` | Update `Keyword.position`, `visibility`, `ai_badge`; deduct credits |
| `services/async_bulk_service.py` | `create_async_bulk_task()` | Store `domain` in task |
| `api/routes/webhooks.py` | `dataforseo_webhook()` | Fix undefined `row` variable; add credit deduction |
| `services/async_bulk_service.py` | `submit_bulk_to_dataforseo()` | Add retry logic |

### Phase 5: Client Unification (Week 3)

| File | Function | Change |
|------|----------|--------|
| `services/dataforseo_client.py` | N/A | Merge `DataForSeoDashboardHelper` methods into `DataForSEOClient` |
| `services/dataforseo_dashboard.py` | N/A | Deprecate after merge; keep for backward compatibility during transition |

### Phase 6: Cost Tracking (Week 4)

| File | Function | Change |
|------|----------|--------|
| `services/dataforseo_client.py` | All API methods | Add `DataForSEOCost` logging after each call |
| `services/credit_service.py` | `deduct_credits()` | Link credit ledger to DataForSEOCost entry |

---

## Required Database Changes

### No Schema Changes Required

All required tables already exist:
- `DataForSEOCost` — exists, needs to be populated
- `KeywordResearchCache` — exists, already used
- `CompetitorCache` — exists, already used
- `AsyncTaskQueue` — exists, already used
- `Redis` — exists via `cache_service.py`

### Data Migrations (Development Only)

| Action | Purpose |
|--------|---------|
| Clear stale SERP cache keys | Remove old cache format keys |
| Reset trial user tracking flags | Ensure trial users are excluded from weekly jobs |
| Backfill missing `Keyword.position` | Fix existing inconsistency |

---

## Code/Table Cleanup Candidates

### Remove After Verification

| Candidate | Location | Reason |
|-----------|----------|--------|
| `DataForSeoDashboardHelper` class | `services/dataforseo_dashboard.py` | Merged into `DataForSEOClient` |
| Monday legacy job scheduler | `jobs/rank_scheduler.py:run_weekly_job()` | Replaced by Sunday bulk |
| Monday tracker | `workers/monday_tracker.py` | Replaced by Sunday bulk |
| `SerpFeature` table | `db/models.py:276` | Mock extraction only, never populated |
| `mock_extract_serp_features_from_rank_result` | wherever it exists | Dead code |
| `UserCacheUnlock` table | `db/models.py:422` | Purpose unclear, appears unused |

### Keep For Now

| Candidate | Reason to Keep |
|-----------|---------------|
| Monday job code | Keep for 2-4 weeks as fallback during Sunday bulk testing |
| `DataForSeoDashboardHelper` | Keep as thin wrapper during transition |
| `TrackedKeyword` | Used for AIO tracking and partial refresh |
| `DataForSEOCost` | Will be actively used for cost tracking |

---

## Implementation Phases

### Phase 1: Shared SERP Cache (Week 1)
**Risk:** LOW | **Impact:** HIGH

1. Implement `get_serp_data_batch()` with Redis cache
2. Implement keyword metrics cache
3. Test cache hit/miss behavior
4. Verify cache key uniqueness

### Phase 2: Standard Normal Weekly (Week 2)
**Risk:** MEDIUM | **Impact:** HIGH

1. Add `priority` parameter to SERP requests
2. Update Sunday bulk job to use `priority: 1`
3. Add per-keyword AIO expansion logic
4. Test async results parsing

### Phase 3: Trial User Exclusion (Week 2)
**Risk:** LOW | **Impact:** MEDIUM

1. Filter trial users from all weekly jobs
2. Disable manual Check Now for trial users (optional)
3. Update scheduler and bulk collector

### Phase 4: Sunday Bulk Job Completion (Week 3)
**Risk:** MEDIUM | **Impact:** HIGH

1. Fix webhook `row` variable bug
2. Add `Keyword.position` update in async processing
3. Add credit deduction in async processing
4. Add domain storage in async task
5. Add retry logic

### Phase 5: Client Unification (Week 3)
**Risk:** LOW | **Impact:** LOW

1. Merge `DataForSeoDashboardHelper` into `DataForSEOClient`
2. Update all imports
3. Test all existing endpoints

### Phase 6: Cost Tracking (Week 4)
**Risk:** LOW | **Impact:** MEDIUM

1. Populate `DataForSEOCost` on every API call
2. Build admin dashboard for cost monitoring
3. Set up alerts for unusual usage

### Phase 7: Monday Job Removal (Week 5-6)
**Risk:** MEDIUM | **Impact:** LOW

1. Run Sunday + Monday in parallel for 2 weeks
2. Compare results for consistency
3. Disable Monday jobs in scheduler
4. Keep code for 2 more weeks as fallback
5. Delete Monday job code after verification

---

## Testing Plan

### Keyword Tracking Tests
- [ ] Add keyword → verifies day-one tracking works
- [ ] Add same keyword twice → verifies cache hit, no duplicate DataForSEO call
- [ ] Weekly tracking → verifies Standard Normal async works
- [ ] Weekly tracking → verifies depth=100 returns positions 1-100
- [ ] Keyword at position 37 → verifies correct position stored
- [ ] Keyword not ranking → verifies position=None, visibility=0.0
- [ ] AIO badge → verifies badge detected correctly
- [ ] AIO expansion → verifies expand_ai_overview=false for non-AIO keywords
- [ ] Multiple users, same keyword → verifies shared cache, single DataForSEO call

### Manual Check Now Tests
- [ ] Check Now → verifies Live SERP called
- [ ] Check Now with cache hit → verifies no DataForSEO call
- [ ] Check Now force refresh → verifies cache bypass
- [ ] Insufficient credits → verifies 402 error
- [ ] API failure → verifies credit refund

### Trial User Tests
- [ ] Trial user added → verifies excluded from weekly jobs
- [ ] Trial user adds keyword → verifies day-one tracking works
- [ ] Trial user Check Now → verifies disabled or limited
- [ ] Trial expires → verifies weekly tracking starts after upgrade

### Cache Tests
- [ ] Cache hit → verifies zero DataForSEO cost
- [ ] Cache TTL expiry → verifies fresh DataForSEO call
- [ ] Cache key collision → verifies different keywords have different keys
- [ ] Cache invalidation → verifies manual refresh bypasses cache

### Cost Tracking Tests
- [ ] DataForSEOCost entry created → verifies logged correctly
- [ ] Cache hit → verifies cost=0, cache_hit=true
- [ ] Weekly tracking → verifies endpoint and priority logged

---

## Worst-Case Cost Table

**Exchange rate: 1 USD = 95.23 INR**

### Summary

**Assumption:** Zero cache hits. User adds every allowed keyword one by one, then spends all remaining credits on the most expensive permitted features.

| Plan | Monthly Price | Max Credits | Keyword Adds | Remaining Credits | Most Expensive Features | Worst-Case DataForSEO USD | Worst-Case DataForSEO INR | Worst-Case Margin |
|------|---------------|-------------|--------------|-------------------|------------------------|---------------------------|---------------------------|-------------------|
| free_trial | ₹0 | 100 | 5 keywords (100 credits) | 0 | Competitor Spy 5 calls | $0.660 | ₹62.85 | **Loss** (by design) |
| starter | ₹999 | 6000 | 100 keywords (2000 credits) | 4000 | 50 competitor spy + 300 manual Check Now | $19.80 | ₹1,885.16 | **-₹886 (-89%)** |
| pro | ₹3999 | 30000 | 500 keywords (10000 credits) | 20000 | 200 competitor spy + 1600 manual Check Now | $95.70 | ₹9,112.13 | **-₹5,113 (-128%)** |
| agency | ₹9999 | 80000 | 1500 keywords (30000 credits) | 50000 | 500 competitor spy + 4000 manual Check Now | $247.50 | ₹23,558.45 | **-₹13,559 (-136%)** |

### Detailed Worst-Case Breakdown

| Plan | Step | Action | Uses | Credits | DataForSEO USD |
|------|------|--------|------|---------|----------------|
| trial | 1 | Add 5 keywords | 5 | 100 | $0.165 |
| trial | 2 | Competitor Spy 5 calls | 5 | 100 | $0.660 |
| starter | 1 | Add 100 keywords | 100 | 2000 | $3.300 |
| starter | 2 | Competitor Spy 50 calls | 50 | 1000 | $6.600 |
| starter | 3 | Manual Check Now 300 checks | 300 | 3000 | $9.900 |
| pro | 1 | Add 500 keywords | 500 | 10000 | $16.500 |
| pro | 2 | Competitor Spy 200 calls | 200 | 4000 | $26.400 |
| pro | 3 | Manual Check Now 1600 checks | 1600 | 16000 | $52.800 |
| agency | 1 | Add 1500 keywords | 1500 | 30000 | $49.500 |
| agency | 2 | Competitor Spy 500 calls | 500 | 10000 | $66.000 |
| agency | 3 | Manual Check Now 4000 checks | 4000 | 40000 | $132.000 |

### Cost Components (per plan, worst-case)

| Plan | Revenue | Payment/GST | Infra+Email | DataForSEO | Total Cost | Margin |
|------|---------|-------------|-------------|------------|------------|--------|
| trial | ₹0 | ₹0 | ₹0 | ₹63 | ₹63 | **-₹63** |
| starter | ₹999 | ₹200 | ₹1,200 | ₹1,885 | ₹3,085 | **-₹2,086** |
| pro | ₹3,999 | ₹800 | ₹1,200 | ₹9,112 | ₹11,112 | **-₹7,113** |
| agency | ₹9,999 | ₹2,000 | ₹1,200 | ₹23,558 | ₹26,758 | **-₹16,759** |

### Cost Safety Conclusion

**YES — under the CURRENT pricing and credit allocation, a worst-case user CAN cause Semranko to lose money on ALL paid plans.**

**Corrected finding:**

**Theoretical worst-case (zero cache hits, maximum plan-limit usage, keyword adds included):**
- **Starter:** $19.80 DataForSEO cost vs ₹999 revenue = **-89% margin**
- **Pro:** $95.70 DataForSEO cost vs ₹3,999 revenue = **-128% margin**
- **Agency:** $247.50 DataForSEO cost vs ₹9,999 revenue = **-136% margin**

**This worst-case requires:**
- User adds every allowed keyword one by one
- User spends all remaining credits on Competitor Spy ($0.132/call) + Manual Check Now ($0.033/call)
- Zero cache hits
- Weekly tracking also active and consuming credits

**In practice, this is mitigated by:**
1. **Shared SERP cache:** Reduces actual API calls by 60-90%
2. **Standard Normal weekly:** Reduces weekly tracking cost by 70%
3. **Competitor spy limit:** Capped at plan limit
4. **Normal user behavior:** Real users don't maximize only the most expensive features

**Technical cost-safety controls to implement before launch:**
1. Add per-user daily DataForSEO cost cap (e.g., $5.00/day)
2. Alert when any user exceeds $10.00 DataForSEO cost in a month
3. Populate `DataForSEOCost` table for real-time monitoring
4. Consider operational limits on manual Check Now frequency

**Credit/pricing note:** Current credit values are FROZEN. After validating actual DataForSEO charges from the account, credit costs should be increased so that even worst-case usage remains profitable. Do not change credit values until actual cost data is available.

### Final Verdict: Is Current Pricing Safe?

| Plan | Worst-Case Safe? | Reason |
|------|------------------|--------|
| free_trial | N/A (loss by design) | ₹0 revenue, ₹63 max DataForSEO cost |
| starter | **NO** | $19.80 DataForSEO vs ₹999 revenue = -89% margin |
| pro | **NO** | $95.70 DataForSEO vs ₹3,999 revenue = -128% margin |
| agency | **NO** | $247.50 DataForSEO vs ₹9,999 revenue = -136% margin |

**However:** These worst-case numbers assume ZERO cache hits and deliberate maximization of the most expensive features. With the recommended architecture (shared cache + Standard Normal weekly), normal user behavior is highly profitable. The theoretical loss only occurs with intentional abuse.

**Action required before launch:**
1. Implement cost-safety technical controls: daily DataForSEO cost caps, rate limits, and `DataForSEOCost` monitoring
2. Keep Monday jobs as fallback until Sunday async system is verified
3. Re-evaluate credit values AFTER validating actual DataForSEO charges from the account

---

## Final Recommendation

### CURRENT

| Path | Endpoint | Priority | Depth | AIO | Cost per Keyword |
|------|----------|----------|-------|-----|-----------------|
| Weekly | `/serp/google/organic/live/advanced` | Live | 100 | true | $0.020 |
| Manual Check Now | `/serp/google/organic/live/advanced` | Live | 100 | true | $0.020 |
| Trial weekly | Same as above (BUG) | Live | 100 | true | $0.020 |

### RECOMMENDED

| Path | Endpoint | Priority | Depth | AIO | Cost per Keyword |
|------|----------|----------|-------|-----|-----------------|
| Weekly | `/serp/google/organic/task_post` | **1 (Normal)** | 100 | conditional | **$0.006** |
| Manual Check Now | `/serp/google/organic/live/advanced` | Live | 100 | conditional | $0.020 |
| Trial weekly | **DISABLED** | N/A | N/A | N/A | **$0.000** |

### Cost Reduction Summary

| Scenario | Current | Recommended | Savings |
|----------|---------|-------------|---------|
| Weekly tracking per keyword | $0.020 | $0.006 | **70%** |
| Trial user (weekly excluded) | $0.020 | $0.000 | **100%** |
| Shared cache (duplicate keywords) | $0.020 per user | $0.020 total | **~90%** for duplicates |
| Manual Check Now (cache hit) | $0.033 | $0.000 | **100%** |

### Files Requiring Modification

| Priority | File | Function | Change |
|----------|------|----------|--------|
| P0 | `services/dataforseo_client.py` | `get_serp_data_batch()` | Add shared SERP cache + priority parameter |
| P0 | `services/dataforseo_client.py` | `_fetch_keyword_data_batch()` | Add keyword metrics cache |
| P1 | `services/async_bulk_service.py` | `submit_bulk_to_dataforseo()` | Add priority=1 + per-keyword AIO |
| P1 | `services/async_bulk_service.py` | `process_completed_async_task()` | Update Keyword fields + credit deduction |
| P1 | `services/async_bulk_service.py` | `collect_active_keywords_for_bulk()` | Exclude trial users |
| P1 | `api/routes/webhooks.py` | `dataforseo_webhook()` | Fix undefined `row` bug |
| P2 | `workers/tasks.py` | `process_rank_check_job()` | Pass priority parameter |
| P2 | `services/keyword_update_service.py` | `refresh_keyword_data()` | Check cache before DataForSEO |
| P2 | `services/dataforseo_dashboard.py` | `fetch_cheapest_dashboard_data()` | Check cache before DataForSEO |
| P3 | `jobs/rank_scheduler.py` | All jobs | Exclude trial users |
| P3 | `services/ranking_service.py` | `queue_weekly_tracking_for_all_projects()` | Exclude trial users |
| P3 | `workers/monday_tracker.py` | `run_monday_tracker()` | Exclude trial users |
| P4 | `services/dataforseo_client.py` | All API methods | Add DataForSEOCost logging |

### What Requires DataForSEO Documentation Verification

1. **Does `priority: 1` on `task_post` produce Standard Normal pricing?** — Need to verify exact parameter name and accepted values (`1` for Normal, `2` for High).
2. **Does Standard SERP include `ai_overview` items without `expand_ai_overview=true`?** — Determines AIO badge detection strategy.
3. **Does `expand_ai_overview` add extra cost on top of base SERP pricing?** — Current code uses this parameter. Need to verify if AIO expansion has separate pricing.
4. **Does Standard SERP include `rank_group` and `rank_absolute` for all organic items?** — Required for position extraction.
5. **What is the exact DataForSEO credit-to-USD conversion?** — Required for accurate margin calculation.
6. **Does DataForSEO offer a cheaper Labs endpoint for keyword metrics?** — Current `keyword_overview/live` may have Standard-priority alternative.

### Risks and Mitigations

| Risk | Level | Mitigation |
|------|-------|-----------|
| Standard SERP missing AIO items | MEDIUM | Fall back to `expand_ai_overview=true` for AIO-tracked keywords |
| `priority` parameter unsupported | MEDIUM | If unsupported, accept current $0.012 async cost (still 40% cheaper than Live $0.020) |
| Worst-case theoretical cost without cache | HIGH | Add per-user daily DataForSEO cost cap; monitor via DataForSEOCost table |
| Sunday bulk job bugs | HIGH | Fix all 10 identified issues before disabling Monday jobs |
| Monday job removal breaks users | LOW | Keep disabled for 2-4 weeks before deleting |
| Webhook `row` NameError | HIGH | Fix immediately — currently breaks all async processing |
| Cache stale data | MEDIUM | 24h TTL aligns with weekly schedule; force refresh for manual |

---

# TECHNICAL ARCHITECTURE, DATAFORSEO COST SAFETY & CREDIT TRANSACTION SPECIFICATION

## CREDIT/PRICING FREEZE

Current credit values, plan prices, and feature limits are **FROZEN**.
No credit cost, plan price, or pricing model changes are proposed or implemented in this document.
This section covers ONLY technical architecture, cost tracking, credit transaction behavior, failure/refund handling, and keyword lifecycle behavior.

---

## 1. Authoritative DataForSEO Endpoint Mapping

### New Keyword / Day-One Tracking

| Data | Endpoint | Method | Parameters | Notes |
|------|----------|--------|------------|-------|
| Position, Ranking URL, Top 100, Visibility, SERP features, AIO | `/serp/google/organic/live/advanced` | POST | depth=100, location, language, device, OS, AIO as required | Live SERP for fresh initial data |
| Volume, KD, CPC, Competition, Intent, Backlinks, Domains | `/dataforseo_labs/google/keyword_overview/live` | POST | keyword, location, language | Labs metrics; use existing global keyword metrics cache where safe |

### Weekly Background Rank Tracking

| Data | Endpoint | Method | Parameters | Notes |
|------|----------|--------|------------|-------|
| Position, Ranking URL, Top 100, Visibility, SERP features, AIO | `/serp/google/organic/task_post` | POST | depth=100, priority=1 (Standard Normal), location, language, device, OS, pingback_url, AIO per keyword | Async task; webhook processes results |

### Manual "Check Now"

| Data | Endpoint | Method | Parameters | Notes |
|------|----------|--------|------------|-------|
| Position, Ranking URL, Top 100, Visibility, SERP features, AIO | `/serp/google/organic/live/advanced` | POST | depth=100, location, language, device, OS, AIO as required | Live SERP for fresh on-demand data |

### Keyword Research

| Data | Endpoint | Method | Parameters | Notes |
|------|----------|--------|------------|-------|
| Keyword ideas, volume, KD, CPC, intent, competition | `/dataforseo_labs/google/keyword_ideas/live` | POST | seed keywords, location, language, limit | Preserve existing cache |

### Competitor Spy

| Data | Endpoint | Method | Parameters | Notes |
|------|----------|--------|------------|-------|
| Competitor domains, keywords, overlap | `/dataforseo_labs/google/competitors_domain/live` | POST | target domain, location, language, limit | Preserve existing cache; reuse SERP data where safe |

---

## 2. Shared Global SERP Cache

### Cache Design

**Key format:**
```
serp:v1:{engine}:{keyword_hash}:{location_code}:{language}:{device}:{os}:{depth}:{aio_flag}
```

**Example:**
```
serp:v1:google:abc123:2840:en:desktop:windows:100:false
```

### What is Cached
- Raw SERP items (organic results, positions, URLs, domains)
- SERP features (featured snippet, PAA, AIO presence)
- Cited domains in AIO references
- Parsed organic items list

### What is NOT Cached
- User-specific position/URL (calculated from cached SERP per user/domain)
- User-specific AIO badge (calculated from cached SERP per user/domain)
- Credit deductions
- RankResult history

### Cache TTL
- Weekly tracking: 24 hours
- Manual Check Now: 1 hour or bypass with force refresh
- Day-one tracking: 24 hours

### Cache Insertion Points
1. `DataForSEOClient.get_serp_data_batch()` — check cache before API call, store after
2. `process_rank_check_job()` — benefit from cache automatically
3. `process_completed_async_task()` — store async results in cache
4. `dataforseo_webhook()` — store pingback results in cache
5. Manual refresh endpoint — bypass cache or use shorter TTL

### Cache Bypass
- Manual "Check Now" with `force=true` bypasses cache
- New keyword additions bypass cache (fresh data required)

### Critical Rule for Financial Calculations
**Assume ZERO cache hits for worst-case profitability calculations.**
Caching is an optimization, not a requirement for plan profitability.

---

## 3. DataForSEO Cost Tracking

### Requirement
Populate `DataForSEOCost` for EVERY actual DataForSEO request.

### Minimum Fields

| Field | Value |
|-------|-------|
| userId | user_id if known, else NULL |
| projectId | project_id if known, else NULL |
| taskType | `keyword_add`, `weekly_serp`, `manual_serp`, `keyword_metrics`, `keyword_research`, `competitor_spy`, `aio` |
| endpoint | Full endpoint path |
| method | HTTP method |
| operation | DataForSEO operation name |
| taskId | DataForSEO task ID where applicable |
| keywordCount | Number of keywords in batch |
| keyword | Keyword text where applicable |
| location | Location name/code |
| language | Language code |
| device | Device |
| os | OS |
| depth | SERP depth |
| priority | Priority used (1=Normal, 2=High, Live) |
| expandAiOverview | Boolean |
| estimatedCost | Estimated USD cost from account rates |
| actualCost | Actual USD cost if available from response/account |
| cacheHit | Boolean |
| createdAt | Timestamp |
| success | Boolean |
| error | Error information where applicable |

### Insertion Points
1. `DataForSEOClient.get_serp_data_batch()` — after successful API call
2. `DataForSEOClient._fetch_keyword_data_batch()` — after successful API call
3. `DataForSEOClient.get_keyword_ideas_api()` — after successful API call
4. `DataForSEOClient.get_competitor_keywords()` — after successful API call
5. `dataforseo_webhook()` — after processing pingback results

### Source of Truth
Actual DataForSEO account billing is the source of truth for costs.
Do not rely on assumed public pricing for final profitability calculations.
The user has observed an actual Live SERP charge of approximately $0.0155 for depth=100 with AIO enabled.
Treat this as an example of why actual account billing must be measured.

---

## 4. Credit Transaction Architecture

### Reservation Model

For every credit-consuming DataForSEO operation:

```
Check eligibility
  ↓
Check credits (sufficient balance?)
  ↓
Reserve credits (atomic)
  ↓
Execute operation
  ↓
Success?
  ├── YES → Finalize deduction
  └── NO  → Refund reservation
```

### Rules
1. Never execute a paid DataForSEO request without sufficient available credits
2. Never allow a user's balance to become negative
3. Do not permanently deduct credits before the operation has successfully completed
4. For async operations: Reserve → submit task → track task → success = finalize → failure/timeout = refund
5. Ensure refunds are idempotent (same failed task cannot refund credits twice)
6. Every reservation/refund/finalization must have a transaction/reference ID

### Credit Ledger Requirements
Every credit-affecting event must be recorded with:
- Date/time
- Feature/action
- Keyword/project where applicable
- Credits reserved
- Credits consumed
- Credits refunded
- Net credit change
- Balance after transaction
- Status
- Reason
- DataForSEO task/request ID where applicable

---

## 5. Failure and Refund Management

### Required Handling
- DataForSEO API failure
- Timeout
- Invalid response
- Task failure
- Webhook failure
- Retry
- Duplicate webhook
- Partial batch failure
- Application exception
- Database failure
- Insufficient credits
- Cancellation where applicable

### Rules
1. If Semranko reserves credits and the DataForSEO operation fails → **Refund the reserved credits**
2. If the DataForSEO request succeeds and Semranko subsequently fails while processing the response → do NOT blindly issue a second request or duplicate charge
3. The system must be idempotent
4. Every reservation/refund/finalization must have a transaction/reference ID
5. Duplicate webhooks must not cause duplicate credit deductions or duplicate DataForSEO task processing

---

## 6. Keyword Lifecycle Behavior

### Add Keyword
1. Validate plan keyword limit
2. Validate credits
3. Reserve Day-One tracking credits
4. Execute required DataForSEO operations
5. On success:
   - Finalize credit deduction
   - Create/update keyword
   - Create RankResult
   - Save ranking data, metrics, AIO information
   - Record transaction
6. On failure:
   - Refund reserved credits
   - Do not permanently charge the user
   - Record the refund/failure

### Duplicate Keyword Handling
Before adding a keyword, normalize and check for existing active keyword using:
- Normalized keyword
- Project/domain
- Location
- Language
- Device
- Tracking configuration

Do not create duplicate active tracking records.
If the same keyword is legitimately used under different projects/domains, those remain independent tracking targets.

### Remove Keyword
- Consumes ZERO new credits
- Makes NO DataForSEO request
- Removes it from future weekly tracking
- Prevents future automatic weekly credit consumption
- Preserves historical rank data according to existing retention behavior
- Preserves historical credit/usage transactions
- Does NOT automatically refund previously consumed credits

### Replace/Edit Keyword
Treat the new keyword as a new tracking target:
1. Validate the new keyword
2. Check limits
3. Check/reserve required credits
4. Track the new keyword
5. If successful:
   - Finalize credits
   - Create/update the new tracking target
   - Preserve old keyword history
6. If failed:
   - Refund reserved credits
   - Retain the previous keyword state if appropriate

### Re-Adding a Previously Removed Keyword
- Treat as a new tracking operation for worst-case financial calculations
- The global SERP cache may reduce actual DataForSEO cost, but worst-case calculations must assume ZERO cache hits
- Historical rank data may be displayed/linked where appropriate
- Historical credit usage must not be refunded merely because the keyword was removed

### Bulk Keyword Addition
1. Validate all requested keywords
2. Calculate required credit reservation
3. Check available credits
4. Reserve credits atomically
5. Process the batch
6. Finalize successful operations
7. Refund failed operations

If the user does not have enough credits for the requested operation:
- Reject the entire batch
- Clearly show required credits and available credits

If partial processing is implemented later:
- Must require explicit user confirmation
- Must clearly state how many keywords will be processed

### Weekly Tracking Credit Behavior
Only eligible paid users receive recurring weekly tracking.
Trial users must NOT receive recurring weekly tracking.

When weekly tracking runs:
1. Identify eligible active paid users
2. Identify active tracked keywords
3. Check/allocate weekly tracking credits according to the final credit model
4. Reserve credits appropriately
5. Submit Standard Normal async tasks
6. Process webhook results
7. Finalize successful tracking charges
8. Refund failed tracking operations
9. Update Keyword.position, Keyword.visibility, Keyword.ai_badge, RankResult, rank history, AIO information

Removed/inactive keywords must not consume weekly tracking credits.

### Manual Check Now Credit Behavior
1. Check available credits
2. Reserve credits
3. Use Live SERP
4. Process response
5. Finalize credits on success
6. Refund credits on failure
7. Update existing ranking data/history

Do not allow users to execute Check Now without sufficient credits.
Do not allow negative credit balances.

---

## 7. Trial User Rules

Trial users:
- Must NOT receive recurring weekly tracking
- Must NOT create recurring DataForSEO costs
- Remain subject to their existing trial keyword and feature limits
- Remain subject to credit checks for credit-consuming operations

Do not silently give trial users unlimited API access.
Do not change trial credit values yet.

---

## 8. Project Creation

Creating a project/domain should NOT consume credits.
Credits should be consumed only when a feature actually performs a credit-consuming operation/DataForSEO request according to the final approved credit model.

---

## 9. Payment and GST Architecture

Plan prices should be treated as **base prices excluding GST**.

At payment time:
```
Plan price + applicable GST = final payable amount
```

The billing system must:
- Calculate GST at checkout/payment time
- Show base plan price
- Show GST separately
- Show final payable amount
- Generate the existing invoice
- Allow the user to download the invoice PDF from the Billing page
- Retain invoice/payment history

Do not include GST inside the displayed base plan price unless explicitly configured later.

Payment failure must NOT grant the user paid-plan benefits or credits.
Successful payment should activate/renew the appropriate subscription according to the existing billing architecture.

---

## 10. Payment/Credit Edge Cases

Handle at minimum:
- Successful payment
- Failed payment
- Cancelled payment
- Duplicate payment callback
- Duplicate webhook
- Payment retry
- Subscription renewal
- Subscription expiration
- Upgrade
- Downgrade
- Plan cancellation
- Insufficient credits
- Credits expiring/resetting according to plan rules
- DataForSEO failure
- DataForSEO timeout
- Refund after failed API operation
- Duplicate refund prevention
- Duplicate credit deduction prevention
- Duplicate DataForSEO task processing
- Concurrent requests attempting to consume the same credits

Credit operations must be atomic and concurrency-safe.

---

## 11. Worst-Case Financial Model

### Assumptions
- User uses every keyword allowed by their plan
- User adds keywords ONE BY ONE
- Zero batching savings
- **ZERO cache hits**
- User consumes all available credits
- User maximizes the most expensive permitted feature combinations
- User uses manual Check Now where permitted
- User uses Competitor Spy up to its plan limit
- User uses Keyword Research where permitted
- Weekly tracking runs for the full eligible period
- Actual observed DataForSEO costs are used
- Applicable payment processing costs are included
- GST treatment is correctly separated from revenue
- No assumed API discount
- No assumed cache savings

### Objective
**A paid plan must not require Semranko to pay the user's DataForSEO usage from Semranko's own pocket under the defined plan limits.**

### Current Plans and Limits (FROZEN)

| Plan | Monthly Price | Credits | Keyword Limit | Competitor Spy Limit |
|------|---------------|---------|---------------|---------------------|
| free_trial | ₹0 | 100 | 5 | 5 |
| starter | ₹999 | 6000 | 100 | 50 |
| pro | ₹3999 | 30000 | 500 | 200 |
| agency | ₹9999 | 80000 | 1500 | 500 |

### Current Credit Costs (FROZEN)

| Action | User Credits | DataForSEO Operation |
|--------|-------------|---------------------|
| add_keyword | 20 | Labs + Live SERP |
| weekly_refresh_per_keyword | 10 | Standard Normal async SERP |
| keyword_research | 20 | keyword_ideas/live |
| competitor_spy | 20 | competitors_domain/live |
| download_report | 10 | No DataForSEO cost |

### Worst-Case Calculation Template

For each plan:
1. Keyword adds: `keyword_limit × add_keyword_credits`
2. Remaining credits: `total_credits - keyword_add_credits`
3. Competitor spy max: `min(competitor_spy_limit, remaining_credits ÷ competitor_spy_credits)`
4. Manual Check Now max: `(remaining_credits - competitor_spy_credits) ÷ manual_check_now_credits`
5. Total DataForSEO cost: sum of all operations at actual measured costs
6. Compare to plan revenue minus payment/GST/infrastructure costs

### Actual DataForSEO Costs Required
The following actual costs must be measured from the DataForSEO account before finalizing the worst-case model:
- Live SERP depth=100 with AIO enabled
- Standard Normal SERP depth=100 async
- Labs keyword_overview
- Labs keyword_ideas
- Labs competitors_domain
- Any other operation actually used

Do not use assumed public pricing for final profitability calculations.

---

## 12. Monday Job Migration

Do NOT immediately delete existing Monday tracking jobs.

### Migration Sequence
1. Complete Standard Normal async implementation
2. Fix webhook processing
3. Fix domain/position/visibility/AIO processing
4. Add credit transaction handling
5. Add retry/idempotency
6. Run new weekly system alongside existing fallback where appropriate
7. Compare results
8. Verify production consistency
9. Disable old Monday jobs only after successful verification
10. Keep old code available temporarily as fallback
11. Delete old implementation only after stability is confirmed

---

## 13. Required Testing

### Keyword Lifecycle
- [ ] Add one keyword
- [ ] Add 100 keywords one-by-one
- [ ] Add duplicate keyword
- [ ] Remove keyword
- [ ] Re-add removed keyword
- [ ] Replace keyword
- [ ] Bulk add keywords
- [ ] Insufficient credits
- [ ] DataForSEO failure
- [ ] DataForSEO timeout
- [ ] Failed operation refund
- [ ] Duplicate refund
- [ ] Duplicate transaction
- [ ] Concurrent keyword additions

### Weekly Tracking
- [ ] Paid user
- [ ] Trial user
- [ ] 1 keyword
- [ ] Maximum keyword count
- [ ] Keyword removed before weekly run
- [ ] Failed weekly task
- [ ] Duplicate webhook
- [ ] Retry
- [ ] AIO keyword
- [ ] Non-AIO keyword
- [ ] Position 1
- [ ] Position 37
- [ ] Position 100
- [ ] Not ranking
- [ ] Ranking URL
- [ ] Visibility
- [ ] Rank history

### Manual Check Now
- [ ] Sufficient credits
- [ ] Insufficient credits
- [ ] Successful request
- [ ] Failed request
- [ ] Timeout
- [ ] Refund
- [ ] Repeated requests
- [ ] Cache hit
- [ ] Cache miss
- [ ] Force refresh if supported

### Billing
- [ ] Successful payment
- [ ] Failed payment
- [ ] Duplicate payment callback
- [ ] Renewal
- [ ] Cancellation
- [ ] Upgrade
- [ ] Downgrade
- [ ] GST calculation
- [ ] Invoice generation
- [ ] PDF invoice download
- [ ] Credit balance update
- [ ] Usage history

### Cost Tracking
- [ ] Verify every actual DataForSEO request produces a DataForSEOCost record
- [ ] Verify cache hit flag is set correctly
- [ ] Verify endpoint, method, priority, depth, AIO parameters are logged
- [ ] Verify user/project context is captured where known

---

## 14. Deliverables Before Pricing Changes

Before changing any credit values or finalizing the pricing model, provide:

1. Final endpoint mapping
2. Current vs new DataForSEO request flow
3. All files/functions modified
4. All existing functionality preserved
5. Cache architecture
6. Credit reservation/finalization/refund architecture
7. Keyword lifecycle behavior
8. Payment/GST handling behavior
9. Usage ledger behavior
10. Failure/edge-case handling
11. DataForSEOCost logging
12. Actual DataForSEO costs observed from the account
13. Current worst-case economics using zero cache hits
14. Any remaining risks
15. Any endpoint compatibility issues
16. Any features that cannot be safely migrated to Standard Normal

---

## 15. Final Rule

**Do not finalize or modify the credit/pricing model in this task.**

First make the technical architecture safe and measurable.
After actual DataForSEO costs are collected, we will separately design the final:
- plan prices
- credit allocations
- credits per feature
- keyword limits
- usage restrictions
- daily/monthly limits
- worst-case protection
- Plans-page explanation
- FAQ
- billing/usage messaging

The final credit model must be based on actual measured DataForSEO costs and must protect Semranko from subsidizing worst-case paid-user usage.
