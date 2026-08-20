Semranko Master Roadmap

Purpose: This is the single source of truth for Semranko's
product, technical, commercial, QA, and launch roadmap. Update this
file whenever a material feature is completed, a bug changes scope, a
business rule changes, or a new requirement is agreed.

Last updated: 2026-08-20
Current stage: Development / pre-launch
Current focus: Finalize Keyword Tracking reliability before moving
to the next product module.

Status Legend

✅ DONE

🟡 IN PROGRESS

🧪 NEEDS VALIDATION

⬜ TODO

🔴 BLOCKED

⏸ DEFERRED / POST-LAUNCH

1. Product and Architecture Baseline

Semranko is an SEO SaaS at semranko.ai.

Current stack:

Frontend: Next.js 16, React 19, Redux Toolkit, PrimeReact, Tailwind
CSS v4.

Backend: FastAPI, SQLAlchemy 2.x, PostgreSQL.

Development database: Neon PostgreSQL.

Cache/queue: Redis + RQ.

Scheduled/background work: APScheduler/RQ.

SEO data provider: DataForSEO.

Billing: Razorpay.

Email: Resend.

Current development deployment: AWS EC2 with Nginx, HTTPS and
systemd.

Current development frontend: app.semranko.ai.

Current development API: api.semranko.ai.

Environment strategy

🟡 Current EC2 + current Neon database are development, not
production.

Planned separation:

Local development → feature branch created from dev.

Development → dev branch, development EC2, development Neon DB,
development Redis.

Production → main branch, separate production EC2, separate
production Neon DB, separate production Redis and production
secrets/configuration.

Local development currently supports:

FastAPI locally.

Next.js locally.

Docker Redis locally.

supervised RQ worker locally.

development Neon DB connection.

Tailscale callback route for DataForSEO.

single local starter script for the application stack.

2. Frozen / Agreed Business and Architecture Decisions

These decisions should not be casually changed while fixing unrelated
bugs.

Preserve all existing user-visible functionality and data.

Pricing/credit configuration remains frozen until actual DataForSEO
economics are validated.

A simple per-keyword credit model is preferred; final commercial
value remains subject to profitability validation.

Monthly subscription credits do not roll over. At a new billing
cycle, unused monthly allocation expires and is replaced.

Purchased/top-up credit lifecycle follows the previously selected
Model A unless deliberately revised.

DataForSEO priority/cost decisions must not be changed simply
because a configuration value looks unusual; profitability must be
evaluated as a complete model.

Avoid unnecessary DataForSEO calls. Cache/database reads must never
accidentally trigger paid calls.

Changes should be implemented/tested locally first,
committed/pushed, then deployed to the development EC2.

Production must be isolated from development infrastructure.

3. Keyword Tracking

3.1 Core tracking architecture

🟡 IN PROGRESS

Existing/implemented work includes:

async DataForSEO SERP processing;

task_post / callback architecture;

Redis/RQ worker processing;

keyword processing states;

SSE keyword update notifications;

development callback routing;

credit protection/idempotency work;

Top-100 SERP tracking requirements;

ranking URL;

organic position;

Local Pack;

AIO/SERP feature data;

Volume/KD/CPC/competition/intent;

backlinks/referring domains where supported;

visibility;

manual/automatic tracking flows;

regression test coverage.

Current confirmed defect --- pending RefreshJob reuse

🔴 CURRENT PRIORITY

A pending add_keyword RefreshJob can currently be reused for a
different keyword in the same project.

Observed result:

new Keyword row can be created;

API can return 201;

no new customer credit reservation;

no new DataForSEO task;

no new ProcessingJob;

UI can remain in processing/shimmer state indefinitely.

Required fix:

pending A + different B → B must create its own reservation/job/DFS
task;

pending A + exact duplicate A → may safely reuse/idempotently return
existing work;

add regression tests for both cases;

do not discard real stale DFS task IDs without reconciliation.

3.2 Add Keyword UX

🟡 IN PROGRESS

Required final behavior:

User clicks Add Keyword.

Modal closes promptly after the request is accepted; expensive
background processing must not keep the modal open.

Processing row is visible.

Fields already available are displayed immediately.

Only genuinely unavailable fields shimmer.

Metrics such as Volume/KD/CPC/Competition/Intent should appear as
soon as persisted.

Position/URL/Local Pack/AIO/Visibility can continue shimmering while
SERP data is pending.

Final callback/SSE refreshes completed data.

No permanent shimmer.

Known frontend work:

valueOrShimmer() now prefers an available value over row
processing state.

Position and Local Pack templates prefer real values over shimmer.

SSE completion should remove only the completed keyword from
processingJobs, not clear every processing keyword.

