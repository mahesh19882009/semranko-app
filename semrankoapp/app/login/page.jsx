import LoginPage from '@/src/views/LoginPage'
import PublicLayout from '@/src/components/PublicLayout'

export const metadata = {
  title: 'Login - Semranko | Semranko',
  description: 'Login to your Semranko account to access keyword rank tracking, competitor analysis, and SEO reporting tools.',
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
      <LoginPage />
    </PublicLayout>
  )
}
