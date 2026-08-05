import ResendVerificationPage from '@/src/views/ResendVerificationPage'
import PublicLayout from '@/src/components/PublicLayout'

export const metadata = {
  title: 'Resend Verification - RankCare',
  description: 'Resend email verification to activate your RankCare account.',
  keywords: 'SEO, keyword tracking, email verification',
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
      <ResendVerificationPage />
    </PublicLayout>
  )
}
