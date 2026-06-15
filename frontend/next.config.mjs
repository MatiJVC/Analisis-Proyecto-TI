/** @type {import('next').NextConfig} */

const isDev = process.env.NODE_ENV === 'development'

function parseOrigin(envValue) {
  if (!envValue) return ''
  try {
    return new URL(envValue).origin
  } catch {
    return ''
  }
}

const nextConfig = {
  output: 'standalone',
  images: {
    unoptimized: true,
  },
  async headers() {
    const connectSrc = [
      "'self'",
      parseOrigin(process.env.NEXT_PUBLIC_API_URL),
      parseOrigin(process.env.NEXT_PUBLIC_KEYCLOAK_URL),
    ].filter(Boolean).join(' ')

    // 'unsafe-eval' is required by Next.js HMR and source maps in dev only;
    // the standalone production build does not need it.
    const scriptSrc = isDev
      ? "script-src 'self' 'unsafe-inline' 'unsafe-eval'"
      : "script-src 'self' 'unsafe-inline'"

    const csp = [
      "default-src 'self'",
      scriptSrc,
      // Tailwind emits inline styles via the PostCSS build step
      "style-src 'self' 'unsafe-inline'",
      "img-src 'self' data: blob:",
      "font-src 'self'",
      `connect-src ${connectSrc}`,
      "frame-ancestors 'none'",
      "object-src 'none'",
      "base-uri 'self'",
    ].join('; ')

    const responseHeaders = [
      { key: 'X-Content-Type-Options',  value: 'nosniff' },
      { key: 'X-Frame-Options',         value: 'DENY' },
      { key: 'Referrer-Policy',         value: 'strict-origin-when-cross-origin' },
      { key: 'Permissions-Policy',      value: 'camera=(), microphone=(), geolocation=()' },
      { key: 'Content-Security-Policy', value: csp },
    ]

    // HSTS only makes sense over HTTPS; skip it in local dev to avoid
    // accidentally pinning localhost as HTTPS-only.
    if (!isDev) {
      responseHeaders.push({
        key: 'Strict-Transport-Security',
        value: 'max-age=63072000; includeSubDomains',
      })
    }

    return [{ source: '/(.*)', headers: responseHeaders }]
  },
}

export default nextConfig