Intent still needs the same field-by-field rendering rule if not
already changed.

DB refresh timing after initial metrics must be validated so early
metrics do not remain hidden behind stale optimistic data.

3.3 Count consistency

🔴 NEEDS FIX

Observed mismatch: plan/project usage can show 4/5 while Keyword page
shows 3/5.

Required:

define exactly which Keyword states consume a plan keyword slot;

project count, subscription usage, keyword table and backend limits
must use the same rule;

incomplete/orphan rows must not create inconsistent usage.

3.4 Credit and failure lifecycle

🧪 NEEDS VALIDATION

For every keyword operation:

reserve credits exactly once;

consume/finalize exactly once;

no duplicate charge on idempotent retry;

correct refund/release on submission failure;

callback retries must not double-charge;

a failed DFS submission must not leave an unusable paid keyword;

customer-visible usage must match the ledger.

3.5 Keyword lifecycle operations

🧪 Validate:

single add;

bulk add;

duplicate add;

remove/delete;

re-add;

replace;

deactivate;

reactivate;

manual refresh;

automatic refresh;

weekly/monthly scheduled refresh;

concurrent operations;

retries;

partial failures.

3.6 Worker/callback reliability

🧪 Validate:

RQ worker restart;

Redis restart/reconnect;

FastAPI restart;

duplicate callback;

delayed callback;

missed callback reconciliation;

stale submitted jobs;

callback idempotency;

recovery without manually editing DB rows.

3.7 Bulk scale validation

⬜ After single-keyword flow is frozen:

100 keywords.

1,000 keywords.

10,000 keywords.

Validate:

batching;

queue pressure;

DFS request economics;

credit reservation;

per-keyword progress;

partial success/failure;

retry/resume;

worker restart;

duplicate callbacks;

no lost jobs;

no double charges;

database performance;

frontend usability/progress.

Keyword Tracking exit criteria

Keyword Tracking is FINALIZED only when single and bulk workflows,
credits, callbacks, retries, counts, history/comparison, worker recovery
and required scale tests pass locally and in development without manual
intervention.

4. Ranking History and Comparison Indicators

⬜ TODO after current tracking defects

Compare the previous completed snapshot with the current
completed snapshot.

Initial fields:

Position;

Local Pack Rank;

KD;

Visibility.

Preferred UI: keep the current columns and display change indicators
rather than creating unnecessary duplicate previous-value columns.

Examples:

Position #7 ↑3 when previous position was 10.

Local Pack #2 ↑1.

Visibility 68% ↑13%.

KD 42 ↑4 (directional/neutral rather than automatically treating a
KD increase as positive).

Rules:

lower Position/LP number = ranking improvement;

higher Visibility = improvement;

KD change is informational;

first completed check has no comparison;

intermediate processing values must never become the comparison
baseline;

audit existing history/change structures before adding DB columns.

5. Keyword Research

⬜ TODO

Existing DataForSEO integration includes Labs keyword research
endpoints.

Audit/finalize:

search/request workflow;

keyword ideas/results;

Volume/KD/CPC/competition/intent;

filtering/sorting/pagination;

country/language/device behavior where applicable;

caching;

repeated-query behavior;

credit reservation/consumption/refund;

actual DFS cost;

adding researched keywords to Tracking;

exports;

errors/empty states;

limits;

usage history;

profitability protection.

Preserve existing functionality unless a deliberate product decision
changes it.

6. Competitor Spy

⬜ TODO

Existing integration includes DataForSEO competitor/domain
functionality.

Audit/finalize:

domain input and validation;

competitor discovery;

keyword/metric results;

pagination/filtering;

caching;

repeat searches;

credits;

actual DFS costs;

failure/refund behavior;

exports;

usage records;

plan limits;

UI states;

profitability.

7. Credits, Usage and Cost Accounting

⬜ TODO / partially implemented

Create one trustworthy accounting model covering:

subscription credit allocation;

top-up allocation;

reservations;

consumption;

refunds/releases;

expiration/reset;

operation history;

DataForSEO actual cost;

user-facing usage.

Required consistency:

UI balance = backend balance = ledger;

each billable operation is explainable;

duplicate/retried operations do not double-charge;

failure handling is auditable;

plan resets follow agreed non-rollover rules.

Profitability instrumentation should allow comparison of:

customer revenue / credits consumed vs actual DataForSEO cost.

Cache savings are beneficial but should not be required to make an
otherwise unprofitable plan viable.

8. Billing, Subscriptions and Payments

⬜ TODO / partially implemented

Razorpay end-to-end validation:

plan checkout;

subscription creation;

successful payment;

failed payment;

renewal;

cancellation;

upgrade/downgrade rules;

