# RankCare — DataForSEO Integration & Pricing (FINAL)

## Goal
Fix critical bugs in keyword add/research/spy, restructure credit-based pricing with INR/USD toggle, implement Razorpay payment integration with GST billing, and ensure AIO tracking + auth work.

## Final Pricing Model (INR ₹ — primary)

### Per-Operation Credit Costs
| Operation | Cost (credits) | Frequency |
|-----------|----------------|-----------|
| Add keyword | 20 | One-time per keyword |
| Weekly refresh | 10/keyword | Every 6+ days since last fetch |
| Keyword research | 20 | Per research request |
| Competitor spy | 20 | Per spy request |
| Report download | 10 | Per download |
| Project addition | 1 free, then 10 | Per project after first |
| Team management | 1 team free, then 10/team | Per extra team |
| Team member | 2 free/team, then 10/member | Per extra member per team |

### Plan Allocations (INR ₹)
| Plan | Monthly Price | Max Keywords | Monthly Credits | Credit Breakdown |
|------|--------------|-------------|-----------------|------------------|
| Free | ₹0 | 5 | 100 | 5×20 = 100 (add only; no refresh until paid) |
| Starter | ₹999 | 100 | 6000 | 100×20 + 100×10×3 + 1000 (extra) |
| Pro | ₹3999 | 500 | 30000 | 500×20 + 500×10×3 + 5000 (extra) |
| Agency | ₹9999 | 1500 | 80000 | 1500×20 + 1500×10×3 + 5000 (extra) |

### Credit Top-Up
- 600 credits per ₹100
- Multiples of 600 only (1× = 600, 2× = 1200, etc.)
- No bulk discount
- All payments via Razorpay

### USD/INR Toggle
- Primary display: INR (₹)
- Toggle in UI to switch to USD
- Exchange rate: configurable (default 1 USD = 95.23 INR)
- Conversion charges: configurable fee % (default 3%)
- USD prices computed with margin: Starter ~$10.74, Pro ~$31.92, Agency ~$107.08

### Key Rules
- No credit rollover — forfeited at plan end
- Overage: Warning shown, operation blocked if insufficient credits. Partial processing allowed — refresh as many keywords as credits allow, remaining show stale data with "outdated" label (red/yellow)
- Refresh eligibility: Keywords 6+ days old (user's local timezone)
- Add cost: One-time 20 credits, not recurring
- Extra credits cover: keyword research, competitor spy, report download, project addition, team management
- Credit reset timing: On plan activation anniversary date
- Downgrade: No keyword limits — only credit limits
- GST: Excluded from displayed prices, calculated at payment time (18%)
- GSTIN: 06FHDPK2516L1ZB (CodMonks Technologies)
- Every payment adds entry in billing page table
- Succeeded payment shows PDF view/download with GST details
- Option to add user GST info on Settings page

### Warnings
1. Plan ending in 5 days
2. Low credit balance (relative to next operation cost)
3. Insufficient credits for full operation (partial processing with outdated flag)

## Tasks
1. Update config.py with final plan pricing, credit costs, limits, conversion rate
2. Update plan_service.py with new pricing (Pro=3999, Agency=80000 credits)
3. Update payments.py for new top-up model (600 credits/₹100)
4. Update credit_service.py for new credit costs
5. Implement USD/INR toggle in frontend
6. Implement billing page with PDF download and GST details
7. Implement user GST info on Settings page
8. Implement DataForSEO cost tracker for profit/loss ledger
9. Implement partial refresh with dataStatus field
10. Implement credit rollover (no rollover) and plan anniversary reset
11. Implement all warnings
12. Implement team/member/project cost deduction
13. Re-run all tests

## Already Done (prior session)
- Labs result list parsing fix, language_code additions, competitor_ids NameError, credit deduct-after-success, refresh endpoint, LOCATION_CODE_MAP, AIO toggle calls track_aio_for_project, lockedUntil fix, 401 handleUnauthenticated, get_user_plan_limits fix.

## Validation
- pytest all tests pass.
- Manual: add keyword shows fields, research returns ideas, spy returns keywords, refresh deducts 10/keyword, cost ledger logs DFO cost, outdated flag works, warnings display correctly, INR/USD toggle works, billing PDF with GST downloads.
