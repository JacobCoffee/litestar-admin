/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  trailingSlash: true,

  // Output directory for static export - relative to frontend/
  // This builds directly to src/litestar_admin/static/
  distDir: '../src/litestar_admin/static',

  // Base path for serving from Litestar static files
  basePath: '/admin',

  // Asset prefix ensures all assets use the correct base path
  assetPrefix: '/admin',

  // Image optimization settings (Next.js Image component)
  images: {
    unoptimized: true,
  },

  // Disable x-powered-by header for security
  poweredByHeader: false,

  // Production optimizations
  compiler: {
    // Remove console.log in production
    removeConsole: process.env.NODE_ENV === 'production',
  },

  // Generate source maps only in development
  productionBrowserSourceMaps: false,

  // Optimize bundle size
  experimental: {
    // Enable optimized package imports
    optimizePackageImports: ['@tanstack/react-query', 'clsx'],
  },
};

export default nextConfig;
