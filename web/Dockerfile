# Build stage - runs from project root to access shared/ and web/
FROM node:20-alpine AS builder

WORKDIR /app

# Copy workspace config and package files
COPY package.json package-lock.json* ./
COPY shared/package.json ./shared/
COPY web/package.json ./web/

# Install dependencies using workspaces
RUN npm ci --workspace=web --workspace=shared --include-workspace-root

# Copy shared types/constants
COPY shared/ ./shared/

# Copy web source
COPY web/ ./web/

# Build-time environment variables (public only - safe to expose).
# NEXT_PUBLIC_* values are inlined into the client bundle at build
# time; without an ARG line here, Railway's runtime env var is
# invisible to `npm run build` and the inlined value is `undefined`.
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
ARG NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY
ARG NEXT_PUBLIC_STRIPE_PRICE_ID_PRO
ARG NEXT_PUBLIC_STRIPE_PRICE_ID_DEVELOPER
ARG NEXT_PUBLIC_SUBSCRIPTIONS_ENABLED=false
ARG NEXT_PUBLIC_SENTRY_DSN
ARG NEXT_PUBLIC_COOKIEYES_ID
ARG NEXT_PUBLIC_POSTHOG_KEY
ARG NEXT_PUBLIC_POSTHOG_HOST

ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=$NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
ENV NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=$NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY
ENV NEXT_PUBLIC_STRIPE_PRICE_ID_PRO=$NEXT_PUBLIC_STRIPE_PRICE_ID_PRO
ENV NEXT_PUBLIC_STRIPE_PRICE_ID_DEVELOPER=$NEXT_PUBLIC_STRIPE_PRICE_ID_DEVELOPER
ENV NEXT_PUBLIC_SUBSCRIPTIONS_ENABLED=$NEXT_PUBLIC_SUBSCRIPTIONS_ENABLED
ENV NEXT_PUBLIC_SENTRY_DSN=$NEXT_PUBLIC_SENTRY_DSN
ENV NEXT_PUBLIC_COOKIEYES_ID=$NEXT_PUBLIC_COOKIEYES_ID
ENV NEXT_PUBLIC_POSTHOG_KEY=$NEXT_PUBLIC_POSTHOG_KEY
ENV NEXT_PUBLIC_POSTHOG_HOST=$NEXT_PUBLIC_POSTHOG_HOST

# Build the web app
WORKDIR /app/web
RUN npm run build

# Production stage
FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production

# Create non-root user for security
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Copy built assets from standalone output.
# outputFileTracingRoot=<repo root> makes the standalone bundle nest the app
# under web/ (server.js at standalone/web/server.js) with hoisted node_modules
# at standalone root. public/ and static/ must therefore land under web/ so the
# nested server resolves them. CMD runs web/server.js.
COPY --from=builder /app/web/.next/standalone ./
COPY --from=builder /app/web/public ./web/public
COPY --from=builder /app/web/.next/static ./web/.next/static

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "web/server.js"]
