import RegisterPage from '@/src/views/RegisterPage'
import PublicLayout from '@/src/components/PublicLayout'

export const metadata = {
  title: 'Register - RankCare | RankCare',
  description: 'Create your RankCare account and start your 10-day free trial. Track keyword rankings, monitor competitors, and grow organic traffic.',
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
      <RegisterPage />
    </PublicLayout>
  )
}
