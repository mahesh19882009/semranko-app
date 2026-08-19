import ForgotPasswordPage from '@/src/views/ForgotPasswordPage'
import PublicLayout from '@/src/components/PublicLayout'

export const metadata = {
  title: 'Forgot Password - Semranko | Semranko',
  description: 'Forgot your password? Enter your email to receive a link to reset your Semranko password.',
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
      <ForgotPasswordPage />
    </PublicLayout>
  )
}