top-ups;

monthly credit allocation/reset;

webhook authentication;

webhook idempotency;

duplicate webhook handling;

payment/subscription reconciliation;

GST;

invoices;

billing history;

subscription status;

plan limits;

production-vs-test configuration.

Do not enable production payments until the complete credit/billing
lifecycle is validated.

9. Admin System

⬜ TODO / expansion required

Admin is part of the Semranko roadmap and must not be omitted from
launch planning.

Planned/admin areas include:

user management;

account status;

administrator assignment/control;

subscriptions;

payments;

invoices;

credits and manual adjustments with audit trail;

usage;

DataForSEO costs;

profitability/operation visibility;

RefreshJobs/ProcessingJobs;

stuck/failed job operational visibility;

project/keyword operational support;

centrally configurable plans;

limits;

feature availability/configuration;

audit/history for sensitive admin actions.

Final V1 admin scope must be explicitly marked as launch-blocking vs
post-launch enhancement.

10. Calculators

⬜ TODO

The roadmap includes calculator functionality. Exact
formulas/specification must be preserved/updated when recovered or
finalized rather than invented.

Known planned calculator areas include:

SEO / rank / ROI calculator;

custom-plan / profitability calculator;

mid-cycle upgrade/proration calculator or equivalent commercial
calculation logic.

Before implementation:

freeze formulas;

identify public vs authenticated vs admin-only calculators;

define which calculator affects actual billing vs informational
estimates;

add tests for money/credit calculations.

11. White Label / Agency

⬜ TODO

White-label and agency functionality is part of the broader Semranko
roadmap.

Potential/planned scope includes:

agency/customer separation;

branded reporting;

white-labelled PDF reports;

agency branding;

custom domains;

tenant-aware access/RBAC;

agency dashboard;

client-facing experience;

scheduled reports;

agency/API capabilities.

Before V1 launch, explicitly split this into:

V1 launch blocker;

V1.1/post-launch expansion.

Do not allow advanced white-label scope to delay launch unless it is
commercially required for the initial customer segment.

12. Dashboard, Reports and Exports

⬜ TODO / partially implemented

Validate:

dashboard project counts;

keyword counts;

ranking distribution;

visibility;

subscription/usage information;

account-wide vs project-specific data;

independent loading/error states;

historical movement where designed;

CSV exports;

PDF reports;

scheduled reports;

white-label reporting hooks;

large export behavior.

All displayed numbers must agree with backend source-of-truth rules.

13. Public Product, Content and Legal

⬜ TODO / audit required

Before paid launch audit:

landing/public pages;

pricing;

feature descriptions;

contact/support paths;

onboarding;

legal pages;

privacy policy;

terms;

refund/cancellation information;

billing/GST disclosures;

email templates;

SEO/meta/schema where applicable;

responsive/mobile behavior;

broken links/content.

14. Authentication, Security and Abuse Protection

🟡 PARTIALLY IMPLEMENTED / needs launch audit

Existing work includes authentication, cookies, CSRF/CORS and security
headers.

Final audit:

auth/session lifecycle;

secure production secrets;

CSRF;

CORS;

cookie domain/SameSite/Secure;

Turnstile;

rate limiting;

admin authorization;

RBAC/multi-tenant authorization;

webhook authentication;

secret rotation/storage;

sensitive logging;

input validation;

security headers;

production debug/config;

account abuse protection.

15. Email and Notifications

⬜ TODO / audit

Using Resend where applicable.

Validate:

verification;

password/account flows if supported;

billing/payment notifications;

subscription notifications;

scheduled report delivery;

operational emails;

sender/domain configuration;

failure handling;

production templates.

16. Observability, Reliability and Operations

⬜ TODO / partially implemented

Before production:

structured application logging;

API error visibility;

worker/job visibility;

queue health;

Redis health;

callback failures;

external-provider failures;

DataForSEO request/cost visibility;

payment webhook visibility;

uptime/health endpoints;

alerts;

database backup strategy;

restore procedure;

deployment rollback;

migration safety;

log retention;

incident runbook.

17. CI/CD and Branching

⬜ TODO

Target workflow:

