# Semranko App - Optimized Implementation Summary

## Overview
This document summarizes the implementation of the high-margin SEO SaaS using DataForSEO API with "Global Smart Cache" and "Async Bulk Update" strategy.

## 1. Pricing & Credit System Updates

### Updated Plans (Excluding 18% GST)
- **Starter**: ₹999/mo → 2,000 Credits
- **Pro**: ₹3,799/mo → 8,000 Credits  
- **Agency**: ₹8,999/mo → 20,000 Credits

### Credit Deduction Rules
| Feature | Credits | Frequency |
|---------|---------|-----------|
| Rank Tracking | 30/keyword | One-time (covers initial + unlimited weekly refreshes) |
| Keyword Research | 10/seed keyword | On-Demand (every click) |
| Competitor Spy | 20/domain | On-Demand (every click) |
| Reports Download | 15/report | On-Demand |
| Project Addition | 15/project | After 1st free project |
| Team Creation | 50/team | After 1st free team |
| Team Members | 15/member | After 2 free members per team |

## 2. Database Schema Changes

### New Table: AsyncTaskQueue
Tracks bulk async job statuses for weekly rank updates.

**Fields:**
- `id`: Primary key
- `taskId`: DataForSEO task ID
- `taskType`: 'rank_tracking', 'competitor_spy', 'keyword_research'
- `status`: pending, processing, completed, failed
- `keywordsJson`: JSON array of keywords
- `domain`: Target domain for rank tracking
- `locationCode`: Location code (e.g., 2840 for US)
- `device`: desktop/mobile
- `userId`: Optional user association
- `projectId`: Optional project association
- `resultJson`: JSON result data
- `errorMessage`: Error details if failed
- `createdAt`, `updatedAt`, `completedAt`: Timestamps

### Updated Table: KeywordCache
Added field:
- `lastApiCallAt`: Track when API was last called for deduplication

## 3. Core Services Implemented

### A. Global Smart Cache Service (`global_cache_service.py`)
**Purpose**: Deduplicate API calls across all users tracking same keywords.

**Key Functions:**
- `get_cached_keyword_metrics()`: Fetch from global cache (30-day TTL)
- `get_cached_rank_position()`: Fetch rank data (7-day freshness)
- `save_keyword_metrics_to_cache()`: Update global cache
- `get_cached_competitor_data()`: Fetch competitor data (30-day TTL)
- `save_competitor_data_to_cache()`: Update competitor cache
- `deduplicate_keywords_for_api_call()`: Separate cached vs. missing keywords

**Benefit**: Reduces API costs by ~60-80% as user base grows.

### B. Async Bulk Update Service (`async_bulk_service.py`)
**Purpose**: Weekly "Sunday Night" job for bulk rank tracking.

**Key Functions:**
- `collect_active_keywords_for_bulk()`: Gather all active keywords, deduplicate
- `create_async_bulk_task()`: Create AsyncTaskQueue entry
- `submit_bulk_to_dataforseo()`: Submit to DataForSEO async API
- `process_completed_async_task()`: Update KeywordCache and RankResult tables
- `run_weekly_bulk_update_job()`: Main entry point

**Schedule**: Runs every Sunday at 11 PM via APScheduler.

**Benefit**: Async API is ~30-40% cheaper than Live API; bulk grouping reduces overhead.

### C. Updated Scheduler (`rank_scheduler.py`)
**Jobs:**
1. **Sunday Night Bulk Job** (11 PM Sunday): New optimized async bulk update
2. **Legacy Monday Job** (1 AM Monday): Existing queue-based system (kept for fallback)
3. **Monday Position Tracker** (2 AM Monday): Process position updates and charge credits

## 4. On-Demand Features Strategy

### Keyword Research & Competitor Spy
- Cache results for 30 days
- Charge credits every time user clicks/searches
- Show user their last search data even if cached
- **Benefit**: 100% revenue margin on repeated searches within 30 days

### Implementation Notes:
- Check `KeywordCache` or `CompetitorCache` before API call
- If cache hit (< 30 days old), return cached data but still charge credits
- If cache miss, call API, save to cache, charge credits

## 5. Migration

### Alembic Migration: `a8b9c0d1e2f3_add_async_task_queue_and_cache_fields.py`
Run with:
```bash
cd /workspace/api
alembic upgrade head
```

**Changes:**
- Adds `lastApiCallAt` column to `KeywordCache` table
- Creates new `AsyncTaskQueue` table with indexes

## 6. Frontend Pricing Updates (`semrankoapp/src/config/pricing.js`)

Updated plan configurations and credit items to reflect new pricing model:
- Updated monthly/yearly prices for Pro and Agency plans
- Updated credit allocations
- Added new credit items for Team and Team Member charges
- Updated descriptions to clarify one-time vs. recurring charges

## 7. Files Created/Modified

### Created:
- `/workspace/api/fastapi_app/app/services/async_bulk_service.py` - Async bulk processing
- `/workspace/api/fastapi_app/app/services/global_cache_service.py` - Global smart cache
- `/workspace/api/alembic/versions/a8b9c0d1e2f3_add_async_task_queue_and_cache_fields.py` - DB migration

### Modified:
- `/workspace/api/fastapi_app/app/db/models.py` - Added AsyncTaskQueue model, lastApiCallAt field
- `/workspace/api/fastapi_app/app/jobs/rank_scheduler.py` - Added Sunday night bulk job
- `/workspace/semrankoapp/src/config/pricing.js` - Updated pricing and credit rules

## 8. Next Steps / TODO

1. **DataForSEO API Integration**: Complete the actual API calls in `async_bulk_service.py` using the correct endpoints:
   - Use `serp/google/organic/task_post` for async rank tracking
   - Use `serp/google/organic/task_get/advanced/{task_id}` for retrieving results
   - Implement proper polling logic with exponential backoff

2. **Credit Service Updates**: Update `credit_service.py` to implement the new credit deduction rules:
   - 30 credits for rank tracking (one-time)
   - 10 credits for keyword research
   - 20 credits for competitor spy
   - 15 credits for projects after first free
   - 50 credits for teams after first free
   - 15 credits per team member after 2 free

3. **Dashboard UI Updates**: 
   - Show cached vs. fresh data indicators
   - Display "Last updated" timestamps
   - Add warnings when showing stale data

4. **Testing**:
   - Test weekly bulk job with sample data
   - Verify cache deduplication works correctly
   - Test credit deductions match new pricing

5. **Monitoring**:
   - Add logging for cache hit/miss ratios
   - Track API cost savings from deduplication
   - Monitor async job success/failure rates

## 9. Architecture Benefits

1. **Cost Reduction**: 
   - Global cache eliminates duplicate API calls
   - Async bulk API is 30-40% cheaper than live
   - 30-day cache on on-demand features = 100% margin on repeats

2. **Scalability**:
   - Bulk processing handles thousands of keywords efficiently
   - Queue-based architecture prevents API rate limiting
   - Deduplication improves as user base grows

3. **User Experience**:
   - Instant responses from cache
   - Weekly auto-refreshes without user action
   - Transparent about data freshness
