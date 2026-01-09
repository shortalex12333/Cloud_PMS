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
              "script-src 'self' 'unsafe-eval' 'unsafe-inline'",
              "style-src 'self' 'unsafe-inline'",
              "img-src 'self' data: blob: https://vzsohavtuotocgrfkfyd.supabase.co",
              "font-src 'self'",
              "object-src 'none'",
              "base-uri 'self'",
              "form-action 'self'",
              "frame-ancestors 'none'",
              "frame-src 'self' https://vzsohavtuotocgrfkfyd.supabase.co",
              "connect-src 'self' https://vzsohavtuotocgrfkfyd.supabase.co",
            ].join('; '),
          },
        ],
      },
    ];
  },
}

module.exports = nextConfig
