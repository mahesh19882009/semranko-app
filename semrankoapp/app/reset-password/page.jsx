import ResetPasswordPage from '@/src/views/ResetPasswordPage'
import PublicLayout from '@/src/components/PublicLayout'

export const metadata = {
  title: 'Reset Password - Semranko | Semranko',
  description: 'Reset your Semranko account password. Enter your new password to regain access.',
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
      <ResetPasswordPage />
    </PublicLayout>
  )
}
