import ResendVerificationPage from '@/src/views/ResendVerificationPage'
import PublicLayout from '@/src/components/PublicLayout'

export const metadata = {
  title: 'Resend Verification - Semranko',
  description: 'Resend email verification to activate your Semranko account.',
  keywords: 'SEO, keyword tracking, email verification',
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
      <ResendVerificationPage />
    </PublicLayout>
  )
}
