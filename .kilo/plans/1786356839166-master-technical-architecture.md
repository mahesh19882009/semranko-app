# Semranko — Final Technical Architecture, Credit Transaction & Cost-Safety Master Plan

## CREDIT/PRICING FREEZE NOTICE

Current credit values, plan prices, and feature limits are **FROZEN**.
No credit cost, plan price, or pricing model changes are proposed or implemented in this document.
This document covers ONLY technical architecture, cost tracking, credit transaction behavior, failure/refund handling, and keyword lifecycle behavior.

Actual DataForSEO account charges are the source of truth. We have observed an actual Live SERP charge of approximately **$0.0155** for a depth=100 request with AIO enabled. Do not assume public pricing such as $0.006 is our actual account cost.

---

## 1. Preserve ALL Existing Product Data and Functionality

We are optimizing API usage and architecture, NOT reducing functionality.

The following user-visible data must continue to work without degradation:

* Keyword
* Position
* Ranking URL
* Top 100 results
* Rank history
* Visibility
* Search volume
* KD
* CPC
* Competition
* Search intent where currently supported
* AIO data
* AIO badge
* AIO description/content where currently supported
* SERP features
* Featured snippets
* PAA
* Competitor data
* Historical RankResult records
* Dashboard data
* Reports
* CSV/PDF exports
* Existing billing/invoice functionality

Do not remove or silently downgrade any existing feature simply to reduce DataForSEO cost.

The optimization should happen through:
* Appropriate DataForSEO endpoint selection
* Async processing
* Standard priority where technically compatible
* Caching
* Deduplication
* Correct scheduling
* Credit controls
* Rate limits
* Usage restrictions
* Cost monitoring

---

## 2. DataForSEO Endpoint Strategy

### Weekly Background Tracking

Preferred endpoint:
```
POST /serp/google/organic/task_post
```

Configuration:
* Async task_post
* Standard Normal priority if supported by our account/API
* depth=100
* webhook/pingback
* AIO behavior based on actual supported response behavior
* asynchronous result processing

Do NOT assume the cost is $0.006.
The actual DataForSEO account charge must be measured.
If Standard Normal is unavailable or does not support a required feature, document the fallback and actual observed cost.

### Manual "Check Now"

Continue using:
```
POST /serp/google/organic/live/advanced
```

The user expects fresh/on-demand results.

Preserve:
* depth=100
* required ranking data
* AIO behavior where required
* all existing SERP fields

Do not reduce depth or remove AIO information unless explicitly validated that the product does not depend on it.

### Keyword Metrics

Continue using the appropriate DataForSEO Labs endpoint for:
* volume
* KD
* CPC
* competition
* other existing keyword metrics

Do not remove these metrics.
Caching may be used because these metrics do not need to be requested repeatedly when the cached data is still valid.

### Keyword Research

Continue using the existing Keyword Research DataForSEO endpoint and existing cache.

### Competitor Spy

Continue using the existing Competitor Spy DataForSEO endpoint and existing cache.

Do not assume competitor spy is cheap.
Its actual account cost must be measured and used in the final profitability model.

---

## 3. Actual DataForSEO Cost Validation

Before changing credit values, create/verify a cost matrix based on REAL account billing.

For every DataForSEO operation measure:

```text
Feature
Endpoint
Method
Priority
Depth
AIO parameters
Keyword count
Request ID / task ID
Actual DataForSEO charge
Date/time
User
Project
Cache hit/miss
```

At minimum measure:
1. Add keyword / Day-one tracking
2. Weekly SERP tracking
3. Manual Check Now
4. Keyword Research
5. Competitor Spy
6. Any other DataForSEO operation currently used by Semranko

The final pricing model MUST use these observed costs.
Do not use assumed public pricing as the final cost model.

---

## 4. Shared Global SERP Cache

Implement a shared global SERP cache.

**NEVER use cache savings when calculating worst-case profitability.**
Worst-case calculations must assume:
```text
ZERO cache hits
ZERO batching savings
ZERO duplicate savings
```

Cache is an optimization, not a financial dependency.

### Cache Key Design

Key format:
```
serp:v1:{engine}:{keyword_hash}:{location_code}:{language}:{device}:{os}:{depth}:{aio_flag}
```

Example:
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

---

