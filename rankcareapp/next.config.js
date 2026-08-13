/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  reactCompiler: false,
  trailingSlash: false,
  turbopack: {
    root: process.cwd(),
  },
  images: {
    unoptimized: true,
  },
  async headers() {
    const csp = [
      "default-src 'self'",
      "script-src 'self' 'unsafe-inline' https://challenges.cloudflare.com https://checkout.razorpay.com",
      "style-src 'self' 'unsafe-inline'",
      "img-src 'self' data: https:",
      "connect-src 'self' https://challenges.cloudflare.com https://api.razorpay.com",
      "frame-src https://challenges.cloudflare.com https://api.razorpay.com https://checkout.razorpay.com",
      "frame-ancestors 'none'",
      "base-uri 'self'",
      "form-action 'self'",
    ].join('; ')
    return [{
      source: '/(.*)',
      headers: [
        { key: 'Content-Security-Policy', value: csp },
        { key: 'X-Content-Type-Options', value: 'nosniff' },
        { key: 'X-Frame-Options', value: 'DENY' },
        { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
        { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=()' },
      ],
    }]
  },
  async rewrites() {
    const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:4000/api'
    return [
      {
        source: '/api/:path*',
        destination: `${apiBase}/:path*`,
      },
    ]
  },
}

export default nextConfig
