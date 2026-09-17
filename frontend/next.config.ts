import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'export',
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/:path*',
      },
    ];
  },

  /* config options here */
};

export default nextConfig;
