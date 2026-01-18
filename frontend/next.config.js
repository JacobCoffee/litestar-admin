/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  trailingSlash: true,
  images: {
    unoptimized: true,
  },
  // Base path for serving from Litestar static files
  basePath: '/admin',
  // Disable x-powered-by header
  poweredByHeader: false,
};

export default nextConfig;