## 5. Weekly Tracking Architecture

The long-term target is ONE weekly tracking system.

Preferred flow:
```
Sunday async task_post
        ↓
DataForSEO
        ↓
Webhook / Pingback
        ↓
Async result processor
        ↓
RankResult
Keyword.position
Keyword.visibility
Keyword.ai_badge
Rank history
Credit transaction
Usage history
```

Weekly tracking should only run for eligible paid users.
Trial users must NOT receive recurring weekly tracking.

Do not disable the existing Monday jobs immediately.
Keep them available as fallback until the new async system has been validated against production results.

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

## 6. Preserve All Async Processing Correctness

Fix all previously identified problems:

* webhook `row` variable bug
* task/domain association
* position extraction
* Keyword.position update
* Keyword.visibility update
* AIO badge processing
* AIO description where required
* RankResult creation/update
* duplicate webhook processing
* duplicate task processing
* retry handling
* timeout handling
* partial failures
* failed task handling

Every async DataForSEO task must have a unique internal transaction/reference ID.

---

## 7. Credit Transaction Architecture

Implement credits using a reservation/finalization/refund model.

### Required Flow

```
Feature requested
       ↓
Check plan eligibility
       ↓
Check credit balance
       ↓
Atomically RESERVE credits
       ↓
Execute DataForSEO / feature operation
       ↓
       ├── SUCCESS
       │      ↓
       │   FINALIZE deduction
       │
       └── FAILURE
              ↓
           REFUND reservation
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
* Date/time
* Feature/action
* Keyword/project where applicable
* Credits reserved
* Credits consumed
* Credits refunded
* Net credit change
* Balance after transaction
* Status
* Reason
* DataForSEO task/request ID where applicable

---

## 8. Credit Ledger / Usage History

Every credit-affecting operation MUST create a ledger record.

Record:
```text
transaction_id
user_id
project_id
keyword_id where applicable
feature/action
timestamp
credits_reserved
credits_consumed
credits_refunded
net_credit_change
balance_before
balance_after
status
reason
DataForSEO request_id
DataForSEO task_id
```

The Billing page must always show the user's credit usage/refund history.

The user should be able to understand:
* what consumed credits
* how many credits were consumed
* what was refunded
* why it was refunded
* current balance
* previous balance
* date/time
* feature involved

Do not silently modify balances.

---

## 9. Keyword Lifecycle and Credit Transactions

### A. Add Keyword

When a user adds a keyword:
1. Check subscription/plan eligibility
2. Check keyword limit
3. Check duplicate keyword
4. Check available credits
5. Reserve required Day-One tracking credits
6. Perform required DataForSEO operations
7. On success:
   * Create keyword
   * Create/update RankResult
   * Store position
   * Store URL
   * Store metrics
   * Store AIO data
   * Store SERP features
   * Finalize credit deduction
   * Record transaction
8. On failure:
   * Do not permanently charge credits
   * Refund reservation
   * Record failure/refund

This must work whether keywords are added:
* one at a time
* in bulk
* through API
* through UI
* repeatedly

---

## 10. Adding Keywords ONE BY ONE

The financial model MUST assume the user can add every keyword allowed by their plan individually.

Example:
```text
Starter keyword limit = X
User adds keyword 1
User adds keyword 2
User adds keyword 3
...
User adds keyword X
```

Do NOT assume that batching will reduce DataForSEO cost.

For worst-case financial calculations:
```text
Each keyword addition is treated independently.
Zero batching savings.
Zero cache hits.
```

This is mandatory.

---

## 11. Duplicate Keyword

Before creating a new active keyword, check:
```text
normalized keyword
project/domain
location
language
device
tracking configuration
```

If an identical active tracking target already exists:
* Do not create duplicate tracking
* Do not make unnecessary DataForSEO requests
* Do not consume credits unnecessarily
* Show a clear user-facing message

If the same keyword is intentionally tracked for different domains/projects, those are separate tracking targets.

---

## 12. Remove Keyword

Removing a keyword:
* consumes ZERO new credits
* makes NO DataForSEO request
* removes the keyword from future weekly tracking
* prevents future weekly credit consumption
* preserves existing historical data according to retention rules
* preserves credit transaction history
* does NOT automatically refund previously consumed credits

This behavior is explicitly required by the current architecture.

---

## 13. Replace Keyword

Implement an explicit and safe "Replace Keyword" lifecycle.

When the user replaces:
```text
Old Keyword → New Keyword
```

DO NOT silently treat it as a rename if it changes the tracking target.

The system must:
1. Validate the new keyword
2. Check keyword limits
3. Check whether the new keyword already exists
4. Determine whether the operation requires Day-One tracking
5. Reserve credits BEFORE performing any paid operation
6. Execute the new keyword tracking
7. If successful:
   * Create/update the new tracking target
   * Preserve old keyword historical data
   * Stop future tracking for old keyword
   * Finalize new-keyword credits
   * Record the replacement transaction
8. If the new keyword tracking fails:
   * Refund reserved credits
   * Keep the old keyword active
   * Do not leave the user without tracking
   * Record failure/refund

Never delete the old keyword first and then attempt the new DataForSEO request.
The user's existing tracking must remain safe until replacement succeeds.

---

## 14. Bulk Add Keywords

If bulk keyword addition exists:
* Validate the entire request
* Check plan keyword limit
* Check available credits
* Reserve credits atomically
* Process each keyword independently
* Support partial success
* Deduct only successful operations
* Refund failed operations
* Record every keyword transaction separately
* Prevent duplicate charging

Example:
```text
100 keywords submitted

