import ResetPasswordPage from '@/src/views/ResetPasswordPage'
import PublicLayout from '@/src/components/PublicLayout'

export const metadata = {
  title: 'Reset Password - RankCare | RankCare',
  description: 'Reset your RankCare account password. Enter your new password to regain access.',
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
      <ResetPasswordPage />
    </PublicLayout>
  )
}
