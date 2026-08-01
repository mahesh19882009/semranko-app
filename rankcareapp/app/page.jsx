import HomePage from '@/src/views/HomePage'
import PublicLayout from '@/src/components/PublicLayout'

export const metadata = {
  title: 'RankCare - SEO Rank Tracking',
  description: 'Track keyword rankings, monitor competitors, and grow your organic traffic.',
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
      <HomePage />
    </PublicLayout>
  )
}
