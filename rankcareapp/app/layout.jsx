import './globals.css'
import { Inter } from 'next/font/google'
import { Providers } from './context/Providers'
import 'primereact/resources/themes/lara-light-indigo/theme.css'
import 'primereact/resources/primereact.css'
import 'primeicons/primeicons.css'

const inter = Inter({
  subsets: ['latin'],
  weight: ['300', '400', '500', '600', '700'],
  display: 'swap',
  variable: '--font-sans',
})

export const metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL || 'https://rankcare.com'),
  title: { default: 'RankCare | SEO rank tracking', template: '%s | RankCare' },
  description: 'Track keyword rankings, understand search visibility, and research SEO opportunities with RankCare.',
  openGraph: {
    title: 'RankCare | SEO rank tracking',
    description: 'Track keyword rankings, understand search visibility, and research SEO opportunities.',
    type: 'website',
    url: 'https://rankcare.com',
    locale: 'en_US',
  },
  twitter: {
    card: 'summary',
    title: 'RankCare | SEO rank tracking',
    description: 'Track keyword rankings, understand search visibility, and research SEO opportunities.',
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
