# Restore AIO Column in Keywords Table

## Goal
Show AIO status as a read-only column in the keywords table. Keep the toggle feature fully removed.

## Current State
- `KeywordsPage.jsx` was rewritten and the AIO column was completely removed
- Backend `/tracked-keywords/toggle-aio` and `/toggle-aio-bulk` endpoints are removed
- `pricingApi.js` no longer has `toggleTrackedKeywordAioApi` or `bulkToggleTrackedKeywordAioApi`
- AIO data is still fetched automatically from DFS and stored in `Keyword.ai_badge` / `AIOTracking`

## Required Changes

### Frontend: `rankcareapp/src/views/KeywordsPage.jsx`
- Add back an AIO column as a **read-only badge** only
- Column header: `AIO`
- Body template:
  - If `rowData.ai === "AIO"` or `rowData.hasAIOverview` is truthy → show blue/purple `AIO` badge
  - Else → show `—` or `No AIO`
- Remove all toggle-related code (already done):
  - `handleAioToggle`
  - `handleBulkAioToggle`
  - `aioConfirm` state
  - `aioLoading` state
  - `bulkAioConfirm` state
  - `bulkAioLoading` state
  - AIO bulk action buttons in selection toolbar
  - AIO confirm modals
- Keep the AIO column **non-interactive** — no click handlers, no API calls

### Data Source
- The `/api/keywords/{projectId}/table` endpoint already returns `ai` / `hasAIOverview` fields from `Keyword.ai_badge`
- No backend changes needed

## Verification
- Frontend `npm run build` passes
- Keywords table shows AIO column with correct badge states
- No toggle buttons or modals present
- No references to removed toggle APIs
