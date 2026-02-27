/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    return [
      {
        source: '/api/shorten',
        destination: `${apiUrl}/shorten`,
      },
      {
        source: '/api/urls',
        destination: `${apiUrl}/urls`,
      },
    ];
  },
  async headers() {
    return [
      {
        source: '/api/:path*',
        headers: [
          { key: 'Access-Control-Allow-Methods', value: 'GET,DELETE,POST,PUT' },
        ],
      },
    ];
  },
};

module.exports = nextConfig;
