import HomePage from '@/src/views/HomePage'
import PublicLayout from '@/src/components/PublicLayout'

export const metadata = {
  title: 'SEO rank tracking',
  description: 'Track keyword rankings, understand search visibility, and research SEO opportunities with Semranko.',
  alternates: { canonical: '/' },
  openGraph: {
    title: 'Semranko | SEO rank tracking',
    description: 'Track keyword rankings, understand search visibility, and research SEO opportunities.',
    type: 'website',
    url: 'https://semranko.com',
  },
}

export default function Page() {
  const structuredData = {
    '@context': 'https://schema.org', '@type': 'SoftwareApplication', name: 'Semranko',
    applicationCategory: 'BusinessApplication', operatingSystem: 'Web',
    description: 'SEO rank tracking, keyword metrics, research, and reporting.',
  };
  return (
    <PublicLayout>
      <HomePage />
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(structuredData) }} />
    </PublicLayout>
  )
}
