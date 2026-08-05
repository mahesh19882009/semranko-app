import PricingPage from '@/src/views/PricingPage'
import PublicLayout from '@/src/components/PublicLayout'

export const metadata = {
  title: 'Pricing - RankCare | RankCare',
  description: 'Choose the perfect SEO plan for your business. Start your free trial today.',
  keywords: 'SEO, keyword tracking, rank checking, competitor analysis, search engine optimization',
  openGraph: {
    title: 'RankCare - SEO Rank Tracking & Competitor Analysis',
    description: 'Track keyword rankings, monitor competitors, and grow your organic traffic.',
    type: 'website',
    url: 'https://rankcare.com',
  },
}

export default function Page() {
  return (
    <PublicLayout>
      <PricingPage />
    </PublicLayout>
  )
}
