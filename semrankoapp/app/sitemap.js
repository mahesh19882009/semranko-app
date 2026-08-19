const pages = ['', '/features', '/pricing', '/about', '/contact', '/faq', '/privacy', '/terms', '/refund-policy'];
export default function sitemap() {
  const base = process.env.NEXT_PUBLIC_SITE_URL || 'https://semranko.com';
  return pages.map((path) => ({ url: `${base}${path}`, lastModified: new Date(), changeFrequency: path === '' ? 'weekly' : 'monthly', priority: path === '' ? 1 : 0.7 }));
}
