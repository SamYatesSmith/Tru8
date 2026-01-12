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

# Build-time environment variables (public only - safe to expose)
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
ARG NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY
ARG NEXT_PUBLIC_STRIPE_PRICE_ID_PRO
ARG NEXT_PUBLIC_SUBSCRIPTIONS_ENABLED=false

ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=$NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
ENV NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=$NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY
ENV NEXT_PUBLIC_STRIPE_PRICE_ID_PRO=$NEXT_PUBLIC_STRIPE_PRICE_ID_PRO
ENV NEXT_PUBLIC_SUBSCRIPTIONS_ENABLED=$NEXT_PUBLIC_SUBSCRIPTIONS_ENABLED

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

# Copy built assets from standalone output
COPY --from=builder /app/web/public ./public
COPY --from=builder /app/web/.next/standalone ./
COPY --from=builder /app/web/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
