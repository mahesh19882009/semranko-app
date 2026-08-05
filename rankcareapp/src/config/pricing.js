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
      "On-demand Keyword Research tool",
      "On-demand Competitor Spy module",
      "Native AI Overview (AIO) badge visibility",
    ],
  },
  {
    key: "pro",
    name: "Pro",
    monthlyPrice: 3999,
    yearlyPrice: 43189,
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
      "Downloadable data report exports enabled",
    ],
  },
  {
    key: "agency",
    name: "Agency",
    monthlyPrice: 15999,
    yearlyPrice: 172789,
    description: "Built for agencies handling multiple clients and organized client delivery.",
    highlighted: false,
    cta: "Upgrade to Agency",
    refreshFrequency: "weekly",
    individual_discount_pct: 15,
    monthlyCredits: 32000,
    competitorSpyLimit: 1000,
    weeklyTrackingEnabled: true,
    features: [
      "32,000 platform credits",
      "Unlimited client project domains",
      "Downloadable data report exports enabled",
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
  { label: "Monthly Credits", free_trial: "200", starter: "2,000", pro: "8,000", agency: "32,000", enterprise: "Custom" },
  { label: "Competitor Spy", free_trial: "20 rows", starter: "100 rows", pro: "300 rows", agency: "1,000 rows", enterprise: "5,000 rows" },
  { label: "Weekly Tracking", free_trial: "Disabled", starter: "Included", pro: "Included", agency: "Included", enterprise: "Included" },
  { label: "AIO Tracking", free_trial: "0", starter: "100", pro: "100", agency: "500", enterprise: "Unlimited" },
];

export const VALID_PLAN_KEYS = PLANS.map((plan) => plan.key);

export const CREDIT_ITEMS = [
  { icon: "⚡", label: "Database Cache Hit", credits: 0, description: "Recent keyword data served instantly" },
  { icon: "🎯", label: "Rank Tracking (Add Keyword & Weekly Updates)", credits: 15, description: "Add keyword to tracker + weekly Monday update" },
  { icon: "🔍", label: "Keyword Research Search Query", credits: 4, description: "Live keyword ideas / metrics lookup" },
  { icon: "🕵️", label: "Competitor Domain Spy Lookup", credits: 6, description: "Full competitor keyword analysis per domain" },
  { icon: "🌐", label: "Add Extra Multi-Domain Project", credits: 10, description: "Create an additional website property" },
  { icon: "📄", label: "Premium CSV Report Download", credits: 10, description: "Export downloadable data report spreadsheet" },
  { icon: "➕", label: "Credit Top-Up Packet", credits: 1000, description: "Flat ₹500 per 1,000 credits anytime" },
];
