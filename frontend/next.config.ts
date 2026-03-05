import type { NextConfig } from "next";

const GATEWAY_URL =
  process.env.NEXT_PUBLIC_GATEWAY_URL || "http://localhost:30866";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${GATEWAY_URL}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
