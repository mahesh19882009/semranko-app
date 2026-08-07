# Plan: AIO Badge Modal + Visibility + Charts + Weekly Comparison

## Goal
1. Clickable AIO badge in keywords table → modal with AI Overview details
2. Visibility metric per keyword (calculated using DFS formula)
3. Charts/graphs for position, visibility, traffic history
4. Weekly comparison: last week vs current week for position, traffic, visibility

## Visibility Formula (from DFS)
Per keyword based on SERP position:
- Positions 1-10: `1.0 - (position - 1) * 0.1` → 1st=1.0, 2nd=0.9, ..., 10th=0.1
- Positions 11-20: fixed `0.05`
- Positions 21-100: `0.0`
- No rank / >100: `0.0`

## 1. Database Migration
**File:** `api/alembic/versions/<new_migration>.py`

### AIOTracking additions:
- `aiOverviewTitle` — String, nullable
- `aiOverviewMarkdown` — Text, nullable
- `references` — JSON, nullable
- `images` — JSON, nullable
- `aiOverviewType` — String, nullable

### RankResult additions (for history):
- `etv` — Float, nullable (estimated traffic value from SERP organic result)
- Add index on `(projectId, keywordId, checkedAt)` for efficient history queries

## 2. Backend: Fix RankResult History
**File:** `api/fastapi_app/app/workers/tasks.py`

Stop wiping old RankResult rows. Instead, INSERT new rows on each check. This preserves position/visibility/traffic history for weekly comparison.

Change in `process_rank_check_job`:
```python
# REMOVE this block:
for keyword in keywords:
    db.execute(delete(RankResult).where(...))

# Keep only the bulk_insert_mappings
```

## 3. Backend: Update Rank Check Worker
**File:** `api/fastapi_app/app/workers/tasks.py` — `process_rank_check_job`

When saving each rank check, also calculate and save:
- `visibility` = dfs_visibility_formula(position) → save to `Keyword.visibility`
- `etv` = from organic result if available → save to `RankResult.etv`

## 4. Backend: Update AIO Tracking Worker
**File:** `api/fastapi_app/app/workers/tasks.py` — `process_aio_tracking_job`

Extract from SERP response and save to AIOTracking:
- `aiOverviewTitle`, `aiOverviewMarkdown`, `references`, `images`, `aiOverviewType`

## 5. Backend: New AIO Detail Endpoint
**File:** `api/fastapi_app/app/api/routes/aio.py`

```
GET /api/v1/aio/{project_id}/keyword/{keyword_text}
```

Returns full AIOTracking row by projectId + keywordText. 404 if not found.

## 6. Backend: History Endpoint
**File:** `api/fastapi_app/app/api/routes/keywords.py`

```
GET /api/v1/keywords/{project_id}/history/{keyword_id}
```

Returns weekly aggregated data for last 8 weeks:
```json
{
  "keyword": "string",
  "history": [
    {
      "week_start": "2025-01-01",
      "week_end": "2025-01-07",
      "avg_position": 5,
      "avg_visibility": 0.4,
      "traffic": 120
    }
  ]
}
```

Aggregation logic: group RankResult rows by week (Mon-Sun), compute avg(position), avg(visibility), sum(etv).

## 7. Backend: Weekly Comparison Endpoint
**File:** `api/fastapi_app/app/api/routes/keywords.py`

```
GET /api/v1/keywords/{project_id}/weekly-comparison
```

Returns:
```json
{
  "position": { "this_week": 5, "last_week": 7, "change": -2, "direction": "up" },
  "visibility": { "this_week": 0.4, "last_week": 0.3, "change": 0.1, "direction": "up" },
  "traffic": { "this_week": 120, "last_week": 100, "change": 20, "direction": "up" }
}
```

Aggregation: average position/visibility and sum traffic for current week vs previous week across all active keywords.

## 8. Frontend: Keywords Table
**File:** `rankcareapp/src/views/KeywordsPage.jsx`

- Add AIO column with clickable badge (blue active, gray inactive)
- Add Visibility column
- Add AIO modal using existing Modal component

## 9. Frontend: Keyword Detail View
**File:** `rankcareapp/src/views/KeywordsPage.jsx` or new component

When clicking a keyword (or new "History" action):
- Show position line chart (Chart.js via `RankHistoryChart.jsx`)
- Show visibility line chart
- Show traffic bar/line chart
- Show weekly comparison cards

## 10. Frontend: API Functions
**File:** `rankcareapp/src/lib/api.js`

Add:
- `getAioDetailApi(projectId, keywordText)`
- `getKeywordHistoryApi(projectId, keywordId)`
- `getWeeklyComparisonApi(projectId)`

## Validation Steps
1. Run migration, verify new columns on AIOTracking and RankResult
2. Trigger rank check, verify RankResult history is preserved (no delete)
3. Verify `Keyword.visibility` is calculated and saved
4. Verify `RankResult.etv` is saved
5. Visit keywords table, verify AIO badge + Visibility column
6. Click AIO badge → modal with title, markdown, references, images
7. Click keyword history → charts show position, visibility, traffic trends
8. Verify weekly comparison shows correct deltas

## Risks / Notes
- RankResult history can grow large; consider cleanup policy for old rows (>90 days)
- Visibility is calculated per keyword, not per domain
- ETV may be null for some organic results; handle gracefully
- `aiOverviewMarkdown` can be large; modal body is scrollable
