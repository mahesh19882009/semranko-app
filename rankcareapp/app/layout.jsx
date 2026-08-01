import './globals.css'
import { Inter } from 'next/font/google'
import { Providers } from './context/Providers'

const inter = Inter({
  subsets: ['latin'],
  weight: ['300', '400', '500', '600', '700'],
  display: 'swap',
  variable: '--font-sans',
})

export const metadata = {
  title: 'RankCare - SEO Rank Tracking',
  description: 'Track keyword rankings, monitor competitors, and grow your organic traffic.',
  keywords: 'SEO, keyword tracking, rank checking, competitor analysis, search engine optimization',
  openGraph: {
    title: 'RankCare - SEO Rank Tracking & Competitor Analysis',
    description: 'Track keyword rankings, monitor competitors, and grow your organic traffic.',
    type: 'website',
    url: 'https://rankcare.com',
    locale: 'en_US',
  },
  twitter: {
    card: 'summary',
    title: 'RankCare - SEO Rank Tracking & Competitor Analysis',
    description: 'Track keyword rankings, monitor competitors, and grow your organic traffic.',
  },
  icons: {
    icon: '/favicon.svg',
  },
}

export default function RootLayout({ children }) {
  return (
    <html lang="en" className={inter.variable} suppressHydrationWarning>
      <body suppressHydrationWarning className="bg-slate-50 text-slate-900 antialiased" style={{ fontFamily: 'var(--font-sans)' }}>
        <Providers>
          {children}
        </Providers>
      </body>
    </html>
  )
}
