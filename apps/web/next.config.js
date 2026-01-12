/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'Content-Security-Policy',
            value: [
              "default-src 'self'",
              "script-src 'self' 'unsafe-eval' 'unsafe-inline' https://vercel.live",
              "style-src 'self' 'unsafe-inline'",
              "img-src 'self' data: blob: https://vzsohavtuotocgrfkfyd.supabase.co",
              "font-src 'self' data:",
              "object-src 'none'",
              "base-uri 'self'",
              "form-action 'self'",
              "frame-ancestors 'none'",
              "frame-src 'self' blob: https://vzsohavtuotocgrfkfyd.supabase.co",
              "media-src 'self' blob: https://vzsohavtuotocgrfkfyd.supabase.co",
              "worker-src 'self' blob:",
              "connect-src 'self' https://vzsohavtuotocgrfkfyd.supabase.co https://pipeline-core.int.celeste7.ai https://api.celeste7.ai",
            ].join('; '),
          },
        ],
      },
    ];
  },
}

module.exports = nextConfig