80 successful
15 failed
5 duplicates

Credits:
80 successful → consumed
15 failed → refunded
5 duplicates → no charge
```

Do not charge for failed or duplicate operations.

---

## 15. Bulk Remove Keywords

Removing multiple keywords:
* consumes zero credits
* makes zero DataForSEO calls
* stops future weekly tracking
* preserves historical data
* preserves transaction history

---

## 16. Weekly Credit Consumption

Weekly tracking credits should only be consumed for successfully processed eligible keywords.

For each weekly keyword:
```text
Eligible?
 ↓
Credits available?
 ↓
Reserve
 ↓
DataForSEO task
 ↓
Successful result
 ↓
Finalize weekly tracking credits
```

If DataForSEO fails:
```text
Reserved credits → refund
```

If the keyword was removed before the weekly job executes:
```text
Do not track
Do not consume credits
```

If the user is no longer eligible for weekly tracking:
```text
Do not track
Do not consume credits
```

---

## 17. Trial Users

Trial users must NOT receive recurring weekly tracking.

Do not silently spend their credits on scheduled tracking.

Trial usage must still follow:
* credit limits
* keyword limits
* feature restrictions
* DataForSEO cost controls

Do not give trial users unlimited API access.

---

## 18. Project Creation

REMOVE project creation charges.

Creating a project/domain must consume:
```text
ZERO credits
ZERO DataForSEO requests
```

Credits are only consumed when a credit-consuming feature actually performs work.

This requirement is already present in the architecture.

---

## 19. Failure / Refund Edge Cases

Handle all of the following:
* DataForSEO API failure
* DataForSEO timeout
* invalid response
* async task failure
* webhook failure
* duplicate webhook
* retry
* partial batch failure
* application exception
* database exception
* insufficient credits
* cancelled operation where applicable
* duplicate payment callback
* duplicate credit deduction
* duplicate refund
* concurrent requests
* task submitted successfully but webhook delayed
* webhook received multiple times
* DataForSEO succeeds but Semranko processing fails
* user removes keyword while async task is running
* user replaces keyword while async task is running
* subscription expires while task is running
* plan changes while task is running

Credits must be concurrency-safe and idempotent.

---

## 20. Payment and Subscription Edge Cases

Preserve and correctly handle:
* successful payment
* failed payment
* cancelled payment
* duplicate payment callback
* duplicate webhook
* payment retry
* subscription renewal
* subscription expiration
* upgrade
* downgrade
* cancellation
* insufficient credits
* monthly credit reset
* credit expiration according to plan rules

Payment failure must NOT activate paid benefits or grant paid credits.
Successful payment must activate/renew the correct plan.

---

## 21. GST and Invoice

Plan prices displayed on the pricing page are BASE prices excluding GST.

At payment:
```text
Plan price
+
Applicable GST
=
Final payable amount
```

The checkout must clearly show:
```text
Plan price
GST
Final amount
```

GST should NOT be hidden inside the displayed base plan price.

The existing invoice system must continue working.

After successful payment:
* generate invoice
* include applicable GST
* save invoice/payment history
* allow user to download invoice PDF from Billing page

The Billing page must provide access to invoice PDFs.

---

## 22. Billing Page

The Billing page should show:

### Subscription
* Current plan
* Plan price
* Billing cycle
* Renewal date
* Subscription status
* Available credits

### Payment history
* Date
* Plan
* Base amount
* GST
* Total paid
* Payment status
* Invoice
* Download PDF

### Credit usage

Show complete credit history:
```text
Date
Feature
Project
Keyword
Credits reserved
Credits consumed
Credits refunded
Net change
Balance after
Status
Reason
```

Examples:
```text
Keyword Added
-20 credits
Success

