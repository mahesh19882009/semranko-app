import VerifyEmailPage from '@/src/views/VerifyEmailPage'
import PublicLayout from '@/src/components/PublicLayout'

export const metadata = {
  title: 'Verify Email - RankCare | RankCare',
  description: 'Verify your email address to activate your RankCare account and start tracking keyword rankings.',
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
      <VerifyEmailPage />
    </PublicLayout>
  )
}
