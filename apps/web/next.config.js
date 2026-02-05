/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  async headers() {
    // Local development CSP: allow localhost Supabase and API
    const isDev = process.env.NODE_ENV === 'development';
    const localDevUrls = isDev
      ? 'http://127.0.0.1:54321 http://localhost:54321 http://127.0.0.1:8000 http://localhost:8000 '
      : '';

    return [
      {
        // CSP and security headers (CORS handled by middleware.ts)
        source: '/(.*)',
        headers: [
          {
            key: 'Content-Security-Policy',
            value: [
              "default-src 'self'",
              "script-src 'self' 'unsafe-eval' 'unsafe-inline' https://vercel.live",
              "style-src 'self' 'unsafe-inline'",
              "img-src 'self' data: blob: https://qvzmkaamzaqxpzbewjxe.supabase.co https://vzsohavtuotocgrfkfyd.supabase.co",
              "font-src 'self' data:",
              "object-src 'none'",
              "base-uri 'self'",
              "form-action 'self' https://app.celeste7.ai",
              "frame-ancestors 'none'",
              "frame-src 'self' blob: https://qvzmkaamzaqxpzbewjxe.supabase.co https://vzsohavtuotocgrfkfyd.supabase.co",
              "media-src 'self' blob: https://qvzmkaamzaqxpzbewjxe.supabase.co https://vzsohavtuotocgrfkfyd.supabase.co",
              "worker-src 'self' blob:",
              `connect-src 'self' ${localDevUrls}https://qvzmkaamzaqxpzbewjxe.supabase.co https://vzsohavtuotocgrfkfyd.supabase.co https://pipeline-core.int.celeste7.ai https://api.celeste7.ai https://app.celeste7.ai https://auth.celeste7.ai https://handover-export.onrender.com`,
            ].join('; '),
          },
        ],
      },
    ];
  },
}

module.exports = nextConfig
