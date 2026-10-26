import type { NextConfig } from "next";
import { BACKEND_URL } from "./src/lib/backend";

const securityHeaders = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
];

const nextConfig: NextConfig = {
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  // Le navigateur n'appelle que le frontend : /api/v1/* est relayé vers FastAPI (même origine,
  // cookies httpOnly), comme les images stockées en local (/media) avant le passage à R2.
  async rewrites() {
    return [
      { source: "/api/v1/:path*", destination: `${BACKEND_URL}/api/v1/:path*` },
      { source: "/media/:path*", destination: `${BACKEND_URL}/media/:path*` },
    ];
  },
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
};

export default nextConfig;
