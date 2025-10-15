/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: false, // Disable strict mode to prevent double-rendering issues
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '**',
      },
    ],
  },
  // Optimize webpack for faster chunk loading
  webpack: (config, { dev, isServer }) => {
    if (dev && !isServer) {
      // Increase chunk loading timeout significantly in development
      config.output = {
        ...config.output,
        chunkLoadTimeout: 300000, // 5 minutes for slow systems
      };

      // Optimize chunk splitting to prevent large chunks
      config.optimization = {
        ...config.optimization,
        splitChunks: {
          ...config.optimization?.splitChunks,
          chunks: 'all',
          cacheGroups: {
            default: false,
            vendors: false,
            // Separate framework code
            framework: {
              name: 'framework',
              chunks: 'all',
              test: /[\\/]node_modules[\\/](react|react-dom|scheduler|next)[\\/]/,
              priority: 40,
              enforce: true,
            },
            // Clerk in its own chunk
            clerk: {
              name: 'clerk',
              chunks: 'all',
              test: /[\\/]node_modules[\\/]@clerk[\\/]/,
              priority: 30,
              enforce: true,
            },
            // Lucide icons
            icons: {
              name: 'icons',
              chunks: 'all',
              test: /[\\/]node_modules[\\/]lucide-react[\\/]/,
              priority: 20,
              enforce: true,
            },
            // Other vendor code
            lib: {
              test: /[\\/]node_modules[\\/]/,
              name: 'lib',
              priority: 10,
              minChunks: 1,
              reuseExistingChunk: true,
            },
          },
        },
      };
    }
    return config;
  },
  experimental: {
    optimizePackageImports: ['lucide-react', '@clerk/nextjs'],
  },
}

module.exports = nextConfig
