/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Server components by default; opt out where needed.
  experimental: {
    typedRoutes: false,
  },
};

export default nextConfig;
