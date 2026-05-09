/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // No `output: 'standalone'` here on purpose — it's for self-hosted/Docker
  // deploys. Vercel does its own server bundling via the Build Output API
  // and ignores .next/standalone, but you still pay the file-tracing cost.
  experimental: {
    typedRoutes: false,
  },
};

export default nextConfig;
