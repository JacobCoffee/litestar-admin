/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  trailingSlash: true,

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
    // Remove React dev-only properties
    reactRemoveProperties: process.env.NODE_ENV === 'production',
  },

  // Generate source maps only in development
  productionBrowserSourceMaps: false,

  // Optimize bundle size
  experimental: {
    // Enable optimized package imports - tree-shake these packages
    optimizePackageImports: ['@tanstack/react-query', 'clsx'],
  },

  // Webpack optimizations for smaller bundle size
  webpack: (config, { dev, isServer }) => {
    // Production optimizations only
    if (!dev && !isServer) {
      // Enable module concatenation for smaller bundles
      config.optimization.concatenateModules = true;

      // Optimize chunk splitting for better caching
      config.optimization.splitChunks = {
        ...config.optimization.splitChunks,
        cacheGroups: {
          ...config.optimization.splitChunks?.cacheGroups,
          // Separate TanStack Query into its own chunk
          tanstack: {
            test: /[\\/]node_modules[\\/]@tanstack[\\/]/,
            name: 'tanstack',
            chunks: 'all',
            priority: 30,
          },
          // Separate React into its own chunk for better caching
          react: {
            test: /[\\/]node_modules[\\/](react|react-dom)[\\/]/,
            name: 'react',
            chunks: 'all',
            priority: 40,
          },
          // Common components chunk
          components: {
            test: /[\\/]src[\\/]components[\\/]ui[\\/]/,
            name: 'ui-components',
            chunks: 'all',
            minSize: 0,
            priority: 20,
          },
        },
      };
    }

    return config;
  },
};

export default nextConfig;
