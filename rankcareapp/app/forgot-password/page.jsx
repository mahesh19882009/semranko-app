import ForgotPasswordPage from '@/src/views/ForgotPasswordPage'
import PublicLayout from '@/src/components/PublicLayout'

export const metadata = {
  title: 'Forgot Password - RankCare | RankCare',
  description: 'Forgot your password? Enter your email to receive a link to reset your RankCare password.',
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
      <ForgotPasswordPage />
    </PublicLayout>
  )
}