feature/* → local testing.

merge to dev → development EC2 deployment/testing.

approved release → merge/promote to main.

main → production only.

Required:

automated tests before merge/deploy;

environment-specific secrets;

migration procedure;

deployment checklist;

rollback procedure;

smoke tests after deployment;

prevent accidental production deployment from feature/dev work.

18. Profitability Validation

⬜ TODO before final pricing

Measure actual worst-case economics for:

initial keyword tracking;

manual refresh;

recurring tracking;

Keyword Research;

Competitor Spy;

reports/exports where provider cost exists;

any future paid external operation.

For each:

DFS endpoint;

priority;

depth;

request count/batching;

actual cost;

Semranko credits charged;

effective customer revenue;

gross margin under realistic/worst-case use;

effect of caching separately.

Only after this evidence should frozen pricing/credit values be
revisited.

19. Full Product E2E / Regression

⬜ TODO

Required launch journey:

Register/create account.

Verify/login.

Subscribe/select plan.

Create project.

Add keyword.

Receive initial metrics.

Receive completed ranking data.

View history/comparison.

Bulk keyword workflow.

Keyword Research.

Add research result to Tracking.

Competitor Spy.

Manual refresh.

Scheduled refresh.

Usage/credits.

Reports/export.

Top-up.

Billing/invoice.

Renewal/cancellation/failure scenarios.

Admin operational visibility/support flow.

Also test:

desktop/mobile;

slow external APIs;

provider failures;

Redis/worker restart;

backend restart;

duplicate requests;

duplicate callbacks/webhooks;

stale jobs;

empty states;

limits;

unauthorized access;

large workloads.

20. Production Infrastructure

⬜ TODO

Production must be separate from the current development environment.

Provision/configure:

production EC2;

production Neon PostgreSQL;

production Redis;

production frontend/backend/RQ services;

Nginx;

SSL;

production environment/secrets;

DataForSEO callback;

Razorpay production webhook;

Resend production configuration;

domain/cookie/CORS/CSRF settings;

migrations;

backups;

monitoring;

log/alert configuration.

21. Launch Strategy

Current planning estimate: approximately 6--8 weeks from 2026-08-20
for a solid paid V1, subject to scope decisions and issues found in
scale/billing testing.

Planning targets:

Feature-complete/internal target: late September / early October
2026.

Production/beta target: early October 2026.

Public paid-launch planning target: approximately 2026-10-15.

Contingency: approximately 2026-10-23.

These are planning estimates, not guarantees.

Recommended launch:

internal E2E;

controlled beta;

small number of real paying users;

monitor DFS costs, jobs, billing and support issues;

widen access after stability is demonstrated.

22. Immediate Execution Order

Do not jump between modules unless a blocker requires it.

🔴 Fix different-keyword pending RefreshJob reuse.

Add regression tests for same-vs-different pending requests.

Run a clean local single-keyword E2E.

Fix field-by-field loading/shimmer behavior.

Fix keyword-count consistency.

Validate credit/refund/failure lifecycle.

Reconcile stale/missed async jobs.

Implement/validate ranking comparison indicators.

Validate keyword lifecycle edge cases.

Run 100 → 1k → 10k bulk tests.

Freeze Keyword Tracking.

Keyword Research.

Competitor Spy.

Credits/Usage/Cost accounting.

Billing.

Admin.

Calculators.

Dashboard/Reports/Exports.

White-label/agency V1 scope.

Public/legal/security/email.

Profitability validation.

Full regression/load/recovery testing.

Production infrastructure.

Controlled launch.

23. Definition of "Done"

A feature is not Done merely because the happy-path UI works.

For launch-critical features, Done means:

implementation complete;

automated regression coverage where appropriate;

local E2E passes;

development E2E passes;

credit/cost behavior verified if billable;

failure/retry behavior verified;

no known data consistency bug;

logs/operational behavior are understandable;

responsive UI checked;

documentation/roadmap status updated.

24. Decision Log

Use this section for durable project decisions.

2026-08-20 --- Master roadmap established

The repository roadmap becomes the project source of truth. Significant
scope, architecture, commercial, environment, and launch decisions
should be recorded here.

2026-08-20 --- Environment separation

Current EC2 and Neon remain development. Production will use separate
infrastructure. Planned branch model is feature branches → dev →
development, and main → production.

2026-08-20 --- Local development infrastructure

Local testing uses local FastAPI/Next.js/RQ, Docker Redis, development
Neon and Tailscale for external DFS callbacks.

2026-08-20 --- Keyword tracking current blocker

A pending RefreshJob must never be reused merely because a new keyword
belongs to the same project. Reuse is permitted only for an
equivalent/idempotent in-flight request.

2026-08-20 --- Pricing/cost configuration

Do not change frozen credit/pricing/DFS priority decisions while
debugging unrelated functionality. Revisit after measured profitability
analysis.

25. Roadmap Maintenance Rule

Whenever we:

remember an omitted requirement;

add/remove a feature;

change a business rule;

change architecture;

complete a milestone;

discover a launch blocker;

defer something to post-launch;

change launch timing;

update this file in the same development cycle.

This roadmap should be reviewed before answering "what next?", "are we
ready?", "what remains?", or "when can we launch?".