const path = require("path");

// Sentry is optional - only load if installed and configured
let withSentryConfig;
try {
  withSentryConfig = require("@sentry/nextjs").withSentryConfig;
} catch (e) {
  // @sentry/nextjs not installed - Sentry disabled
}

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'standalone',
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'i.ytimg.com',
      },
      {
        protocol: 'https',
        hostname: 'img.youtube.com',
      },
      {
        protocol: 'https',
        hostname: 'img.clerk.com',
      },
    ],
  },
  experimental: {
    optimizePackageImports: ['lucide-react', '@clerk/nextjs'],
    // Monorepo: deps hoist to the repo root node_modules. Without this, the
    // standalone tracer infers the root as web/ and fails to bundle the
    // hoisted `next` package, crashing the container at runtime with
    // "Cannot find module 'next'". Pointing the trace root at the repo root
    // nests output under standalone/web/ and bundles node_modules correctly.
    // (Top-level in Next 15; under `experimental` in 14.2.) Dockerfile
    // COPY/CMD paths are aligned to this nested layout.
    outputFileTracingRoot: path.join(__dirname, '..'),
  },
  async redirects() {
    // SEO canonicalisation: the apex (trueight.com) and www both resolve on
    // Railway with no redirect between them, so Google indexes them as two
    // separate sites and splits ranking signals. Force the apex to 308-redirect
    // to www — the canonical host used by sitemap.ts, robots.ts and metadataBase.
    return [
      {
        source: '/:path*',
        has: [{ type: 'host', value: 'trueight.com' }],
        destination: 'https://www.trueight.com/:path*',
        permanent: true,
      },
    ];
  },
  async headers() {
    // F-SEC-03: CSP whitelists Clerk, Stripe, Sentry (de.sentry.io),
    // cdn.jsdelivr.net (Swagger UI), and PostHog EU (eu.i.posthog.com +
    // eu-assets.i.posthog.com — analytics ingestion + lazy-loaded helpers;
    // without these connect-src entries the browser silently drops every
    // PostHog event). 'unsafe-inline'/'unsafe-eval' kept on
    // script-src because Next.js App Router relies on them; nonce-based CSP
    // is post-launch work bundled with the Next 16 migration.
    const csp = [
      "default-src 'self'",
      "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://*.clerk.accounts.dev https://clerk.trueight.com https://js.stripe.com https://browser.sentry-cdn.com https://*.sentry.io https://*.ingest.de.sentry.io https://cdn.jsdelivr.net https://eu-assets.i.posthog.com",
      "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",
      "img-src 'self' data: blob: https:",
      "font-src 'self' data:",
      "connect-src 'self' https://api.trueight.com https://*.clerk.accounts.dev https://clerk.trueight.com https://api.stripe.com https://*.sentry.io https://*.ingest.de.sentry.io https://eu.i.posthog.com https://eu-assets.i.posthog.com",
      "frame-src 'self' https://js.stripe.com https://hooks.stripe.com https://*.clerk.accounts.dev https://challenges.cloudflare.com",
      "worker-src 'self' blob:",
      "frame-ancestors 'none'",
      "base-uri 'self'",
      "form-action 'self'",
      "object-src 'none'",
      "upgrade-insecure-requests",
    ].join('; ');

    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'Content-Security-Policy',
            value: csp,
          },
          {
            key: 'Strict-Transport-Security',
            value: 'max-age=63072000; includeSubDomains; preload',
          },
          {
            key: 'X-Frame-Options',
            value: 'DENY',
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'Referrer-Policy',
            value: 'strict-origin-when-cross-origin',
          },
          {
            key: 'Permissions-Policy',
            value: 'camera=(), microphone=(), geolocation=()',
          },
          {
            key: 'X-DNS-Prefetch-Control',
            value: 'on',
          },
          {
            key: 'Cross-Origin-Opener-Policy',
            value: 'same-origin',
          },
        ],
      },
    ];
  },
}

// Sentry configuration options
const sentryWebpackPluginOptions = {
  // For all available options, see:
  // https://github.com/getsentry/sentry-webpack-plugin#options

  org: process.env.SENTRY_ORG,
  project: process.env.SENTRY_PROJECT,

  // Only print logs for uploading source maps in CI
  silent: !process.env.CI,

  // For all available options, see:
  // https://docs.sentry.io/platforms/javascript/guides/nextjs/manual-setup/

  // Upload a larger set of source maps for prettier stack traces (increases build time)
  widenClientFileUpload: true,

  // Automatically annotate React components to show their full name in breadcrumbs and session replay
  reactComponentAnnotation: {
    enabled: true,
  },

  // Hides source maps from generated client bundles
  hideSourceMaps: true,

  // Automatically tree-shake Sentry logger statements to reduce bundle size
  disableLogger: true,
};

// Only wrap with Sentry if installed and DSN is configured
module.exports = (withSentryConfig && process.env.NEXT_PUBLIC_SENTRY_DSN)
  ? withSentryConfig(nextConfig, sentryWebpackPluginOptions)
  : nextConfig;
