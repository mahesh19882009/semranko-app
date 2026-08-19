import RegisterPage from '@/src/views/RegisterPage'
import PublicLayout from '@/src/components/PublicLayout'

export const metadata = {
  title: 'Register - Semranko | Semranko',
  description: 'Create your Semranko account on the permanent Free plan and start tracking keyword rankings.',
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
      <RegisterPage />
    </PublicLayout>
  )
}
