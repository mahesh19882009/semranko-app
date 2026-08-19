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
    const isDev = process.env.NODE_ENV === "development";

    const apiBase =
      process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:4000/api";

    let apiOrigin = null;

    try {
      apiOrigin = new URL(apiBase).origin;
    } catch {
      apiOrigin = null;
    }

    const scriptSrc = [
      "'self'",
      "'unsafe-inline'",
      ...(isDev ? ["'unsafe-eval'"] : []),
      "https://challenges.cloudflare.com",
      "https://checkout.razorpay.com",
    ].join(" ");

    const connectSrc = [
      "'self'",
      ...(apiOrigin ? [apiOrigin] : []),
      "https://challenges.cloudflare.com",
      "https://api.razorpay.com",
    ].join(" ");

    const csp = [
      "default-src 'self'",
      `script-src ${scriptSrc}`,
      "style-src 'self' 'unsafe-inline'",
      "img-src 'self' data: https:",
      `connect-src ${connectSrc}`,
      "frame-src https://challenges.cloudflare.com https://api.razorpay.com https://checkout.razorpay.com",
      "frame-ancestors 'none'",
      "base-uri 'self'",
      "form-action 'self'",
    ].join("; ");

    return [
      {
        source: "/(.*)",
        headers: [
          { key: "Content-Security-Policy", value: csp },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          {
            key: "Referrer-Policy",
            value: "strict-origin-when-cross-origin",
          },
          {
            key: "Permissions-Policy",
            value: "camera=(), microphone=(), geolocation=()",
          },
        ],
      },
    ];
  },
  async rewrites() {
    const apiBase =
      process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:4000/api";
    return [
      {
        source: "/api/:path*",
        destination: `${apiBase}/:path*`,
      },
    ];
  },
};

export default nextConfig;