Weekly Tracking
-10 credits
Success

Check Now
-10 credits
Success

DataForSEO Failure
+10 credits
Refund

Duplicate Keyword
0 credits
Skipped
```

Users should always be able to understand where their credits went.

---

## 23. User-Facing Usage Transparency

The pricing page and FAQ must clearly explain how credits work.

Do NOT expose internal DataForSEO implementation unnecessarily, but clearly communicate:

### Example FAQ

**What uses credits?**
* Adding/tracking a keyword
* Weekly keyword refresh
* Manual Check Now
* Keyword Research
* Competitor Spy
* Reports, if applicable

**Does creating a project cost credits?**
No. Project creation is free.

**Does removing a keyword refund credits?**
No. Removing a keyword stops future tracking but does not refund previously completed work.

**What happens if a tracking request fails?**
Reserved credits are automatically refunded when the paid operation fails.

**Can I add keywords one by one?**
Yes, subject to your plan's keyword limit and available credits.

**Will my active keywords continue to be tracked weekly?**
Eligible paid-plan keywords continue to be tracked according to the plan's weekly tracking rules.

**What happens if I don't have enough credits?**
The system will not start a credit-consuming operation without sufficient credits.

**Can I see my credit usage?**
Yes. The Billing page shows credit consumption and refund history.

**Are plan prices inclusive of GST?**
No. GST is calculated separately at payment time and shown before payment.

**Can I download my invoice?**
Yes. Invoice PDFs are available from the Billing page after successful payment.

---

## 24. Worst-Case Financial Model

Do NOT calculate profitability using normal user behavior.

Use this exact worst-case model:
```text
ZERO cache hits
ZERO batching savings
User adds every keyword allowed by plan
User adds them ONE BY ONE
Every successful keyword addition incurs its actual required DataForSEO operations
User performs all permitted expensive features
User uses Competitor Spy up to its plan limit
User uses Manual Check Now up to permitted limits
User uses Keyword Research where allowed
Weekly tracking runs for every eligible keyword for the full period
Actual DataForSEO account charges are used
Payment processing costs included
GST handled separately
No assumed API discounts
No assumed cache savings
No assumed public pricing
```

The paid plan must be designed so that:
**Semranko does not pay the user's DataForSEO usage from Semranko's own pocket under the defined plan limits.**

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
* Live SERP depth=100 with AIO enabled
* Standard Normal SERP depth=100 async
* Labs keyword_overview
* Labs keyword_ideas
* Labs competitors_domain
* Any other operation actually used

Do not use assumed public pricing for final profitability calculations.

---

## 25. Important Pricing Rule

DO NOT change the existing credit values yet.

Current values remain frozen until actual DataForSEO costs are validated.

The architecture must be ready to support:
* different credit costs per feature
* different limits per plan
* daily feature limits
* per-keyword limits
* monthly limits
* rate limits
* cost caps

Only after real account data is collected should we decide:
```text
Plan price
+
Plan credits
+
Keyword limits
+
Credit cost per operation
+
Feature limits
+
Manual refresh limits
+
Competitor limits
```

---

## 26. Cost-Safety Restrictions

Implement configurable safeguards.

### Per-user daily DataForSEO cost limit

If actual DataForSEO spend exceeds the configured threshold:
* block further expensive operations
* show clear message
* allow normal non-DataForSEO features
* notify admin

### Manual Check Now rate limit

Example configuration:
```text
Maximum checks per keyword per day
Maximum checks per user per day
Maximum checks per project per day
```

These values must remain configurable and should NOT be hardcoded into the final pricing until cost validation is complete.

### Competitor Spy

Maintain plan-level limits.

### Keyword Research

Maintain plan-level/credit limits.

### Weekly Tracking

Only eligible paid users.

---

## 27. DataForSEOCost Logging

Populate `DataForSEOCost` for EVERY actual DataForSEO request.

### Required Fields

```text
user_id
project_id
keyword_id
task_type
endpoint
HTTP method
priority
depth
AIO configuration
keyword_count
estimated_cost
actual_cost when available
cache_hit
cache_key/version
DataForSEO request ID
DataForSEO task ID
timestamp
status
error
```

### Task Types
* `keyword_add`
* `weekly_serp`
* `manual_serp`
* `keyword_metrics`
* `keyword_research`
* `competitor_spy`
* `aio`

This table becomes the source for actual cost analysis.

Do not log only successful requests.
Also log failed requests where DataForSEO may have charged us.

---

## 28. Cost Dashboard / Reporting

Create internal/admin reporting showing:
```text
Total DataForSEO spend
Spend by endpoint
Spend by feature
Spend by user
Spend by plan
Spend by project
Spend per keyword
Spend per successful operation
Cache hit rate
Cache miss rate
Refunded credits
Consumed credits
DataForSEO cost vs user revenue
```

This is required before finalizing pricing.

---

## 29. Production Verification

Before removing any old job:

Compare old and new systems for the same keywords.

Verify:
* position
* URL
* visibility
* rank history
* AIO badge
* AIO data
* SERP features
* metrics
* RankResult
* credit deduction
* refunds
* DataForSEO costs

The new architecture must produce equivalent user-visible results.

---

## 30. What AG Must NOT Do

Do NOT:
* change credit values
* change plan prices
* assume $0.006 is our actual DataForSEO cost
* assume cache savings in worst-case calculations
* remove existing ranking data
* remove Top 100 tracking
* remove AIO functionality
* remove volume/KD/CPC/competition
* charge for project creation
* charge for removing a keyword
* permanently charge failed operations
* allow negative credits
* silently consume credits
* silently refund credits
* delete historical keyword data during replacement
* disable Monday fallback before verification
* make pricing decisions based only on public DataForSEO pricing

---

## 31. Required Deliverables From AG

Before changing pricing, AG must provide:

### A. Technical architecture changes
List every modified file/function and why.

### B. DataForSEO endpoint matrix
```text
Feature
Endpoint
Priority
Depth
AIO
Async/Sync
Actual observed cost
```

### C. Credit transaction matrix
```text
Feature
When credits are reserved
When credits are consumed
When credits are refunded
Failure behavior
```

### D. Keyword lifecycle matrix
```text
Add
Duplicate
Remove
Replace
Bulk Add
Bulk Remove
Weekly Tracking
Manual Check Now
```

### E. Payment/billing matrix
```text
Payment success
Payment failure
Renewal
Upgrade
Downgrade
Cancellation
GST
Invoice
Credit reset
```

### F. Actual cost report
Use real DataForSEO account charges.
Do NOT use estimated public pricing for the final calculation.

### G. Worst-case profitability report
For every plan show:
```text
Plan price excluding GST
Payment processing cost
Maximum allowed keywords
Day-One DataForSEO cost
Weekly DataForSEO cost
Maximum Manual Check Now cost
Maximum Competitor Spy cost
Maximum Keyword Research cost
Total DataForSEO cost
Total operational cost
Worst-case profit/loss
```

Assume ZERO cache hits and ZERO batching savings.

### H. Recommended final pricing
Only AFTER all of the above is validated, recommend:
* credits per plan
* credits per feature
* keyword limits
* manual refresh limits
* competitor limits
* other restrictions

Do not change pricing before this validation.

---

## 25. Implementation Order

Follow this exact order:

### Phase 1 — Freeze
Freeze current pricing and credit configuration.

### Phase 2 — Instrumentation
Implement complete DataForSEOCost logging for every actual request.

### Phase 3 — Transactions
Implement robust credit reservation/deduction/refund transaction handling.

### Phase 4 — Keyword Operations
Verify add/remove/replace/retry/failure/refund/duplicate requests/concurrent requests.

### Phase 5 — API Optimization
Implement shared SERP cache.

### Phase 6 — Async Weekly
Implement Standard Normal async weekly tracking where verified.

### Phase 7 — Validation
Compare async weekly results with the existing Monday implementation.

### Phase 8 — Cost Collection
Collect actual DataForSEO charges from the account.

### Phase 9 — Financial Simulation
Calculate true worst-case economics.

### Phase 10 — Pricing Decision
Only now recommend final credits per feature, monthly credits, keyword limits, manual refresh limits, competitor limits, other restrictions.

### Phase 11 — User Transparency
Update pricing page, FAQ, billing page, usage history, feature-level credit messaging.

### Phase 12 — Production Rollout
Keep existing Monday jobs available as fallback until the new architecture has been verified against production results.

---

## 26. What AG Must NOT Do

Do NOT:
* change credit values
* change plan prices
* assume $0.006 is our actual DataForSEO cost
* assume cache savings in worst-case calculations
* remove existing ranking data
* remove Top 100 tracking
* remove AIO functionality
* remove volume/KD/CPC/competition
* charge for project creation
* charge for removing a keyword
* permanently charge failed operations
* allow negative credits
* silently consume credits
* silently refund credits
* delete historical keyword data during replacement
* disable Monday fallback before verification
* make pricing decisions based only on public DataForSEO pricing

---

## 27. Important Pricing Principle

Do NOT finalize the credit model based on theoretical DataForSEO pricing.

Use actual DataForSEO account charges.

We have already observed an actual charge around:
```text
$0.015500
```
for a Live Google Organic SERP request with:
* depth=100
* expand_ai_overview=true
* desktop
* Windows
* location_code=2356

Therefore, validate actual charges for EACH important operation.

Record at least several real samples for:
1. Live SERP without AIO
2. Live SERP with AIO
3. Standard Normal async SERP
4. Standard High async SERP if relevant
5. Keyword Overview
6. Keyword Ideas
7. Competitor Spy
8. Any other billable DataForSEO operation used by Semranko

Only after these are validated should we finalize credits.

---

## 28. Cost-Safety Restrictions

Implement configurable safeguards.

### Per-user daily DataForSEO cost limit

If actual DataForSEO spend exceeds the configured threshold:
* block further expensive operations
* show clear message
* allow normal non-DataForSEO features
* notify admin

### Manual Check Now rate limit

Example configuration:
```text
Maximum checks per keyword per day
Maximum checks per user per day
Maximum checks per project per day
```

These values must remain configurable and should NOT be hardcoded into the final pricing until cost validation is complete.

### Competitor Spy
Maintain plan-level limits.

### Keyword Research
Maintain plan-level/credit limits.

### Weekly Tracking
Only eligible paid users.

---

## 29. Production Verification

Before removing any old job:

Compare old and new systems for the same keywords.

Verify:
* position
* URL
* visibility
* rank history
* AIO badge
* AIO data
* SERP features
* metrics
* RankResult
* credit deduction
* refunds
* DataForSEO costs

The new architecture must produce equivalent user-visible results.

---

## FINAL OBJECTIVE

The final Semranko system must satisfy all of these simultaneously:

1. Preserve all existing user-visible functionality.
2. Use the cheapest technically compatible DataForSEO endpoint for each operation.
3. Use async Standard SERP for weekly tracking where validated.
4. Keep Live SERP for fresh manual checks.
5. Use global caching to reduce real-world costs.
6. NEVER depend on cache savings for worst-case profitability.
7. Correctly reserve, consume and refund credits.
8. Make all credit transactions auditable.
9. Handle add/remove/replace/bulk keyword lifecycle safely.
10. Make project creation free.
11. Exclude trial users from recurring weekly tracking.
12. Keep Monday jobs as fallback until production verification is complete.
13. Show users clear usage/credit information.
14. Show GST separately at payment time.
15. Provide downloadable PDF invoices from Billing.
16. Preserve credit usage/refund history.
17. Log every actual DataForSEO cost.
18. Base final pricing on actual DataForSEO account charges.
19. Ensure worst-case permitted usage does not make Semranko pay the user's DataForSEO costs from its own pocket.
20. Do NOT change credit values until the actual cost-validation phase is complete.

Treat this document as the master technical specification until the actual DataForSEO cost validation is completed.
