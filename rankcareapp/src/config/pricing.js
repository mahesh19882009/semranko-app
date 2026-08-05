'use client'
export const TRIAL_DAYS = 7;

export const PLANS = [
  {
    key: "free_trial",
    name: "Free Trial",
    monthlyPrice: 0,
    yearlyPrice: 0,
    description: "7-day free trial to test RankCare.",
    highlighted: false,
    cta: "Start Free Trial",
    refreshFrequency: "weekly",
    individual_discount_pct: 0,
    monthlyCredits: 200,
    competitorSpyLimit: 20,
    weeklyTrackingEnabled: false,
    features: [
      "200 platform credits",
      "7-day free trial",
      "Basic keyword tracking",
    ],
  },
  {
    key: "starter",
    name: "Starter",
    monthlyPrice: 999,
    yearlyPrice: 10789,
    description: "Best for freelancers and small websites starting SEO tracking.",
    highlighted: false,
    cta: "Upgrade to Starter",
    refreshFrequency: "weekly",
    individual_discount_pct: 0,
    monthlyCredits: 2000,
    competitorSpyLimit: 100,
    weeklyTrackingEnabled: true,
    features: [
      "2,000 platform credits",
      "Single project domain monitoring",
      "On-demand Keyword Research tool (10 credits/seed)",
      "On-demand Competitor Spy module (20 credits/domain)",
      "Native AI Overview (AIO) badge visibility",
    ],
  },
  {
    key: "pro",
    name: "Pro",
    monthlyPrice: 3799,
    yearlyPrice: 41029,
    description: "Ideal for growing businesses that need stronger reporting and tracking.",
    highlighted: true,
    cta: "Upgrade to Pro",
    refreshFrequency: "weekly",
    individual_discount_pct: 10,
    monthlyCredits: 8000,
    competitorSpyLimit: 300,
    weeklyTrackingEnabled: true,
    features: [
      "8,000 platform credits",
      "Multi-domain tracking support",
      "Full access to advanced search utilities",
      "Native AI Overview (AIO) badge visibility",
      "Downloadable data report exports enabled (15 credits/report)",
    ],
  },
  {
    key: "agency",
    name: "Agency",
    monthlyPrice: 8999,
    yearlyPrice: 97189,
    description: "Built for agencies handling multiple clients and organized client delivery.",
    highlighted: false,
    cta: "Upgrade to Agency",
    refreshFrequency: "weekly",
    individual_discount_pct: 15,
    monthlyCredits: 20000,
    competitorSpyLimit: 1000,
    weeklyTrackingEnabled: true,
    features: [
      "20,000 platform credits",
      "Unlimited client project domains",
      "Downloadable data report exports enabled (15 credits/report)",
      "Full Agency White-Label brand logo engine",
      "Priority bulk processing background queues",
    ],
  },
  {
    key: "enterprise",
    name: "Enterprise",
    monthlyPrice: 0,
    yearlyPrice: 0,
    description: "Custom bulk allocation for large teams. Contact sales for pricing.",
    highlighted: false,
    cta: "Contact Sales",
    refreshFrequency: "weekly",
    individual_discount_pct: 0,
    monthlyCredits: 999999,
    competitorSpyLimit: 5000,
    weeklyTrackingEnabled: true,
    features: [
      "Tailored bulk allocation",
      "Unlimited projects",
      "Dedicated support",
    ],
  },
];

export const CREDIT_PACKS = [
  { credits: 1000, priceInr: 500, popular: false },
  { credits: 2000, priceInr: 1000, popular: false },
  { credits: 3000, priceInr: 1500, popular: true },
  { credits: 4000, priceInr: 2000, popular: false },
];

export const PLAN_COMPARISON = [
  { label: "Monthly Credits", free_trial: "200", starter: "2,000", pro: "8,000", agency: "20,000", enterprise: "Custom" },
  { label: "Competitor Spy", free_trial: "20 rows", starter: "100 rows", pro: "300 rows", agency: "1,000 rows", enterprise: "5,000 rows" },
  { label: "Weekly Tracking", free_trial: "Disabled", starter: "Included", pro: "Included", agency: "Included", enterprise: "Included" },
  { label: "AIO Tracking", free_trial: "0", starter: "100", pro: "100", agency: "500", enterprise: "Unlimited" },
];

export const VALID_PLAN_KEYS = PLANS.map((plan) => plan.key);

export const CREDIT_ITEMS = [
  { icon: "⚡", label: "Database Cache Hit", credits: 0, description: "Recent keyword data served instantly" },
  { icon: "🎯", label: "Rank Tracking (Add Keyword + Weekly Updates)", credits: 30, description: "One-time charge per keyword covers initial fetch + unlimited weekly auto-refreshes" },
  { icon: "🔍", label: "Keyword Research (Seed Keyword)", credits: 10, description: "Live keyword ideas / metrics lookup (charged every click, cached 30 days)" },
  { icon: "🕵️", label: "Competitor Domain Spy Lookup", credits: 20, description: "Full competitor keyword analysis per domain (charged every click, cached 30 days)" },
  { icon: "🌐", label: "Add Extra Project (After 1st Free)", credits: 15, description: "Create an additional website property (first project free)" },
  { icon: "📄", label: "Premium CSV Report Download", credits: 15, description: "Export downloadable data report spreadsheet" },
  { icon: "👥", label: "Team (After 1st Free)", credits: 50, description: "Create additional team (first team free)" },
  { icon: "👤", label: "Team Member (After 2 Free)", credits: 15, description: "Add team member beyond 2 free members per team" },
  { icon: "➕", label: "Credit Top-Up Packet", credits: 1000, description: "Flat ₹500 per 1,000 credits anytime" },
];
