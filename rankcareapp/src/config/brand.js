export const brand = Object.freeze({
  name: 'RankCare',
  siteUrl: process.env.NEXT_PUBLIC_SITE_URL || 'https://rankcare.com',
  supportEmail: process.env.NEXT_PUBLIC_SUPPORT_EMAIL || '',
  salesEmail: process.env.NEXT_PUBLIC_SALES_EMAIL || '',
  legalName: process.env.NEXT_PUBLIC_LEGAL_NAME || '',
  social: {
    linkedin: process.env.NEXT_PUBLIC_LINKEDIN_URL || '',
    x: process.env.NEXT_PUBLIC_X_URL || '',
  },
});

export const contactHref = (email, subject = '') => (
  email ? `mailto:${email}${subject ? `?subject=${encodeURIComponent(subject)}` : ''}` : '/contact'
);
