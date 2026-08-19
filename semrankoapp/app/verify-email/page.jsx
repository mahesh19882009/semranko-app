import VerifyEmailPage from '@/src/views/VerifyEmailPage'
import PublicLayout from '@/src/components/PublicLayout'

export const metadata = {
  title: 'Verify Email - Semranko | Semranko',
  description: 'Verify your email address to activate your Semranko account and start tracking keyword rankings.',
  keywords: 'SEO, keyword tracking, rank checking, competitor analysis, search engine optimization',
  openGraph: {
    title: 'Semranko - SEO Rank Tracking & Competitor Analysis',
    description: 'Track keyword rankings, monitor competitors, and grow your organic traffic.',
    type: 'website',
    url: 'https://semranko.com',
  },
}

export default function Page() {
  return (
    <PublicLayout>
      <VerifyEmailPage />
    </PublicLayout>
  )
}
