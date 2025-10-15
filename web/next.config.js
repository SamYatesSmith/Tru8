/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '**',
      },
    ],
  },
  // Optimize chunk loading to prevent timeouts
  webpack: (config, { dev, isServer }) => {
    if (dev && !isServer) {
      // Increase chunk loading timeout in development
      config.output = {
        ...config.output,
        chunkLoadTimeout: 60000, // Increase from default 120000ms to prevent timeouts
      };
    }
    return config;
  },
  // Reduce strict mode re-renders that can cause chunk loading issues
  experimental: {
    optimizePackageImports: ['lucide-react'],
  },
}

module.exports = nextConfig
