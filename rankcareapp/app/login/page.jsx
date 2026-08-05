import LoginPage from '@/src/views/LoginPage'
import PublicLayout from '@/src/components/PublicLayout'

export const metadata = {
  title: 'Login - RankCare | RankCare',
  description: 'Login to your RankCare account to access keyword rank tracking, competitor analysis, and SEO reporting tools.',
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
      <LoginPage />
    </PublicLayout>
  )
}
