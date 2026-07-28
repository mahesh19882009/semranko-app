export const TRIAL_DAYS = 10;

export const PLANS = [
  {
    key: "starter",
    name: "Starter",
    monthlyPrice: 1999,
    yearlyPrice: 1499,
    description: "Best for freelancers and small websites starting SEO tracking.",
    highlighted: false,
    cta: "Start Starter Trial",
    limits: {
      projects: 1,
      keywords: 25,
      competitorsPerProject: 3,
      reportsPerMonth: 2,
      teamMembers: 1,
      whiteLabel: false,
    },
    features: [
      "1 project",
      "Track up to 25 keywords",
      "Daily rank updates",
      "Basic reports",
      "Email support",
    ],
  },
  {
    key: "pro",
    name: "Pro",
    monthlyPrice: 4999,
    yearlyPrice: 3999,
    description: "Ideal for growing businesses that need stronger reporting and tracking.",
    highlighted: true,
    cta: "Start Pro Trial",
    limits: {
      projects: 3,
      keywords: 100,
      competitorsPerProject: 10,
      reportsPerMonth: 10,
      teamMembers: 2,
      whiteLabel: false,
    },
    features: [
      "Up to 3 projects",
      "Track up to 100 keywords",
      "Competitor tracking",
      "Advanced reports",
      "Priority support",
    ],
  },
  {
    key: "agency",
    name: "Agency",
    monthlyPrice: 9999,
    yearlyPrice: 7999,
    description: "Built for agencies handling multiple clients and white-label style delivery.",
    highlighted: false,
    cta: "Start Agency Trial",
    limits: {
      projects: 10,
      keywords: 300,
      competitorsPerProject: 25,
      reportsPerMonth: 25,
      teamMembers: 5,
      whiteLabel: true,
    },
    features: [
      "Up to 10 projects",
      "Track up to 300 keywords",
      "White-label reports",
      "Team access",
      "Premium support",
    ],
  },
];

export const PLAN_COMPARISON = [
  { label: "Projects", starter: "1", pro: "3", agency: "10" },
  { label: "Tracked keywords", starter: "25", pro: "100", agency: "300" },
  { label: "Competitors per project", starter: "3", pro: "10", agency: "25" },
  { label: "Reports / month", starter: "2", pro: "10", agency: "25" },
  { label: "Team members", starter: "1", pro: "2", agency: "5" },
  { label: "Daily rank updates", starter: "Yes", pro: "Yes", agency: "Yes" },
  { label: "Advanced reports", starter: "No", pro: "Yes", agency: "Yes" },
  { label: "White-label reports", starter: "No", pro: "No", agency: "Yes" },
  { label: "Priority support", starter: "No", pro: "Yes", agency: "Yes" },
];

export const VALID_PLAN_KEYS = PLANS.map((plan) => plan.key);